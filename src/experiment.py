"""Bounded engineering SFT: exact response loss, audited exposure, raw outputs.

Invoke through scripts/run_bounded.py. No final-test access and no packing.
"""
from __future__ import annotations
import argparse
from collections import Counter
import datetime
import importlib.metadata
import json
import os
from pathlib import Path
import random
import subprocess
import time

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from .countdown_smoke import render_trace, verify_expression
from .evaluation import score_text, summarize
from .sft_data import (prefix, read_jsonl, encode_row, collate, update_schedule,
                       budget_report, shifted_loss_sum, sha256_file)


def dump(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False)+'\n')


def rows_from_problems(problems):
    rows = []
    for problem in problems:
        path = problem['paths'][0]
        row = {k: problem[k] for k in ['problem_id', 'prompt', 'numbers', 'target']}
        row.update(path_id=path['path_id'], structure_id=path['structure_id'],
                   response=render_trace(path['program']), expression=path['expression'])
        if not verify_expression(row['expression'], row['numbers'], row['target']):
            raise ValueError('Invalid reference program')
        rows.append(row)
    return rows


def reference_nll(model, encoded, tokenizer, microbatch):
    model.eval()
    total, count = 0., 0
    with torch.no_grad(), torch.autocast('cuda', dtype=torch.bfloat16):
        for start in range(0, len(encoded), microbatch):
            rows = encoded[start:start+microbatch]
            batch = {k: v.cuda() for k, v in collate(rows, tokenizer.pad_token_id).items()}
            out = model(input_ids=batch['input_ids'], attention_mask=batch['attention_mask'], use_cache=False)
            total += shifted_loss_sum(out.logits, batch['labels']).item()
            count += sum(r['n_supervised'] for r in rows)
    return total/count


def generate(model, tokenizer, rows, config, samples=1, sample=False):
    model.eval()
    tokenizer.padding_side = 'left'
    predictions = []
    torch.manual_seed(config['seed'])
    started = time.perf_counter()
    with torch.no_grad(), torch.autocast('cuda', dtype=torch.bfloat16):
        for start in range(0, len(rows), config['eval_batch_size']):
            part = rows[start:start+config['eval_batch_size']]
            inputs = tokenizer([prefix(r['prompt']) for r in part], padding=True,
                               add_special_tokens=False, return_tensors='pt').to('cuda')
            kwargs = {'max_new_tokens': config['max_new_tokens'], 'do_sample': sample,
                      'num_return_sequences': samples, 'pad_token_id': tokenizer.pad_token_id,
                      'eos_token_id': tokenizer.eos_token_id, 'use_cache': True}
            if sample:
                kwargs.update(temperature=config['temperature'], top_p=config['top_p'])
            generated = model.generate(**inputs, **kwargs)
            for i, tokens in enumerate(generated[:, inputs['input_ids'].shape[1]:].tolist()):
                row = part[i//samples]
                eos = tokenizer.eos_token_id in tokens
                if eos:
                    tokens = tokens[:tokens.index(tokenizer.eos_token_id)+1]
                text = tokenizer.decode(tokens, skip_special_tokens=True)
                predictions.append({'problem_id': row['problem_id'], 'sample_index': i % samples,
                                    'prompt': row['prompt'], 'numbers': row['numbers'], 'target': row['target'],
                                    'text': text, 'output_tokens': len(tokens), 'eos': eos,
                                    'truncated': not eos and len(tokens) >= config['max_new_tokens'],
                                    'reference_exact_match': text.strip() == row['response'].strip(),
                                    **score_text(text, row['numbers'], row['target'])})
    elapsed = time.perf_counter()-started
    stats = summarize(predictions, config['sampled_ks'] if sample else ())
    stats.update(elapsed_seconds=elapsed,
                 aggregate_output_tokens_per_second=sum(p['output_tokens'] for p in predictions)/elapsed,
                 decoding='sampled' if sample else 'greedy')
    return predictions, stats


def save_predictions(path, predictions):
    with Path(path).open('x') as f:
        for item in predictions:
            f.write(json.dumps(item, ensure_ascii=False)+'\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    cfg = json.loads(Path(args.config).read_text())
    out = Path(args.out)
    if os.environ.get('CS294_BOUNDED_RUN_ID') != out.name or out.parent != Path('runs'):
        raise RuntimeError('Use scripts/run_bounded.py with matching runs/<run-id> output')
    out.mkdir(parents=True, exist_ok=True)
    if (out/'run_manifest.json').exists():
        raise FileExistsError('Run already exists')
    if cfg['mode'] not in ['engineering_overfit', 'memory_profile']:
        raise ValueError('Scientific comparisons require a reviewed protocol implementation')
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA required for this entry point')
    if not cfg['steps'] > 0 or cfg['batch_size'] % cfg['microbatch_size']:
        raise ValueError('Invalid steps or microbatch accumulation')
    if subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],text=True).strip():
        raise RuntimeError('Commit code before model execution')
    # A clean index alone does not prove newly added source/config files are committed.
    source_files = [str(p) for directory in ('src', 'scripts') for p in Path(directory).glob('*.py')]
    subprocess.run(['git', 'ls-files', '--error-unmatch', *source_files,
                    args.config, 'configs/models.lock.json'], check=True, stdout=subprocess.DEVNULL)
    lock = json.loads(Path('configs/models.lock.json').read_text())[cfg['model_role']]
    if len(lock['revision']) != 40 or lock['tokenizer_revision'] != lock['revision']:
        raise ValueError('Model/tokenizer revisions must be exact and equal')
    data_dir = Path(cfg['data_dir'])
    # Final tests are deliberately not opened by this program.
    train_problems = read_jsonl(data_dir/'train_pool.jsonl')[:cfg['train_examples']]
    dev_problems = read_jsonl(data_dir/'dev.jsonl')[:cfg['dev_examples']]
    train_groups = {tuple(sorted(p['numbers'])) for p in train_problems}
    if train_groups & {tuple(sorted(p['numbers'])) for p in dev_problems}:
        raise ValueError('Train/dev number-group leakage')
    train_rows, dev_rows = rows_from_problems(train_problems), rows_from_problems(dev_problems)
    if len(train_rows) != cfg['train_examples'] or len(dev_rows) != cfg['dev_examples']:
        raise ValueError('Insufficient data')
    tokenizer = AutoTokenizer.from_pretrained(lock['repo_id'], revision=lock['tokenizer_revision'],
                                             use_fast=True, local_files_only=True)
    tokenizer.pad_token = tokenizer.eos_token
    encoded = [encode_row(r, tokenizer, cfg['max_length']) for r in train_rows]
    dev_encoded = [encode_row(r, tokenizer, cfg['max_length']) for r in dev_rows]
    schedule = update_schedule(len(encoded), cfg['steps'], cfg['batch_size'], cfg['seed'])
    budget = budget_report(encoded, schedule, cfg['microbatch_size'])
    budget.update(model=lock, data_sha256={name: sha256_file(data_dir/name)
                                         for name in ['train_pool.jsonl', 'dev.jsonl']},
                  max_sequence_tokens=max(r['n_processed'] for r in encoded),
                  scope='engineering-only, one reference path per problem')
    dump(out/'budget_report.json', budget)  # Written BEFORE loading/training the model.
    manifest = {'config': cfg, 'model': lock, 'git_commit': subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
                'python': importlib.metadata.version('pip'), 'torch': torch.__version__,
                'transformers': importlib.metadata.version('transformers'), 'cuda': torch.version.cuda,
                'gpu': torch.cuda.get_device_name(0), 'status': 'started',
                'started_at': datetime.datetime.now(datetime.timezone.utc).isoformat()}
    import platform
    manifest['python'] = platform.python_version()
    dump(out/'run_manifest.json', manifest)
    random.seed(cfg['seed'])
    torch.manual_seed(cfg['seed'])
    torch.set_num_threads(8)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    model = None
    try:
        model = AutoModelForCausalLM.from_pretrained(lock['repo_id'], revision=lock['revision'],
                    dtype=torch.float32, attn_implementation='sdpa', local_files_only=True).cuda()
        model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={'use_reentrant': False})
        model.config.use_cache = False
        manifest['parameter_count'] = sum(p.numel() for p in model.parameters())
        dump(out/'run_manifest.json', manifest)
        optimizer = torch.optim.AdamW(model.parameters(), lr=cfg['learning_rate'],
                                     weight_decay=cfg['weight_decay'], foreach=False)
        baseline = {}
        if cfg['mode'] == 'engineering_overfit':
            for name, rows in [('train', train_rows), ('dev', dev_rows)]:
                predictions, stats = generate(model, tokenizer, rows, cfg)
                save_predictions(out/f'base_{name}_greedy.jsonl', predictions)
                baseline[name] = stats
            baseline['train_nll'] = reference_nll(model, encoded, tokenizer, cfg['microbatch_size'])
            baseline['dev_nll'] = reference_nll(model, dev_encoded, tokenizer, cfg['microbatch_size'])
            if cfg.get('baseline_sampled_dev', False):
                predictions, stats = generate(model, tokenizer, dev_rows, cfg,
                                              samples=cfg['samples_per_problem'], sample=True)
                save_predictions(out/'base_dev_sampled.jsonl', predictions)
                baseline['dev_sampled'] = stats
            dump(out/'baseline_metrics.json', baseline)
        history, checkpoint_metrics = [], []
        torch.cuda.reset_peak_memory_stats()
        with (out/'train_history.jsonl').open('x') as log:
            for step, indices in enumerate(schedule, 1):
                model.train()
                optimizer.zero_grad(set_to_none=True)
                torch.cuda.synchronize()
                start = time.perf_counter()
                denominator = sum(encoded[i]['n_supervised'] for i in indices)
                total_loss = 0.
                for j in range(0, len(indices), cfg['microbatch_size']):
                    rows = [encoded[i] for i in indices[j:j+cfg['microbatch_size']]]
                    batch = {k: v.cuda() for k, v in collate(rows, tokenizer.pad_token_id).items()}
                    with torch.autocast('cuda', dtype=torch.bfloat16):
                        outputs = model(input_ids=batch['input_ids'], attention_mask=batch['attention_mask'], use_cache=False)
                        loss_sum = shifted_loss_sum(outputs.logits, batch['labels'])
                        loss = loss_sum/denominator
                    loss.backward()
                    total_loss += loss_sum.detach().item()
                    del loss, loss_sum, outputs
                grad_norm = torch.nn.utils.clip_grad_norm_(model.parameters(), cfg['grad_clip'])
                if not torch.isfinite(grad_norm):
                    raise FloatingPointError('Nonfinite gradient')
                optimizer.step()
                torch.cuda.synchronize()
                record = {'step': step, 'response_nll': total_loss/denominator,
                          'supervised_tokens': denominator,
                          'processed_tokens': sum(encoded[i]['n_processed'] for i in indices),
                          'seconds': time.perf_counter()-start,
                          'grad_norm': grad_norm.item(),
                          'peak_allocated_mib': torch.cuda.max_memory_allocated()/1024**2,
                          'peak_reserved_mib': torch.cuda.max_memory_reserved()/1024**2}
                history.append(record)
                log.write(json.dumps(record)+'\n')
                log.flush()
                if step % 20 == 0 or step == 1:
                    print(json.dumps(record), flush=True)
                if cfg['mode'] == 'engineering_overfit' and (step % cfg['eval_every'] == 0 or step == cfg['steps']):
                    predictions, stats = generate(model, tokenizer, train_rows, cfg)
                    save_predictions(out/f'train_step_{step:04d}_greedy.jsonl', predictions)
                    stats.update(step=step, train_nll=reference_nll(model, encoded, tokenizer, cfg['microbatch_size']))
                    checkpoint_metrics.append(stats)
                    dump(out/'checkpoint_metrics.json', checkpoint_metrics)
                    print(json.dumps({'checkpoint': stats}), flush=True)
                    if step >= cfg['profile_warmup']+cfg['profile_updates'] and stats['accuracy_macro'] >= .95 and stats['train_nll'] < .2:
                        break
        profile = history[cfg['profile_warmup']:cfg['profile_warmup']+cfg['profile_updates']]
        elapsed = sum(h['seconds'] for h in profile)
        measured = {'profile_updates': len(profile), 'warmup_excluded': cfg['profile_warmup'],
                    'profile_complete': len(profile) == cfg['profile_updates'],
                    'supervised_tokens_per_second': sum(h['supervised_tokens'] for h in profile)/elapsed if elapsed else None,
                    'processed_tokens_per_second': sum(h['processed_tokens'] for h in profile)/elapsed if elapsed else None,
                    'peak_allocated_mib': max(h['peak_allocated_mib'] for h in history),
                    'peak_reserved_mib': max(h['peak_reserved_mib'] for h in history)}
        dump(out/'throughput.json', measured)
        dump(out/'actual_budget.json', budget_report(encoded, schedule[:len(history)], cfg['microbatch_size']))
        results = {'baseline': baseline, 'throughput': measured, 'steps': len(history)}
        if cfg['mode'] == 'engineering_overfit':
            for name, rows in [('train', train_rows), ('dev', dev_rows)]:
                predictions, stats = generate(model, tokenizer, rows, cfg)
                save_predictions(out/f'final_{name}_greedy.jsonl', predictions)
                results[name] = stats
            predictions, stats = generate(model, tokenizer, dev_rows, cfg, samples=cfg['samples_per_problem'], sample=True)
            save_predictions(out/'final_dev_sampled.jsonl', predictions)
            results['dev_sampled'] = stats
            results['final_train_nll'] = reference_nll(model, encoded, tokenizer, cfg['microbatch_size'])
            results['final_dev_nll'] = reference_nll(model, dev_encoded, tokenizer, cfg['microbatch_size'])
            results['overfit_passed'] = results['train']['accuracy_macro'] >= .95 and results['final_train_nll'] < .2
            # Weight artifact is optional, separate from reproducible public result records.
            checkpoint = out/'checkpoint_final'
            model.save_pretrained(checkpoint, safe_serialization=True)
            tokenizer.save_pretrained(checkpoint)
            dump(out/'checkpoint_manifest.json', {'kind':'model_weights_only_not_optimizer_resume',
                 'files': {p.name: sha256_file(p) for p in checkpoint.iterdir() if p.is_file()}})
        dump(out/'metrics.json', results)
        manifest['status'] = 'completed'
        manifest['steps_completed'] = len(history)
    except Exception as exc:
        manifest.update(status='failed', exception_type=type(exc).__name__, exception=str(exc))
        if torch.cuda.is_initialized():
            manifest['peak_allocated_mib'] = torch.cuda.max_memory_allocated()/1024**2
        raise
    finally:
        manifest['finished_at'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        dump(out/'run_manifest.json', manifest)


if __name__ == '__main__':
    main()

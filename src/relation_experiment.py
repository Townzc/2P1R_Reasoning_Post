"""One bounded relation engineering trajectory; no arithmetic scoring or automatic retry."""
from __future__ import annotations

import argparse
from contextlib import nullcontext
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import random
import signal
import time

from src.relation_engineering import (CONFIG, RELEASE, dump, provenance, load_frozen,
                                       score_completion, summarize)
from src.sft_data import collate, shifted_loss_sum, prefix, sha256_file, budget_report


def accumulate_gradients(model, rows, pad_id, microbatch, device):
    """Token-normalized update loss; CPU is supported solely for small unit fixtures."""
    import torch
    denominator = sum(r['n_supervised'] for r in rows)
    if denominator <= 0 or microbatch <= 0:
        raise ValueError('Positive supervision and microbatch required')
    total = 0.0
    for start in range(0, len(rows), microbatch):
        batch = {k: v.to(device) for k, v in collate(rows[start:start+microbatch], pad_id).items()}
        context = torch.autocast('cuda', dtype=torch.bfloat16) if str(device).startswith('cuda') else nullcontext()
        with context:
            output = model(input_ids=batch['input_ids'], attention_mask=batch['attention_mask'], use_cache=False)
            loss_sum = shifted_loss_sum(output.logits, batch['labels'])
        if not torch.isfinite(loss_sum):
            raise FloatingPointError('Nonfinite response loss')
        (loss_sum/denominator).backward()
        total += loss_sum.detach().item()
        del output, loss_sum, batch
    return total/denominator


def profile(history, cfg):
    selected = history[cfg['profile_warmup']:cfg['profile_warmup']+cfg['profile_updates']]
    seconds = sum(r['seconds'] for r in selected)
    return {'profile_updates': len(selected), 'warmup_excluded': cfg['profile_warmup'],
            'profile_complete': len(selected) == cfg['profile_updates'],
            'profile_step_seconds': seconds,
            'supervised_tokens_per_second': sum(r['supervised_tokens'] for r in selected)/seconds if seconds else None,
            'processed_tokens_per_second': sum(r['processed_tokens'] for r in selected)/seconds if seconds else None,
            'peak_allocated_mib': max((r['peak_allocated_mib'] for r in history), default=0),
            'peak_reserved_mib': max((r['peak_reserved_mib'] for r in history), default=0)}


def engineering_gate(cfg, steps, throughput, train_stats, nll):
    return {'passed': bool(steps == cfg['steps'] and throughput['profile_complete'] and
                         train_stats['n'] == cfg['train_count'] and
                         train_stats['complete_correct'] >= cfg['overfit_required_correct'] and
                         train_stats['truncated'] == 0 and math.isfinite(nll) and nll < cfg['overfit_max_nll']),
            'scope': 'engineering_feasibility_only_no_scientific_treatment_effect'}


def generate(model, tokenizer, rows, cfg, output_path):
    import torch
    from transformers import GenerationConfig
    model.eval()
    predictions = []
    settings = GenerationConfig(do_sample=False, num_beams=1, max_new_tokens=cfg['max_new_tokens'],
                                eos_token_id=tokenizer.eos_token_id, pad_token_id=tokenizer.pad_token_id,
                                use_cache=True)
    with Path(output_path).open('x') as f:
        for start in range(0, len(rows), cfg['eval_batch_size']):
            group = rows[start:start+cfg['eval_batch_size']]
            ids = [tokenizer(prefix(r['prompt']), add_special_tokens=False)['input_ids'] for r in group]
            width = max(map(len, ids))
            if width+cfg['max_new_tokens'] > cfg['max_length']:
                raise ValueError('Generation context cap would be exceeded')
            inputs = torch.tensor([[tokenizer.pad_token_id]*(width-len(x))+x for x in ids], device='cuda')
            masks = torch.tensor([[0]*(width-len(x))+[1]*len(x) for x in ids], device='cuda')
            with torch.inference_mode(), torch.autocast('cuda', dtype=torch.bfloat16):
                output = model.generate(input_ids=inputs, attention_mask=masks, generation_config=settings)
            for row, generated in zip(group, output[:, width:].tolist()):
                eos = tokenizer.eos_token_id in generated
                tokens = generated[:generated.index(tokenizer.eos_token_id)+1] if eos else generated
                content = tokens[:-1] if eos else tokens
                raw = tokenizer.decode(content, skip_special_tokens=False, clean_up_tokenization_spaces=False)
                truncated = not eos and len(tokens) == cfg['max_new_tokens']
                record = {**row, 'text': raw, 'generated_ids': tokens, 'generated_tokens': len(tokens),
                          'score': score_completion(row, raw, eos, truncated)}
                predictions.append(record)
                f.write(json.dumps(record, allow_nan=False)+'\n'); f.flush()
            del inputs, masks, output
    return predictions


def reference_nll(model, encoded, tokenizer, microbatch):
    import torch
    model.eval()
    total, count = 0.0, 0
    with torch.inference_mode(), torch.autocast('cuda', dtype=torch.bfloat16):
        for start in range(0, len(encoded), microbatch):
            rows = encoded[start:start+microbatch]
            batch = {k: v.cuda() for k, v in collate(rows, tokenizer.pad_token_id).items()}
            output = model(input_ids=batch['input_ids'], attention_mask=batch['attention_mask'], use_cache=False)
            loss = shifted_loss_sum(output.logits, batch['labels']).item()
            if not math.isfinite(loss):
                raise FloatingPointError('Nonfinite reference loss')
            total += loss; count += sum(r['n_supervised'] for r in rows)
            del batch, output
    return {'response_loss_sum': total, 'supervised_tokens': count, 'reference_count': len(encoded),
            'nll': total/count}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--snapshot', required=True)
    p.add_argument('--preflight', required=True)
    a = p.parse_args()
    cfg = json.loads(CONFIG.read_text())
    out = Path('runs')/cfg['run_id']
    if os.environ.get('CS294_BOUNDED_RUN_ID') != cfg['run_id'] or not out.is_dir():
        raise ValueError('Mandatory bounded wrapper and unique run directory required')
    if (out/'run_manifest.json').exists():
        raise FileExistsError('Run manifest already exists')
    source = provenance([str(RELEASE)])
    preflight = json.loads(Path(a.preflight).read_text())
    if preflight['source_commit'] != source['source_commit'] or not preflight['server']['model']['all_files_verified']:
        raise ValueError('Missing matching server/base-model preflight')
    from scripts.audit_family_matching import verified_tokenizer
    tokenizer, tokenizer_record = verified_tokenizer(Path(a.snapshot))
    tokenizer.pad_token = tokenizer.eos_token
    cfg, data_manifest, train, evaluation, encoded, schedule, budget = load_frozen(tokenizer)
    import torch
    from transformers import AutoModelForCausalLM
    if not torch.cuda.is_available():
        raise ValueError('CUDA is required for this registered model run')
    torch.manual_seed(cfg['seed']); random.seed(cfg['seed']); torch.set_num_threads(8)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    manifest = {**source, 'phase': 'E011', 'status': 'running', 'config': cfg,
                'tokenizer': tokenizer_record, 'data_manifest_sha256': sha256_file(Path(cfg['data_dir'])/'manifest.json'),
                'preflight_sha256': sha256_file(a.preflight), 'server': preflight['server'],
                'model': json.loads(Path('configs/models.lock.json').read_text())['main']['repo_id'],
                'model_revision': tokenizer_record['revision'], 'weights': 'fresh_pinned_base',
                'parameter_dtype': 'float32', 'autocast_dtype': 'bfloat16', 'optimizer': 'AdamW_foreach_false',
                'attention': 'sdpa', 'gradient_checkpointing': 'nonreentrant', 'tf32': False,
                'pad_token_id': tokenizer.pad_token_id, 'eos_token_id': tokenizer.eos_token_id,
                'started_at_utc': datetime.now(timezone.utc).isoformat(), 'holdout_access': False,
                'scientific_treatment_comparison': False}
    dump(out/'run_manifest.json', manifest)
    dump(out/'planned_budget.json', budget)
    history = []
    def stop(*_):
        raise TimeoutError('Bounded watchdog requested termination; no automatic retry')
    signal.signal(signal.SIGTERM, stop)
    start = time.monotonic()
    try:
        model = AutoModelForCausalLM.from_pretrained(a.snapshot, dtype=torch.float32,
                   attn_implementation='sdpa', local_files_only=True).cuda()
        model.config.use_cache = False
        model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={'use_reentrant': False})
        if any(p.dtype != torch.float32 or not p.requires_grad for p in model.parameters()):
            raise ValueError('All original model parameters must train in FP32')
        optimizer = torch.optim.AdamW(model.parameters(), lr=cfg['learning_rate'],
                                     weight_decay=cfg['weight_decay'], foreach=False)
        baseline = generate(model, tokenizer, [r for r in evaluation['dev'] if r['view'] == 'clean'],
                            cfg, out/'base_dev_clean.jsonl')
        dump(out/'baseline_metrics.json', summarize(baseline))
        torch.cuda.reset_peak_memory_stats()
        with (out/'train_history.jsonl').open('x') as log:
            for step, indices in enumerate(schedule, 1):
                model.train(); optimizer.zero_grad(set_to_none=True)
                torch.cuda.synchronize(); tick = time.perf_counter()
                rows = [encoded[i] for i in indices]
                nll = accumulate_gradients(model, rows, tokenizer.pad_token_id, cfg['microbatch_size'], 'cuda')
                norm = torch.nn.utils.clip_grad_norm_(model.parameters(), cfg['grad_clip'])
                if not torch.isfinite(norm):
                    raise FloatingPointError('Nonfinite gradient')
                optimizer.step(); torch.cuda.synchronize()
                record = {'step': step, 'response_nll': nll, 'grad_norm': norm.item(),
                          'supervised_tokens': sum(r['n_supervised'] for r in rows),
                          'processed_tokens': sum(r['n_processed'] for r in rows),
                          'seconds': time.perf_counter()-tick,
                          'peak_allocated_mib': torch.cuda.max_memory_allocated()/1024**2,
                          'peak_reserved_mib': torch.cuda.max_memory_reserved()/1024**2}
                history.append(record); log.write(json.dumps(record, allow_nan=False)+'\n'); log.flush()
                if step == 1 or step % 32 == 0:
                    print(json.dumps(record), flush=True)
        throughput = profile(history, cfg)
        dump(out/'throughput.json', throughput)
        dump(out/'actual_budget.json', budget_report(encoded, schedule, cfg['microbatch_size']))
        # Final-only measurements: no intermediate checkpoint selection or dev-driven stopping.
        model.gradient_checkpointing_disable()
        train_predictions = generate(model, tokenizer, evaluation['train'], cfg, out/'final_train.jsonl')
        dev_predictions = generate(model, tokenizer, evaluation['dev'], cfg, out/'final_dev.jsonl')
        nll = reference_nll(model, encoded, tokenizer, cfg['microbatch_size'])
        stats = summarize(train_predictions)
        results = {'steps': len(history), 'baseline_dev_clean': summarize(baseline), 'train': stats,
                   'dev_by_view': {name: summarize([p for p in dev_predictions if p['view'] == name]) for name in cfg['dev_views']},
                   'train_reference_nll': nll, 'throughput': throughput,
                   'engineering_gate': engineering_gate(cfg, len(history), throughput, stats, nll['nll']),
                   'peak_including_final_eval_mib': torch.cuda.max_memory_allocated()/1024**2}
        dump(out/'evaluation_metrics.json', results)
        checkpoint = out/'checkpoint_final'
        model.save_pretrained(checkpoint, safe_serialization=True)
        tokenizer.save_pretrained(checkpoint)
        dump(out/'checkpoint_manifest.json', {'kind': 'model_weights_only_not_optimizer_or_rng_resume',
             'files': {p.name: {'sha256': sha256_file(p), 'bytes': p.stat().st_size}
                       for p in sorted(checkpoint.iterdir()) if p.is_file()}})
        dump(out/'metrics.json', results)
        manifest['status'] = 'completed'
    except Exception as exc:
        manifest.update(status='failed', exception_type=type(exc).__name__, exception=str(exc))
        raise
    finally:
        manifest.update(steps_completed=len(history), wall_seconds=time.monotonic()-start,
                        finished_at_utc=datetime.now(timezone.utc).isoformat())
        if torch.cuda.is_initialized():
            manifest['peak_allocated_mib'] = torch.cuda.max_memory_allocated()/1024**2
        temporary = out/'run_manifest.tmp'
        dump(temporary, manifest); temporary.replace(out/'run_manifest.json')


if __name__ == '__main__':
    main()

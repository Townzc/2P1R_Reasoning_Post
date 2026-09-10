"""One fresh-base GSM8K engineering trajectory, mandatory E013 budget wrapper."""
from datetime import datetime, timezone
import argparse
import json
import os
from pathlib import Path
import random
import signal
import time

from src.real_math_engineering import (CONFIG, RELEASE, dump, provenance, load_frozen,
                                      score_completion, summarize, engineering_gate)
from src.relation_experiment import accumulate_gradients, reference_nll, profile
from src.sft_data import prefix, sha256_file, budget_report


def generate(model, tokenizer, rows, cfg, path):
    import torch
    from transformers import GenerationConfig
    model.eval()
    settings = GenerationConfig(do_sample=False, num_beams=1, max_new_tokens=cfg['max_new_tokens'],
        eos_token_id=tokenizer.eos_token_id, pad_token_id=tokenizer.pad_token_id, use_cache=True)
    predictions = []
    with Path(path).open('x', encoding='utf-8') as f:
        for start in range(0, len(rows), cfg['eval_batch_size']):
            part = rows[start:start+cfg['eval_batch_size']]
            ids = [tokenizer(prefix(r['prompt']), add_special_tokens=False)['input_ids'] for r in part]
            width = max(map(len, ids))
            if width + cfg['max_new_tokens'] > cfg['max_length']:
                raise ValueError('Generation context cap exceeded')
            inputs = torch.tensor([[tokenizer.pad_token_id]*(width-len(x))+x for x in ids], device='cuda')
            masks = torch.tensor([[0]*(width-len(x))+[1]*len(x) for x in ids], device='cuda')
            tick = time.perf_counter()
            with torch.inference_mode(), torch.autocast('cuda', dtype=torch.bfloat16):
                output = model.generate(input_ids=inputs, attention_mask=masks, generation_config=settings)
            torch.cuda.synchronize()
            batch_seconds = time.perf_counter()-tick
            for row, generated in zip(part, output[:, width:].tolist()):
                eos = tokenizer.eos_token_id in generated
                tokens = generated[:generated.index(tokenizer.eos_token_id)+1] if eos else generated
                text = tokenizer.decode(tokens[:-1] if eos else tokens, skip_special_tokens=False,
                                        clean_up_tokenization_spaces=False)
                truncated = not eos and len(tokens) == cfg['max_new_tokens']
                prediction = {**row, 'text': text, 'generated_ids': tokens,
                    'generated_tokens': len(tokens), 'generation_batch_seconds': batch_seconds,
                    'score': score_completion(row, text, eos, truncated)}
                predictions.append(prediction)
                f.write(json.dumps(prediction, ensure_ascii=False, allow_nan=False)+'\n'); f.flush()
            print(json.dumps({'evaluation': Path(path).name, 'completed_prompts': len(predictions),
                              'batch_seconds': batch_seconds}), flush=True)
            del inputs, masks, output
    return predictions


def training_cost_projection(history, planned, proposal_path):
    """A measured scaling proxy, explicitly not a complete-phase runtime bound."""
    proposal = json.loads(Path(proposal_path).read_text())
    seconds = sum(r['seconds'] for r in history)
    arms = []
    for arm in proposal['arms']:
        if arm['seed'] != 17:
            continue
        estimates = [seconds*arm['supervised_response_tokens']/planned['supervised_response_tokens'],
                     seconds*arm['processed_nonpadding_tokens']/planned['processed_nonpadding_tokens']]
        arms.append({'arm': arm['arm'], 'training_only_seconds_proxy_range': [min(estimates), max(estimates)],
                     'supervised_tokens': arm['supervised_response_tokens'], 'updates': arm['optimizer_updates']})
    return {'observed_training_seconds': seconds, 'seed17_arms': arms,
            'seed17_training_only_proxy_range': [sum(a['training_only_seconds_proxy_range'][i] for a in arms) for i in (0, 1)],
            'complete_phase_bound_available': False, 'automatic_launch_authorized': False,
            'limitations': 'Linear response/processed-token extrapolations are proxies, not confidence bounds. Different rows per update and length distributions change throughput. Full phase also needs frozen development decoding, base loads, checkpoints, verification and watchdog margins. Public source creation/generation costs remain unknown.'}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--snapshot', required=True)
    p.add_argument('--preflight', required=True)
    a = p.parse_args()
    cfg = json.loads(CONFIG.read_text())
    out = Path('runs')/cfg['run_id']
    if os.environ.get('CS294_BOUNDED_RUN_ID') != cfg['run_id'] or not out.is_dir():
        raise ValueError('Mandatory E013 bounded wrapper and unique run directory required')
    if (out/'run_manifest.json').exists():
        raise FileExistsError('Immutable run already started')
    source = provenance([RELEASE])
    preflight = json.loads(Path(a.preflight).read_text())
    if preflight['phase'] != 'E013' or preflight['source_commit'] != source['source_commit'] or not preflight['server']['model']['all_files_verified']:
        raise ValueError('Missing matching E013 server/original-model preflight')
    from scripts.audit_family_matching import verified_tokenizer
    tokenizer, token_record = verified_tokenizer(Path(a.snapshot))
    tokenizer.pad_token = tokenizer.eos_token
    cfg, _, train, dev, encoded, schedule, planned = load_frozen(tokenizer)
    if preflight['data_manifest_sha256'] != sha256_file(Path(cfg['data_dir'])/'manifest.json'):
        raise ValueError('Preflight input manifest differs')
    import torch
    from transformers import AutoModelForCausalLM
    if not torch.cuda.is_available():
        raise ValueError('CUDA required')
    torch.manual_seed(cfg['seed']); random.seed(cfg['seed']); torch.set_num_threads(8)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    manifest = {**source, 'phase': 'E013', 'status': 'running', 'config': cfg,
        'data_manifest_sha256': sha256_file(Path(cfg['data_dir'])/'manifest.json'),
        'preflight_sha256': sha256_file(a.preflight), 'server': preflight['server'], 'tokenizer': token_record,
        'weights': 'fresh_pinned_Qwen2.5_1.5B_base', 'model_revision': token_record['revision'],
        'parameter_dtype': 'float32', 'autocast_dtype': 'bfloat16', 'optimizer': 'AdamW_foreach_false',
        'attention': 'sdpa', 'gradient_checkpointing': 'nonreentrant', 'tf32': False,
        'eos_token_id': tokenizer.eos_token_id, 'pad_token_id': tokenizer.pad_token_id,
        'decoding': {'greedy': True, 'num_beams': 1, 'max_new_tokens': cfg['max_new_tokens'],
                     'batch_size': cfg['eval_batch_size'], 'prompt_serialization': 'Problem: {prompt}\nSolution:\n'},
        'official_test_evaluation': False, 'scientific_treatment_comparison': False,
        'started_at_utc': datetime.now(timezone.utc).isoformat()}
    dump(out/'run_manifest.json', manifest)
    dump(out/'planned_budget.json', planned)
    history, phases = [], {}
    def timed(name, operation):
        tick = time.perf_counter()
        result = operation()
        if torch.cuda.is_initialized():
            torch.cuda.synchronize()
        phases[name] = time.perf_counter()-tick
        return result
    def stop(*_):
        raise TimeoutError('Bounded watchdog terminated E013; no automatic retry')
    signal.signal(signal.SIGTERM, stop)
    started = time.monotonic()
    try:
        model = timed('base_model_load', lambda: AutoModelForCausalLM.from_pretrained(a.snapshot,
            dtype=torch.float32, attn_implementation='sdpa', local_files_only=True).cuda())
        if any(p.dtype != torch.float32 or not p.requires_grad for p in model.parameters()):
            raise ValueError('All original FP32 parameters must train')
        model.config.use_cache = False
        model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={'use_reentrant': False})
        optimizer = torch.optim.AdamW(model.parameters(), lr=cfg['learning_rate'],
                                     weight_decay=cfg['weight_decay'], foreach=False)
        baseline = timed('base_dev_generation', lambda: generate(model, tokenizer, dev, cfg, out/'base_dev.jsonl'))
        base_nll = timed('base_train_nll', lambda: reference_nll(model, encoded, tokenizer, cfg['microbatch_size']))
        dump(out/'baseline_metrics.json', {'dev': summarize(baseline), 'train_reference_nll': base_nll})
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
        phases['training'] = sum(r['seconds'] for r in history)
        throughput = profile(history, cfg)
        dump(out/'throughput.json', throughput)
        model.gradient_checkpointing_disable()
        final_train = timed('final_train_generation', lambda: generate(model, tokenizer, train, cfg, out/'final_train.jsonl'))
        final_dev = timed('final_dev_generation', lambda: generate(model, tokenizer, dev, cfg, out/'final_dev.jsonl'))
        nll = timed('final_train_nll', lambda: reference_nll(model, encoded, tokenizer, cfg['microbatch_size']))
        stats = summarize(final_train)
        results = {'steps': len(history), 'train': stats, 'base_dev': summarize(baseline),
            'final_dev': summarize(final_dev), 'base_train_reference_nll': base_nll,
            'train_reference_nll': nll, 'throughput': throughput,
            'engineering_gate': engineering_gate(cfg, len(history), throughput, stats, nll['nll']),
            'interpretation': 'Development n=16 is descriptive. No test, generalization-effect, or intermediate-proof claim.'}
        dump(out/'evaluation_metrics.json', results)
        dump(out/'training_scale_projection.json', training_cost_projection(history, planned,
             'reports/real_math_c017_scale_proposal_r1/proposal.json'))
        def save_checkpoint():
            checkpoint = out/'checkpoint_final'
            model.save_pretrained(checkpoint, safe_serialization=True)
            tokenizer.save_pretrained(checkpoint)
            dump(out/'checkpoint_manifest.json', {'kind': 'weights_only_not_optimizer_rng_resume',
                'files': {p.name: {'sha256': sha256_file(p), 'bytes': p.stat().st_size}
                          for p in sorted(checkpoint.iterdir()) if p.is_file()}})
        timed('checkpoint_write_and_hash', save_checkpoint)
        dump(out/'metrics.json', results)
        manifest['status'] = 'completed'
    except Exception as exc:
        manifest.update(status='failed', exception_type=type(exc).__name__, exception=str(exc))
        raise
    finally:
        dump(out/'actual_budget.json', budget_report(encoded, schedule[:len(history)], cfg['microbatch_size']))
        dump(out/'phase_timings.json', {'completed_phases_seconds': phases,
             'process_wall_seconds': time.monotonic()-started,
             'limitation': 'Failed/interrupted phase time is included only in wall/guard receipt; a failed in-flight update may have consumed additional uncommitted microbatches.'})
        manifest.update(steps_completed=len(history), wall_seconds=time.monotonic()-started,
                        finished_at_utc=datetime.now(timezone.utc).isoformat())
        if torch.cuda.is_initialized():
            manifest['peak_allocated_mib'] = torch.cuda.max_memory_allocated()/1024**2
        temporary = out/'run_manifest.tmp'
        dump(temporary, manifest); temporary.replace(out/'run_manifest.json')


if __name__ == '__main__':
    main()

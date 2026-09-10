"""Prepare or inspect E015 on CPU; execute one frozen repair only on owner startup."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import random
import signal
import subprocess
import sys
import time

from analyses.e014 import library_sources, stream_hash
from analyses.e015_core import make_cases, reference_record, terminal_lr, train_updates
from scripts.audit_family_matching import verified_tokenizer
from scripts.run_relation_engineering import check_ledger, server_preflight, verify_snapshot
from src.real_math_engineering import dump, engineering_gate, git, load_frozen, source_files, summarize
from src.real_math_experiment import generate
from src.relation_experiment import profile, reference_nll
from src.sft_data import budget_report, sha256_file

CONFIG = Path('configs/real_math_e015/terminal_decay.json')
RELEASE = Path('configs/real_math_e015/release.json')
INPUTS = Path('reports/real_math_e015_inputs_r1')
RENTAL = Path('configs/rental_budget_20260910.json')


def dependencies():
    return sorted(set(source_files() + [
        'analyses/e014.py', 'analyses/e014_audit.py', 'analyses/real_math_e013_failures.py',
        'analyses/e015.py', 'analyses/e015_core.py', 'analyses/e015_audit.py',
        'analyses/e015_storage.py', 'analyses/e015_export.py', 'analyses/verify_e015_inputs.py',
        'tests/test_e015.py', 'tests/test_e015_core.py', 'tests/test_e015_audit.py',
        'tests/test_e015_storage.py', 'tests/test_e015_export.py',
        'reports/real_math_e015_local_preservation.json',
        str(CONFIG), str(RENTAL)]))


def provenance():
    if git('status', '--porcelain', '--untracked-files=no'):
        raise ValueError('Commit and publish tracked source before E015 preparation or execution')
    names = dependencies()
    git('ls-files', '--error-unmatch', *names)
    head = git('rev-parse', 'HEAD')
    if head != git('rev-parse', 'origin/main'):
        raise ValueError('Synchronize published origin/main before E015')
    return {'source_commit': head, 'source_worktree_dirty': False,
            'source_files_sha256': {name: sha256_file(name) for name in names}}


def input_state(tokenizer):
    cfg = json.loads(CONFIG.read_text())
    old, _, train, _, encoded, schedule, planned = load_frozen(tokenizer)
    overrides = {'phase', 'mode', 'run_id', 'max_seconds', 'expected_prior_jobs',
                 'expected_prior_used_seconds', 'expected_ledger_sha256'}
    if any(cfg[key] != value for key, value in old.items() if key not in overrides):
        raise ValueError('An inherited E013 training or scoring factor changed')
    if (cfg['phase'] != 'E015' or cfg['run_id'] != 'gsm8k_terminal_decay_e015_r1'
            or cfg['max_seconds'] != 360 or cfg['guard_seconds'] != 15
            or cfg['learning_rate_schedule'] != 'constant_192_then_cosine_64_to_zero'
            or cfg['model_vocab_size'] != 151936 or cfg['development_evaluation']
            or cfg['base_generation'] or cfg['teacher_calls'] != 0):
        raise ValueError('E015 finite intervention differs')
    if (len(train) != 32 or len(schedule) != 256
            or planned['supervised_response_tokens'] != 167232
            or planned['processed_nonpadding_tokens'] != 229056):
        raise ValueError('Original E013 dose differs')
    cases = make_cases(train, encoded)
    if sum(len(c['target_ids']) for c in cases) != 5226 or any(
            c['target_ids'][-1] != tokenizer.eos_token_id for c in cases):
        raise ValueError('All 5226 original targets and supervised EOS are required')
    return cfg, old, train, encoded, schedule, planned, cases


def prepare(tokenizer):
    if INPUTS.exists() or RELEASE.exists():
        raise FileExistsError('E015 inputs and release are immutable')
    source = provenance()
    cfg, old, train, encoded, schedule, planned, cases = input_state(tokenizer)
    rates = [terminal_lr(step) for step in range(1, 257)]
    evidence = {'phase': 'E015_CPU_PREPARATION', 'model_execution_performed': False,
                'server_contacted': False, 'train_rows': len(train), 'reference_targets': 5226,
                'supervised_eos': 32, 'optimizer_updates': 256,
                'nonzero_lr_updates': sum(rate > 0 for rate in rates), 'summed_lr': math.fsum(rates),
                'supervised_tokens': planned['supervised_response_tokens'],
                'processed_tokens': planned['processed_nonpadding_tokens'],
                'e013_train_sha256': sha256_file(Path(old['data_dir']) / 'train.jsonl'),
                'e013_schedule_sha256': sha256_file(Path(old['data_dir']) / 'schedule.json'),
                'same_data_order_seed_dose': True, 'new_development_or_test_generations': 0,
                'rental_budget_sha256': sha256_file(RENTAL)}
    INPUTS.mkdir()
    dump(INPUTS / 'cases.json', cases)
    dump(INPUTS / 'learning_rates.json', rates)
    dump(INPUTS / 'budget.json', planned)
    dump(INPUTS / 'cpu_evidence.json', evidence)
    dump(INPUTS / 'manifest.json', {**source, 'phase': 'E015_INPUTS',
        'config_sha256': sha256_file(CONFIG), 'library_sources_sha256': library_sources(),
        'e013_input_manifest_sha256': sha256_file(Path(old['data_dir']) / 'manifest.json'),
        'files_sha256': {name: sha256_file(INPUTS / name) for name in
                        ('cases.json', 'learning_rates.json', 'budget.json', 'cpu_evidence.json')}})
    dump(RELEASE, {'phase': 'E015_RELEASE', 'manifest_sha256': sha256_file(INPUTS / 'manifest.json'),
                   'model_execution_performed': False})
    return evidence


def load_release(tokenizer):
    release = json.loads(RELEASE.read_text())
    if release['phase'] != 'E015_RELEASE' or sha256_file(INPUTS / 'manifest.json') != release['manifest_sha256']:
        raise ValueError('E015 release manifest differs')
    manifest = json.loads((INPUTS / 'manifest.json').read_text())
    if manifest['config_sha256'] != sha256_file(CONFIG) or set(manifest['source_files_sha256']) != set(dependencies()):
        raise ValueError('Frozen E015 source/config dependency set differs')
    for name, expected in manifest['source_files_sha256'].items():
        historical = subprocess.check_output(['git', 'show', manifest['source_commit'] + ':' + name])
        if sha256_file(name) != expected or hashlib.sha256(historical).hexdigest() != expected:
            raise ValueError('E015 current/historical source bytes differ: ' + name)
    if library_sources() != manifest['library_sources_sha256']:
        raise ValueError('Installed generation or Qwen2 source differs')
    for name, expected in manifest['files_sha256'].items():
        if Path(name).name != name or sha256_file(INPUTS / name) != expected:
            raise ValueError('Frozen E015 input artifact differs')
    state = input_state(tokenizer)
    if (state[-1] != json.loads((INPUTS / 'cases.json').read_text())
            or state[-2] != json.loads((INPUTS / 'budget.json').read_text())
            or [terminal_lr(step) for step in range(1, 257)] != json.loads((INPUTS / 'learning_rates.json').read_text())):
        raise ValueError('Reconstructed reference cases, dose or LR schedule differs')
    return state


def rental_window(start_text, source, now=None):
    """Require enough time for the whole job and preservation, not just model use."""
    plan = json.loads(RENTAL.read_text())
    if source not in ('provider_timestamp', 'owner_start_notification'):
        raise ValueError('Record the source of the power-on time')
    start = datetime.fromisoformat(start_text.replace('Z', '+00:00'))
    if start.tzinfo is None or start.utcoffset() is None:
        raise ValueError('Timezone-aware power-on timestamp required')
    now = now or datetime.now(timezone.utc)
    elapsed = (now - start).total_seconds()
    if elapsed < 0:
        raise ValueError('Power-on timestamp cannot be in the future')
    window = plan['current_window']
    remaining = window['planned_ceiling_seconds'] - elapsed
    required = sum(window[key] for key in
                   ('process_plus_guard_seconds', 'export_and_verification_seconds', 'shutdown_and_slack_seconds'))
    if remaining < required:
        raise ValueError('Insufficient whole-rental window for job, export and safe exit')
    return {'power_on_at_utc': start.astimezone(timezone.utc).isoformat(), 'time_source': source,
            'provider_start_time_verified': source == 'provider_timestamp',
            'notification_may_postdate_actual_power_on': source == 'owner_start_notification',
            'elapsed_since_recorded_start_seconds': elapsed, 'remaining_planned_window_seconds': remaining,
            'required_job_export_exit_seconds': required, 'currency': plan['currency'],
            'hourly_rate': plan['hourly_rate'], 'overall_ceiling_cny': plan['overall_ceiling_cny'],
            'planned_window_ceiling_cny': window['planned_ceiling_compute_cost_cny'],
            'provider_shutdown_confirmed': False, 'actual_bill_known': False}


def worker(args, tokenizer):
    cfg, old, train, encoded, schedule, planned, cases = load_release(tokenizer)
    out = Path('runs') / cfg['run_id']
    if os.environ.get('CS294_BOUNDED_RUN_ID') != cfg['run_id'] or not out.is_dir():
        raise ValueError('E015 requires its unique bounded wrapper')
    if (out / 'run_manifest.json').exists():
        raise FileExistsError('E015 run already started; no retry')
    source = provenance()
    preflight = json.loads(Path(args.preflight).read_text())
    if (preflight['phase'] != 'E015' or preflight['source_commit'] != source['source_commit']
            or preflight['release_sha256'] != sha256_file(RELEASE)
            or not preflight['server']['model']['all_files_verified']
            or preflight['accounting']['ledger_sha256'] != cfg['expected_ledger_sha256']):
        raise ValueError('Matching E015 original-base/release/ledger preflight required')
    rental_window(preflight['rental']['power_on_at_utc'], preflight['rental']['time_source'])
    manifest = {**source, 'phase': 'E015', 'status': 'running', 'config': cfg,
        'release_sha256': sha256_file(RELEASE), 'preflight_sha256': sha256_file(args.preflight),
        'server': preflight['server'], 'tokenizer': preflight['tokenizer'], 'rental': preflight['rental'],
        'weights': 'fresh_pinned_Qwen2.5_1.5B_base', 'parameter_dtype': 'float32',
        'autocast_dtype': 'bfloat16', 'attention': 'sdpa', 'tf32': False,
        'optimizer': 'AdamW_foreach_false', 'model_execution_performed': False,
        'training_updates': 0, 'steps_completed': 0, 'official_test_evaluation': False,
        'development_evaluation': False, 'started_at_utc': datetime.now(timezone.utc).isoformat()}
    dump(out / 'run_manifest.json', manifest)
    dump(out / 'planned_budget.json', planned)
    history, phases = [], {}
    started = time.monotonic()
    def stop(*_):
        raise TimeoutError('E015 watchdog terminated; preserve partial state without retry')
    signal.signal(signal.SIGTERM, stop)
    try:
        import torch
        from transformers import AutoModelForCausalLM
        if not torch.cuda.is_available():
            raise ValueError('Registered E015 model execution requires CUDA')
        torch.manual_seed(cfg['seed'])
        random.seed(cfg['seed'])
        torch.set_num_threads(8)
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        tokenizer.pad_token = tokenizer.eos_token
        def timed(name, operation):
            tick = time.perf_counter()
            result = operation()
            torch.cuda.synchronize()
            phases[name] = time.perf_counter() - tick
            return result
        manifest['model_execution_performed'] = True
        model = timed('base_model_load', lambda: AutoModelForCausalLM.from_pretrained(
            args.tokenizer_dir, dtype=torch.float32, attn_implementation='sdpa', local_files_only=True).cuda())
        if any(p.dtype != torch.float32 or not p.requires_grad for p in model.parameters()):
            raise ValueError('All original FP32 parameters must train')
        if model.config.vocab_size != cfg['model_vocab_size']:
            raise ValueError('Original model vocabulary differs')
        model.config.use_cache = False
        model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={'use_reentrant': False})
        optimizer = torch.optim.AdamW(model.parameters(), lr=cfg['learning_rate'],
                                     weight_decay=cfg['weight_decay'], foreach=False)
        baseline = timed('base_train_nll', lambda: reference_nll(model, encoded, tokenizer, cfg['microbatch_size']))
        dump(out / 'base_reference_nll.json', baseline)
        torch.cuda.reset_peak_memory_stats()
        with (out / 'train_history.jsonl').open('x') as log:
            train_updates(model, optimizer, encoded, schedule, cfg, tokenizer.pad_token_id, log, history)
        phases['training'] = sum(row['seconds'] for row in history)
        throughput = profile(history, cfg)
        dump(out / 'throughput.json', throughput)
        model.gradient_checkpointing_disable()
        predictions = timed('final_train_generation', lambda: generate(
            model, tokenizer, train, old, out / 'final_train.jsonl'))
        def measure_all():
            records = []
            model.eval()
            with (out / 'reference_tokens.jsonl').open('x') as log:
                for enc, case in zip(encoded, cases):
                    ids = torch.tensor([enc['input_ids']], device='cuda')
                    with torch.inference_mode(), torch.autocast('cuda', dtype=torch.bfloat16):
                        output = model(input_ids=ids, attention_mask=torch.ones_like(ids), use_cache=False)
                    record = reference_record(output.logits[0], case)
                    records.append(record)
                    log.write(json.dumps(record, allow_nan=False) + '\n')
                    log.flush()
                    del ids, output
            return records
        references = timed('all32_reference_tokens', measure_all)
        count = sum(r['supervised_tokens'] for r in references)
        total = math.fsum(r['loss_sum'] for r in references)
        nll = {'nll': total / count, 'response_loss_sum': total,
               'supervised_tokens': count, 'reference_count': len(references)}
        stats = summarize(predictions)
        metrics = {'steps': len(history), 'train': stats, 'train_reference_nll': nll, 'throughput': throughput,
                   'engineering_gate': engineering_gate(cfg, len(history), throughput, stats, nll['nll']),
                   'reference_top1_correct': sum(r['target_top1_correct'] for r in references),
                   'reference_eos_top1_correct': sum(r['eos_is_argmax'] for r in references),
                   'lr_accounting': {'nonzero_lr_updates': sum(r['actual_learning_rate'] > 0 for r in history),
                                     'summed_lr': math.fsum(r['actual_learning_rate'] for r in history)},
                   'interpretation': 'Engineering memorization only; no new development/test scoring or treatment effect.'}
        def save_checkpoint():
            checkpoint = out / 'checkpoint_final'
            model.save_pretrained(checkpoint, safe_serialization=True)
            tokenizer.save_pretrained(checkpoint)
            dump(out / 'checkpoint_manifest.json', {'kind': 'weights_only_not_optimizer_rng_resume',
                'files': {p.name: {'sha256': stream_hash(p), 'bytes': p.stat().st_size}
                          for p in sorted(checkpoint.iterdir()) if p.is_file()}})
        timed('checkpoint_write_and_hash', save_checkpoint)
        dump(out / 'metrics.json', metrics)
        manifest['status'] = 'completed'
    except Exception as exc:
        manifest.update(status='failed', exception_type=type(exc).__name__, exception=str(exc))
        raise
    finally:
        dump(out / 'actual_budget.json', budget_report(encoded, schedule[:len(history)], cfg['microbatch_size']))
        dump(out / 'phase_timings.json', {'completed_phases_seconds': phases,
            'process_wall_seconds': time.monotonic() - started,
            'limitation': 'Incomplete phase/in-flight update time is included in wall/guard receipt; only completed updates enter dose.'})
        manifest.update(steps_completed=len(history), training_updates=len(history),
                        finished_at_utc=datetime.now(timezone.utc).isoformat())
        manifest['artifact_sha256'] = {p.name: sha256_file(p) for p in out.iterdir()
            if p.suffix in ('.json', '.jsonl') and p.name != 'run_manifest.json'}
        temporary = out / 'run_manifest.tmp'
        dump(temporary, manifest)
        temporary.replace(out / 'run_manifest.json')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', nargs='?', default='inspect', choices=('prepare', 'inspect', 'reclaim', 'launch', 'worker'))
    parser.add_argument('--tokenizer-dir', required=True)
    parser.add_argument('--ledger', default='.local/resource_ledger.json')
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--preflight')
    parser.add_argument('--power-on-at-utc')
    parser.add_argument('--power-on-time-source', choices=('provider_timestamp', 'owner_start_notification'))
    args = parser.parse_args()
    tokenizer, token_record = verified_tokenizer(Path(args.tokenizer_dir))
    if args.action == 'prepare':
        print(json.dumps(prepare(tokenizer), indent=2))
        return 0
    if args.action == 'worker':
        worker(args, tokenizer)
        return 0
    cfg, _, _, _, _, planned, _ = load_release(tokenizer)
    source = provenance()
    git('ls-files', '--error-unmatch', str(RELEASE), *map(str, INPUTS.iterdir()))
    resource = json.loads(Path('configs/resource_budget.json').read_text())
    accounting = check_ledger(cfg, args.ledger, resource)
    report = {'phase': 'E015', 'status': 'not_run', 'source_commit': source['source_commit'],
              'release_sha256': sha256_file(RELEASE), 'accounting': accounting, 'tokenizer': token_record,
              'optimizer_updates': planned['optimizer_updates'],
              'supervised_tokens': planned['supervised_response_tokens'],
              'processed_tokens': planned['processed_nonpadding_tokens'],
              'model_execution_performed': False, 'rental_budget_sha256': sha256_file(RENTAL)}
    if args.action == 'inspect' or not args.execute:
        print(json.dumps(report, indent=2))
        return 0
    if not args.power_on_at_utc or not args.power_on_time_source:
        raise ValueError('Supply the power-on timestamp and its evidence source before server actions')
    report['rental'] = rental_window(args.power_on_at_utc, args.power_on_time_source)
    if args.action == 'reclaim':
        from analyses.e015_storage import reclaim_duplicate
        # Permit only verification-backed reclamation before the unchanged 12-GiB gate.
        report['server'] = server_preflight({**cfg, 'min_free_gib': 0}, Path(args.tokenizer_dir))
        result = reclaim_duplicate(Path(args.tokenizer_dir), Path(args.ledger), execute=True)
        path = Path('.local') / ('e015_cleanup_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f') + '.json')
        dump(path, {**report, 'cleanup': result})
        print(json.dumps({'phase': 'E015_CLEANUP', 'receipt': str(path), 'cleanup': result}, indent=2))
        return 0
    report['server'] = server_preflight(cfg, Path(args.tokenizer_dir))
    if report['server']['gpu'].split(',')[2].strip() != cfg['driver_version']:
        raise ValueError('Recorded driver differs')
    report['rental'] = rental_window(args.power_on_at_utc, args.power_on_time_source)
    report['checked_at_utc'] = datetime.now(timezone.utc).isoformat()
    preflight = Path('.local') / ('e015_preflight_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f') + '.json')
    dump(preflight, report)
    check_ledger(cfg, args.ledger, resource)
    return subprocess.call([sys.executable, '-m', 'scripts.run_bounded', '--run-id', cfg['run_id'],
        '--max-seconds', str(cfg['max_seconds']), '--ledger', args.ledger,
        '--expected-ledger-sha256', cfg['expected_ledger_sha256'], '--require-full-cap', '--',
        sys.executable, '-m', 'analyses.e015', 'worker', '--tokenizer-dir', args.tokenizer_dir,
        '--preflight', str(preflight)])


if __name__ == '__main__':
    sys.exit(main())

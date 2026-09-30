"""Run one owner-approved control completion after the CPU semantics gate.

Fresh C128/C128/R128 and their original three evaluations only. No W model load,
server startup, automatic phase retry, failed-batch replay, or deadline renewal.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import re
import shutil
import signal
import subprocess
import sys
import time

from . import completion_plan as fixed
from . import screen_plan as scientific
from . import screen_runtime as runtime
from .contracts import identity_hash
from .gpu_profile import ProfileError, durable_json, launch_guarded, pinned_json, sha256


def verify_source(source_root, manifest_path, manifest_sha256, source_commit):
    root = Path(source_root).resolve()
    manifest = pinned_json(manifest_path, manifest_sha256)
    if not re.fullmatch('[a-f0-9]{40}', source_commit) or manifest.get('commit') != source_commit:
        raise ProfileError('published source commit differs from the pinned source manifest')
    files = manifest.get('files')
    if not isinstance(files, dict) or not files:
        raise ProfileError('source manifest must list actual files')
    for name, expected in files.items():
        path = root / name
        if (Path(name).is_absolute() or '..' in Path(name).parts or path.is_symlink() or
                not path.resolve().is_relative_to(root) or not path.is_file() or
                type(expected.get('bytes')) is not int or path.stat().st_size != expected['bytes'] or
                sha256(path) != expected.get('sha256')):
            raise ProfileError('published execution source file identity differs')
    prefix = 'experiments/q2_supervision_migration/'
    actual_py = {str(p.relative_to(root)) for p in (root / prefix).glob('*.py')}
    listed_py = {name for name in files if name.startswith(prefix) and name.endswith('.py')}
    if actual_py != listed_py or not {
            prefix + 'completion_parent.py', prefix + 'completion_plan.py',
            prefix + 'screen_runtime.py', prefix + 'rollout_recovery.py'} <= listed_py:
        raise ProfileError('source manifest must cover exactly every Q2 Python execution module')
    return {'commit': source_commit, 'manifest_sha256': manifest_sha256, 'file_count': len(files)}


def verify_gate(gate_dir, expected_sha256, source_commit, plan_identity):
    gate = Path(gate_dir)
    complete = pinned_json(gate / 'preflight_complete.json', expected_sha256)
    receipt_path = gate / 'cpu_launcher_receipt.json'
    receipt = json.loads(receipt_path.read_text())
    if (complete.get('passed') is not True or complete.get('reward_semantics_unchanged') is not True or
            complete.get('source_commit') != source_commit or complete.get('plan_sha256') != plan_identity or
            type(complete.get('new_generations')) is not int or complete['new_generations'] != 0 or
            type(complete.get('optimizer_updates')) is not int or complete['optimizer_updates'] != 0 or
            receipt.get('status') != 'completed' or receipt.get('returncode') != 0):
        raise ProfileError('saved-output CPU semantics gate is missing or did not pass')
    if (gate / 'preflight_failure.json').exists():
        raise ProfileError('CPU gate directory also contains failure evidence')
    counts = {'original_saved_outputs': 96, 'previous_known_pairs': 90, 'matched_pairs': 90,
              'resolved_pairs': 96, 'known_W_sentinels_matched': 32}
    if any(type(complete.get(k)) is not int or complete[k] != v for k, v in counts.items()):
        raise ProfileError('CPU gate lacks exact saved-output and known-W regression coverage')
    controls = complete.get('authored_controls_passed')
    if (not isinstance(controls, list) or len(controls) != 5 or
            set(controls) != {'valid', 'wrong', 'syntax', 'init', 'test_timeout'}):
        raise ProfileError('CPU gate lacks all five authored attribution controls')
    diagnoses = complete.get('diagnoses')
    if (not isinstance(diagnoses, list) or len(diagnoses) != 2 or
            any(not isinstance(x, dict) for x in diagnoses) or
            {x.get('fixture') for x in diagnoses} != {'R599', 'C260'}):
        raise ProfileError('CPU gate lacks both exact failure diagnoses')
    for diagnosis in diagnoses:
        verdicts = diagnosis.get('verdicts')
        if (not isinstance(verdicts, list) or len(verdicts) != 3 or
                any(v not in ('pass', 'fail') for v in verdicts) or len(set(verdicts)) != 1 or
                (diagnosis['fixture'] == 'C260' and verdicts != ['fail'] * 3)):
            raise ProfileError('CPU gate failure diagnosis is unresolved or nonrepeatable')
    if (complete.get('historical_records_relabelled') is not False or
            complete.get('reward_semantics_changed') is not False or
            not re.fullmatch('[a-f0-9]{64}', str(complete.get('reference_manifest_sha256', '')))):
        raise ProfileError('CPU gate changed historical meaning or lacks pinned references')
    return {'preflight_sha256': expected_sha256, 'launcher_receipt_sha256': sha256(receipt_path),
            'passed': True, 'reward_semantics_unchanged': True,
            'reference_manifest_sha256': complete['reference_manifest_sha256']}


def verify_references(reference_root, plan, data_sha256):
    root = Path(reference_root).resolve()
    manifest_path, cache = root / 'manifest.json', root / 'groundtruth.pickle'
    if manifest_path.is_symlink() or cache.is_symlink() or not cache.is_file():
        raise ProfileError('reference files must be preserved regular files')
    manifest = json.loads(manifest_path.read_text())
    if (manifest.get('plan_sha256') != identity_hash(plan) or manifest.get('data_sha256') != data_sha256 or
            manifest.get('task_ids') != sorted(plan['train_ids'] + plan['eval_ids']) or
            sha256(cache) != manifest.get('sha256')):
        raise ProfileError('canonical reference cache identity differs')
    return {'manifest_sha256': sha256(manifest_path), 'cache_sha256': manifest['sha256'],
            'task_count': len(manifest['task_ids'])}


def verify_flags(args):
    if (not args.execute_screen or not args.recover_initialization_timeout or
            not args.retain_evaluation_unknowns or not getattr(args, 'guarded_scoring_v2', False) or
            not getattr(args, 'durable_rollout_evidence', False) or
            getattr(args, 'execution_attempt', None) != fixed.ATTEMPT):
        raise ProfileError('completion requires the explicit frozen attempt and repaired runtime flags')
    if args.recover_suite_watchdog:
        raise ProfileError('failed historical suite-watchdog repair is prohibited')
    if args._worker or args.phase or args.worker_deadline_epoch:
        raise ProfileError('completion parent controls phases and child deadlines')


def assert_no_workers():
    if subprocess.check_output(['nvidia-smi', '--query-compute-apps=pid', '--format=csv,noheader'], text=True).strip():
        raise ProfileError('GPU already has workers; refusing duplicate execution')
    for proc in Path('/proc').glob('[0-9]*'):
        if int(proc.name) == os.getpid():
            continue
        try:
            cmd = (proc / 'cmdline').read_bytes()
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            continue
        if b'experiments.q2_supervision_migration.' in cmd:
            raise ProfileError('another Q2 parent or CPU/GPU worker is still present')


def verify_phase_complete(path, name, plan_identity):
    marker = 'evaluation_complete.json' if name.startswith('eval_') else 'phase_complete.json'
    complete = json.loads((Path(path) / marker).read_text())
    if complete.get('plan_sha256') != plan_identity:
        raise ProfileError('child completion belongs to a different scientific plan')
    if name.startswith('eval_'):
        if complete.get('state') != name.removeprefix('eval_') or complete.get('completions') != 1024:
            raise ProfileError('evaluation child did not complete its frozen dose')
    elif (complete.get('phase') != name or complete.get('committed_updates') != 128 or
          complete.get('training_completions') != 2048):
        raise ProfileError('training child did not complete its frozen dose')
    return {'phase': name, 'receipt_sha256': sha256(Path(path) / marker)}


def run_queue(args, plan, command, *, clock=time.time, launcher=launch_guarded):
    """Serial owned child groups; the first unsuccessful phase is terminal."""
    out = Path(args.out)
    completed = []
    for index, name in enumerate(fixed.PHASES):
        runtime.remaining(args)
        runtime.disk_gate(out)
        end = fixed.phase_deadline(name, clock(), args.worker_deadline_epoch)
        phase_out = out / name
        phase_out.mkdir(exist_ok=False)
        rc = launcher(command + ['--phase', name, '--worker-deadline-epoch', str(end)],
                      phase_out, end - clock(), phase='process')
        if rc:
            durable_json(out / 'completion_failure.json', {'phase': name, 'retry': False,
                'remaining_phases_not_run': list(fixed.PHASES[index + 1:]),
                'completed_phase_receipts': completed,
                'direction_should_be_paused_if_completion_unsuccessful': True})
            return 1
        completed.append(verify_phase_complete(phase_out, name, args.plan_identity))
    durable_json(out / 'control_completion_complete.json', {'phases': list(fixed.PHASES),
        'plan_sha256': args.plan_identity, 'execution_attempt': fixed.ATTEMPT,
        'dose': fixed.DOSE, 'phase_receipts': completed, 'finished_epoch': clock(),
        'all_available_comparisons_require_separate_local_verification': True,
        'unknown_evaluation_scores_must_be_reported': True,
        'scientific_success_claimed': False, 'automatic_continuation': False})
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument('--power-on-epoch', type=float, required=True)
    p.add_argument('--model-deadline-epoch', type=float)
    for name in ('diagnostic-dir', 'preflight-sha256', 'source-manifest', 'source-manifest-sha256', 'reference-root'):
        p.add_argument('--' + name, required=True)
    extra, common = p.parse_known_args(argv)
    args = runtime.parse(common)
    if platform.system() != 'Linux':
        raise ProfileError('explicit Linux completion execution required')
    verify_flags(args)
    split = pinned_json(args.split_json, args.split_sha256)
    plan = scientific.validate_plan(pinned_json(args.plan_json, args.plan_sha256), split)
    args.plan_identity = identity_hash(plan)
    execution = fixed.make_completion_plan(plan)
    deadlines = fixed.fixed_deadlines(extra.power_on_epoch, args.provider_deadline_epoch, time.time(),
                                     extra.model_deadline_epoch)
    args.worker_deadline_epoch = deadlines['worker_deadline_epoch']
    source = verify_source(Path(__file__).resolve().parents[2], extra.source_manifest,
                           extra.source_manifest_sha256, args.source_commit)
    gate = verify_gate(extra.diagnostic_dir, extra.preflight_sha256, args.source_commit, args.plan_identity)
    references = verify_references(extra.reference_root, plan, args.data_sha256)
    if gate['reference_manifest_sha256'] != references['manifest_sha256']:
        raise ProfileError('CPU gate and model execution use different reference manifests')
    assert_no_workers()
    paths = [str(Path(sys.executable).parent)]
    if Path('/usr/local/cuda/bin').is_dir():
        paths.append('/usr/local/cuda/bin')
    os.environ['PATH'] = os.pathsep.join(paths + [os.environ.get('PATH', '')])
    if not shutil.which('ninja') or not shutil.which('nvcc'):
        raise ProfileError('installed build tools unavailable; no model launch')
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=False)
    args.out = str(out)
    runtime.disk_gate(out, initial=True)
    versions = runtime.validate_environment(args, plan)
    _, initial_model_identity, _ = runtime.source_for(args, 'R')
    remaining_at_admission = runtime.remaining(args)
    (out / 'references').symlink_to(Path(extra.reference_root).resolve(), target_is_directory=True)
    durable_json(out / 'completion_intent.json', {'execution': execution, 'scientific_plan': plan,
        'plan_sha256': args.plan_identity, 'source_commit': args.source_commit, 'source': source,
        'gate': gate, 'references': references, 'initial_model_identity': initial_model_identity,
        'versions': versions, 'started_epoch': time.time(), **deadlines,
        'model_work_remaining_seconds_at_admission': remaining_at_admission,
        'prior_closed_dose': fixed.PRIOR_DOSE, 'automatic_retry': False,
        'old_failure_checkpoint_used': False, 'old_W_model_loaded': False,
        'new_attempt_is_not_exact_resume': True})
    command = [sys.executable, '-m', 'experiments.q2_supervision_migration.screen_runtime', *common, '--_worker']
    def interrupted(signum, frame):
        raise InterruptedError(f'completion parent received {signum}')
    previous = signal.signal(signal.SIGTERM, interrupted)
    try:
        return run_queue(args, plan, command)
    except BaseException as exc:
        durable_json(out / 'completion_parent_failure.json', {'error': repr(exc), 'retry': False,
            'direction_should_be_paused_if_completion_unsuccessful': True})
        raise
    finally:
        signal.signal(signal.SIGTERM, previous)


if __name__ == '__main__':
    raise SystemExit(main())

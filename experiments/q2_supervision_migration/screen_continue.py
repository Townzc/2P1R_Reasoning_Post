"""Run only untouched W/R phases after the closed C-prefix engineering fault.

This does not retry C, regenerate W, change the frozen plan, or renew deadlines.
A separate owner decision is needed for lost C updates. Old evidence is read-only.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import platform
import re
import signal
import subprocess
import sys
import time

from . import screen_runtime as runtime
from . import screen_plan as spec
from .contracts import identity_hash
from .gpu_profile import ProfileError, durable_json, sha256, pinned_json, launch_guarded

PHASES = ('W_future', 'R_future', 'eval_R', 'eval_W_prefix', 'eval_W_future', 'eval_R_future')


def inherited_deadline(intent, provider_deadline, now):
    if provider_deadline != intent['provider_deadline_epoch']:
        raise ProfileError('original provider deadline must be retained')
    deadline = intent['worker_deadline_epoch']
    if not now < deadline <= provider_deadline - 600:
        raise ProfileError('original worker window is closed or lacks reserve')
    return deadline


def validate_old(old, plan_identity):
    intent = json.loads((old/'screen_intent.json').read_text())
    failure = json.loads((old/'screen_failure.json').read_text())
    if intent['plan_sha256'] != plan_identity or failure['phase'] != 'C_prefix':
        raise ProfileError('wrong original plan/failure')
    for phase in PHASES:
        if (old/phase).exists():
            raise ProfileError('phase already attempted; no replay')
    for phase in ('W_prefix', 'C_prefix', 'references'):
        receipt = json.loads((old/phase/'process_launcher_receipt.json').read_text())
        pid = receipt['pid']
        cmdline = Path(f'/proc/{pid}/cmdline')
        if cmdline.exists() and b'q2_supervision_migration' in cmdline.read_bytes():
            raise ProfileError('old worker is still present')
    if json.loads((old/'W_prefix/phase_complete.json').read_text())['committed_updates'] != 128:
        raise ProfileError('W prefix not complete')
    return intent


def main(argv=None):
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument('--old-output', required=True)
    p.add_argument('--diagnostic-dir', required=True)
    extra, common = p.parse_known_args(argv)
    args = runtime.parse(common)
    if platform.system() != 'Linux' or not args.execute_screen or not args.recover_initialization_timeout:
        raise ProfileError('explicit repaired Linux continuation required')
    if args._worker or args.phase or args.worker_deadline_epoch or not re.fullmatch('[a-f0-9]{40}', args.source_commit):
        raise ProfileError('continuation parent controls phases/deadlines')
    old = Path(extra.old_output).resolve()
    split = pinned_json(args.split_json, args.split_sha256)
    plan = spec.validate_plan(pinned_json(args.plan_json, args.plan_sha256), split)
    args.plan_identity = identity_hash(plan)
    intent = validate_old(old, args.plan_identity)
    args.worker_deadline_epoch = inherited_deadline(intent, args.provider_deadline_epoch, time.time())
    gate = Path(extra.diagnostic_dir)
    complete = json.loads((gate/'preflight_complete.json').read_text())
    receipt = json.loads((gate/'cpu_launcher_receipt.json').read_text())
    if complete['saved_timeout_attributed'] != 1 or receipt['returncode'] != 0 or receipt['status'] != 'completed':
        raise ProfileError('saved-candidate CPU gate did not pass')
    if subprocess.check_output(['nvidia-smi', '--query-compute-apps=pid', '--format=csv,noheader'], text=True).strip():
        raise ProfileError('existing GPU worker; refusing duplicate')
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=False)
    args.out = str(out)
    runtime.disk_gate(out, initial=True)
    runtime.validate_environment(args, plan)
    (out/'references').symlink_to(old/'references', target_is_directory=True)
    (out/'W_prefix').symlink_to(old/'W_prefix', target_is_directory=True)
    runtime.source_for(args, 'W_prefix')
    refs = json.loads((old/'references/manifest.json').read_text())
    if refs['plan_sha256'] != args.plan_identity or sha256(old/'references/groundtruth.pickle') != refs['sha256']:
        raise ProfileError('reference cache identity differs')
    durable_json(out/'continuation_intent.json', {
        'source_commit': args.source_commit, 'original_source_commit': intent['source_commit'],
        'plan_sha256': args.plan_identity, 'old_intent_sha256': sha256(old/'screen_intent.json'),
        'phases': PHASES, 'new_training_updates': 256, 'new_training_generations': 4096,
        'new_evaluation_generations': 4096, 'reuse': ['W_prefix', 'references'],
        'missing_without_owner_amendment': ['C_prefix', 'C_future'],
        'worker_deadline_epoch': args.worker_deadline_epoch,
        'provider_deadline_epoch': args.provider_deadline_epoch,
        'cpu_gate_sha256': sha256(gate/'preflight_complete.json'),
        'started_epoch': time.time(), 'automatic_retry': False})
    command = [sys.executable, '-m', 'experiments.q2_supervision_migration.screen_runtime', *common, '--_worker']
    def interrupted(signum, frame):
        raise InterruptedError(f'continuation parent received {signum}')
    previous = signal.signal(signal.SIGTERM, interrupted)
    try:
        for phase in PHASES:
            runtime.remaining(args)
            runtime.disk_gate(out)
            phase_out = out/phase
            phase_out.mkdir(exist_ok=False)
            limit = plan['limits']['evaluation_phase_seconds' if phase.startswith('eval_') else 'training_phase_seconds']
            end = min(args.worker_deadline_epoch, time.time()+limit)
            rc = launch_guarded(command+['--phase', phase, '--worker-deadline-epoch', str(end)],
                                phase_out, end-time.time(), phase='process')
            if rc:
                durable_json(out/'continuation_failure.json', {'phase': phase, 'retry': False,
                    'remaining_phases_not_run': list(PHASES[PHASES.index(phase)+1:])})
                return 1
        durable_json(out/'continuation_complete.json', {'phases': PHASES,
            'finished_epoch': time.time(), 'full_W_C_R_screen_complete': False,
            'C_comparisons_missing': True, 'automatic_continuation': False})
        return 0
    except BaseException as exc:
        durable_json(out/'continuation_parent_failure.json', {'error': repr(exc), 'retry': False})
        raise
    finally:
        signal.signal(signal.SIGTERM, previous)

if __name__ == '__main__':
    raise SystemExit(main())

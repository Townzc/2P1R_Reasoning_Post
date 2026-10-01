"""Bounded paired diagnostic of a saved timeout; never admits model work."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import time

from .completion_preflight import saved_sample
from .gpu_profile import ProfileError, durable_json, launch_guarded
from .screen_scoring import load_problems, load_references


def worker(a):
    from .scoring_cpu import pin_scoring_cpu
    durable_json(Path(a.out) / 'scoring_cpu_placement.json', pin_scoring_cpu())
    from evalplus.eval import untrusted_check
    from .scoring_guard_v2 import diagnose_timeout
    old, code = saved_sample(Path(a.continuation_root) / 'R_future', 25, 8)
    if old['task_id'] != 'Mbpp/599' or old['extra']['status'] != 'timeout':
        raise ProfileError('wrong immutable failure fixture')
    problems = load_problems(a.data_json, a.data_sha256)
    refs, manifest = load_references(a.references)
    if manifest['data_sha256'] != a.data_sha256:
        raise ProfileError('reference identity mismatch')
    problem, ref = problems['Mbpp/599'], refs['Mbpp/599']
    durable_json(Path(a.out) / 'fixture.json', {'sample_id': old['sample_id'],
        'old_score': old['extra'], 'code': code, 'source_commit': a.source_commit,
        'new_model_outputs': 0, 'optimizer_updates': 0, 'model_admitted': False})
    for repeat in range(3):
        # Check the first guard before any long upstream run, avoiding an
        # accidental fixed order/warmup explanation for the earlier paired audit.
        if repeat % 2 == 0:
            result = diagnose_timeout(problem, code, ref['plus'], ref['plus_time'],
                suite='extra', original_details=[True] * 34, outer_cap_seconds=180)
            durable_json(Path(a.out) / f'guard_{repeat}.json', result)
        started = time.monotonic()
        status, details = untrusted_check('mbpp', code, problem['plus_input'],
            problem['entry_point'], expected=ref['plus'], atol=problem['atol'],
            ref_time=ref['plus_time'], fast_check=True)
        durable_json(Path(a.out) / f'upstream_{repeat}.json', {
            'status': status, 'details': [bool(x) for x in details],
            'elapsed_seconds': time.monotonic() - started, 'repeat': repeat,
            'test_limits_unchanged': True, 'historical_records_changed': False})
        if repeat % 2 == 1:
            result = diagnose_timeout(problem, code, ref['plus'], ref['plus_time'],
                suite='extra', original_details=[True] * 34, outer_cap_seconds=180)
            durable_json(Path(a.out) / f'guard_{repeat}.json', result)
    durable_json(Path(a.out) / 'audit_complete.json', {'repeats': 3,
        'source_commit': a.source_commit, 'model_admitted': False,
        'new_model_outputs': 0, 'optimizer_updates': 0,
        'scope': 'paired measurement only; no new scoring rule or historical relabelling'})


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('continuation-root', 'references', 'data-json', 'data-sha256', 'out', 'source-commit'):
        p.add_argument('--' + name, required=True)
    p.add_argument('--_worker', action='store_true')
    a = p.parse_args()
    if sys.platform != 'linux' or os.environ.get('CUDA_VISIBLE_DEVICES') != '':
        raise ProfileError('isolated Linux CPU diagnostic required')
    if a._worker:
        if os.environ.get('Q2_PROFILE_PARENT_PID') != str(os.getppid()):
            raise ProfileError('owned diagnostic parent required')
        try:
            worker(a)
        except BaseException as exc:
            durable_json(Path(a.out) / 'audit_failure.json', {'error': repr(exc), 'model_admitted': False})
            os._exit(1)
        os._exit(0)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=False)
    durable_json(out / 'audit_intent.json', {'repeats': 3, 'cap_seconds': 780,
        'source_commit': a.source_commit, 'started_epoch': time.time(),
        'model_admitted': False, 'new_model_outputs': 0, 'optimizer_updates': 0})
    return launch_guarded([sys.executable, '-m', 'experiments.q2_supervision_migration.timing_audit',
        *sys.argv[1:], '--_worker'], out, 780, phase='cpu')


if __name__ == '__main__':
    raise SystemExit(main())

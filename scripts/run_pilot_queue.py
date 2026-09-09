"""Inspect a finite queue by default; execute only the explicitly selected phase.

The original cumulative ledger is mandatory. A failed calibration or job stops
the queue. Completed runs are retained; this is not a best-result search loop.
"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

from src.pilot_runtime import load_pilot_inputs, validate_pilot_job
from src.sft_data import sha256_file


def inspect_queue(queue, phase, ledger):
    if ledger['budget_id'] != queue['budget_id'] or ledger['authorized_gpu_seconds'] != 7200:
        raise ValueError('Cumulative authorization mismatch')
    if any(j['status'] == 'reserved' for j in ledger['jobs']):
        raise ValueError('Unresolved job reservation')
    if any(j['charged_seconds'] < 0 for j in ledger['jobs']):
        raise ValueError('Invalid negative charge')
    used = sum(j['charged_seconds'] for j in ledger['jobs'])
    if used < queue['minimum_prior_charged_seconds']:
        raise ValueError('Missing or stale migration ledger')
    jobs = queue[phase]
    required = sum(j['max_seconds'] + 15 for j in jobs)
    if required > ledger['authorized_gpu_seconds'] - used:
        raise ValueError('Insufficient budget for the complete phase; do not shorten an arm')
    if len({j['run_id'] for j in jobs}) != len(jobs):
        raise ValueError('Duplicate queue run IDs')
    previous = {j['run_id'] for j in ledger['jobs']}
    if previous & {j['run_id'] for j in jobs}:
        raise ValueError('Run ID already charged; retain it and create a reviewed recovery queue')
    return {'used_seconds': used, 'remaining_seconds': 7200-used, 'phase_reservation_seconds': required,
            'jobs': len(jobs)}


def check_calibration(queue):
    root = Path('runs')/queue['calibration'][0]['run_id']
    manifest = json.loads((root/'run_manifest.json').read_text())
    metrics = json.loads((root/'metrics.json').read_text())
    receipt = json.loads((root/'resource_receipt.json').read_text())
    cfg = json.loads(Path(queue['calibration'][0]['config']).read_text())
    if (manifest['status'] != 'completed' or receipt['status'] != 'completed'
            or manifest['config'] != cfg or metrics['steps'] != cfg['steps']
            or not metrics['pilot_gate']['passed']):
        raise ValueError('Calibration did not pass at the complete frozen dose; stop for diagnosis')
    return root


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--queue', default='configs/pilot_v1/queue.json')
    p.add_argument('--phase', choices=['calibration', 'comparison'], default='calibration')
    p.add_argument('--ledger', default='.local/resource_ledger.json')
    p.add_argument('--execute', action='store_true')
    a = p.parse_args()
    queue = json.loads(Path(a.queue).read_text())
    ledger = json.loads(Path(a.ledger).read_text())  # Never initialize a fresh ledger here.
    summary = inspect_queue(queue, a.phase, ledger)
    common = None
    for job in queue[a.phase]:
        cfg = json.loads(Path(job['config']).read_text())
        if sha256_file(job['config']) != job['config_sha256']:
            raise ValueError('Queue configuration changed')
        linked_queue, _ = validate_pilot_job(cfg, job['run_id'], job['config'])
        if linked_queue != Path(a.queue):
            raise ValueError('Config references a different queue')
        load_pilot_inputs(cfg)
        signature = {k: v for k, v in cfg.items() if k not in ('arm',)}
        if common is not None and signature != common:
            raise ValueError('Scientific arms differ outside their treatment')
        common = signature
    if a.phase == 'comparison' and a.execute:
        check_calibration(queue)
    summary.update(phase=a.phase, execute=a.execute, calibration_required_before_comparison=True)
    print(json.dumps(summary, indent=2), flush=True)
    if not a.execute:
        return
    minimum_gib = queue.get('minimum_free_disk_gib', 30)
    if a.phase == 'comparison' and shutil.disk_usage('runs').free < minimum_gib * 1024**3:
        raise RuntimeError(f'Need {minimum_gib} GiB free for the frozen phase checkpoints and write headroom; verify backups before freeing space')
    for job in queue[a.phase]:
        subprocess.run([sys.executable, 'scripts/run_bounded.py', '--ledger', a.ledger,
                        '--run-id', job['run_id'], '--max-seconds', str(job['max_seconds']), '--',
                        sys.executable, '-m', 'src.experiment', '--config', job['config'],
                        '--out', 'runs/'+job['run_id']], check=True)
        # A completed subprocess must also have complete result artifacts.
        root = Path('runs')/job['run_id']
        metrics = json.loads((root/'metrics.json').read_text())
        cfg = json.loads(Path(job['config']).read_text())
        if metrics['steps'] != cfg['steps']:
            raise ValueError('Incomplete dose: do not continue')
        if a.phase == 'calibration':
            check_calibration(queue)


if __name__ == '__main__':
    main()

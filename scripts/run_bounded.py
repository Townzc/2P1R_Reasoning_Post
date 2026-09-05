"""Single-GPU subprocess budget guard, persistent conservative reservations.

All model runs must go through this wrapper. The lock prevents concurrent jobs.
Reservations survive wrapper crashes; reconcile manually instead of resetting.
"""
import argparse
import datetime
import fcntl
import json
import math
import os
from pathlib import Path
import signal
import shutil
import subprocess
import sys
import time


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--run-id', required=True)
    p.add_argument('--max-seconds', type=int, required=True)
    p.add_argument('--ledger', default='.local/resource_ledger.json')
    p.add_argument('--budget', default='configs/resource_budget.json')
    p.add_argument('command', nargs=argparse.REMAINDER)
    a = p.parse_args()
    command = a.command[1:] if a.command[:1] == ['--'] else a.command
    if not command or a.max_seconds <= 0 or Path(a.run_id).name != a.run_id or a.run_id in ('.', '..'):
        p.error('Need a command, a safe run-id and positive timeout')
    budget = json.loads(Path(a.budget).read_text())
    timeout = shutil.which('timeout')
    if not timeout or budget['gpus'] != 1:
        raise RuntimeError('Single GPU and GNU timeout are required')
    ledger_path = Path(a.ledger)
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    with ledger_path.with_suffix('.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        ledger = json.loads(ledger_path.read_text()) if ledger_path.exists() else {
            'budget_id': budget['budget_id'], 'authorized_gpu_seconds': budget['authorized_gpu_seconds'], 'jobs': []}
        if ledger['budget_id'] != budget['budget_id'] or ledger['authorized_gpu_seconds'] != budget['authorized_gpu_seconds']:
            raise ValueError('Ledger authorization mismatch')
        if any(x['status'] == 'reserved' for x in ledger['jobs']):
            raise RuntimeError('Unresolved reservation: check running processes and reconcile before continuing')
        if any(x['charged_seconds'] < 0 for x in ledger['jobs']):
            raise ValueError('Invalid negative ledger charge')
        if a.run_id in {x['run_id'] for x in ledger['jobs']}:
            raise ValueError('Run ID already recorded')
        remaining = budget['authorized_gpu_seconds'] - sum(x['charged_seconds'] for x in ledger['jobs'])
        seconds = min(a.max_seconds, remaining-15)
        if seconds <= 0:
            raise RuntimeError('No approved GPU runtime remains')
        out = Path('runs')/a.run_id
        out.mkdir(parents=True, exist_ok=False)
        entry = {'run_id': a.run_id, 'status': 'reserved', 'max_seconds': seconds,
                 'charged_seconds': seconds+15, 'command': command,
                 'started_at': datetime.datetime.now(datetime.timezone.utc).isoformat()}
        ledger['jobs'].append(entry)
        def save():
            temporary = ledger_path.with_suffix('.tmp')
            temporary.write_text(json.dumps(ledger, indent=2)+'\n')
            temporary.replace(ledger_path)
        save()
        start, proc, code = time.monotonic(), None, 1
        try:
            with (out/'stdout.log').open('w') as log:
                env = dict(os.environ, CUDA_VISIBLE_DEVICES='0', PYTHONUNBUFFERED='1', CS294_BOUNDED_RUN_ID=a.run_id)
                # Independent watchdog remains alive even if this Python wrapper is killed.
                guarded = [timeout, '--signal=TERM', '--kill-after=5s', str(seconds), *command]
                proc = subprocess.Popen(guarded, stdout=log, stderr=subprocess.STDOUT, env=env, start_new_session=True)
                try:
                    code = proc.wait(timeout=seconds+10)
                    entry['status'] = 'completed' if code == 0 else ('timeout' if code in (124, 137) else 'failed')
                except subprocess.TimeoutExpired:
                    entry['status'] = 'timeout'
                    code = 124
        finally:
            if proc is not None and proc.poll() is None:
                os.killpg(proc.pid, signal.SIGTERM)
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait()
            entry['elapsed_seconds'] = time.monotonic()-start
            entry['charged_seconds'] = math.ceil(entry['elapsed_seconds'])
            entry['exit_code'] = code
            if entry['status'] == 'reserved':
                entry['status'] = 'interrupted'
            save()
            (out/'resource_receipt.json').write_text(json.dumps(entry, indent=2)+'\n')
        print(json.dumps(entry, indent=2))
        return code


if __name__ == '__main__':
    sys.exit(main())

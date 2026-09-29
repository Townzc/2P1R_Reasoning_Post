"""Launch resumable, finite worker slices under one persistent rental budget."""
from __future__ import annotations

import argparse
import fcntl
import importlib.metadata
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

from experiments.thursday_probe.common import stamp, verify_manifest
from experiments.thursday_probe_v2.config import OLD_LEDGER_HASH
from experiments.thursday_probe_v2.resume_diagnostics import RESUME_RELEASE, load_generation_rows
from experiments.thursday_probe_v2.resume_resources import (
    RentalBudget, ResumeGenerationBudget, PROCESS_SLICE_SECONDS)
from experiments.thursday_probe_v2.training import atomic_json
from src.sft_data import sha256_file

OUT = Path('runs/thursday_arithmetic_resume_r1')
RUN_ID = 'thursday_arithmetic_resume_r1'
GUARD_SECONDS = 15
MIN_USEFUL_SECONDS = 600
LOAD_ALLOWANCE_SECONDS = 120


def source():
    from experiments.thursday_probe_v2.queue import source as original_source
    record = original_source()
    # The existing publication check ignores untracked outputs. Require every
    # executable source it inventories to be tracked by the published commit.
    subprocess.check_call(['git', 'ls-files', '--error-unmatch', '--',
                           *record['source_files_sha256']], stdout=subprocess.DEVNULL)
    return record


def load_inputs():
    from experiments.thursday_probe_v2.queue import load_inputs as original_load
    return original_load()


def server_preflight(configuration, snapshot):
    from scripts.run_relation_engineering import server_preflight as original_preflight
    return original_preflight(configuration, snapshot)


def _immutable_json(path, record):
    with Path(path).open('x') as stream:
        json.dump(record, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n'); stream.flush(); os.fsync(stream.fileno())


def _validate_initial_checkpoint(checkpoint):
    checkpoint = Path(checkpoint)
    identity = json.loads((checkpoint/'checkpoint_identity.json').read_text())
    expected = json.loads(Path('runs/thursday_arithmetic_v2_r2/run_manifest_final.json').read_text())['initial_adapter']
    if (identity['parameter_digest'] != expected['parameter_digest'] or
            identity['files_sha256'].get('adapter_model.safetensors') !=
            expected['files_sha256']['adapter_model.safetensors']):
        raise ValueError('Continuation must start from the preserved original C0, never E030')
    for name, expected_hash in identity['files_sha256'].items():
        if Path(name).is_absolute() or '..' in Path(name).parts:
            raise ValueError('Unsafe checkpoint inventory path')
        if sha256_file(checkpoint/name) != expected_hash:
            raise ValueError('Initial checkpoint differs from its saved identity')
    return identity


def slice_seconds(remaining, now=None):
    """Leave the 1,500-second rental reserve and hard-kill guard untouched."""
    now = time.time() if now is None else now
    cap = math.floor(min(PROCESS_SLICE_SECONDS,
                         remaining['worker_deadline_epoch'] - now - GUARD_SECONDS))
    return cap if cap >= MIN_USEFUL_SECONDS + LOAD_ALLOWANCE_SECONDS else None


def _receipts(output):
    attempts = sorted((output/'attempts').glob('attempt_*')) if (output/'attempts').exists() else []
    receipts = []
    for number, directory in enumerate(attempts, 1):
        if directory.name != f'attempt_{number:06d}':
            raise ValueError('Attempt history is not contiguous; never renumber/reset it')
        if not (directory/'resource_receipt.json').exists():
            raise ValueError('Unreconciled prior worker attempt; inspect it before continuing')
        record = json.loads((directory/'resource_receipt.json').read_text())
        if (record['attempt'] != number or record['run_id'] != RUN_ID or
                record['charged_seconds'] != math.ceil(record['wall_seconds']) or
                not record['historical_ledger_unchanged']):
            raise ValueError('Invalid prior attempt receipt')
        receipts.append(record)
    return receipts


def _export(output):
    """Atomically refresh the full byte inventory after each child has exited."""
    target = output/'export_manifest_final.json'
    paths = [p for p in sorted(output.rglob('*')) if p.is_file() and p != target]
    if any(p.name.endswith('.pending') for p in paths):
        # A pending file is evidence after a fault and must be retained/exported.
        pass
    record = dict(created_at_utc=stamp(), files={str(p.relative_to(output)):
        dict(sha256=sha256_file(p), bytes=p.stat().st_size) for p in paths})
    atomic_json(target, record)
    return record


def _work_state(output, budget):
    return (budget.used, tuple((str(p.relative_to(output)), p.stat().st_size, p.stat().st_mtime_ns)
            for p in sorted(output.rglob('*')) if p.is_file() and
            p.suffix in ('.jsonl', '.pt', '.safetensors')))


def _run_worker(command, environment, stream):
    process = subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT,
                               env=environment, start_new_session=True)
    try:
        return process.wait()
    except BaseException:
        # A parent interruption must not leave a detached CUDA worker alive.
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            process.wait(timeout=GUARD_SECONDS)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
        raise


def _phase_summary(output, receipts, status, budget, rental):
    charged = sum(r['charged_seconds'] for r in receipts)
    atomic_json(output/'phase_ledger.json', dict(
        phase=RUN_ID, status=status, receipts=len(receipts),
        attempt_charged_seconds=charged, prior_receipts=24,
        prior_charged_seconds=8915, total_receipts_across_phases=24+len(receipts),
        total_charged_seconds_across_phases=8915+charged,
        generation_attempts=budget.used, active_worker=False,
        rental=rental.remaining(), provider_shutdown_confirmed=False,
        shutdown_note='Child exit does not establish provider shutdown or stop billing.'))


def launch(snapshot, initial_checkpoint, old_ledger, power_on_at_utc, current_rate, *, output=OUT):
    """Automatically continue only clean code-75 pauses with useful time left.

    Returns 0 for a completed queue, 75 for a recoverable resource pause, and
    the worker fault code otherwise. Provider shutdown is handled externally.
    """
    provenance = source(); load_inputs()
    diagnostic = verify_manifest(RESUME_RELEASE)
    if len(load_generation_rows()) != 16 or diagnostic['endpoint_generations'] != 64:
        raise ValueError('Frozen diagnostic generation registration differs')
    if sha256_file(old_ledger) != OLD_LEDGER_HASH:
        raise ValueError('Historical ledger differs; never reset it')
    initial = _validate_initial_checkpoint(initial_checkpoint)
    output = Path(output); output.mkdir(parents=True, exist_ok=True)
    with (output/'launcher.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError('A launcher already owns this continuation') from exc
        receipts = _receipts(output)
        if receipts and not (output/'generation_ledger.json').exists():
            raise ValueError('Missing cumulative generation ledger; refuse a reset')
        if receipts and not (output/'rental_budget.json').exists():
            raise ValueError('Missing cumulative rental ledger; refuse a reset')
        budget = ResumeGenerationBudget(output/'generation_ledger.json')
        rental = RentalBudget(output/'rental_budget.json', power_on_at_utc, current_rate)
        if receipts and receipts[-1]['status'] == 'completed':
            return 0
        while True:
            remaining = rental.remaining()
            cap = slice_seconds(remaining)
            if cap is None or budget.used >= 4864:
                _phase_summary(output, receipts, 'paused_resource_limit', budget, rental)
                _export(output)
                return 75
            minimum_disk = 4.5 if not receipts else 1.25
            server = server_preflight({'min_free_gib': minimum_disk}, Path(snapshot))
            if importlib.metadata.version('peft') != '0.17.1':
                raise ValueError('Pinned PEFT 0.17.1 required')
            remaining = rental.remaining(); cap = slice_seconds(remaining)
            if cap is None:
                _phase_summary(output, receipts, 'paused_after_preflight', budget, rental)
                _export(output)
                return 75
            attempt = len(receipts)+1
            directory = output/'attempts'/f'attempt_{attempt:06d}'
            directory.mkdir(parents=True, exist_ok=False)
            deadline = time.time()+cap
            command = ['timeout', '--signal=TERM', f'--kill-after={GUARD_SECONDS}s', f'{cap}s',
                       sys.executable, '-m', 'experiments.thursday_probe_v2.resume_queue',
                       '--worker', '--snapshot', str(snapshot),
                       '--initial-checkpoint', str(initial_checkpoint)]
            public_command = command[:4]+['PINNED_RUNTIME']+command[5:9]+['PINNED_MODEL_SNAPSHOT',
                            '--initial-checkpoint', 'PRESERVED_C0_CHECKPOINT']
            intent = dict(attempt=attempt, run_id=RUN_ID, started_at_utc=stamp(),
                          process_cap_seconds=cap, guard_seconds=GUARD_SECONDS,
                          worker_deadline_epoch=deadline,
                          global_worker_deadline_epoch=remaining['worker_deadline_epoch'],
                          historical_ledger_sha256=OLD_LEDGER_HASH,
                          generation_attempts_before=budget.used,
                          initial_adapter=initial['parameter_digest'], command=public_command,
                          **provenance)
            _immutable_json(directory/'intent.json', intent)
            _immutable_json(directory/'preflight.json', dict(server=server,
                            minimum_free_disk_gib=minimum_disk, rental=remaining,
                            diagnostic_manifest_sha256=sha256_file(RESUME_RELEASE/'manifest.json')))
            environment = {**os.environ, 'THU_RESUME_BOUNDED': RUN_ID,
                           'THU_RESUME_DEADLINE': str(deadline),
                           'THU_RESUME_GLOBAL_DEADLINE': str(remaining['worker_deadline_epoch']),
                           'TOKENIZERS_PARALLELISM': 'false', 'HF_HUB_OFFLINE': '1',
                           'TRANSFORMERS_OFFLINE': '1'}
            before = _work_state(output, budget); tick = time.monotonic()
            failure = None
            with (directory/'stdout.log').open('x') as stream:
                try:
                    code = _run_worker(command, environment, stream)
                except BaseException as exc:
                    code = 1
                    failure = dict(type=type(exc).__name__, message=str(exc))
                stream.flush(); os.fsync(stream.fileno())
            elapsed = time.monotonic()-tick
            unchanged = sha256_file(old_ledger) == OLD_LEDGER_HASH
            effective_code = code if unchanged else 1
            status = 'completed' if effective_code == 0 else 'paused_resumable' if effective_code == 75 else 'fault_stop'
            receipt = dict(attempt=attempt, run_id=RUN_ID, status=status,
                           exit_code=effective_code, worker_exit_code=code,
                           wall_seconds=elapsed, charged_seconds=math.ceil(elapsed),
                           process_cap_seconds=cap, guard_seconds=GUARD_SECONDS,
                           started_at_utc=intent['started_at_utc'], finished_at_utc=stamp(),
                           historical_ledger_sha256=OLD_LEDGER_HASH,
                           historical_ledger_unchanged=unchanged,
                           generation_attempts_after=budget.used,
                           source_commit=provenance['source_commit'], failure=failure,
                           command=public_command)
            _immutable_json(directory/'resource_receipt.json', receipt)
            receipts.append(receipt)
            _phase_summary(output, receipts, status, budget, rental)
            _export(output)
            print(json.dumps(receipt, sort_keys=True), flush=True)
            if effective_code != 75:
                return effective_code
            if _work_state(output, budget) == before:
                # Prevent repeated reloads if the next unit did not fit or no
                # durable progress was possible. A new window may resume later.
                return 75


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['launch'])
    parser.add_argument('--snapshot', required=True)
    parser.add_argument('--initial-checkpoint', required=True)
    parser.add_argument('--old-ledger', required=True)
    parser.add_argument('--power-on-at-utc', required=True)
    parser.add_argument('--current-rate', required=True, type=float)
    args = parser.parse_args()
    sys.exit(launch(args.snapshot, args.initial_checkpoint, args.old_ledger,
                    args.power_on_at_utc, args.current_rate))

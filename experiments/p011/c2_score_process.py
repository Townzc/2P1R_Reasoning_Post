"""Prepared one-use local P011 C2 new-only scoring supervisor, not A3 acceptance.

The future full driver must first verify the original model's complete proof,
the exact source/input reviews and a numerical local-time admission. This helper
only isolates that already-authorized scoring operation in an owned POSIX
process group. It grants no review, result adjudication or G1 permission.
An existing control directory, even an empty or failed one, blocks replay.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

MODULE = 'experiments.p011.c2_score_process'
SOURCES = (
    'experiments/p011/c2_score_process.py',
    'experiments/p011/c2_scoring.py',
)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def create(path, value):
    # A torn or incomplete record remains visible and cannot be overwritten.
    path = Path(path)
    with path.open('xb') as stream:
        stream.write(canonical(value)+b'\n')
        stream.flush()
        os.fsync(stream.fileno())
    fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def command(root):
    return [sys.executable, '-m', MODULE, '--owned-worker', str(root)]


def kill_owned_group(process):
    """Only the group created by our own start_new_session=True Popen."""
    signalled = False
    try:
        os.killpg(process.pid, signal.SIGKILL)
        signalled = True
    except ProcessLookupError:
        pass
    process.wait(timeout=5)
    return signalled


def group_alive(pgid):
    try:
        os.killpg(pgid, 0)
        return True
    except ProcessLookupError:
        return False


def supervise_once(root, rows, binding, local_seconds):
    """Bound the whole child lifetime; retain partial evidence, never retry.

    No raw decode, model state load or symbolic comparison occurs in this
    parent. The small two-file snapshot below is an integrity check between
    parent and child, not the future full transitive source review.
    """
    if (os.name != 'posix' or not isinstance(rows, list) or not 1 <= len(rows) <= 2800
            or not isinstance(binding, dict) or not binding
            or type(local_seconds) is not int or not 0 < local_seconds <= 28000):
        raise ValueError('Complete new bounded window rows, explicit binding and bounded POSIX window required')
    canonical(rows); canonical(binding)
    sources = {name:sha(name) for name in SOURCES}
    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=False)
    started = time.monotonic(); deadline = started+local_seconds
    process = None
    try:
        create(root/'ROWS.json', rows)
        create(root/'BINDING.json', binding)
        create(root/'INTENT.json', dict(utc=datetime.now(timezone.utc).isoformat(),
            rows_sha256=sha(root/'ROWS.json'), binding_sha256=sha(root/'BINDING.json'),
            local_seconds=local_seconds, source_files=sources, automatic_retry=False,
            full_runtime_lineage_admission_checked=False, payload_only=True,
            child_inner_window_seconds=local_seconds,
            parent_window_includes_input_writes_and_child_startup=True,
            owned_process_group=True, cleanup_after_cutoff_max_seconds=5))
        if time.monotonic() >= deadline:
            raise TimeoutError('Original local window expired before child launch')
        with (root/'worker.log').open('xb') as log:
            process = subprocess.Popen(command(root), stdout=log, stderr=subprocess.STDOUT,
                                       start_new_session=True)
            create(root/'CHILD.json', dict(pid=process.pid, pgid=process.pid,
                new_session=True, elapsed_after_spawn_seconds=time.monotonic()-started))
            remaining = deadline-time.monotonic()
            if remaining <= 0:
                raise TimeoutError('Original local window expired during child startup')
            code = process.wait(timeout=remaining)
        if code != 0:
            raise RuntimeError(f'Original scoring child exited {code}; no retry')
        # Python's owned resource tracker can take a moment to exit after its
        # parent closes. This wait is inside, not added to, the original cap.
        reap_deadline = min(deadline, time.monotonic()+1)
        while group_alive(process.pid) and time.monotonic() < reap_deadline:
            time.sleep(min(.02, max(0, reap_deadline-time.monotonic())))
        elapsed = time.monotonic()-started
        if elapsed >= local_seconds:
            raise TimeoutError('Child completion exceeded the original local window')
        # An exited parent with a surviving pool is incomplete cleanup, not success.
        if kill_owned_group(process):
            raise RuntimeError('Scoring child left descendants; owned group terminated')
        done = read(root/'CHILD_COMPLETED.json')
        if (done['intent_sha256'] != sha(root/'INTENT.json')
                or done['payload_sha256'] != sha(root/'payload/COMPLETED.json')
                or (root/'payload/FAILED.json').exists()):
            raise ValueError('Complete original child proof is missing or inconsistent')
        result = dict(child_exit_code=code, child_lifetime_with_startup_seconds=elapsed,
            local_seconds=local_seconds, child_proof_sha256=sha(root/'CHILD_COMPLETED.json'),
            payload_complete_sha256=done['payload_sha256'],
            payload_only=True, full_runtime_lineage_admission_checked=False,
            independent_adjudication_complete=False, independent_A3_pending=True,
            automatic_retry=False, new_model_calls=0,
            final_parent_record_write_excluded=True)
        create(root/'COMPLETED.json', result)
        return result
    except BaseException as exc:
        cleanup = None
        if process is not None:
            try:
                cleanup = dict(group_signalled=kill_owned_group(process),
                               child_exit_code=process.returncode)
            except BaseException as stop_error:
                cleanup = dict(unknown=True, type=type(stop_error).__name__, error=str(stop_error))
        create(root/'FAILED.json', dict(type=type(exc).__name__, error=str(exc),
            elapsed_seconds=time.monotonic()-started, cleanup=cleanup,
            partial_evidence_preserved=True, automatic_retry=False,
            complete_endpoint=False, failed_or_unknown_is_not_scored_zero=True))
        raise


def owned_worker(root):
    """Internal child entry; the parent creates all inputs before this process."""
    root = Path(root).resolve()
    intent = read(root/'INTENT.json')
    if (os.getpid() != os.getpgrp()
            or intent['source_files'] != {name:sha(name) for name in SOURCES}
            or intent['rows_sha256'] != sha(root/'ROWS.json')
            or intent['binding_sha256'] != sha(root/'BINDING.json')):
        raise ValueError('Owned process group or original input/source binding differs')
    create(root/'CHILD_STARTED.json', dict(pid=os.getpid(), pgid=os.getpgrp(),
        intent_sha256=sha(root/'INTENT.json'), automatic_retry=False))
    from experiments.p011.c2_scoring import score_once
    score_once(root/'payload', read(root/'ROWS.json'), read(root/'BINDING.json'),
                        intent['local_seconds'])
    create(root/'CHILD_COMPLETED.json', dict(intent_sha256=sha(root/'INTENT.json'),
        payload_sha256=sha(root/'payload/COMPLETED.json')))


if __name__ == '__main__':
    # No public scoring/admission CLI. A future reviewed driver calls the parent.
    if len(sys.argv) != 3 or sys.argv[1] != '--owned-worker':
        raise SystemExit('Only an owned child of the reviewed future driver is supported')
    owned_worker(sys.argv[2])

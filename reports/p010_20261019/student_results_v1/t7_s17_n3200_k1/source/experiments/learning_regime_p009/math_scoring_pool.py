"""Bounded CPU scheduling candidate; the accepted scalar scoring rules stay intact.

No model calls or training. Exact (gold, extracted answer) pairs share one
symbolic attempt, including a failed/timed-out attempt. Every input row retains
its own stop rule and provenance. Not admitted for actual P1 until reviewed.
"""
from collections import deque
from copy import deepcopy
import hashlib
import importlib.metadata
import json
import multiprocessing
from multiprocessing.connection import wait
import time

from experiments.learning_regime_p009.math_scoring import (
    VERSIONS, decide, last_box, symbolic,
)

VERSION = 'p009_persistent_math_pair_pool_candidate_v1'
MAX_WORKERS = 2
TASK_SECONDS = 8.0
STARTUP_SECONDS = 30.0
STOPS = ('native_eos', 'new_problem_boundary', 'length_cap', 'invalid_special_token')


def pair_digest(pair):
    return hashlib.sha256(json.dumps(pair, ensure_ascii=False,
        separators=(',', ':')).encode()).hexdigest()


def _worker_main(connection):
    """Signals in math-verify run in each process's main thread, not a thread pool."""
    try:
        actual = {name: importlib.metadata.version(name) for name in VERSIONS}
        if actual != VERSIONS:
            connection.send({'ready': False, 'versions': actual})
            return
        # Pay imports once, and include their wall time in the startup record.
        import math_verify  # noqa: F401
        connection.send({'ready': True, 'versions': actual})
        while True:
            task = connection.recv()
            if task is None:
                return
            key, gold, answer = task
            connection.send({'pair_id': key, 'result': symbolic(gold, answer)})
    except (EOFError, BrokenPipeError):
        pass
    finally:
        connection.close()


class SymbolicPool:
    """One bounded, serially used session; no cross-session or disk cache.

    Workers may be replaced after a crash/outer timeout, but that original
    pair's failure is final in this session. A replacement handles only future
    distinct pairs. Closing the context terminates all processes.
    """

    def __init__(self):
        self.ctx = multiprocessing.get_context('spawn')
        self.workers = []
        self.cache = {}
        self.row_ids = set()
        self.attempts = []
        self.startups = []
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def _start(self):
        parent, child = self.ctx.Pipe(duplex=True)
        proc = self.ctx.Process(target=_worker_main, args=(child,), daemon=False)
        started = time.monotonic()
        try:
            proc.start()
            child.close()
            ready = parent.recv() if parent.poll(STARTUP_SECONDS) else None
            if ready != {'ready': True, 'versions': VERSIONS}:
                raise RuntimeError('Scorer worker environment/startup failed; not a scored zero')
        except BaseException:
            child.close()
            parent.close()
            if proc.pid is not None:
                if proc.is_alive():
                    proc.kill()
                proc.join(timeout=2)
            raise
        self.startups.append({'pid': proc.pid, 'seconds': time.monotonic() - started,
                              'versions': ready['versions']})
        worker = {'process': proc, 'connection': parent, 'task': None}
        self.workers.append(worker)
        return worker

    def _retire(self, worker):
        proc, conn = worker['process'], worker['connection']
        try:
            if proc.is_alive():
                proc.kill()
            proc.join(timeout=2)
        finally:
            conn.close()
            self.workers.remove(worker)
        if proc.is_alive():
            raise RuntimeError('Failed to terminate scorer child; abort before replacement')

    def _finish(self, worker, result, *, retire=False):
        key, pair, started = worker['task']
        # The accepted decision function validates status/value before caching.
        decide(pair[0], {'answer': pair[1]}, result, stop_reason='native_eos')
        if pair in self.cache:
            raise RuntimeError('A pair must never receive two symbolic attempts')
        observation = {'pair_id': key, 'symbolic': deepcopy(result),
            'worker_pid': worker['process'].pid,
            'elapsed_seconds': time.monotonic() - started,
            'attempt_index': len(self.attempts)}
        self.attempts.append(observation)
        self.cache[pair] = observation
        worker['task'] = None
        if retire:
            self._retire(worker)

    def score_rows(self, rows):
        """Return every row, in input order, without altering selection or costs.

        Caller supplies complete answer segments after original stop validation.
        Required fields: id, gold, answer_segment, stop_reason. Across calls the
        same session rejects duplicate row IDs; exact answer-pair reuse is fine.
        Timing for the first 100 actual rows must be reviewed before a full pass.
        """
        if self.closed:
            raise RuntimeError('Scoring session is closed')
        prepared = []
        pending = deque()
        seen_pairs = set(self.cache)
        ids = set()
        for row in rows:
            row_id = row.get('id')
            if not isinstance(row_id, str) or not row_id or row_id in ids | self.row_ids:
                raise ValueError('Missing/duplicate row identity')
            if not isinstance(row.get('gold'), str) or not row['gold'].strip():
                raise ValueError('Unsupported gold is not a scored zero')
            if (row.get('stop_reason') not in STOPS or
                    not isinstance(row.get('answer_segment'), str)):
                raise ValueError('Unknown/incomplete answer must be reconciled')
            ids.add(row_id)
            extracted = last_box(row['answer_segment'])
            pair = None
            if (row['stop_reason'] in ('native_eos', 'new_problem_boundary') and
                    extracted['answer']):
                pair = (row['gold'], extracted['answer'])
                if pair not in seen_pairs:
                    pending.append(pair)
                    seen_pairs.add(pair)
            prepared.append((row, extracted, pair))
        # Mark identities before any attempt; a failed call cannot be repeated.
        self.row_ids.update(ids)
        started = time.monotonic()
        original_attempt_count = len(self.attempts)
        try:
            while pending or any(w['task'] is not None for w in self.workers):
                # Readiness can wait up to 30 s. Never wait for a replacement
                # while another pair's 8 s outer deadline is running.
                while (pending and len(self.workers) < MAX_WORKERS and
                       not any(w['task'] is not None for w in self.workers)):
                    self._start()
                for worker in list(self.workers):
                    if pending and worker['task'] is None:
                        pair = pending.popleft()
                        key = pair_digest(pair)
                        worker['task'] = (key, pair, time.monotonic())
                        try:
                            worker['connection'].send((key, *pair))
                        except (BrokenPipeError, EOFError, OSError):
                            self._finish(worker, {'status': 'tool_error', 'equivalent': None,
                                'error_type': 'worker_send_failure'}, retire=True)
                active = [w for w in self.workers if w['task'] is not None]
                if not active:
                    continue
                delay = max(0., min(.1, min(TASK_SECONDS - (time.monotonic() - w['task'][2])
                                             for w in active)))
                ready = wait([w['connection'] for w in active], timeout=delay)
                for worker in active:
                    if worker['connection'] in ready:
                        try:
                            message = worker['connection'].recv()
                        except (EOFError, OSError):
                            self._finish(worker, {'status': 'tool_error', 'equivalent': None,
                                'error_type': 'worker_eof'}, retire=True)
                            continue
                        if (not isinstance(message, dict) or
                                message.get('pair_id') != worker['task'][0] or
                                not isinstance(message.get('result'), dict)):
                            raise RuntimeError('Mismatched scorer result protocol')
                        self._finish(worker, message['result'])
                    elif time.monotonic() - worker['task'][2] >= TASK_SECONDS:
                        self._finish(worker, {'status': 'outer_timeout', 'equivalent': None},
                                     retire=True)
            output = []
            for row, extracted, pair in prepared:
                observation = self.cache[pair] if pair is not None else None
                result = decide(row['gold'], extracted,
                    observation['symbolic'] if observation else {}, stop_reason=row['stop_reason'])
                output.append({'id': row['id'], 'score': result,
                    'symbolic_attempt': deepcopy(observation),
                    'pair_id': pair_digest(pair) if pair is not None else None})
            return {'pool_version': VERSION, 'rows': output,
                'new_symbolic_attempts': len(self.attempts) - original_attempt_count,
                'unique_pairs_in_session': len(self.cache),
                'rows_in_session': len(self.row_ids),
                'call_elapsed_seconds': time.monotonic() - started,
                'startup_observations': deepcopy(self.startups)}
        except BaseException:
            self.close()
            raise

    def close(self):
        if self.closed:
            return
        self.closed = True
        for worker in list(self.workers):
            self._retire(worker)

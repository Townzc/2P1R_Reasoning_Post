"""Future P008 students only: fresh, bounded reads before every work unit.

No reads are cached across checks. Admission, atomic writes and terminal writes
remain with the original RunGuard. Like the original sequential reads, this is
not a transactional snapshot and cannot eliminate a concurrent terminal race.
The original validator runs unchanged against the complete fetched records.
"""
from concurrent.futures import ThreadPoolExecutor
from copy import copy, deepcopy
import time

from experiments.sft_allocation_midpoint.guard import GuardError, identity_hash


class _ReadSet:
    def __init__(self, records):
        self.records = records

    def get(self, key, default=None):
        if key not in self.records:
            raise GuardError("active validation requested an unfetched key")
        return deepcopy(self.records[key])

    def put(self, *args, **kwargs):
        raise GuardError("active read set cannot write")


class ParallelActiveCheck:
    def __init__(self, guard, *, clock=time.time, monotonic=time.monotonic,
                 readers=8, read_timeout=15.0):
        if type(readers) is not int or not 1 <= readers <= 8:
            raise ValueError("at most eight readers")
        if not 0 < read_timeout <= 15:
            raise ValueError("at most fifteen seconds for one read set")
        self.guard = guard
        self.clock = clock
        self.monotonic = monotonic
        self.read_timeout = read_timeout
        self.pool = ThreadPoolExecutor(max_workers=readers)
        self.failed = False
        self.metrics = dict(checks=0, remote_reads=0, seconds=0.0,
                            max_seconds=0.0, readers=readers,
                            cache_across_checks=False, transactional_snapshot=False)

    def check_active(self, admission, *, spent_cents, next_cost_cents=0):
        if self.failed:
            raise GuardError("failed read check cannot be reused")
        g = self.guard
        futures = []
        tick = self.monotonic()
        try:
            if identity_hash(g.plan) != g.plan_hash:
                raise GuardError("in-memory plan was changed")
            keys = [g._key("campaign"), g._key("claim", admission.run_id),
                    g._key("attempt", admission.run_id + "/" + admission.attempt_id),
                    g._key("terminal", admission.run_id)]
            keys += [g._key("reconciliation", run) for run in g.plan["slots"]]
            futures = [self.pool.submit(g.store.get, key) for key in keys]
            records = {}
            for key, future in zip(keys, futures):
                left = self.read_timeout - (self.monotonic() - tick)
                if left <= 0:
                    raise TimeoutError("active read deadline exceeded")
                records[key] = future.result(timeout=left)
            # Keep the ORIGINAL immutable plan hash and all validator logic;
            # rebuilding RunGuard from a mutated plan would lose that check.
            validator = copy(g)
            validator.store = _ReadSet(records)
            validator.check_active(admission, now_epoch=self.clock(),
                                   spent_cents=spent_cents,
                                   next_cost_cents=next_cost_cents)
            elapsed = self.monotonic() - tick
            if elapsed >= self.read_timeout:
                raise TimeoutError("active read deadline exceeded")
            self.metrics["checks"] += 1
            self.metrics["remote_reads"] += len(keys)
            self.metrics["seconds"] += elapsed
            self.metrics["max_seconds"] = max(self.metrics["max_seconds"], elapsed)
        except BaseException:
            self.failed = True
            for future in futures:
                future.cancel()
            raise

    def close(self):
        # A stalled SDK read cannot authorize work; the existing worker hard
        # timer still bounds process lifetime. Never wait indefinitely here.
        self.pool.shutdown(wait=False, cancel_futures=True)

"""Fresh child ownership AND original parent dependencies in one bounded read set."""
from copy import copy, deepcopy
from experiments.sft_allocation_midpoint.guard import GuardError, identity_hash
from .parallel_guard import ParallelActiveCheck, _ReadSet


class ContinuationActiveCheck(ParallelActiveCheck):
    def __init__(self, guard, parent_records, **kwargs):
        super().__init__(guard, **kwargs)
        self.parent_records = deepcopy(parent_records)
        self.parent_records_hash = identity_hash(parent_records)

    def check_active(self, admission, *, spent_cents, next_cost_cents=0):
        if self.failed:
            raise GuardError('failed complete check cannot be reused')
        g = self.guard; futures = []; tick = self.monotonic()
        try:
            if identity_hash(g.plan) != g.plan_hash or identity_hash(self.parent_records) != self.parent_records_hash:
                raise GuardError('in-memory child or parent binding changed')
            keys = [g._key('campaign'), g._key('claim', admission.run_id),
                    g._key('attempt', admission.run_id+'/'+admission.attempt_id),
                    g._key('terminal', admission.run_id)]
            keys += [g._key('reconciliation', run) for run in g.plan['slots']]
            keys += list(self.parent_records)
            if len(keys) != len(set(keys)):
                raise GuardError('overlapping parent and child key sets')
            futures = [self.pool.submit(g.store.get, key) for key in keys]
            records = {}
            for key, future in zip(keys, futures):
                left = self.read_timeout-(self.monotonic()-tick)
                if left <= 0: raise TimeoutError('complete read-set deadline exceeded')
                records[key] = future.result(timeout=left)
            if any(records[k] != v for k, v in self.parent_records.items()):
                raise GuardError('original parent/D1 dependency changed')
            validator = copy(g); validator.store = _ReadSet(records)
            validator.check_active(admission, now_epoch=self.clock(), spent_cents=spent_cents,
                                   next_cost_cents=next_cost_cents)
            elapsed = self.monotonic()-tick
            if elapsed >= self.read_timeout: raise TimeoutError('complete read-set deadline exceeded')
            self.metrics['checks'] += 1; self.metrics['remote_reads'] += len(keys)
            self.metrics['seconds'] += elapsed
            self.metrics['max_seconds'] = max(self.metrics['max_seconds'], elapsed)
            self.metrics['complete_keys_per_check'] = len(keys)
        except BaseException:
            self.failed = True
            for future in futures: future.cancel()
            raise

"""Fresh fencing and cost/deadline checks: CPU only, no provider mutations."""
import copy
import threading
import unittest

from experiments.sft_allocation_midpoint.guard import GuardError, RunGuard
from experiments.sft_allocation_p008.parallel_guard import ParallelActiveCheck
from tests.test_midpoint_guard import FakeAtomicStore, plan, intent


class ParallelGuardTests(unittest.TestCase):
    def setUp(self):
        self.store = FakeAtomicStore()
        self.g = RunGuard(self.store, plan())
        self.g.register(now_epoch=1000)
        self.a = self.g.admit(intent(), attempt_id='worker', now_epoch=1100,
                              max_runtime_seconds=100)
        self.p = ParallelActiveCheck(self.g, clock=lambda: 1101)
        self.addCleanup(self.p.close)

    def check(self):
        self.p.check_active(self.a, spent_cents=0, next_cost_cents=500)

    def test_read_only_full_key_set_every_check(self):
        before = copy.deepcopy(self.store.records)
        seen = []
        get = self.store.get
        self.store.get = lambda k: (seen.append(k), get(k))[1]
        self.check(); self.check()
        keys = [self.g._key('campaign'), self.g._key('claim', 'first'),
                self.g._key('attempt', 'first/worker'), self.g._key('terminal', 'first')]
        keys += [self.g._key('reconciliation', run) for run in self.g.plan['slots']]
        self.assertCountEqual(seen, keys * 2)
        self.assertEqual(before, self.store.records)
        self.assertEqual(self.p.metrics['checks'], 2)

    def test_terminal_after_previous_check_is_seen(self):
        self.check()
        self.g.finish(self.a, status='completed', evidence_sha256='d'*64,
                      actual_cost_cents=500, finished_epoch=1102)
        with self.assertRaisesRegex(GuardError, 'terminal'):
            self.check()

    def test_fencing_after_previous_check_is_seen(self):
        self.check()
        self.store.put(self.g._key('reconciliation', 'child'),
                       {'parent_run_id': 'first'}, skip_if_exists=True)
        with self.assertRaisesRegex(GuardError, 'fenced'):
            self.check()

    def test_missing_or_conflicting_records_rejected_as_original(self):
        original = copy.deepcopy(self.store.records)
        for key in original:
            if '/intent/' in key:
                continue  # unchanged active validator uses the owned claim/attempt
            for value in (None, {}):
                with self.subTest(key=key, value=value):
                    self.store.records = copy.deepcopy(original)
                    self.store.records[key] = value
                    p = ParallelActiveCheck(self.g, clock=lambda: 1101)
                    try:
                        with self.assertRaises(GuardError):
                            self.g.check_active(self.a, now_epoch=1101, spent_cents=0)
                        with self.assertRaises(GuardError):
                            p.check_active(self.a, spent_cents=0)
                    finally:
                        p.close()

    def test_plan_mutation_does_not_create_a_new_trusted_hash(self):
        self.g.plan['deadline_epoch'] = 2100
        with self.assertRaisesRegex(GuardError, 'plan was changed'):
            self.check()

    def test_expiry_is_checked_after_reads(self):
        now = [1101]
        self.p.clock = lambda: now[0]
        get = self.store.get
        def late(k):
            now[0] = 1200
            return get(k)
        self.store.get = late
        with self.assertRaisesRegex(GuardError, 'deadline'):
            self.check()

    def test_cost_overrun_rejected(self):
        with self.assertRaisesRegex(GuardError, 'reservation'):
            self.p.check_active(self.a, spent_cents=1, next_cost_cents=500)

    def test_read_error_fails_closed_and_disables_reuse(self):
        get = self.store.get
        def broken(k):
            if '/reconciliation/child' in k:
                raise OSError('injected transport failure')
            return get(k)
        self.store.get = broken
        with self.assertRaises(OSError):
            self.check()
        self.store.get = get
        with self.assertRaisesRegex(GuardError, 'cannot be reused'):
            self.check()

    def test_stalled_read_is_bounded_and_cannot_authorize_work(self):
        release = threading.Event()
        get = self.store.get
        def stalled(k):
            if '/reconciliation/child' in k:
                release.wait(1)
            return get(k)
        self.store.get = stalled
        self.p.read_timeout = 0.02
        try:
            with self.assertRaises(TimeoutError):
                self.check()
            self.assertEqual(self.p.metrics['checks'], 0)
        finally:
            release.set()

    def test_parallelism_is_real_and_bounded(self):
        barrier = threading.Barrier(4, timeout=1)
        get = self.store.get
        active = [0, 0]
        lock = threading.Lock()
        def concurrent(k):
            with lock:
                active[0] += 1
                active[1] = max(active[1], active[0])
            if '/reconciliation/' not in k:
                barrier.wait()
            result = get(k)
            with lock:
                active[0] -= 1
            return result
        self.store.get = concurrent
        self.check()
        self.assertGreaterEqual(active[1], 4)
        self.assertLessEqual(active[1], 8)


if __name__ == '__main__':
    unittest.main()

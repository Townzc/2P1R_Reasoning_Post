"""Deterministic CPU-only tests: no Modal import, model work, or provider calls."""

import copy
from concurrent.futures import ThreadPoolExecutor
import threading
import unittest

from experiments.sft_allocation_midpoint.guard import (
    Admission, DICT_TTL_SECONDS, GuardError, RunGuard, identity_hash,
)


class FakeAtomicStore:
    """Linearizable fake with JSON-like value copies and injected RPC failures."""

    def __init__(self):
        self.records = {}
        self.lock = threading.Lock()
        self.fail_before = None
        self.fail_after = None

    def get(self, key, default=None):
        with self.lock:
            return copy.deepcopy(self.records.get(key, default))

    def put(self, key, value, *, skip_if_exists=False):
        assert skip_if_exists, "guard must never overwrite a record"
        with self.lock:
            if self.fail_before and self.fail_before in key:
                raise OSError("injected pre-write failure")
            if key in self.records:
                return False
            self.records[key] = copy.deepcopy(value)
            if self.fail_after and self.fail_after in key:
                raise OSError("injected lost post-commit response")
            return True


def plan():
    return {"campaign_id": "finite-pilot", "created_epoch": 1000,
            "deadline_epoch": 2000, "total_cap_cents": 1500,
            "stage_caps_cents": {"train": 1000, "eval": 500},
            "slots": {"first": {"stage": "train", "reserved_cents": 500},
                      "child": {"stage": "train", "reserved_cents": 500},
                      "eval": {"stage": "eval", "reserved_cents": 500}}}


def intent(run_id="first"):
    return {"run_id": run_id, "config_sha256": "a" * 64,
            "source_sha256": "b" * 64, "data_sha256": "c" * 64}


class MidpointGuardTests(unittest.TestCase):
    def setUp(self):
        self.store = FakeAtomicStore()
        self.guard = RunGuard(self.store, plan())
        self.guard.register(now_epoch=1000)

    def admit(self, run_id="first", attempt_id="worker-1", **kwargs):
        return self.guard.admit(intent(run_id), attempt_id=attempt_id,
                                now_epoch=1100, max_runtime_seconds=100, **kwargs)

    def finish(self, admission, status="completed", cost=450):
        return self.guard.finish(admission, status=status, evidence_sha256="d" * 64,
                                 actual_cost_cents=cost, finished_epoch=1201)

    def reconciliation(self, **updates):
        r = {"parent_run_id": "first", "child_run_id": "child",
             "child_config_sha256": "a" * 64, "evidence_sha256": "d" * 64,
             "remaining_work_sha256": "e" * 64, "workers_stopped": True,
             "no_ambiguous_replay": True}
        return {**r, **updates}

    def test_competing_claims_admit_exactly_one_worker(self):
        barrier = threading.Barrier(2)

        def compete(n):
            barrier.wait()
            try:
                return self.admit(attempt_id=f"worker-{n}")
            except GuardError:
                return None

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(compete, [1, 2]))
        self.assertEqual(sum(isinstance(r, Admission) for r in results), 1)
        self.assertEqual(len([k for k in self.store.records if "/attempt/" in k]), 1)

    def test_lost_claim_response_blocks_new_attempt(self):
        self.store.fail_after = "/claim/first"
        with self.assertRaises(OSError):
            self.admit()
        self.store.fail_after = None
        with self.assertRaisesRegex(GuardError, "already claimed"):
            self.admit(attempt_id="new-process")
        self.assertIn("midpoint/finite-pilot/claim/first", self.store.records)

    def test_crash_between_claim_and_attempt_is_ambiguous_and_not_replayed(self):
        self.store.fail_before = "/attempt/"
        with self.assertRaises(OSError):
            self.admit()
        self.store.fail_before = None
        with self.assertRaises(GuardError):
            self.admit(attempt_id="replacement")
        claim = self.store.get("midpoint/finite-pilot/claim/first")
        forged = Admission("finite-pilot", "first", "worker-1", identity_hash(claim))
        with self.assertRaisesRegex(GuardError, "ownership"):
            self.guard.check_active(forged, now_epoch=1101, spent_cents=0)

    def test_crash_after_admission_never_releases_claim(self):
        a = self.admit()
        with self.assertRaises(GuardError):
            self.admit(attempt_id="worker-1")
        with self.assertRaises(GuardError):
            self.admit(attempt_id="worker-2")
        self.assertEqual(self.store.get("midpoint/finite-pilot/claim/first")["attempt_id"], a.attempt_id)

    def test_completed_failed_and_unknown_states_all_block_replay(self):
        for status in ("completed", "failed", "ambiguous"):
            with self.subTest(status=status):
                store = FakeAtomicStore()
                g = RunGuard(store, plan())
                g.register(now_epoch=1000)
                a = g.admit(intent(), attempt_id="worker", now_epoch=1100, max_runtime_seconds=100)
                g.finish(a, status=status, evidence_sha256="d" * 64,
                         actual_cost_cents=None if status == "ambiguous" else 400,
                         finished_epoch=1200)
                before = copy.deepcopy(store.records)
                with self.assertRaises(GuardError):
                    g.admit(intent(), attempt_id="retry", now_epoch=1201, max_runtime_seconds=100)
                self.assertEqual(before, store.records)

    def test_completion_is_idempotent_but_different_evidence_cannot_overwrite(self):
        a = self.admit()
        first = self.finish(a)
        self.assertEqual(self.finish(a), first)
        with self.assertRaisesRegex(GuardError, "immutable record conflict"):
            self.finish(a, status="failed")
        with self.assertRaises(GuardError):
            self.guard.check_active(a, now_epoch=1150, spent_cents=400)

    def test_negative_results_are_preserved_as_completed_evidence(self):
        a = self.admit()
        negative_result = {"delta_accuracy": -0.04, "failed_hypothesis": True}
        receipt = self.guard.finish(a, status="completed", evidence_sha256=identity_hash(negative_result),
                                    actual_cost_cents=500, finished_epoch=1200)
        self.assertEqual(receipt["status"], "completed")
        self.assertEqual(receipt["evidence_sha256"], identity_hash(negative_result))

    def test_fixed_deadline_and_seven_day_expiry_safety(self):
        for now, runtime in [(999, 1), (2000, 1), (1999, 2), (1100, 0), (float("nan"), 1)]:
            with self.subTest(now=now, runtime=runtime), self.assertRaises(GuardError):
                self.guard.admit(intent(), attempt_id="x", now_epoch=now, max_runtime_seconds=runtime)
        p = plan()
        p["deadline_epoch"] = p["created_epoch"] + DICT_TTL_SECONDS
        with self.assertRaisesRegex(GuardError, "seven days"):
            RunGuard(FakeAtomicStore(), p)
        # Even if a backend eventually expires all records, the original fixed
        # deadline denies re-registration rather than silently starting anew.
        self.store.records.clear()
        with self.assertRaises(GuardError):
            self.guard.register(now_epoch=1000 + DICT_TTL_SECONDS)

    def test_active_runtime_and_cost_checks_and_late_receipt(self):
        a = self.admit()
        self.guard.check_active(a, now_epoch=1199, spent_cents=490, next_cost_cents=10)
        for kw in [{"now_epoch": 1200, "spent_cents": 0},
                   {"now_epoch": 1099, "spent_cents": 0},
                   {"now_epoch": 1150, "spent_cents": 490, "next_cost_cents": 11}]:
            with self.assertRaises(GuardError):
                self.guard.check_active(a, **kw)
        # Cost overruns and failures must remain recordable, not disappear when a
        # deadline or cap is crossed. Subsequent admissions fail closed.
        self.guard.finish(a, status="failed", evidence_sha256="d" * 64,
                          actual_cost_cents=501, finished_epoch=1250)
        with self.assertRaisesRegex(GuardError, "overrun"):
            self.guard.admit(intent("eval"), attempt_id="eval-worker", now_epoch=1300,
                             max_runtime_seconds=100)

    def test_evidence_can_be_preserved_after_campaign_deadline(self):
        a = self.admit()
        receipt = self.guard.finish(a, status="ambiguous", evidence_sha256="d" * 64,
                                    actual_cost_cents=None, finished_epoch=2100)
        self.assertEqual(receipt["finished_epoch"], 2100)

    def test_stage_and_total_reservations_are_validated_upfront(self):
        p = plan()
        p["slots"]["child"]["reserved_cents"] = 501
        with self.assertRaisesRegex(GuardError, "stage budget"):
            RunGuard(self.store, p)
        p = plan()
        p["total_cap_cents"] = 1499
        with self.assertRaisesRegex(GuardError, "total campaign"):
            RunGuard(self.store, p)
        p = plan()
        p["slots"]["first"]["reserved_cents"] = True
        with self.assertRaises(GuardError):
            RunGuard(self.store, p)

    def test_fixed_plan_and_hashes_cannot_be_changed(self):
        p = plan()
        p["deadline_epoch"] += 1
        with self.assertRaisesRegex(GuardError, "immutable record conflict"):
            RunGuard(self.store, p).register(now_epoch=1100)
        with self.assertRaises(GuardError):
            self.guard.admit({**intent(), "source_sha256": "git-sha-is-not-a-sha256"},
                             attempt_id="x", now_epoch=1100, max_runtime_seconds=100)
        a = self.admit()
        with self.assertRaises(GuardError):
            self.guard.admit({**intent(), "data_sha256": "f" * 64},
                             attempt_id="x", now_epoch=1100, max_runtime_seconds=100)
        self.assertEqual(self.store.get("midpoint/finite-pilot/intent/first"), intent())
        self.assertIsInstance(a, Admission)

    def test_only_explicit_reconciled_child_can_continue_without_releasing_parent(self):
        a = self.admit()
        child = {**intent("child"), "parent_run_id": "first", "reconciliation_sha256": "e" * 64}
        with self.assertRaisesRegex(GuardError, "reconciliation"):
            self.guard.admit(child, attempt_id="child-worker", now_epoch=1200, max_runtime_seconds=100)
        for updates in [{"workers_stopped": False}, {"no_ambiguous_replay": False}]:
            with self.assertRaises(GuardError):
                self.guard.record_reconciliation(self.reconciliation(**updates))
        receipt = self.reconciliation()
        child["reconciliation_sha256"] = self.guard.record_reconciliation(receipt)
        with self.assertRaisesRegex(GuardError, "fenced"):
            self.guard.check_active(a, now_epoch=1150, spent_cents=100)
        b = self.guard.admit(child, attempt_id="child-worker", now_epoch=1200, max_runtime_seconds=100)
        self.assertEqual(b.run_id, "child")
        self.assertEqual(self.store.get("midpoint/finite-pilot/claim/first")["attempt_id"], "worker-1")
        self.assertEqual(self.store.get("midpoint/finite-pilot/claim/child")["reserved_cents"], 500)
        with self.assertRaises(GuardError):
            self.admit(attempt_id="reuse-parent")

    def test_completed_parent_cannot_be_reconciled_for_replay(self):
        self.finish(self.admit())
        with self.assertRaisesRegex(GuardError, "completed parent"):
            self.guard.record_reconciliation(self.reconciliation())

    def test_child_config_and_parent_linkage_are_bound_to_reconciliation(self):
        self.admit()
        h = self.guard.record_reconciliation(self.reconciliation())
        for i in [intent("child"), {**intent("child"), "parent_run_id": "first",
                                  "reconciliation_sha256": h, "config_sha256": "f" * 64}]:
            with self.assertRaises(GuardError):
                self.guard.admit(i, attempt_id="child", now_epoch=1200, max_runtime_seconds=100)

    def test_completed_evidence_blocks_admission_even_if_claim_was_lost(self):
        self.finish(self.admit())
        del self.store.records["midpoint/finite-pilot/claim/first"]
        with self.assertRaisesRegex(GuardError, "terminal"):
            self.admit(attempt_id="replay")

    def test_mutating_external_plan_does_not_change_envelope(self):
        p = plan()
        g = RunGuard(self.store, p)
        p["slots"]["first"]["reserved_cents"] = 99999
        self.assertEqual(g.plan["slots"]["first"]["reserved_cents"], 500)
        g.plan["deadline_epoch"] = 99999
        with self.assertRaisesRegex(GuardError, "in-memory plan"):
            g.register(now_epoch=1100)


if __name__ == "__main__":
    unittest.main()

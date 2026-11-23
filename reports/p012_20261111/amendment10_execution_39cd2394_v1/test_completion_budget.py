"""Offline tests of the owner's scoped November 22 change and historical admission bindings."""
import math
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import run_queue as q


class CompletionBudgetTest(unittest.TestCase):
    def test_all_remaining_training_and_evaluations_cross_both_references(self):
        cells = q.read(q.OWNER_BUDGET)["remaining_training_endpoints"]
        self.assertEqual(cells, q.ORDER[3:])
        self.assertEqual(len(cells), 11)
        for cell in cells:
            for name, parent in [(cell, None), (q.evaluation_of(cell), cell)]:
                with self.subTest(name=name):
                    result = q.budget_decision(name, parent, "train_eval", 130, 210)
                    self.assertTrue(result["admitted"])
                    self.assertEqual(result["exceeded_reference_limits"], ["train_eval", "A10_total"])
                    self.assertEqual(result["owner_budget_authority_commit"], q.OWNER_BUDGET_COMMIT)

    def test_each_limit_is_still_reported_individually(self):
        cell = q.ORDER[3]
        for sub, total, expected in [(125, 200, []), (126, 160, ["train_eval"]), (120, 201, ["A10_total"])]:
            result = q.budget_decision(cell, None, "train_eval", sub, total)
            self.assertTrue(result["admitted"])
            self.assertEqual(result["exceeded_reference_limits"], expected)

    def test_completed_and_unregistered_calls_have_no_override(self):
        for name, parent, bucket in [(q.FIRST[0], None, "baseline"), (q.ORDER[2], None, "train_eval"),
                                      ("other", None, "train_eval"), ("other", q.ORDER[3], "train_eval")]:
            result = q.budget_decision(name, parent, bucket, 210, 220)
            self.assertFalse(result["admitted"])
            self.assertNotIn("owner_budget_authority_commit", result)
        with self.assertRaisesRegex(ValueError, "outside the frozen"):
            q.resolve_request("other")
        with self.assertRaisesRegex(ValueError, "Unregistered post-training"):
            q.resolve_request("other", q.ORDER[3])

    def test_invalid_cost_and_changed_authority_fail(self):
        for invalid in (math.nan, math.inf, -1):
            with self.assertRaisesRegex(ValueError, "Invalid cost"):
                q.budget_decision(q.ORDER[3], None, "train_eval", invalid, 210)
        with patch.object(q, "OWNER_BUDGET_SHA", "0" * 64), self.assertRaisesRegex(ValueError, "hash"):
            q.budget_decision(q.ORDER[3], None, "train_eval", 130, 210)

    def test_real_request_preparation_with_synthetic_costs_and_no_service(self):
        name = q.ORDER[4]
        books = dict(spent={"train_eval":126}, reserved={"train_eval":3},
                     total_accounted_usd=205, total_reserved_usd=3)
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.multiple(q, PUB=root/"public", RUNS=root/"runs"), patch.object(q, "ledger", return_value=books), \
                    patch.object(q, "estimates", return_value=(10,3,"test")), \
                    patch.object(q, "publish", return_value="offline"), patch.object(q, "remote_bytes"):
                d, _ = q.resolve_request(name)
                req = q.read(d/"request.json")
                gate = q.read(Path(req["forecast"]["admission_file"]))
                self.assertEqual((gate["projected_bucket_usd"], gate["projected_total_usd"]), (142,221))
                self.assertTrue(gate["admitted"])
                self.assertEqual(gate["owner_budget_authority_sha256"], q.OWNER_BUDGET_SHA)
                self.assertEqual(q.sha(req["forecast"]["admission_file"]), req["forecast"]["admission_sha256"])
                self.assertTrue(req["forecast"]["dollar_limits_are_reporting_thresholds"])
                self.assertFalse((d/"run.log").exists())
                q.resolve_request(name)
                self.assertEqual(req, q.read(d/"request.json"))

    def test_five_existing_admissions_match_owner_snapshot(self):
        previous = q.read(q.OWNER_BUDGET)["existing_admissions"]
        self.assertEqual(len(previous),5)
        for name, digest in previous.items():
            self.assertEqual(q.sha(q.PUB/"admissions"/(name+".json")),digest)


if __name__ == "__main__":
    unittest.main()

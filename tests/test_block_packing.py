import copy
import itertools
import json
import random
import unittest
from functools import lru_cache
from types import SimpleNamespace
from unittest import mock

import numpy as np

from src.block_packing import PackingVerificationError, pack_support_groups


def group(pids, representative=None):
    return {"problem_ids": list(pids), "representative": representative}


def brute_force(groups):
    """Independent search over explicit four-element blocks, not the MILP."""
    pids = sorted({pid for item in groups for pid in item["problem_ids"]})
    positions = {pid: i for i, pid in enumerate(pids)}
    masks = sorted({sum(1 << positions[pid] for pid in block)
                    for item in groups
                    for block in itertools.combinations(item["problem_ids"], 4)})

    @lru_cache(None)
    def solve(used):
        return max([0] + [1 + solve(used | mask) for mask in masks if not used & mask])
    return solve(0)


def fake_result(x, *, status=0, fun=-1.0, dual=-1.0, gap=0.0):
    return SimpleNamespace(x=x, status=status, fun=fun, mip_dual_bound=dual,
                           mip_gap=gap, message="synthetic solver return")


class BlockPackingTests(unittest.TestCase):
    def verify_blocks(self, result, groups):
        used = []
        for block in result["blocks"]:
            self.assertEqual(len(block["problem_ids"]), 4)
            self.assertEqual(len(set(block["problem_ids"])), 4)
            source = groups[block["group_id"]]
            self.assertTrue(set(block["problem_ids"]) <= set(source["problem_ids"]))
            self.assertEqual(block["representative"], source["representative"])
            used.extend(block["problem_ids"])
        self.assertEqual(len(used), len(set(used)))
        self.assertEqual(len(used), result["primal_block_count"] * 4)
        self.assertEqual(sorted(used), result["used_problem_ids"])
        self.assertGreaterEqual(result["integer_upper_bound"], result["primal_block_count"])
        json.dumps(result, allow_nan=False)

    def test_empty_and_too_small_support_are_analytically_optimal(self):
        for groups in ([], [group([])], [group("abc"), group("def")]):
            with self.subTest(groups=groups), mock.patch("src.block_packing.milp") as solver:
                result = pack_support_groups(groups)
                solver.assert_not_called()
                self.assertTrue(result["is_optimal"])
                self.assertEqual(result["primal_block_count"], 0)
                self.assertEqual(result["integer_upper_bound"], 0)
                self.verify_blocks(result, groups)

    def test_one_support_group_can_supply_multiple_blocks(self):
        groups = [group("ihgfedcba", {"key": [1, True, None, {"value": "x"}]})]
        original = copy.deepcopy(groups)
        result = pack_support_groups(groups)
        self.assertTrue(result["is_optimal"])
        self.assertEqual(result["primal_block_count"], 2)
        self.assertEqual(result["dual_upper_bound"], 2)
        self.assertEqual(result["absolute_gap_blocks"], 0)
        self.assertEqual(groups, original)
        self.verify_blocks(result, groups)

    def test_largest_support_greedy_counterexample(self):
        groups = [group("abcdef", "large"), group("abgh", "left"),
                  group("cdij", "middle"), group("efkl", "right")]
        used, greedy = set(), 0
        for item in sorted(groups, key=lambda item: (-len(item["problem_ids"]), item["problem_ids"])):
            available = sorted(set(item["problem_ids"]) - used)
            count = len(available) // 4
            used.update(available[:4 * count])
            greedy += count
        self.assertEqual(greedy, 2)
        result = pack_support_groups(groups)
        self.assertEqual(result["primal_block_count"], 3)
        self.assertEqual(result["primal_block_count"], brute_force(groups))
        self.verify_blocks(result, groups)

    def test_matches_exhaustive_small_random_inventories(self):
        rng = random.Random(812)
        for case in range(24):
            universe = [f"p{i}" for i in range(rng.randint(4, 10))]
            supports = set()
            for _ in range(rng.randint(1, 5)):
                supports.add(tuple(sorted(rng.sample(universe, rng.randint(1, len(universe))))))
            groups = [group(ids, {"case": case, "key": i}) for i, ids in enumerate(sorted(supports))]
            with self.subTest(case=case):
                result = pack_support_groups(groups)
                self.assertTrue(result["is_optimal"])
                self.assertEqual(result["primal_block_count"], brute_force(groups))
                self.verify_blocks(result, groups)

    def test_duplicate_ids_and_duplicate_exact_support_are_rejected(self):
        for groups in ([group("aabc")], [group("abcd"), group("dcba", "another key")],
                       [group([]), group([])]):
            with self.subTest(groups=groups), self.assertRaises(ValueError):
                pack_support_groups(groups)

    def test_invalid_schema_or_non_json_representative_rejected(self):
        bad = [None, (), [None], [{"problem_ids": []}],
               [{"problem_ids": ["a"], "representative": None, "unexpected": 2}],
               [{"problem_ids": ("a",), "representative": None}],
               [group(["a", ""])], [group(["a", 4])],
               [group("abcd", float("nan"))], [group("abcd", {1: "bad key"})],
               [group("abcd", {"not_json": {1, 2}})]]
        for groups in bad:
            with self.subTest(groups=groups), self.assertRaises(ValueError):
                pack_support_groups(groups)

    def test_invalid_limits_rejected(self):
        for limit in (0, -1, 61, True, float("inf"), float("nan"), "60"):
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                pack_support_groups([], time_limit=limit)

    def test_single_call_uses_total_remaining_limit_and_zero_relative_gap(self):
        with mock.patch("src.block_packing.milp", return_value=fake_result(np.ones(5))) as solver:
            result = pack_support_groups([group("abcd")], time_limit=3)
        solver.assert_called_once()
        options = solver.call_args.kwargs["options"]
        self.assertGreater(options["time_limit"], 0)
        self.assertLessEqual(options["time_limit"], 3)
        self.assertEqual(options["mip_rel_gap"], 0)
        self.assertTrue(result["is_optimal"])

    def test_time_limit_with_incumbent_is_never_reported_optimal(self):
        with mock.patch("src.block_packing.milp", return_value=fake_result(np.ones(5), status=1)):
            result = pack_support_groups([group("abcd")])
        self.assertEqual(result["solver_status"], 1)
        self.assertFalse(result["is_optimal"])
        self.assertEqual(result["primal_block_count"], 1)
        self.assertEqual(result["absolute_gap_blocks"], 0)
        self.assertEqual(result["solution_source"], "solver_incumbent")

    def test_time_limit_without_incumbent_retains_valid_zero_lower_bound(self):
        with mock.patch("src.block_packing.milp", return_value=fake_result(None, status=1, fun=None,
                                                                         dual=-1.75, gap=None)):
            result = pack_support_groups([group("abcdefgh")])
        self.assertFalse(result["is_optimal"])
        self.assertEqual(result["primal_block_count"], 0)
        self.assertEqual(result["dual_upper_bound"], 1.75)
        self.assertEqual(result["integer_upper_bound"], 1)
        self.assertEqual(result["solution_source"], "empty_feasible_fallback")

    def test_global_budget_exhausted_before_solver_does_not_call_it(self):
        with mock.patch("src.block_packing.time.monotonic", side_effect=[0.0, 2.0, 2.0]), \
                mock.patch("src.block_packing.milp") as solver:
            result = pack_support_groups([group("abcd")], time_limit=1)
        solver.assert_not_called()
        self.assertEqual(result["solver_status"], 1)
        self.assertFalse(result["is_optimal"])

    def test_rounding_within_tolerance_then_exact_constraint_check(self):
        vector = np.asarray([1 + 4e-7, 1 - 4e-7, 1, 1, 1])
        with mock.patch("src.block_packing.milp", return_value=fake_result(vector)):
            result = pack_support_groups([group("abcd")])
        self.verify_blocks(result, [group("abcd")])

    def test_invalid_solver_vectors_are_rejected(self):
        vectors = [[1, 1, 1, .5, 1], [1, 1, 1, 0, 1], [2, 1, 1, 0, 1],
                   [-1, 1, 1, 3, 1], [1, 1, 1, float("nan"), 1], [1, 1, 1, 1]]
        for vector in vectors:
            with self.subTest(vector=vector), \
                    mock.patch("src.block_packing.milp", return_value=fake_result(vector)), \
                    self.assertRaises(PackingVerificationError):
                pack_support_groups([group("abcd")])

    def test_reusing_problem_between_groups_is_rejected(self):
        groups = [group("abcd"), group("abef")]
        with mock.patch("src.block_packing.milp", return_value=fake_result(np.ones(10), fun=-2, dual=-2)), \
                self.assertRaises(PackingVerificationError):
            pack_support_groups(groups)

    def test_inconsistent_objective_dual_and_status_are_rejected(self):
        results = [fake_result(np.ones(5), fun=-2), fake_result(np.ones(5), dual=-.5),
                   fake_result(None), fake_result(None, status=2), fake_result(None, status=3),
                   fake_result(None, status=8)]
        for result in results:
            with self.subTest(result=result), \
                    mock.patch("src.block_packing.milp", return_value=result), \
                    self.assertRaises(PackingVerificationError):
                pack_support_groups([group("abcd")])

    def test_missing_dual_after_limit_does_not_mean_zero_upper_bound(self):
        with mock.patch("src.block_packing.milp", return_value=fake_result(None, status=1,
                                                                         fun=None, dual=None, gap=None)):
            result = pack_support_groups([group("abcdefgh")])
        self.assertIsNone(result["dual_upper_bound"])
        self.assertEqual(result["integer_upper_bound"], 2)
        self.assertEqual(result["absolute_gap_blocks"], 2)


if __name__ == "__main__":
    unittest.main()

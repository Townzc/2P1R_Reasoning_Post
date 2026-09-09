"""Synthetic fixed-feature tests; never read a training pool or token archive."""
import copy
import itertools
import unittest

from src.single_family_matching import single_family_keys


def row(pid, structure, ac_class=None, length=60, family="identity_absent", expression=None):
    ac_class = ac_class or "class-" + structure
    return {"problem_id": pid, "structure_id": structure, "ac_class": ac_class,
            "expression": expression or f"{pid}:{length}:{structure}:{ac_class}",
            "family": family, "n_supervised": length, "encodable": True}


def square(problems=4, structures=4):
    return [row(f"p{pid}", f"S{structure}")
            for pid in range(problems) for structure in range(structures)]


class TickClock:
    def __init__(self, switch=0):
        self.calls, self.switch = 0, switch

    def __call__(self):
        self.calls += 1
        return 0 if self.calls <= self.switch else 999


class SingleFamilyTests(unittest.TestCase):
    def test_complete_shared_square_and_explicit_witness(self):
        result = single_family_keys(square())
        self.assertTrue(result["complete"])
        self.assertEqual(result["shared_key_count"], 1)
        self.assertEqual(result["counters"]["structure_combinations_tested"], 4)
        self.assertEqual(result["supported_problem_ids"], ["p0", "p1", "p2", "p3"])
        for witness in result["keys"][0]["witnesses"].values():
            self.assertEqual(len(witness["slots"]), 4)
            self.assertEqual(len({slot["ac_class"] for slot in witness["slots"]}), 4)

    def test_all_local_combinations_not_first_four(self):
        result = single_family_keys(square(structures=5))
        self.assertEqual(result["total_local_structure_combinations"], 20)
        self.assertEqual(result["shared_key_count"], 5)
        self.assertEqual({tuple(key["structures"]) for key in result["keys"]},
                         set(itertools.combinations([f"S{i}" for i in range(5)], 4)))

    def test_different_problems_may_have_different_lengths(self):
        rows = [row(f"p{pid}", f"S{s}", length=60 + pid) for pid in range(4) for s in range(4)]
        result = single_family_keys(rows)
        self.assertEqual(result["shared_key_count"], 1)
        self.assertEqual([result["keys"][0]["witnesses"][f"p{i}"]["n_supervised"] for i in range(4)],
                         [60, 61, 62, 63])

    def test_same_problem_cannot_union_structures_across_lengths(self):
        rows = [row(f"p{pid}", f"S{s}", length=60 + s // 2) for pid in range(4) for s in range(4)]
        result = single_family_keys(rows)
        self.assertTrue(result["complete"])
        self.assertEqual(result["shared_key_count"], 0)
        self.assertEqual(result["total_local_structure_combinations"], 0)

    def test_same_pid_at_four_lengths_is_not_four_problems(self):
        rows = [row("only", f"S{s}", length=60 + length) for length in range(4) for s in range(4)]
        result = single_family_keys(rows)
        self.assertEqual(result["shared_key_count"], 0)
        self.assertEqual(result["local_key_count"], 1)
        self.assertEqual(result["counters"]["distinct_problem_key_support"], 1)

    def test_lowest_feasible_length_and_deterministic_representative(self):
        rows = square()
        rows += [dict(r, n_supervised=65, expression="later:" + r["expression"]) for r in rows]
        rows.append(row("p0", "S0", expression="ZZZ"))
        original = copy.deepcopy(rows)
        first, second = single_family_keys(rows), single_family_keys(reversed(rows))
        self.assertEqual(first["keys"], second["keys"])
        self.assertEqual(first["keys"][0]["witnesses"]["p0"]["n_supervised"], 60)
        self.assertEqual(rows, original)

    def test_lower_length_without_four_classes_is_skipped(self):
        rows = square()
        for item in rows:
            if item["problem_id"] == "p0" and item["structure_id"] == "S3":
                item["ac_class"] = "class-S0"
        rows += [row("p0", f"S{s}", length=61) for s in range(4)]
        result = single_family_keys(rows)
        self.assertEqual(result["shared_key_count"], 1)
        self.assertEqual(result["keys"][0]["witnesses"]["p0"]["n_supervised"], 61)

    def test_alternating_path_reroutes_a_shared_class(self):
        rows = []
        for pid in range(4):
            for s, ac in (("A", "a-shared"), ("A", "z-private"), ("B", "a-shared"),
                          ("C", "c"), ("D", "d")):
                rows.append(row(f"p{pid}", s, ac))
        result = single_family_keys(rows)
        self.assertEqual(result["shared_key_count"], 1)
        slots = result["keys"][0]["witnesses"]["p0"]["slots"]
        self.assertEqual({slot["structure_id"]: slot["ac_class"] for slot in slots},
                         {"A": "z-private", "B": "a-shared", "C": "c", "D": "d"})

    def test_four_structures_but_three_classes_is_infeasible(self):
        rows = [row(f"p{pid}", f"S{s}", f"C{s % 3}") for pid in range(4) for s in range(4)]
        result = single_family_keys(rows)
        self.assertTrue(result["complete"])
        self.assertEqual(result["shared_key_count"], 0)
        self.assertEqual(result["counters"]["class_assignment_checks_completed"], 4)

    def test_opposite_family_is_not_a_requirement(self):
        rows = square()
        rows.append(row("other", "S0", family="identity_present"))
        result = single_family_keys(rows)
        self.assertEqual(result["shared_key_count"], 1)
        self.assertEqual(result["counters"]["other_family_records"], 1)

    def test_unencodable_rows_do_not_supply_lengths(self):
        rows = square()
        for row_ in rows:
            if row_["problem_id"] == "p3":
                row_["encodable"] = False
                del row_["n_supervised"]
        result = single_family_keys(rows)
        self.assertTrue(result["complete"])
        self.assertEqual(result["shared_key_count"], 0)
        self.assertEqual(result["counters"]["excluded_unencodable_records"], 4)

    def test_duplicate_rows_cannot_inflate_support(self):
        result = single_family_keys(square(problems=1) * 4)
        self.assertEqual(result["shared_key_count"], 0)
        self.assertEqual(result["input_problem_count"], 1)

    def test_deadline_during_indexing_is_incomplete_not_negative(self):
        result = single_family_keys(square(), clock=TickClock(1))
        self.assertFalse(result["complete"])
        self.assertFalse(result["indexing_complete"])
        self.assertEqual(result["stop_stage"], "indexing")
        self.assertIsNone(result["total_local_structure_combinations"])
        self.assertIn("not_absence", result["support_interpretation"])

    def test_deadline_during_assignment_never_retains_partial_witness(self):
        result = single_family_keys(square(), clock=TickClock(20))
        self.assertFalse(result["complete"])
        self.assertTrue(result["indexing_complete"])
        self.assertEqual(result["stop_stage"], "class_assignment")
        self.assertEqual(result["keys"], [])
        self.assertEqual(result["counters"]["class_assignment_checks_completed"], 0)

    def test_deadline_keeps_completed_shared_key_as_lower_bound(self):
        result = single_family_keys(square(problems=5), clock=TickClock(62))
        self.assertFalse(result["complete"])
        self.assertEqual(result["shared_key_count"], 1)
        self.assertEqual(result["supported_problem_ids"], ["p0", "p1", "p2", "p3"])
        self.assertEqual(result["counters"]["class_assignment_checks_completed"], 4)
        self.assertEqual(result["total_local_structure_combinations"], 5)

    def test_invalid_feature_and_deadline_inputs_rejected(self):
        for invalid in (True, 0, -1, float("inf"), float("nan")):
            with self.subTest(limit=invalid), self.assertRaises(ValueError):
                single_family_keys([], max_seconds=invalid)
        for changes in ({"n_supervised": True}, {"n_supervised": 0}, {"structure_id": ""},
                        {"encodable": 1}, {"family": "unknown"}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                single_family_keys([dict(row("p", "s"), **changes)])


if __name__ == "__main__":
    unittest.main()

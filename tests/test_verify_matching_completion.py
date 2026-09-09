"""Synthetic counterexamples for independent completion certificates."""
import copy
from pathlib import Path
import tempfile
import unittest

from scripts.verify_matching_completion import (
    FAMILIES, _problem_flags, _two_family_support, component_upper_bound,
    fixed_structure_matching, record_ref, verify_lengths, verify_packing,
    verify_report, verify_single_keys,
)


def row(pid, family, structure, ac, length):
    return {"problem_id": pid, "family": family, "structure_id": structure,
            "ac_class": ac, "expression": f"{pid}:{family}:{structure}:{ac}:{length}",
            "encodable": True, "n_supervised": length}


def single_fixture():
    records = [row(f"p{i}", "identity_absent", f"S{j}", f"C{j}", 60 + i)
               for i in range(4) for j in range(4)]
    pids = [f"p{i}" for i in range(4)]
    key = {"structures": [f"S{i}" for i in range(4)], "problem_ids": pids, "witnesses": {}}
    for pid in pids:
        rows = [r for r in records if r["problem_id"] == pid]
        key["witnesses"][pid] = {"problem_id": pid, "n_supervised": rows[0]["n_supervised"],
            "slots": [{"family": r["family"], "structure_id": r["structure_id"], "ac_class": r["ac_class"],
                       "record_ref": record_ref(r)} for r in rows]}
    join = {"complete": True, "indexing_complete": True, "stop_reason": "completed",
            "family": "identity_absent", "per_family": 4, "keys": [key],
            "per_problem_feasible_lengths": {pid: [60 + i] for i, pid in enumerate(pids)},
            "counters": {"input_records_seen": 16, "family_records_indexed": 16,
                         "other_family_records": 0, "excluded_unencodable_records": 0,
                         "problem_length_groups_completed": 4, "structure_combinations_tested": 4,
                         "class_assignment_checks_completed": 4, "feasible_problem_length_keys": 4,
                         "distinct_problem_key_support": 4},
            "total_local_structure_combinations": 4, "local_key_count": 1,
            "shared_key_count": 1, "input_problem_count": 4, "supported_problem_ids": pids}
    return records, join, {pid: {} for pid in pids}


def packing_fixture():
    records, join, _ = single_fixture()
    key = join["keys"][0]
    expanded = copy.deepcopy(key)
    lookup = {record_ref(r): r for r in records}
    for witness in expanded["witnesses"].values():
        for slot in witness["slots"]:
            slot["record"] = lookup[slot.pop("record_ref")]
    pids = key["problem_ids"]
    packing = {"group_assignments": [{"group_id": 0, "problem_ids": pids,
                    "block_count": 1, "representative": key}],
               "blocks": [{"group_id": 0, "problem_ids": pids, "representative": expanded}],
               "primal_block_count": 1, "block_count": 1, "selected_problem_ids": pids,
               "used_problem_ids": pids, "input_group_count": 1, "group_variable_count": 1,
               "input_problem_count": 4, "assignment_variable_count": 4, "elementary_upper_bound": 1,
               "integer_upper_bound": 1, "global_optimal": True, "solver_status": 0,
               "input_join_complete": True, "optimality_scope": "complete_key_universe"}
    return records, join, packing


class SingleSupportVerificationTests(unittest.TestCase):
    def test_full_finite_listing_and_lowest_lengths(self):
        records, join, problems = single_fixture()
        result = verify_single_keys(join, records, problems)
        self.assertEqual(result["local_combinations_checked"], 4)
        self.assertEqual(result["shared_keys_checked"], 1)
        self.assertEqual(result["key_problem_witnesses_checked"], 4)

    def test_hopcroft_karp_handles_conflict_and_rerouting(self):
        rows = [row("p", "identity_absent", s, ac, 60)
                for s, ac in (("A", "common"), ("A", "private"), ("B", "common"), ("C", "c"), ("D", "d"))]
        self.assertTrue(fixed_structure_matching(rows, ["A", "B", "C", "D"]))
        self.assertFalse(fixed_structure_matching(rows[1:], ["A", "B", "C", "MISSING"]))
        collision = [row("p", "identity_absent", str(i), str(i % 3), 60) for i in range(4)]
        self.assertFalse(fixed_structure_matching(collision, list("0123")))

    def test_omitted_key_unsupported_pid_and_counter_tamper_rejected(self):
        records, original, problems = single_fixture()
        for kind in ("omitted", "missing_pid", "counter", "wrong_length", "incomplete"):
            join = copy.deepcopy(original)
            if kind == "omitted":
                join["keys"] = []
            elif kind == "missing_pid":
                join["keys"][0]["problem_ids"].pop()
            elif kind == "counter":
                join["counters"]["structure_combinations_tested"] = 3
            elif kind == "wrong_length":
                join["keys"][0]["witnesses"]["p0"]["n_supervised"] = 61
            else:
                join["complete"] = False
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                verify_single_keys(join, records, problems)

    def test_combining_a_problems_lengths_does_not_create_support(self):
        records, join, problems = single_fixture()
        for r in records:
            if r["structure_id"] in ("S2", "S3"):
                r["n_supervised"] += 10
        with self.assertRaisesRegex(ValueError, "listing"):
            verify_single_keys(join, records, problems)


class FamilyLengthVerificationTests(unittest.TestCase):
    def test_family_separate_lengths_cannot_be_called_common(self):
        records = [row("p", family, f"S{index}", family + str(index), 60 + f)
                   for f, family in enumerate(FAMILIES) for index in range(4)]
        problem = {"numbers": [1, 2, 3, 4], "target": 10}
        pairs = {"common_class": [], "common_structure": [],
                 "per_family_class": [[60, 61]], "per_family_structure": [[60, 61]]}
        payload = {"per_problem": [{"problem_id": "p", **problem,
            "individual_family_class_lengths": {FAMILIES[0]: [60], FAMILIES[1]: [61]},
            "individual_family_lengths_intersect": False, "feasible_length_pairs": pairs,
            "flags": {key: bool(value) for key, value in pairs.items()},
            "structure_witnesses": {"per_family_structure": records}}],
            "stage_ids": {key: ["p"] if value else [] for key, value in pairs.items()},
            "counts": {key: int(bool(value)) for key, value in pairs.items()}}
        result = verify_lengths(payload, records, {"p": problem})
        self.assertEqual(result["counts"]["common_structure"], 0)
        self.assertEqual(result["counts"]["per_family_structure"], 1)
        payload["per_problem"][0]["feasible_length_pairs"]["common_structure"] = [[60, 61]]
        with self.assertRaises(ValueError):
            verify_lengths(payload, records, {"p": problem})

    def test_class_support_is_not_structure_support_or_disjoint_support(self):
        rows = [row("p", family, "one_structure", family + str(i), 60)
                for family in FAMILIES for i in range(4)]
        self.assertTrue(_two_family_support(rows, False))
        self.assertFalse(_two_family_support(rows, True))
        for item in rows:
            item["ac_class"] = item["ac_class"][-1]
        self.assertFalse(_two_family_support(rows, False))


class PackingVerificationTests(unittest.TestCase):
    def test_integer_primal_and_independent_upper_bound(self):
        records, join, packing = packing_fixture()
        result = verify_packing(packing, join, records)
        self.assertTrue(result["independent_optimality_proved"])
        self.assertEqual(result["verified_integer_blocks"], 1)

    def test_disconnected_support_components_strengthen_union_bound(self):
        proof = component_upper_bound([list("abcdefg"), list("hijkl")])
        self.assertEqual([c["size"] for c in proof["components"]], [5, 7])
        self.assertEqual(proof["upper_bound"], 2)
        self.assertLess(proof["upper_bound"], 12 // 4)

    def test_nonintegral_reused_and_wrong_class_packing_rejected(self):
        records, join, original = packing_fixture()
        for kind in ("fractional", "duplicate", "class", "bound"):
            packing = copy.deepcopy(original)
            if kind == "fractional":
                packing["group_assignments"][0]["block_count"] = 1.0
            elif kind == "duplicate":
                packing["group_assignments"][0]["problem_ids"] = ["p0"] * 4
            elif kind == "class":
                packing["blocks"][0]["representative"]["witnesses"]["p0"]["slots"][0]["ac_class"] = "bad"
            else:
                packing["integer_upper_bound"] = 2
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                verify_packing(packing, join, records)


class SelectionAndIOTests(unittest.TestCase):
    def test_preview_template_requires_disjoint_roles(self):
        self.assertFalse(_problem_flags({"numbers": [1, 2, 10, 20], "target": 21})["preview_template"])
        flags = _problem_flags({"numbers": [20, 3, 1, 2], "target": 21})
        self.assertTrue(flags["preview_template"])
        self.assertEqual(flags["preview_template_witnesses"][0]["role_values"], [1, 2, 3, 20])

    def test_output_overwrite_rejected_before_reading_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "receipt.json"
            out.write_text("preserved")
            with self.assertRaisesRegex(ValueError, "overwrite"):
                verify_report("missing", "missing", out)
            self.assertEqual(out.read_text(), "preserved")


if __name__ == "__main__":
    unittest.main()

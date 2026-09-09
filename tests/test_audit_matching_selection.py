"""Synthetic selection/weighting counterexamples; no real inventory is read."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from scripts.audit_matching_selection import (
    FAMILIES, aggregate_numeric_residuals, characterize, problem_characteristics, run,
)


def problem(numbers, target):
    return {"numbers": numbers, "target": target}


def record(pid, family, identity=None, expression=None):
    identity = int(family == FAMILIES[0]) if identity is None else identity
    return {"problem_id": pid, "family": family, "ac_class": "class-" + (expression or pid),
            "expression": expression or pid,
            "numeric_features": {"identity_nodes": identity, "zero_nodes": 0,
                                 "one_nodes": 1, "negative_nodes": 0, "fraction_nodes": 0,
                                 "depth": 2, "max_abs_intermediate": 2.0,
                                 "exact_nonroot_intermediates": ["1", "2"],
                                 "operators": {"+": 1, "-": 1, "*": 1}}}


class CharacteristicsTests(unittest.TestCase):
    def test_template_uses_four_distinct_positions(self):
        row = problem_characteristics(problem([20, 3, 1, 2], 21))
        self.assertTrue(row["preview_template"])
        witness = row["preview_template_witnesses"][0]
        self.assertEqual(witness["role_values"], [1, 2, 3, 20])
        self.assertEqual({witness[key] for key in ("one_index", "pair_lower_index", "pair_upper_index", "remaining_index")}, set(range(4)))

    def test_consecutive_pair_cannot_reuse_literal_one(self):
        row = problem_characteristics(problem([1, 2, 10, 20], 21))
        self.assertTrue(row["input_one"])
        self.assertTrue(row["consecutive_pair"])
        self.assertTrue(row["target_is_input_plus_one"])
        self.assertFalse(row["preview_template"])

    def test_target_and_successor_are_separate(self):
        row = problem_characteristics(problem([1, 4, 5, 20], 20))
        self.assertTrue(row["target_is_input"])
        self.assertFalse(row["target_is_input_plus_one"])
        self.assertFalse(row["preview_template"])
        self.assertFalse(problem_characteristics(problem([1, 4, 5, 20], 40))["target_ge_41"])
        self.assertTrue(problem_characteristics(problem([1, 4, 5, 20], 41))["target_ge_41"])

    def test_duplicate_values_and_boolean_inputs_rejected(self):
        for numbers in ([1, 1, 2, 20], [True, 2, 3, 20], [1, 2, 3], [0, 2, 3, 20]):
            with self.subTest(numbers=numbers), self.assertRaises(ValueError):
                problem_characteristics(problem(numbers, 21))


class SelectionTests(unittest.TestCase):
    def setUp(self):
        self.problems = {"low": problem([1, 2, 3, 20], 21),
                         "high": problem([2, 4, 10, 30], 41),
                         "mid": problem([1, 4, 8, 30], 30)}

    def test_original_and_previous_stratified_denominators(self):
        output = characterize(self.problems, {"raw": ["low", "high"], "common_length": ["low"]})
        stage = output["stages"]["common_length"]
        self.assertEqual(stage["retention_from_original"]["overall"]["ratio"], 1 / 3)
        self.assertEqual(stage["retention_from_previous"]["overall"]["ratio"], 1 / 2)
        self.assertEqual(stage["retention_from_previous"]["strata"]["target_ge_41"]["true"],
                         {"numerator": 0, "denominator": 1, "ratio": 0})
        self.assertEqual(output["original"]["numbers"]["count"], 12)
        self.assertEqual(output["original"]["targets"]["mean_exact"], "92/3")

    def test_empty_stage_has_null_ranges_and_zero_denominator(self):
        output = characterize(self.problems, {"empty": [], "still_empty": []})
        stage = output["stages"]["still_empty"]
        self.assertIsNone(stage["targets"]["mean"])
        self.assertIsNone(stage["retention_from_previous"]["overall"]["ratio"])
        self.assertEqual(stage["retention_from_original"]["overall"]["ratio"], 0)

    def test_unknown_duplicate_and_reintroduced_ids_rejected(self):
        for stages in ({"bad": ["absent"]}, {"bad": ["low", "low"]},
                       {"first": ["low"], "second": ["high"]}):
            with self.subTest(stages=stages), self.assertRaises(ValueError):
                characterize(self.problems, stages)

    def test_characterization_does_not_mutate_inputs(self):
        before = copy.deepcopy(self.problems)
        stages = {"subset": ["mid", "low"]}
        output = characterize(self.problems, stages)
        self.assertEqual(output["stages"]["subset"]["problem_ids"], ["low", "mid"])
        self.assertEqual(self.problems, before)
        self.assertEqual(stages["subset"], ["mid", "low"])


class NumericTests(unittest.TestCase):
    def test_schedule_weights_repeated_exposures_and_paired_problem_means(self):
        family = FAMILIES[0]
        first = [record("a", family, 1)] * 3 + [record("b", family, 3)]
        second = [record("a", family, 1), record("b", family, 1)]
        result = aggregate_numeric_residuals({"schedule": {"unit": "scheduled_presentations",
            "conditions": {family + "_gcm": first, family + "_paths": second}}})
        phase = result["phases"]["schedule"]
        contrast = phase["contrasts"][family + "_gcm_minus_" + family + "_paths"]
        self.assertEqual(contrast["global_mean_difference"]["identity_nodes"], .5)
        self.assertEqual(contrast["mean_paired_problem_difference"]["identity_nodes"], 1)
        self.assertEqual(phase["conditions"][family + "_gcm"]["rows"], 4)
        self.assertEqual(phase["conditions"][family + "_gcm"]["ordered_expressions"], 2)

    def test_inventory_duplicates_rejected_but_distinct_ordered_rows_kept(self):
        family = FAMILIES[0]
        repeated = record("a", family)
        with self.assertRaisesRegex(ValueError, "Duplicated"):
            aggregate_numeric_residuals({"inventory": {"unit": "ordered_inventory_rows",
                "conditions": {family: [repeated, repeated]}}})
        other = dict(repeated, expression="other_order")
        result = aggregate_numeric_residuals({"inventory": {"unit": "ordered_inventory_rows",
            "conditions": {family: [repeated, other]}}})
        summary = result["phases"]["inventory"]["conditions"][family]
        self.assertEqual(summary["rows"], 2)
        self.assertEqual(summary["problem_ac_classes"], 1)

    def test_empty_or_disjoint_condition_has_no_invented_paired_effect(self):
        first, second = FAMILIES
        result = aggregate_numeric_residuals({"inventory": {"unit": "ordered_inventory_rows",
            "conditions": {first: [record("a", first)], second: []}}})
        contrast = result["phases"]["inventory"]["contrasts"][first + "_minus_" + second]
        self.assertIsNone(contrast["global_mean_difference"]["depth"])
        self.assertIsNone(contrast["mean_paired_problem_difference"]["depth"])
        self.assertEqual(contrast["first_only_problem_ids"], ["a"])

    def test_wrong_family_nonfinite_and_inconsistent_exact_value_rejected(self):
        first, second = FAMILIES
        invalid = [record("a", second), record("a", first), record("a", first), record("a", first, 0)]
        invalid[1]["numeric_features"]["max_abs_intermediate"] = float("nan")
        invalid[2]["numeric_features"]["fraction_nodes"] = 1
        for row in invalid:
            with self.assertRaises(ValueError):
                aggregate_numeric_residuals({"inventory": {"unit": "ordered_inventory_rows",
                    "conditions": {first: [row]}}})

    def test_exact_fraction_aggregation(self):
        family = FAMILIES[0]
        row = record("a", family)
        row["numeric_features"].update(one_nodes=0, fraction_nodes=2, max_abs_intermediate=2 / 3,
                                       exact_nonroot_intermediates=["1/3", "2/3"])
        result = aggregate_numeric_residuals({"inventory": {"unit": "ordered_inventory_rows",
            "conditions": {family: [row]}}})
        means = result["phases"]["inventory"]["conditions"][family]["mean_numeric_features_exact"]
        self.assertEqual(means["max_abs_intermediate"], "2/3")


class FileInterfaceTests(unittest.TestCase):
    def test_immutable_output_and_input_hashes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            problems, stages, out = root / "problems.json", root / "stages.json", root / "out.json"
            problems.write_text(json.dumps({"one": problem([1, 2, 3, 20], 21)}))
            stages.write_text(json.dumps({"kept": ["one"]}))
            result = run(problems, stages, out)
            self.assertEqual(set(result["input_sha256"]), {"problems", "stage_ids"})
            original = out.read_bytes()
            with self.assertRaisesRegex(ValueError, "overwrite"):
                run("unread", "unread", out)
            self.assertEqual(out.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()

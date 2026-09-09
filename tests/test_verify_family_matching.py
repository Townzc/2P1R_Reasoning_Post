"""Synthetic, independent-verifier tests; no training pool or census is read."""
import copy
import hashlib
import json
from pathlib import Path
import random
import tempfile
import unittest

from scripts.verify_family_matching import (
    FAMILIES, FEATURES, expected_numeric_features, expected_prompt, expected_response, hall_support, independent_encoding,
    independent_policy, independent_stages,
    inspect_arithmetic, structure_flow_support, support_by_length,
    schedule_totals, shared_key_bytes, verify_blocks, verify_expression_record,
    verify_public_stages, verify_report,
)


def expression_record(expression, numbers, target):
    info = inspect_arithmetic(expression)
    response = expected_response(info)
    return {"problem_id": "synthetic", "numbers": numbers, "target": target,
            "expression": info.expression, "ac_class": info.ac_class,
            "structure_id": info.structure_id, "family": info.family,
            "response": response, "response_hash": hashlib.sha256(response.encode()).hexdigest()}


def support_record(family, structure, ac, length=90):
    return {"family": family, "structure_id": structure, "ac_class": ac,
            "expression": f"synthetic:{family}:{structure}:{ac}", "n_supervised": length,
            "problem_id": "synthetic", "encodable": True, "surface_compatible": True}


def synthetic_block():
    """A finite feature witness, not an arithmetic solution generator."""
    inventory, witnesses = {}, []
    for p in range(4):
        pid, slots = f"synthetic-{p}", []
        for family in FAMILIES:
            for index in range(4):
                structure = f"{family}-S{index}"
                row = support_record(family, structure, f"{family}-C{index}", 90 + p)
                row.update(problem_id=pid, n_prompt=10 + p, n_processed=100 + 2 * p,
                           numeric_features={**{name: 0 for name in FEATURES}, "operators": {"+": 3}})
                inventory[pid, row["expression"]] = row
                slots.append({"family": family, "structure_id": structure,
                              "ac_class": row["ac_class"], "record": row})
        witnesses.append({"problem_id": pid, "n_supervised": 90 + p, "slots": slots})
    assignment = list(range(4))
    random.Random(17).shuffle(assignment)
    block = {"block_id": 0, "problem_ids": [w["problem_id"] for w in witnesses],
             "identity_structures": [f"{FAMILIES[0]}-S{i}" for i in range(4)],
             "nonidentity_structures": [f"{FAMILIES[1]}-S{i}" for i in range(4)],
             "witnesses": witnesses, "assignment": assignment, "conditions": {}}
    from collections import Counter
    for family in FAMILIES:
        for allocation in ("paths", "gcm"):
            updates = []
            for r in range(4):
                rows = []
                for p, witness in enumerate(witnesses):
                    options = [s["record"] for s in witness["slots"] if s["family"] == family]
                    rows.append(options[(assignment[p] + (r if allocation == "paths" else 0)) % 4])
                updates.append({"round": r, "records": rows,
                                "supervised_tokens": sum(row["n_supervised"] for row in rows),
                                "processed_tokens": sum(row["n_processed"] for row in rows),
                                "padding_tokens": 4,
                                "structure_histogram": dict(Counter(row["structure_id"] for row in rows))})
            block["conditions"][family + "_" + allocation] = updates
    payload = {"blocks": [block], "condition_totals": schedule_totals([block])}
    return inventory, payload


class CharacterTokenizer:
    eos_token_id = 50000

    def __call__(self, text, add_special_tokens=False, return_offsets_mapping=False):
        result = {"input_ids": [ord(char) for char in text]}
        if return_offsets_mapping:
            result["offset_mapping"] = [(i, i + 1) for i in range(len(text))]
        return result


class ArithmeticTests(unittest.TestCase):
    def test_ac_mixed_label_counterexample(self):
        identity = expression_record("((1-3)+2)+20", [1, 2, 3, 20], 20)
        other = expression_record("(1-3)+(2+20)", [1, 2, 3, 20], 20)
        self.assertEqual(identity["ac_class"], other["ac_class"])
        self.assertEqual(identity["family"], FAMILIES[0])
        self.assertEqual(other["family"], FAMILIES[1])
        verify_expression_record(identity)
        verify_expression_record(other)

    def test_rejects_invalid_grammar_and_zero_division(self):
        for expression in ("__import__('os')", "True+1", "1.0+2", "-1+2", "2**3",
                           "1//2", "1/0", "[1][0]", "1<<2"):
            with self.subTest(expression=expression), self.assertRaises(ValueError):
                inspect_arithmetic(expression)

    def test_exact_fraction_and_ordered_nonidentity(self):
        info = inspect_arithmetic("(3/(2-1))*(4/3)")
        self.assertEqual(info.value, 4)
        self.assertEqual(info.identity_count, 1)
        self.assertTrue(any(v.denominator != 1 for v in info.intermediate_values))
        for expression in ("0-2", "1/2", "2*0", "2/2"):
            self.assertEqual(inspect_arithmetic(expression).identity_count, 0)

    def test_rejects_metadata_resource_and_trace_tamper(self):
        row = expression_record("((1-3)+2)+20", [1, 2, 3, 20], 20)
        variants = [{"numbers": [1, 2, 2, 20]}, {"target": 21},
                    {"family": FAMILIES[1]}, {"ac_class": "wrong"},
                    {"structure_id": "wrong"}, {"response_hash": "0" * 64},
                    {"response": row["response"].replace("= -2", "= -1")}]
        for changes in variants:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                verify_expression_record(dict(row, **changes))

    def test_features_exclude_root_and_keep_postorder_fraction(self):
        row = expression_record("(1/2)*(3+5)", [1, 2, 3, 5], 4)
        info = inspect_arithmetic(row["expression"])
        row["numeric_features"] = expected_numeric_features(info)
        self.assertEqual(row["numeric_features"]["exact_nonroot_intermediates"], ["1/2", "8"])
        self.assertEqual(row["numeric_features"]["max_abs_intermediate"], 8)
        verify_expression_record(row)
        row["numeric_features"]["exact_nonroot_intermediates"].append("4")
        with self.assertRaisesRegex(ValueError, "Numerical"):
            verify_expression_record(row)


class FlowTests(unittest.TestCase):
    def test_mixed_classes_cannot_fill_twice(self):
        rows = [support_record(family, f"S{i}", f"C{i}")
                for family in FAMILIES for i in range(4)]
        self.assertFalse(hall_support(rows, 4))
        self.assertIsNone(structure_flow_support(rows, 4))

    def test_hall_support_does_not_ensure_four_structures(self):
        rows = [support_record(family, "S0", f"{family}-{i}")
                for family in FAMILIES for i in range(4)]
        self.assertTrue(hall_support(rows, 4))
        self.assertIsNone(structure_flow_support(rows, 4))

    def test_flow_reroutes_shared_class(self):
        first, second = FAMILIES
        rows = [support_record(first, "A", "shared"), support_record(first, "A", "private"),
                support_record(first, "B", "second"), support_record(second, "C", "shared"),
                support_record(second, "D", "fourth")]
        witness = structure_flow_support(rows, 2)
        self.assertIsNotNone(witness)
        self.assertEqual({r["ac_class"] for r in witness[first]}, {"private", "second"})
        self.assertEqual(len({r["ac_class"] for rr in witness.values() for r in rr}), 4)

    def test_common_length_required_and_k2_not_k4(self):
        rows = [support_record(family, f"S{i}", f"{family}-{i}", 90 + family_index)
                for family_index, family in enumerate(FAMILIES) for i in range(4)]
        self.assertTrue(hall_support(rows, 4))
        self.assertTrue(all(not r["hall"] for r in support_by_length(rows).values()))
        small = [support_record(family, f"S{i}", f"{family}-{i}")
                 for family in FAMILIES for i in range(2)]
        self.assertIsNotNone(structure_flow_support(small, 2))
        self.assertIsNone(structure_flow_support(small, 4))

    def test_duplicate_rows_do_not_add_support(self):
        rows = [support_record(family, "S0", family) for family in FAMILIES] * 4
        self.assertFalse(hall_support(rows, 4))
        self.assertIsNone(structure_flow_support(rows, 4))


class EncodingTests(unittest.TestCase):
    def test_shifted_eos_and_prompt_mask(self):
        result = independent_encoding("p", "r", CharacterTokenizer())
        self.assertEqual(result["n_supervised"], 2)
        self.assertEqual(result["labels"][-2:], [ord("r"), 50000])
        self.assertTrue(all(x == -100 for x in result["labels"][:-2]))
        self.assertEqual(result["n_processed"], result["n_prompt"] + 2)

    def test_refuses_boundary_crossing_and_truncation(self):
        class Crossing(CharacterTokenizer):
            def __call__(self, text, **kwargs):
                result = super().__call__(text, **kwargs)
                if kwargs.get("return_offsets_mapping"):
                    result["offset_mapping"][0] = (0, len(text))
                return result
        with self.assertRaisesRegex(ValueError, "boundary"):
            independent_encoding("p", "r", Crossing())
        with self.assertRaisesRegex(ValueError, "truncation"):
            independent_encoding("p", "r", CharacterTokenizer(), max_length=2)

    def test_report_refuses_overwrite_before_any_input_read(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "verification.json"
            out.write_text("existing")
            with self.assertRaisesRegex(ValueError, "overwrite"):
                verify_report("nonexistent", "nonexistent", "nonexistent", out)
            self.assertEqual(out.read_text(), "existing")

    def test_unencodable_record_is_checked_but_has_no_fake_lengths(self):
        class WideTokenizer(CharacterTokenizer):
            def __call__(self, text, **kwargs):
                result = super().__call__(text, **kwargs)
                for key, items in result.items():
                    result[key] = [item for item in items for _ in range(2)]
                return result
        row = expression_record("((1-3)+2)+20", [1, 2, 3, 20], 20)
        row["encodable"] = False
        verify_expression_record(row, WideTokenizer())
        row["n_supervised"] = 0
        with self.assertRaisesRegex(ValueError, "Excluded"):
            verify_expression_record(row, WideTokenizer())


class ReportComponentTests(unittest.TestCase):
    def test_policy_representative_can_remove_family_support(self):
        rows = [support_record(family, f"S{i}", f"{prefix}{i}")
                for family, prefix in ((FAMILIES[0], "Z"), (FAMILIES[1], "A")) for i in range(4)]
        self.assertTrue(independent_stages(rows, ["synthetic"])["synthetic"]["structure_matched"])
        reduced = independent_policy(rows, "first_representative")
        self.assertEqual({row["family"] for row in reduced}, {FAMILIES[1]})
        self.assertFalse(independent_stages(reduced, ["synthetic"])["synthetic"]["raw_disjoint"])

    def test_public_flag_and_id_tamper(self):
        rows = [support_record(family, f"S{i}", f"{family}-C{i}") for family in FAMILIES for i in range(4)]
        computed = independent_stages(rows, ["synthetic"])
        problems = {"synthetic": {"numbers": [1, 2, 3, 4], "target": 10}}
        public = [{"problem_id": "synthetic", **problems["synthetic"], **computed["synthetic"],
                   "shared_key_supported": False, "greedy_selected": False}]
        verify_public_stages(public, computed, problems, set(), set())
        public[0]["structure_matched"] = False
        with self.assertRaisesRegex(ValueError, "stage"):
            verify_public_stages(public, computed, problems, set(), set())
        with self.assertRaisesRegex(ValueError, "IDs"):
            verify_public_stages([], computed, problems, set(), set())

    def test_block_accounting_includes_nonzero_padding(self):
        inventory, payload = synthetic_block()
        verified = verify_blocks(payload, inventory)
        self.assertEqual(verified["block_count"], 1)
        self.assertTrue(all(total["padding_tokens"] == 16 for total in verified["condition_totals"].values()))

    def test_rejects_budget_assignment_and_doublecount_tamper(self):
        inventory, original = synthetic_block()
        for kind in ("padding", "assignment", "repeat_paths", "reused_class"):
            payload = copy.deepcopy(original)
            block = payload["blocks"][0]
            update = block["conditions"][FAMILIES[0] + "_paths"][0]
            if kind == "padding":
                update["padding_tokens"] = 0
            elif kind == "assignment":
                block["assignment"] = block["assignment"][::-1]
            elif kind == "repeat_paths":
                block["conditions"][FAMILIES[0] + "_paths"][1]["records"] = update["records"]
            else:
                block["witnesses"][0]["slots"][4]["ac_class"] = block["witnesses"][0]["slots"][0]["ac_class"]
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                verify_blocks(payload, inventory)

    def test_compact_catalog_reconstructs_exact_original_bytes(self):
        inventory, payload = synthetic_block()
        rows = list(inventory.values())
        index = {(row["problem_id"], row["expression"]): i for i, row in enumerate(rows)}
        block = payload["blocks"][0]
        original = {"complete": False, "keys": [{"identity_structures": block["identity_structures"],
                    "nonidentity_structures": block["nonidentity_structures"], "problem_ids": block["problem_ids"],
                    "witnesses": {w["problem_id"]: w for w in block["witnesses"]}}]}
        compact_key = {key: value for key, value in original["keys"][0].items() if key != "witnesses"}
        compact_key["witnesses"] = {w["problem_id"]: {"n_supervised": w["n_supervised"],
            "record_indices": [index[s["record"]["problem_id"], s["record"]["expression"]] for s in w["slots"]]}
            for w in block["witnesses"]}
        catalog = {"metadata": {"complete": False}, "records": rows, "keys": [compact_key]}
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory)
            (report / "shared_key_catalog.json").write_text(json.dumps(catalog))
            expected = (json.dumps(original, indent=2, sort_keys=True) + "\n").encode()
            self.assertEqual(shared_key_bytes(report), expected)


if __name__ == "__main__":
    unittest.main()

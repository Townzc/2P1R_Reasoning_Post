"""Synthetic checks for the boundary data auditor; no frozen data is read."""
import copy
from pathlib import Path
import tempfile
import unittest

from scripts.verify_absent_boundary import (
    ARMS, audit_exposures, expected_main_rows, independent_budget,
    seeded_schedule, selected_packing_blocks, sha, update_residuals, verify,
    MODEL, PREPARATION_SOURCES, provenance_header,
)
from scripts.verify_family_matching import inspect_arithmetic, require


def fixture(block_count=2, cycles=8):
    blocks = []
    for b in range(block_count):
        items = []
        for q in range(4):
            pid = f"p{b}-{q}"
            paths = []
            for slot in range(4):
                paths.append({"problem_id": pid, "path_id": f"{pid}-AC{slot}", "ac_class": f"{pid}-AC{slot}",
                              "expression": f"synthetic:{pid}:{slot}", "structure_id": f"S{slot}",
                              "numeric_features": {"identity_nodes": 0, "zero_nodes": 0, "one_nodes": 0,
                                                   "negative_nodes": slot % 2, "fraction_nodes": 0, "depth": 3,
                                                   "max_abs_intermediate": slot + 2,
                                                   "exact_nonroot_intermediates": ["2", str(slot + 2)],
                                                   "operators": {"+": slot, "-": 3 - slot}}})
            items.append({"problem": {"problem_id": pid}, "paths": paths})
        blocks.append({"structures": [f"S{i}" for i in range(4)], "problems": items})
    rows = expected_main_rows(blocks)
    encoded = {}
    for arm in ARMS:
        encoded[arm] = [{"n_prompt": 50, "n_supervised": 60 + int(row["problem_id"][-1]),
                         "n_processed": 110 + int(row["problem_id"][-1]),
                         "response_hash": sha(row["expression"].encode())} for row in rows[arm]]
    return blocks, rows, encoded, seeded_schedule(block_count, cycles)


class SelectionTests(unittest.TestCase):
    def test_sorted_seed31_selection_is_independent_of_input_order(self):
        blocks = [{"group_id": i, "problem_ids": [f"p{i}-{j}" for j in range(4)],
                   "representative": {"structures": ["S0", "S1", "S2", "S3"]}} for i in range(33)]
        original = copy.deepcopy(blocks)
        first = selected_packing_blocks({"blocks": blocks})
        second = selected_packing_blocks({"blocks": list(reversed(blocks))})
        self.assertEqual(first, second)
        self.assertEqual(len(first[0]), 32)
        self.assertEqual(len(first[1]), 1)
        self.assertEqual(blocks, original)

    def test_auditor_does_not_silently_accept_smaller_tier(self):
        with self.assertRaises(ValueError):
            selected_packing_blocks({"blocks": []})
        with self.assertRaises(ValueError):
            selected_packing_blocks({"blocks": []}, count=16)


class ExposureTests(unittest.TestCase):
    def test_full_cycle_dose_and_nonzero_padding(self):
        _, rows, encoded, schedule = fixture()
        budgets = audit_exposures(rows, encoded, schedule, expected_problems=8, cycles=8)
        self.assertEqual(len(schedule), 64)
        self.assertEqual(budgets["paths"]["presentations"], 256)
        self.assertEqual(set(budgets["paths"]["problem_exposures"].values()), {32})
        self.assertEqual(set(budgets["paths"]["path_exposures"].values()), {8})
        self.assertEqual(set(budgets["gcm"]["path_exposures"].values()), {32})
        self.assertGreater(budgets["paths"]["padding_tokens"], 0)

    def test_row_gcm_path_tokens_and_operators_tamper_rejected(self):
        _, initial, initial_codes, schedule = fixture()
        for kind in ("path", "tokens", "operators", "structure", "problem"):
            rows, codes = copy.deepcopy(initial), copy.deepcopy(initial_codes)
            if kind == "path":
                rows["gcm"][0]["path_id"] = "new-path"
            elif kind == "tokens":
                codes["gcm"][0]["n_supervised"] += 1
            elif kind == "operators":
                rows["gcm"][0]["numeric_features"]["operators"] = {"*": 3}
            elif kind == "structure":
                rows["gcm"][0]["structure_id"] = "wrong"
            else:
                rows["gcm"][0]["problem_id"] = "wrong"
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                audit_exposures(rows, codes, schedule, expected_problems=8, cycles=8)

    def test_missing_or_duplicate_update_invalidates_dose(self):
        _, rows, codes, schedule = fixture()
        with self.assertRaises(ValueError):
            audit_exposures(rows, codes, schedule[:-1], expected_problems=8, cycles=8)
        bad = copy.deepcopy(schedule)
        bad[0] = [0, 0, 0, 0]
        with self.assertRaises(ValueError):
            audit_exposures(rows, codes, bad, expected_problems=8, cycles=8)

    def test_seeded_schedule_preserves_all_rows_exactly_per_cycle(self):
        schedule = seeded_schedule(32, 8)
        self.assertEqual(len(schedule), 1024)
        from collections import Counter
        self.assertEqual(set(Counter(i for update in schedule for i in update).values()), {8})
        self.assertEqual(len({i for update in schedule for i in update}), 512)
        self.assertNotEqual(schedule, seeded_schedule(32, 8, seed=32))

    def test_numeric_histograms_cover_every_update_and_identity_is_zero(self):
        _, rows, _, schedule = fixture()
        result = update_residuals(rows, schedule)
        self.assertTrue(all(sum(histogram.values()) == len(schedule) for histogram in result["histograms"].values()))
        self.assertEqual(result["histograms"]["identity_nodes"], {"0": len(schedule)})


class ArithmeticAndIOTests(unittest.TestCase):
    def test_missing_source_or_mutated_provenance_is_rejected(self):
        manifest = {"source_files_sha256": dict.fromkeys(PREPARATION_SOURCES, "digest"),
                    "model": dict(MODEL), "source_worktree_dirty": False, "gpu_seconds_added": 0,
                    "model_or_development_outputs_read": False, "candidate_join_complete": True,
                    "candidate_packing_blocks": 33, "candidate_sources": dict.fromkeys(("summary", "packing", "selection")),
                    "schedule_file": "schedule_seed31.json", "compatibility_only_arms": ["repeat", "surface"],
                    "group_disjoint_before_augmentation": True}
        provenance_header(manifest)
        for field, changed in (("source_files_sha256", {}), ("model", {}), ("candidate_join_complete", False),
                               ("model_or_development_outputs_read", True), ("candidate_packing_blocks", 32)):
            altered = copy.deepcopy(manifest)
            altered[field] = changed
            with self.subTest(field=field), self.assertRaises(ValueError):
                provenance_header(altered)

    def test_absence_is_computed_from_evaluated_intermediates(self):
        self.assertEqual(inspect_arithmetic("((2+3)+4)+5").identity_count, 0)
        self.assertEqual(inspect_arithmetic("((1-3)+2)+20").identity_count, 1)
        self.assertEqual(inspect_arithmetic("(1-3)+(2+20)").identity_count, 0)

    def test_existing_audit_is_preserved_without_reading_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "audit.json"
            out.write_text("existing")
            with self.assertRaisesRegex(ValueError, "overwrite"):
                verify("missing", "missing", out)
            self.assertEqual(out.read_text(), "existing")


if __name__ == "__main__":
    unittest.main()

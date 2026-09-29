"""Question-only leakage grouping and deterministic finite-prefix selection."""
import gzip
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from experiments.public_math_pilot_v1 import data


class PublicMathDataTests(unittest.TestCase):
    def test_normalization_preserves_case_numbers_signs_and_operators(self):
        self.assertEqual(data.canonical_question("  Ａ\t+\n１ = −2  "), "A + 1 = −2")
        self.assertNotEqual(data.canonical_question("x+1"), data.canonical_question("X+1"))
        self.assertNotEqual(data.canonical_question("x+1"), data.canonical_question("x-1"))
        for bad in (None, " \n", "replacement\ufffd", "bad\ud800"):
            with self.assertRaises(ValueError):
                data.canonical_question(bad)

    def test_short_questions_exact_only_and_length_jaccard_gates(self):
        self.assertEqual(data.near_duplicate("short", "short"), (True, 1., "exact"))
        self.assertEqual(data.near_duplicate("solve x+1", "solve x+2")[2], "short_exact_only")
        self.assertEqual(data.near_duplicate("a"*50, "a"*100)[2], "length_ratio")
        base = "".join(chr(1000+i) for i in range(300))
        changed = base[:150] + "x" + base[151:]
        matched, score, _ = data.near_duplicate(base, changed)
        self.assertTrue(matched)
        self.assertAlmostEqual(score, len(data.shingles(base) & data.shingles(changed)) /
                               len(data.shingles(base) | data.shingles(changed)))

    def test_minhash_is_fixed_and_matches_reference_library(self):
        from datasketch import MinHash
        text = "The question contains enough characters to enter the five gram MinHash candidate index."
        actual = data._sketch_chunk([(3, text)])[0]
        expected = MinHash(num_perm=128, seed=20260917)
        for gram in sorted(data.shingles(text)):
            expected.update(gram.encode())
        self.assertEqual(actual[0], 3)
        np.testing.assert_array_equal(actual[1], expected.hashvalues.astype(np.uint32))
        np.testing.assert_array_equal(data._sketch_chunk([(3, text)])[0][1], actual[1])

    def test_connected_component_leakage_includes_transitive_rows(self):
        # Each adjacent edge changes 5 of 186 unique shingles; the distant pair
        # changes 10 and fails >=.90. A benchmark still excludes the whole chain.
        base = "".join(chr(1000+i) for i in range(190))
        middle = base[:50] + "A" + base[51:]
        end = middle[:150] + "B" + middle[151:]
        self.assertTrue(data.near_duplicate(base, middle)[0])
        self.assertTrue(data.near_duplicate(middle, end)[0])
        self.assertFalse(data.near_duplicate(base, end)[0])
        db = sqlite3.connect(":memory:")
        db.execute("CREATE TABLE pairs(a,b,bands)")
        db.executemany("INSERT INTO pairs VALUES(?,?,?)", [(0, 1, 1), (1, 2, 2), (0, 2, 4)])
        with tempfile.TemporaryDirectory() as folder:
            roots, groups, blocked, counts = data.group_candidates(
                [base, middle, end], np.array([0, 1]), {2: [{"dataset": "minerva_math", "row_index": 0}]}, db, folder)
            self.assertEqual(roots.tolist(), [0, 0, 0])
            self.assertEqual(groups, {0: [0, 1]})
            self.assertIn(0, blocked)
            self.assertEqual(counts["accepted_edges"], 2)
            with gzip.open(Path(folder) / "near_duplicate_candidates.jsonl.gz", "rt") as stream:
                records = [json.loads(line) for line in stream]
            self.assertEqual(len(records), 3)
            self.assertFalse(records[1]["matched"])
        db.close()

    def test_benchmark_projection_ignores_all_answer_columns(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(data, "BENCHMARKS", {"minerva_math": 1}):
            path = Path(folder) / "minerva_math"
            path.mkdir()
            (path / "test.jsonl").write_text(json.dumps({"problem": "  Ｘ + 1  ",
                "solution": {"nested": ["unread", "not converted to Python data"]}, "answer": 7}) + "\n")
            self.assertEqual(data.read_benchmark_questions(folder), {"minerva_math": ["X + 1"]})
            self.assertEqual(data.read_benchmark_questions(folder, canonical=False), {"minerva_math": ["  Ｘ + 1  "]})

    def test_lazy_eligibility_prefix_matches_exhaustive_selection(self):
        groups = [{"group_id": str(i), "members": [2*i, 2*i+1], "sort_key": f"{i:03d}",
                   "canonical_question_sha256": f"canonical-{i}"} for i in range(20)]
        visited = []
        def refs(group):
            i = int(group["group_id"])
            return [{"row_id": 2*i+j, "question": "question " + str(i), "response": str(i),
                     "source": "fixture"} for j in (0, 1)]
        def qualify(row):
            visited.append(row["row_id"])
            if row["row_id"] % 2 == 0 or int(row["response"]) == 2:
                return None, "ineligible"
            return {"input_ids": [1, 2, 3], "response_length": 2}, None
        parser = lambda text: "answer " + text if int(text) % 3 == 0 else None
        dev, pool, encoded, rejected, audit = data.choose_splits(groups, refs, qualify, parser,
            dev_count=2, pool_count=4, pilot_count=3)
        # Independent exhaustive filter/reference choice and partition.
        all_qualified = []
        for group in groups:
            i = int(group["group_id"])
            if i != 2:
                all_qualified.append((i, 2*i+1))
        expected_dev = [x for x in all_qualified if x[0] % 3 == 0][:2]
        expected_pool = [x for x in all_qualified if x not in expected_dev][:4]
        self.assertEqual([r["row_id"] for r in dev], [r[1] for r in expected_dev])
        self.assertEqual([r["row_id"] for r in pool], [r[1] for r in expected_pool])
        self.assertEqual(len(encoded), 3)
        self.assertEqual(audit["groups_scanned"], 7)
        self.assertLess(max(visited), 14)
        self.assertIsNone(audit["qualified_pool_size_globally"])
        self.assertTrue(all(r["scope"] == "ordered_eligibility_prefix" for r in rejected))
        self.assertEqual(len({r["group_id"] for r in dev + pool}), 6)

    def test_unparseable_references_are_kept_for_training_not_mask_filtered(self):
        groups = [{"group_id": str(i), "sort_key": str(i), "canonical_question_sha256": str(i)} for i in range(3)]
        refs = lambda group: [{"row_id": int(group["group_id"]), "question": "Q", "response": group["group_id"]}]
        qualify = lambda row: ({"input_ids": [1, 2], "response_length": 1}, None)
        dev, pool, _, _, _ = data.choose_splits(groups, refs, qualify,
            lambda text: "0" if text == "0" else None, dev_count=1, pool_count=2, pilot_count=2)
        self.assertEqual([r["response"] for r in pool], ["1", "2"])
        with self.assertRaisesRegex(ValueError, "Insufficient qualified groups"):
            data.choose_splits(groups[:1], refs, qualify, lambda text: None, dev_count=1, pool_count=2, pilot_count=2)

    def test_image_and_encoding_filter_does_not_remove_unboxed_math(self):
        self.assertIsNone(data.reference_text_issue("What is 2+2?", "Four, since two pairs make four."))
        for text in ("![diagram](https://example.test/a.png)", "<image>", r"\includegraphics{a}", "[asy]draw(A--B);[/asy]"):
            self.assertEqual(data.reference_text_issue(text, "answer"), "unprovided_image_marker")
        self.assertIsNone(data.reference_text_issue("A triangle has sides 3,4,5. Its diagram is optional.", "12"))
        self.assertIsNone(data.reference_text_issue("What is 2+2?", "One can illustrate this in the figure; the answer is 4."))
        self.assertEqual(data.reference_text_issue("As shown in the diagram, some triangles are shaded. How many?", "4"),
                         "question_refers_to_unprovided_image")
        for question in ("In Figure 1, an angle is marked x.", "The picture is displayed below.",
                         "What cells change (see picture)?", "Use the given image to count squares.",
                         "[Include similar figure with updated annotation]", "The diagram shows three squares."):
            self.assertEqual(data.reference_text_issue(question, "Reference"), "question_refers_to_unprovided_image")
            self.assertTrue(data.image_exclusion_evidence(question, "Reference"))
        for question in ("What is the image of (1,2) under reflection?", "Is x in the image of this linear map?",
                         "A plane figure is bounded by y=x and y=x^2. Find its area.", "There are two picture books."):
            self.assertIsNone(data.reference_text_issue(question, "Reference"))
        self.assertEqual(data.reference_text_issue("question", ""), "missing_reference")
        self.assertEqual(data.reference_text_issue("question", "bad\x00text"), "bad_encoding")

    def test_independent_missing_visual_judgment_is_question_identity_bound(self):
        missing = (r"In parallelogram \(ABCD\), \(OE = EF = FD\). The area of the parallelogram "
                   "is 240 square centimeters. The area of the shaded region is _______ square centimeters.")
        self.assertEqual(data.reference_text_issue(missing, "Uninspected reference"),
                         "independently_adjudicated_missing_visual_definition")
        evidence = data.image_exclusion_evidence(missing, "Uninspected reference")
        self.assertEqual(evidence[-1]["source_row_id"], 505088)
        self.assertIsNone(data.reference_text_issue("The shaded region is exactly the square 0<=x<=1,0<=y<=1. Find its area.", "1"))

    def test_fully_defined_shaded_region_counterexamples_are_retained(self):
        # Question-only counterexamples from original rows 105202 and 499150;
        # no reference solution or correctness outcome is used for eligibility.
        questions = [
            "Two strips of width 1 and 2 overlap at an angle of $\\beta$. Calculate the area of the overlap "
            "(shaded region), which is defined by the boundaries where these strips intersect, forming a kite-shaped region.",
            "From a rectangle measuring $4 \\times 3$, a circle with a diameter of $2$ and a second circle with a "
            "diameter of $1$ are removed. The first circle is centered at a position so that it doesn't overlap with the "
            "second smaller circle. Determine which whole number is closest to the remaining shaded area of the rectangle.",
        ]
        for question in questions:
            with self.subTest(question=question):
                self.assertIsNone(data.reference_text_issue(question, "Uninspected reference"))

    def test_longest_engineering_profile_uses_real_length_extremes_and_stable_ids(self):
        rows = [{"problem_id": name, "input_ids": [1]*length, "response_ids": [2]*response}
                for name, length, response in (("b", 10, 5), ("a", 10, 4), ("c", 8, 7), ("d", 7, 7))]
        ids, audit = data.longest_profile_ids(rows)
        self.assertEqual(ids, ["a", "b", "c", "d"] * 8)
        self.assertEqual(audit["unique_ids"], ["a", "b", "c", "d"])
        self.assertTrue(audit["engineering_only"])
        self.assertEqual(audit["formal_training_updates"], 0)

    def test_real_tokenizer_complete_length_and_endings_without_model(self):
        from experiments.public_math_pilot_v1.tokenization import encode_training_pair
        from transformers import AutoTokenizer
        path = Path(".local/public_math_assets/model")
        if not (path / "tokenizer.json").exists():
            self.skipTest("Pinned local tokenizer unavailable")
        tokenizer = AutoTokenizer.from_pretrained(path, local_files_only=True)
        row = encode_training_pair(tokenizer, "What is 2+2?", r"Two pairs make four. \boxed{4}")
        self.assertEqual(row["response_ids"][-1], 151645)
        self.assertEqual(row["extra_eos_tokens"], 0)
        self.assertEqual(row["input_ids"][row["response_start"]:], row["blank_input_ids"][row["blank_response_start"]:])
        self.assertTrue(all(x == -100 for x in row["labels"][:row["response_start"]]))
        with self.assertRaisesRegex(ValueError, "truncation is forbidden"):
            encode_training_pair(tokenizer, "Question", "number " * 3000)


if __name__ == "__main__":
    unittest.main()

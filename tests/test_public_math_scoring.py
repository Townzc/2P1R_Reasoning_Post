"""Real pinned CPU parser/grader tests; no generation or network calls."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from experiments.public_math_pilot_v1 import scoring as s


class PublicMathScoringTests(unittest.TestCase):
    def test_vendor_files_and_pinned_cpu_dependencies(self):
        identity = s.environment_identity()
        self.assertEqual(identity["qwen_commit"], s.QWEN_COMMIT)
        self.assertEqual(identity["dependencies"]["sympy"], "1.12")
        self.assertNotIn("python_executor.py", identity["files_sha256"])
        self.assertNotIn("math_eval.py", identity["files_sha256"])

    def test_official_permissive_extraction_is_not_balanced_mask_boundary(self):
        self.assertEqual(s.parse_answer(r"First \boxed{2}; then \boxed{\frac{1}{2}}"), r"\frac{1}{2}")
        self.assertEqual(s.parse_answer(r"Incomplete \boxed{42"), "42")
        self.assertEqual(s.parse_answer("Computation yields 1,234"), "1234")
        self.assertEqual(s.parse_answer("No numerical answer"), "")
        self.assertIsNone(s.parse_answer("error"))

    def test_dataset_ground_truth_contracts(self):
        self.assertEqual(s.ground_truth({"answer": "0.5", "solution": r"Wrong prose \boxed{99}"}, "math500"), "0.5")
        self.assertEqual(s.ground_truth({"solution": r"Therefore \boxed{12}"}, "math"), "12")
        self.assertEqual(s.ground_truth({"answer": "Compute.\n#### 1,024"}, "gsm8k"), "1,024")
        with self.assertRaises(ValueError):
            s.ground_truth({"answer": "missing delimiter"}, "gsm8k")

    def test_official_direction_answer_is_preserved_as_unresolved_reference(self):
        # Real MATH500 index 97: original unit stripping removes "east".
        info = s.ground_truth_info({"answer": r"\text{east}", "solution": "unused"}, "math500")
        self.assertEqual(info["raw_reference"], r"\text{east}")
        self.assertEqual(info["reference"], "")
        self.assertTrue(info["normalization_empty"])
        self.assertEqual(info["reference_status"], "unresolved_reference")
        with s.MathScorer() as judge:
            for text in ("", "No answer", r"\boxed{\text{east}}", r"\boxed{7}"):
                result = judge.score(text, info["reference"], "math500")
                self.assertEqual(result["status"], "unresolved")
                self.assertEqual(result["reason"], "unresolved_reference")
                self.assertIsNone(result["correct"])
            for text in ("", "No answer"):
                result = judge.score(text, "7")
                self.assertEqual(result["status"], "resolved")
                self.assertIs(result["correct"], False)

    def test_symbolic_numeric_percent_wrong_and_parse_failure(self):
        with s.MathScorer(timeout_seconds=10) as judge:
            cases = [(r"\boxed{\frac{1}{2}}", "0.5", True),
                     (r"\boxed{x+x}", "2*x", True),
                     ("50", "0.5", True),  # Official percentage tolerance.
                     ("100.005", "100", True),  # Official rel_tol=1e-4.
                     ("7", "3", False), ("No answer", "3", False)]
            for text, answer, expected in cases:
                with self.subTest(text=text):
                    result = judge.score(text, answer)
                    self.assertEqual(result["status"], "resolved")
                    self.assertIs(result["correct"], expected)
            self.assertFalse(judge.score("No answer", "3")["parseable"])

    def test_no_code_execution_or_extra_round_and_stop_strings(self):
        with tempfile.TemporaryDirectory() as tmp, s.MathScorer() as judge:
            marker = Path(tmp) / "executed"
            code = "```python\nfrom pathlib import Path\nPath(" + repr(str(marker)) + ").write_text('yes')\n```"
            result = judge.score(code, "9")
            self.assertEqual(result["status"], "resolved")
            self.assertFalse(marker.exists())
            self.assertTrue(judge.score(r"\boxed{4}<|im_end|>\boxed{9}", "4")["correct"])

    def test_timeout_retains_unresolved_and_next_request_restarts(self):
        with s.MathScorer() as judge:
            pid = judge.process.pid
            with patch.object(judge, "_read", side_effect=TimeoutError("test deadline")):
                result = judge.score("4", "4")
            self.assertEqual(result["reason"], "judge_timeout")
            self.assertIsNone(result["correct"])
            self.assertEqual(result["status"], "unresolved")
            self.assertIsNone(judge.process)
            self.assertTrue(judge.score("4", "4")["correct"])
            self.assertNotEqual(judge.process.pid, pid)

    def test_infrastructure_and_invalid_reference_are_not_math_errors(self):
        with s.MathScorer() as judge:
            result = judge.score("4", "")
            self.assertEqual(result["status"], "unresolved")
            self.assertEqual(result["reason"], "unresolved_reference")
            self.assertIsNone(result["correct"])
        with patch.object(s.MathScorer, "_start", side_effect=RuntimeError("missing dependency")):
            result = s.score_completion("4", "4")
            self.assertEqual(result["reason"], "judge_unavailable")
            self.assertIsNone(result["correct"])


if __name__ == "__main__":
    unittest.main()

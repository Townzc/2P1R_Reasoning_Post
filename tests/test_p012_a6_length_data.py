import copy
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from experiments.p012.a6_length_data import self_check, strip_terminal_tokens


class A6DataGuards(unittest.TestCase):
    def setUp(self):
        self.rows = [{"parent_id": f"train/{i}", "problem": f"wrapped {i}",
                      "raw_problem": f"problem {i}", "solution": r"\boxed{1}", "gold": "1"}
                     for i in range(512)]
        self.order = {"training4096": [r["parent_id"] for r in self.rows],
                      "holdout500": ["held/1"], "demonstrations": []}

    def check(self, long=None, tests=None):
        fake = (SimpleNamespace(model_input=SimpleNamespace(length=9)),
                {"input_token_ids": list(range(10)), "target_tokens": 3})
        with patch("experiments.p012.a6_length_data.rendered_datum", return_value=fake):
            return self_check(self.rows, long if long is not None else self.rows,
                self.order, tests or [], None, None)

    def test_paired_order_and_supervised_totals(self):
        with patch("experiments.p012.a6_length_data.score_answer", return_value=True):
            result = self.check()
            self.assertEqual(result["tokens"]["long"]["supervised_tokens"]["sum"], 1536)
            altered = copy.deepcopy(self.rows); altered[0], altered[1] = altered[1], altered[0]
            with self.assertRaisesRegex(ValueError, "self-check1"):
                self.check(altered)

    def test_incorrect_or_embedded_terminator_stops(self):
        with patch("experiments.p012.a6_length_data.score_answer", return_value=False):
            with self.assertRaisesRegex(ValueError, "incorrect"):
                self.check()
        for marker in ("<think>", "<|im_end|>", "<|endoftext|>"):
            altered = copy.deepcopy(self.rows); altered[0]["solution"] += marker
            with patch("experiments.p012.a6_length_data.score_answer", return_value=True):
                with self.assertRaisesRegex(ValueError, "thinking/end"):
                    self.check(altered)

    def test_test_or_heldout_parent_stops(self):
        with patch("experiments.p012.a6_length_data.score_answer", return_value=True):
            with self.assertRaisesRegex(ValueError, "contamination"):
                self.check(tests=[{"problem": "problem 0"}])
            self.order["holdout500"].append("train/0")
            with self.assertRaisesRegex(ValueError, "contamination"):
                self.check()

    def test_only_suffix_end_tokens_removed(self):
        self.assertEqual(strip_terminal_tokens([1, 9, 2, 9, 9], {9}), [1, 9, 2])


if __name__ == "__main__":
    unittest.main()

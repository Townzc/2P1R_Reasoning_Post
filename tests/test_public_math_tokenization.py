"""CPU tests against the frozen real tokenizer; never load model weights."""
import os
from pathlib import Path
import unittest

from experiments.public_math_pilot_v1 import tokenization as t


class PublicMathTokenizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(os.environ.get("PUBLIC_MATH_TOKENIZER", ".local/public_math_assets/model"))
        if not (path / "tokenizer.json").exists():
            raise unittest.SkipTest("Frozen tokenizer assets unavailable; CPU integration test not measured")
        from transformers import AutoTokenizer
        cls.tokenizer = AutoTokenizer.from_pretrained(path, local_files_only=True, trust_remote_code=False)

    def test_exact_official_zero_shot_prompt_and_no_second_template(self):
        text = t.qwen_boxed_prompt("What is 2+2?")
        expected = ("<|im_start|>system\nYou are a helpful assistant.<|im_end|>\n"
                    "<|im_start|>user\nWhat is 2+2?\nPlease reason step by step, and put your final answer within \\boxed{}.<|im_end|>\n"
                    "<|im_start|>assistant\n")
        self.assertEqual(text, expected)
        self.assertEqual(self.tokenizer.decode(t.encode_prompt(self.tokenizer, "What is 2+2?")), text)
        self.assertEqual(t.encode_prompt(self.tokenizer, "What is 2+2?").count(151644), 3)

    def test_full_blank_shared_suffix_and_one_supervised_end(self):
        # Leading newline exercises a boundary where whole-text BPE can merge
        # across the response boundary; our policy preserves generation prefix.
        response = "\nCompute 2+2=4.\nFinal: \\boxed{4}."
        row = t.encode_training_pair(self.tokenizer, "What is 2+2?", response)
        self.assertEqual(row["input_ids"][row["response_start"]:], row["response_ids"])
        self.assertEqual(row["blank_input_ids"][row["blank_response_start"]:], row["response_ids"])
        self.assertEqual(row["labels"][:row["response_start"]], [-100] * row["response_start"])
        self.assertEqual(row["labels"][row["response_start"]:], row["response_ids"])
        self.assertEqual(row["response_ids"].count(151645), 1)
        self.assertNotIn(151643, row["response_ids"])
        self.assertEqual(self.tokenizer.decode(row["response_ids"]), response + "<|im_end|>")
        self.assertEqual(self.tokenizer.decode(row["input_ids"]), row["prompt"] + response + "<|im_end|>")
        self.assertEqual(len(row["response_offsets"]), len(row["response_ids"]))
        self.assertEqual(row["response_offsets"][-1], [len(response)] * 2)

    def test_no_silent_end_stripping_or_reference_truncation(self):
        for response in ("x<|im_end|>", "x<|endoftext|>", "", " "):
            with self.subTest(response=response), self.assertRaises(ValueError):
                t.encode_training_pair(self.tokenizer, "q", response)
        with self.assertRaisesRegex(ValueError, "truncation"):
            t.encode_training_pair(self.tokenizer, "q", "token " * 2100)

    def test_real_4096_cap_overrides_tokenizer_advertised_limit(self):
        audit = t.validate_tokenizer(self.tokenizer)
        self.assertEqual(audit["actual_context_limit"], 4096)
        self.assertEqual(audit["tokenizer_advertised_limit"], 131072)
        self.assertEqual(t.validate_eval_context(self.tokenizer, "q")["context_limit"], 4096)
        with self.assertRaisesRegex(ValueError, "actual 4096"):
            t.validate_eval_context(self.tokenizer, "word " * 2100)
        with self.assertRaises(ValueError):
            t.validate_eval_context(self.tokenizer, "q", context_limit=131072)

    def test_stop_postprocessing_preserves_earliest_boundary(self):
        self.assertEqual(t.trim_stop_text(" 4<|im_end|>9</s>8"), "4")


if __name__ == "__main__":
    unittest.main()

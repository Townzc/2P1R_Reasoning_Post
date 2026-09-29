"""CPU boundary tests only: fake generation returns preset token IDs.

No pretrained model, optimizer update, CUDA work, or network is performed.
The real greedy_profile orchestration and durable output writes are exercised.
"""
from contextlib import nullcontext
import copy
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

import torch

from experiments.public_math_pilot_v1 import preflight as p


def encoded(prefix=(101, 102), response=(11, 12, p.ASSISTANT_END_ID)):
    return {"input_ids": list(prefix + response), "labels": [-100] * len(prefix) + list(response),
            "prompt_ids": list(prefix), "response_ids": list(response), "response_start": len(prefix)}


class TinyTokenizer:
    def decode(self, ids, **kwargs):
        tokens = {3: "<", 4: "/s", 5: ">", 6: "4", 7: "x",
                  p.EOS_ID: "<|endoftext|>", p.ASSISTANT_END_ID: "<|im_end|>"}
        return "".join(tokens.get(i, "p") for i in ids)


class PresetGeneration:
    def __init__(self, outputs):
        self.outputs = outputs
        self.cursor = 0
        self.calls = []

    def eval(self):
        return self

    def generate(self, **kwargs):
        self.calls.append(kwargs)
        n = kwargs["input_ids"].shape[0]
        outputs = self.outputs[self.cursor:self.cursor + n]
        self.cursor += n
        return torch.cat([kwargs["input_ids"][:len(outputs)], torch.tensor(outputs)], dim=1)


class PublicMathPreflightTests(unittest.TestCase):
    def test_training_padding_has_no_supervision_or_qdw_mass(self):
        rows = [encoded(), encoded((101,), (11, p.ASSISTANT_END_ID))]
        masks = [[True, False, False], [False, False]]
        batch, labels, mask = p.training_batch(rows, device="cpu", force_length=2048, masks=masks)
        self.assertEqual(batch["input_ids"].shape, (2, 2048))
        self.assertEqual(batch["attention_mask"].sum(1).tolist(), [5, 3])
        self.assertEqual((labels != -100).sum(1).tolist(), [3, 2])
        self.assertEqual(mask.nonzero().tolist(), [[0, 2]])
        self.assertTrue(torch.all(labels[batch["attention_mask"] == 0] == -100))
        self.assertFalse(bool(mask[batch["attention_mask"] == 0].any()))
        with self.assertRaises(ValueError):
            p.training_batch(rows, device="cpu", force_length=4)

    def test_collator_rejects_count_preserving_wrong_label_or_response_alignment(self):
        row = encoded()
        wrong_gold = copy.deepcopy(row); wrong_gold["labels"][2] = 999
        prompt_supervised = copy.deepcopy(row); prompt_supervised["labels"][0] = 11; prompt_supervised["labels"][2] = -100
        wrong_start = copy.deepcopy(row); wrong_start["response_start"] = 1
        wrong_suffix = copy.deepcopy(row); wrong_suffix["response_ids"][0] = 13
        for case in (wrong_gold, prompt_supervised, wrong_start, wrong_suffix):
            with self.subTest(case=case), self.assertRaises(ValueError):
                p.training_batch([case], device="cpu")

    def test_left_padding_and_context_cap(self):
        batch = p.generation_batch([{"prompt_ids": [10]}, {"prompt_ids": [11, 12, 13]}], device="cpu")
        self.assertEqual(batch["input_ids"].tolist(), [[p.EOS_ID, p.EOS_ID, 10], [11, 12, 13]])
        self.assertEqual(batch["attention_mask"].tolist(), [[0, 0, 1], [1, 1, 1]])
        with self.assertRaises(ValueError):
            p.generation_batch([{"prompt_ids": [10] * 2049}], device="cpu")

    def _profile(self, outputs):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        output = Path(temporary.name)
        rows = [{"id": f"dev-{i}", "prompt_ids": [101]} for i in range(32)]
        model = PresetGeneration(outputs)
        original = p.generation_batch
        with patch.object(p, "generation_batch", side_effect=lambda group: original(group, device="cpu")), \
             patch.object(p.torch, "autocast", side_effect=lambda *a, **k: nullcontext()), \
             patch.object(p.torch.cuda, "synchronize"):
            summary = p.greedy_profile(model, TinyTokenizer(), rows, output, {"test": "NO_REAL_MODEL"},
                                       time.time() + 1000, ledger=output / "physical_ledger.jsonl")
        records = [r for path in sorted(output.glob("*.outputs.json"))
                   for r in json.loads(path.read_text())["records"]]
        return model, summary, records

    def test_string_stop_before_batch_eos_padding_is_not_reported_as_eos(self):
        outputs = [[3, 4, 5, p.EOS_ID, p.EOS_ID]] + [[6, p.ASSISTANT_END_ID, p.EOS_ID, p.EOS_ID, p.EOS_ID]] * 31
        model, summary, records = self._profile(outputs)
        self.assertEqual(records[0]["stop_reason"], "stop_string")
        self.assertEqual(records[0]["generated_ids"], [3, 4, 5])
        self.assertEqual(records[0]["output_tokens"], 3)
        self.assertEqual(records[1]["generated_ids"], [6, p.ASSISTANT_END_ID])
        self.assertEqual(records[1]["stop_reason"], "eos")
        self.assertEqual(summary["outputs"], 32)
        self.assertEqual(summary["output_tokens"], 65)
        self.assertEqual(len(model.calls), 2)
        self.assertTrue(all(call["do_sample"] is False for call in model.calls))
        self.assertTrue(all(call["eos_token_id"] == [p.ASSISTANT_END_ID, p.EOS_ID] for call in model.calls))

    def test_real_length_cap_is_retained_and_short_unexplained_output_rejected(self):
        outputs = [[7] * 2048] + [[6, p.ASSISTANT_END_ID] + [p.EOS_ID] * 2046] * 31
        _, summary, records = self._profile(outputs)
        self.assertEqual(records[0]["stop_reason"], "length_cap")
        self.assertEqual(records[0]["output_tokens"], 2048)
        self.assertEqual(summary["length_caps"], 1)
        with self.assertRaises(ValueError):
            self._profile([[7] * 5] * 32)

    def test_missing_generated_batch_row_is_not_silently_complete(self):
        with self.assertRaises(ValueError):
            self._profile([[6, p.ASSISTANT_END_ID]] * 31)

    def test_nonformal_reservations_survive_attempts_and_never_exceed_eight(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "shared_physical.jsonl"
            for i in range(8):
                event = p.reserve_call(ledger, "nonformal_optimizer_update", f"attempt-{i}/SFT")
                self.assertEqual(event["ordinal"], i + 1)
            with self.assertRaisesRegex(RuntimeError, "budget exhausted"):
                p.reserve_call(ledger, "nonformal_optimizer_update", "attempt-9/SFT")
            self.assertEqual(len(ledger.read_text().splitlines()), 8)
            self.assertEqual(p.reserve_call(ledger, "annotation_forward", "row-0/full")["ordinal"], 1)


if __name__ == "__main__":
    unittest.main()

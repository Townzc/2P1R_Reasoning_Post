"""New synthetic C6 adapter cases; no original model, dev rows or gold read."""
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.p010.cue_answer_key import answer_key, extracted_tail
from experiments.p010.cue_probability import DurableProbabilityProvider, next_probabilities, validate_rows


def rows():
    return [dict(problem_id='synthetic/'+str(i), input_ids=[1, 2]+[3]*(i % 4)) for i in range(30)]


class ProbabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import torch
        from transformers import Qwen2Config, Qwen2ForCausalLM
        torch.set_num_threads(2)
        torch.manual_seed(971)
        cls.model = Qwen2ForCausalLM(Qwen2Config(vocab_size=32, hidden_size=16,
            intermediate_size=32, num_hidden_layers=1, num_attention_heads=2,
            num_key_value_heads=2, max_position_embeddings=2048)).eval()

    def test_real_tiny_qwen_padding_and_final_logits(self):
        import torch
        matrix = next_probabilities(self.model, rows(), (5,), 0, 32)
        for row, actual in zip(rows(), matrix):
            with torch.inference_mode():
                logits = self.model(input_ids=torch.tensor([row['input_ids']+[5]]),
                                    use_cache=False).logits[0, -1].float()
                expected = torch.softmax(logits, -1)
            self.assertTrue(torch.allclose(torch.tensor(actual), expected, atol=1e-7, rtol=1e-6))
        self.assertTrue(all(abs(sum(row)-1) < 2e-5 for row in matrix))

    def test_gold_and_overlength_inputs_rejected(self):
        data = rows(); data[0]['solution'] = 'not permitted'
        with self.assertRaises(ValueError): validate_rows(data, 32)
        data = rows(); data[0]['input_ids'] = [1]*1023
        with self.assertRaises(ValueError): validate_rows(data, 32)
        data = rows(); data[0].pop('problem_id')
        with self.assertRaises(ValueError): validate_rows(data, 32)

    def test_confirmed_matrix_exact_and_replay_rejected(self):
        import numpy as np
        with tempfile.TemporaryDirectory() as tmp:
            provider = DurableProbabilityProvider(self.model, rows(), 0, 32, Path(tmp)/'probabilities', time.time()+60)
            actual = provider(())
            saved = np.load(Path(tmp)/'probabilities/root/full_probabilities.npy', allow_pickle=False)
            self.assertTrue(np.array_equal(saved, np.asarray(actual, dtype=np.float32)))
            with self.assertRaises(FileExistsError): provider(())

    def test_unconfirmed_measurement_preserved_and_not_retried(self):
        with tempfile.TemporaryDirectory() as tmp:
            provider = DurableProbabilityProvider(self.model, rows(), 0, 32, Path(tmp)/'p', time.time()+60)
            with patch('experiments.p010.cue_probability.next_probabilities', side_effect=RuntimeError('synthetic forward failure')):
                with self.assertRaises(RuntimeError): provider((2,))
            self.assertTrue((Path(tmp)/'p/token_2/INTENT.json').exists())
            self.assertFalse((Path(tmp)/'p/token_2/COMPLETED.json').exists())
            with self.assertRaises(FileExistsError): provider((2,))


class AnswerKeyTests(unittest.TestCase):
    def test_reference_tail_and_nested_extraction(self):
        self.assertEqual(extracted_tail(r'\boxed{1} revised \boxed{\frac{1}{2}}'), r'\frac{1}{2}')
        self.assertEqual(extracted_tail('Final answer: '+('a'*100)), 'a'*80)
        self.assertIsNone(extracted_tail(r'\boxed{2}'+('x'*2001)))

    def test_numeric_grouping_and_missing_are_label_free(self):
        self.assertEqual(answer_key(r'\boxed{1/2}', lambda _: [.5, '1/2']),
                         answer_key(r'\boxed{0.5}', lambda _: [.5, '0.5']))
        self.assertEqual(answer_key(r'\boxed{-0}', lambda _: [-0., '-0']), 'number:0.0')
        self.assertIsNone(answer_key('no committed answer', lambda _: self.fail('parser must not run')))
        self.assertIsNone(answer_key(r'\boxed{x}', lambda _: []))

    def test_technical_failure_never_silently_missing(self):
        def timeout(_): raise TimeoutError('synthetic parser timeout')
        with self.assertRaises(TimeoutError): answer_key(r'\boxed{1}', timeout)
        with self.assertRaises(ValueError): answer_key(r'\boxed{x}', lambda _: [float('inf')])


if __name__ == '__main__':
    unittest.main()

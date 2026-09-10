"""E015 CPU correctness fixtures; no pretrained weights or GPU execution.

The tiny-model equality check covers deterministic CPU update operations only.
It does not claim numerical reproduction of the historical A800 trajectory.
"""
from collections import Counter
from contextlib import redirect_stdout
import copy
import io
import json
import math
import types
import unittest

import torch
import torch.nn.functional as F

from analyses.e014 import token_hash
from analyses.e015_core import make_cases, reference_record, terminal_lr, train_updates
from src.relation_experiment import accumulate_gradients
from src.sft_data import update_schedule


def encoded_fixture(count=32):
    rows = []
    for index in range(count):
        prompt = [3 + index % 3] * (1 + index % 2)
        target = [6 + index % 3] * (1 + index % 3) + [2]
        rows.append({'problem_id': f'fixture-{index}', 'input_ids': prompt + target,
                     'labels': [-100] * len(prompt) + target, 'n_prompt': len(prompt),
                     'n_supervised': len(target), 'n_processed': len(prompt + target)})
    return rows


class TinyCausalLM(torch.nn.Module):
    """Tokenwise embedding/linear logits exercise the real shifted SFT loss."""

    def __init__(self):
        super().__init__()
        self.embedding = torch.nn.Embedding(12, 4)
        self.projection = torch.nn.Linear(4, 12)
        self.forward_calls = 0
        self.interrupt_at = None

    def forward(self, input_ids, attention_mask, use_cache):
        self.forward_calls += 1
        if self.forward_calls == self.interrupt_at:
            raise KeyboardInterrupt('fixture interrupted during a microbatch')
        if use_cache:
            raise AssertionError('Training must disable cache')
        return types.SimpleNamespace(logits=self.projection(self.embedding(input_ids)))


class ObservedAdamW(torch.optim.AdamW):
    """Observe the LR passed into the real optimizer, not only logged values."""

    def __init__(self, model):
        super().__init__([{'params': model.embedding.parameters(), 'lr': .02},
                          {'params': model.projection.parameters(), 'lr': .03}],
                         weight_decay=.1)
        self.actual_lrs = []
        self.parameter_history = []
        self.state_steps = []
        self.final_state_before = None

    def step(self, closure=None):
        self.actual_lrs.append([group['lr'] for group in self.param_groups])
        first = self.param_groups[0]['params'][0]
        if len(self.actual_lrs) == 256:
            self.final_state_before = copy.deepcopy(self.state[first])
        result = super().step(closure)
        self.parameter_history.append([p.detach().clone() for group in self.param_groups
                                       for p in group['params']])
        self.state_steps.append(int(self.state[first]['step'].item()))
        return result


class FlushedLog(io.StringIO):
    def __init__(self):
        super().__init__()
        self.flushes = 0

    def flush(self):
        self.flushes += 1
        super().flush()


class TerminalLearningRate(unittest.TestCase):
    def test_integer_boundaries_and_terminal_zero(self):
        self.assertEqual(terminal_lr(1), 5e-5)
        self.assertEqual(terminal_lr(192), 5e-5)
        self.assertAlmostEqual(terminal_lr(193), 4.996988640512931e-5, places=18)
        self.assertAlmostEqual(terminal_lr(255), 3.011359487068987e-8, places=18)
        self.assertEqual(terminal_lr(256), 0.0)
        values = [terminal_lr(step) for step in range(192, 257)]
        self.assertTrue(all(a > b for a, b in zip(values, values[1:])))

    def test_noninteger_boolean_and_out_of_range_steps_rejected(self):
        for bad in (True, False, 0, -1, 257, 192.0, '192', None):
            with self.subTest(step=bad), self.assertRaises(ValueError):
                terminal_lr(bad)


class FrozenReferenceCases(unittest.TestCase):
    def test_exact_order_masks_eos_and_hashes_are_retained(self):
        encoded = encoded_fixture(3)
        train = [{'problem_id': row['problem_id']} for row in encoded]
        cases = make_cases(train, encoded)
        self.assertEqual([case['row_index'] for case in cases], [0, 1, 2])
        for case, row in zip(cases, encoded):
            self.assertEqual(case['problem_id'], row['problem_id'])
            self.assertEqual(case['prompt_ids'] + case['target_ids'], row['input_ids'])
            self.assertEqual(case['target_ids'][-1], 2)
            self.assertEqual(case['prompt_ids_sha256'], token_hash(case['prompt_ids']))
            self.assertEqual(case['target_ids_sha256'], token_hash(case['target_ids']))
            self.assertFalse(case['selected_for_batch1'])

    def test_cardinality_order_empty_sides_and_mask_tampering_rejected(self):
        encoded = encoded_fixture(2)
        train = [{'problem_id': row['problem_id']} for row in encoded]
        variants = [(train[:-1], encoded), (list(reversed(train)), encoded)]
        for key, value in [('n_prompt', 0), ('n_prompt', len(encoded[0]['input_ids'])),
                           ('labels', encoded[0]['input_ids'])]:
            bad = copy.deepcopy(encoded)
            bad[0][key] = value
            variants.append((train, bad))
        bad = copy.deepcopy(encoded)
        bad[0]['labels'][-1] = -100
        variants.append((train, bad))
        for rows, encodings in variants:
            with self.subTest(rows=rows, encoded=encodings), self.assertRaises(ValueError):
                make_cases(rows, encodings)


class ReferenceConfidence(unittest.TestCase):
    def setUp(self):
        torch.set_num_threads(1)
        self.case = {'problem_id': 'confidence-fixture', 'prompt_ids': [3, 8, 9],
                     'target_ids': [4, 5, 7, 2], 'prompt_ids_sha256': token_hash([3, 8, 9])}
        self.logits = torch.full((7, 12), -2.0)
        # Target j uses row 2+j. Row 6 is the unused output after terminal EOS.
        self.logits[2, 4], self.logits[2, 7] = 5, 2
        self.logits[3, 5], self.logits[3, 11] = 1, 6
        self.logits[4, 7], self.logits[4, 0] = 3, 3
        self.logits[5, 2], self.logits[5, 9] = 4, 4
        self.logits[6, 11] = 1000

    def test_all_targets_and_eos_match_independent_causal_cross_entropy(self):
        record = reference_record(self.logits, self.case)
        labels = torch.tensor([-100, -100, -100, 4, 5, 7, 2])
        expected = F.cross_entropy(self.logits[:-1], labels[1:], ignore_index=-100,
                                   reduction='sum').item()
        self.assertAlmostEqual(record['loss_sum'], expected, places=5)
        self.assertEqual(record['supervised_tokens'], 4)
        self.assertEqual(record['argmax_ids'], [4, 11, 0, 2])
        self.assertEqual(record['target_top1_correct'], 2)
        self.assertTrue(record['eos_is_argmax'])
        event, = record['queries']
        self.assertEqual(event['kind'], 'reference_eos')
        self.assertEqual(event['target_position'], 3)
        self.assertEqual(event['causal_logit_index'], 5)
        self.assertEqual(event['context_ids_sha256'], token_hash([3, 8, 9, 4, 5, 7]))
        self.assertEqual(event['conditioning'], 'reference_prefix_full_forward_use_cache_false')
        changed = self.logits.clone()
        changed[0:2] = torch.arange(12)
        changed[-1] = -1000
        self.assertEqual(reference_record(changed, self.case), record)

    def test_signed_best_other_confidence_distinguishes_wins_errors_and_ties(self):
        record = reference_record(self.logits, self.case)
        self.assertEqual(record['target_minus_best_other_logit'], [3, -5, 0, 0])
        self.assertEqual(record['target_minus_argmax_logit'], [0, -5, 0, 0])
        # Independently enumerate all vocabulary entries; no top-k implementation.
        for j, target in enumerate(self.case['target_ids']):
            values = self.logits[2 + j].tolist()
            maximum = max(values)
            log_z = maximum + math.log(math.fsum(math.exp(v - maximum) for v in values))
            self.assertAlmostEqual(record['argmax_log_probability'][j], maximum - log_z, places=6)
            self.assertAlmostEqual(record['target_nll'][j], log_z - values[target], places=6)
            other = max(value for index, value in enumerate(values) if index != target)
            self.assertEqual(record['target_minus_best_other_logit'][j], values[target] - other)
        self.assertFalse(record['argmax_ids'][2] == self.case['target_ids'][2])
        self.assertEqual(record['queries'][0]['target_rank_strict_greater'], 1)

    def test_model_vocabulary_argmax_may_exceed_tokenizer_vocabulary(self):
        tokenizer_vocab_size = 10
        record = reference_record(self.logits, self.case)
        self.assertTrue(all(token < tokenizer_vocab_size for token in record['target_ids']))
        self.assertGreaterEqual(record['argmax_ids'][1], tokenizer_vocab_size)
        self.assertLess(record['argmax_ids'][1], self.logits.shape[-1])
        self.assertEqual(record['target_minus_best_other_logit'][1], -5)

    def test_nonfinite_supervised_logits_and_single_token_vocabulary_rejected(self):
        for row in range(2, 6):
            for value in (float('nan'), float('inf'), float('-inf')):
                bad = self.logits.clone()
                bad[row, 10] = value
                with self.subTest(row=row, value=value), self.assertRaises(ValueError):
                    reference_record(bad, self.case)
        one = {**self.case, 'prompt_ids': [0], 'target_ids': [0]}
        with self.assertRaises(ValueError):
            reference_record(torch.zeros(2, 1), one)


class TrainingIntervention(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)
        torch.manual_seed(815)
        cls.initial_model = TinyCausalLM()
        cls.encoded = encoded_fixture()
        cls.schedule = update_schedule(32, 256, 4, 17)
        cls.cfg = {'microbatch_size': 1, 'grad_clip': .3}
        cls.model = copy.deepcopy(cls.initial_model)
        cls.optimizer = ObservedAdamW(cls.model)
        cls.log, cls.history = FlushedLog(), []
        with redirect_stdout(io.StringIO()):
            cls.returned = train_updates(cls.model, cls.optimizer, cls.encoded, cls.schedule,
                                         cls.cfg, 2, cls.log, cls.history, device='cpu')

    def test_actual_optimizer_lr_precedes_each_step_and_matches_every_record(self):
        self.assertIs(self.returned, self.history)
        self.assertEqual(len(self.optimizer.actual_lrs), 256)
        for step, (actual, record) in enumerate(zip(self.optimizer.actual_lrs, self.history), 1):
            self.assertEqual(actual, [terminal_lr(step)] * 2)
            self.assertEqual(record['actual_learning_rate'], actual[0])
            self.assertEqual(record['step'], step)
        self.assertEqual(self.log.flushes, 256)
        self.assertEqual([json.loads(line) for line in self.log.getvalue().splitlines()], self.history)

    def test_zero_lr_final_step_keeps_weights_but_advances_optimizer_state(self):
        before, after = self.optimizer.parameter_history[-2:]
        for old, new in zip(before, after):
            self.assertTrue(torch.equal(old, new))
        self.assertEqual(self.optimizer.actual_lrs[-1], [0.0, 0.0])
        self.assertEqual(self.optimizer.state_steps, list(range(1, 257)))
        first = self.optimizer.param_groups[0]['params'][0]
        self.assertEqual(int(self.optimizer.final_state_before['step'].item()), 255)
        self.assertFalse(torch.equal(self.optimizer.final_state_before['exp_avg'],
                                    self.optimizer.state[first]['exp_avg']))

    def test_all_256_records_and_32_exposures_per_parent_include_final_step(self):
        self.assertEqual([row['row_indices'] for row in self.history], self.schedule)
        exposures = Counter(index for row in self.history for index in row['row_indices'])
        self.assertEqual(exposures, Counter({index: 32 for index in range(32)}))
        self.assertEqual(sum(row['supervised_tokens'] for row in self.history),
                         32 * sum(row['n_supervised'] for row in self.encoded))
        self.assertEqual(sum(row['processed_tokens'] for row in self.history),
                         32 * sum(row['n_processed'] for row in self.encoded))
        self.assertTrue(all(row['peak_allocated_mib'] == row['peak_reserved_mib'] == 0
                            for row in self.history))

    def test_first_192_updates_match_original_constant_lr_operations_on_cpu(self):
        historical = copy.deepcopy(self.initial_model)
        optimizer = torch.optim.AdamW(historical.parameters(), lr=5e-5, weight_decay=.1)
        for step, indices in enumerate(self.schedule[:192]):
            historical.train()
            optimizer.zero_grad(set_to_none=True)
            nll = accumulate_gradients(historical, [self.encoded[i] for i in indices], 2,
                                       self.cfg['microbatch_size'], 'cpu')
            norm = torch.nn.utils.clip_grad_norm_(historical.parameters(), self.cfg['grad_clip'])
            optimizer.step()
            self.assertEqual(nll, self.history[step]['response_nll'])
            self.assertEqual(norm.item(), self.history[step]['grad_norm'])
            for actual, expected in zip(historical.parameters(), self.optimizer.parameter_history[step]):
                self.assertTrue(torch.equal(actual, expected), f'CPU divergence at update {step + 1}')

    def test_interrupted_microbatch_preserves_only_completed_history_and_flushed_log(self):
        model = copy.deepcopy(self.initial_model)
        # Two updates finish (8 forwards), then interruption follows one microbatch.
        model.interrupt_at = 10
        optimizer = ObservedAdamW(model)
        log, history = FlushedLog(), []
        with redirect_stdout(io.StringIO()), self.assertRaises(KeyboardInterrupt):
            train_updates(model, optimizer, self.encoded, self.schedule, self.cfg, 2,
                          log, history, device='cpu')
        self.assertEqual(model.forward_calls, 10)
        self.assertEqual([row['step'] for row in history], [1, 2])
        self.assertEqual([row['row_indices'] for row in history], self.schedule[:2])
        self.assertEqual([json.loads(line) for line in log.getvalue().splitlines()], history)
        self.assertEqual(log.flushes, 2)
        self.assertEqual(optimizer.state_steps, [1, 2])
        self.assertEqual(len(optimizer.actual_lrs), 2)
        self.assertTrue(any(p.grad is not None for p in model.parameters()))
        for actual, expected in zip(model.parameters(), self.optimizer.parameter_history[1]):
            self.assertTrue(torch.equal(actual, expected))


if __name__ == '__main__':
    unittest.main()

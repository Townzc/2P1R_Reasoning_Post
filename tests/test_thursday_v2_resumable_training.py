"""CPU fixtures for exact state continuation; no pretrained model is loaded."""
import copy
import json
from pathlib import Path
import random
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
import torch
from transformers import Qwen2Config, Qwen2ForCausalLM

from experiments.thursday_probe.lora import attach, parameter_digest
from experiments.thursday_probe_v2.config import learning_rates
from experiments.thursday_probe_v2 import resumable_training as rt
from experiments.thursday_probe_v2.training import train as original_train


class ResumableTrainingTests(unittest.TestCase):
    def setUp(self):
        torch.manual_seed(17); torch.set_num_threads(1)
        config = Qwen2Config(vocab_size=32, hidden_size=16, intermediate_size=32,
            num_hidden_layers=1, num_attention_heads=2, num_key_value_heads=1,
            max_position_embeddings=32, attention_dropout=0)
        self.model = attach(Qwen2ForCausalLM(config))
        self.rows = [dict(input_ids=[1, 2, 3, 4, 5], labels=[-100, -100, 3, 4, 5],
                         n_supervised=3, n_processed=5),
                     dict(input_ids=[2, 1, 4, 3], labels=[-100, -100, 4, 3],
                         n_supervised=2, n_processed=4)]
        self.schedule = [[0, 1], [1, 0], [0, 1], [1, 0]]
        self.lrs = learning_rates(4)
        self.tokenizer = SimpleNamespace(pad_token_id=0)
        self.identity = dict(run_id='cpu_fixture', parent=parameter_digest(self.model, True))

    def run_segment(self, model, out, end_step=4, deadline=None, identity=None):
        return rt.train_segment(model, self.rows, self.schedule, self.lrs, self.tokenizer, out,
            identity=identity or self.identity, end_step=end_step,
            deadline=time.time() + 600 if deadline is None else deadline, device='cpu')

    def recovery(self, out):
        pointer = json.loads((out / 'recovery/latest.json').read_text())
        return torch.load(out / 'recovery' / pointer['file'], map_location='cpu', weights_only=True)

    def assert_tree_equal(self, left, right):
        self.assertTrue(rt._same_tree(left, right))

    def test_continuous_equals_two_segments_full_rng_and_optimizer(self):
        continuous = copy.deepcopy(self.model); split = copy.deepcopy(self.model)
        original = rt.accumulate_gradients

        def with_random_consumption(*args, **kwargs):
            random.random(); np.random.random(); torch.rand(3)
            return original(*args, **kwargs)

        with tempfile.TemporaryDirectory() as folder, patch.object(rt, 'accumulate_gradients', with_random_consumption):
            root = Path(folder)
            complete = self.run_segment(continuous, root / 'continuous')
            partial = self.run_segment(split, root / 'split', end_step=2)
            self.assertEqual((partial['status'], partial['step']), ('partial', 2))
            # Simulate a new process with another loaded adapter and unrelated RNG.
            restarted = copy.deepcopy(self.model)
            random.seed(812); np.random.seed(913); torch.manual_seed(414)
            resumed = self.run_segment(restarted, root / 'split')
            self.assertEqual((resumed['status'], resumed['step']), ('completed', 4))
            self.assertEqual(complete['final_adapter'], resumed['final_adapter'])
            self.assertEqual([r['step'] for r in resumed['cumulative_history']], [1, 2, 3, 4])
            self.assertEqual(sum(r['supervised_tokens'] for r in resumed['cumulative_history']), 20)
            state_a = self.recovery(root / 'continuous'); state_b = self.recovery(root / 'split')
            for key in ('adapter', 'optimizer', 'rng'):
                self.assert_tree_equal(state_a[key], state_b[key])
            self.assertEqual(len(list((root / 'split/recovery').glob('*.pt'))), 1)
            self.assertEqual(len(list((root / 'split/segments').glob('*.jsonl'))), 2)

    def test_soft_deadline_commits_a_completed_update_then_resumes(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with patch.object(rt.time, 'time', side_effect=[1000., 1031.]):
                result = self.run_segment(self.model, root, deadline=1060.)
            self.assertEqual((result['status'], result['step']), ('partial', 1))
            self.assertEqual(self.recovery(root)['step'], 1)
            final = self.run_segment(copy.deepcopy(self.model), root)
            self.assertEqual((final['status'], final['step']), ('completed', 4))
            self.assertEqual(len(final['cumulative_history']), 4)

    def test_expired_soft_deadline_preserves_zero_step_and_resume(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            result = self.run_segment(self.model, root, deadline=time.time() + 29)
            self.assertEqual((result['status'], result['step']), ('partial', 0))
            self.assertEqual(set(result['checkpoints']), {'0'})
            self.assertFalse(self.recovery(root)['optimizer']['state'])
            self.assertEqual(self.run_segment(self.model, root)['step'], 4)

    def test_new_child_resets_optimizer_but_resume_does_not(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.run_segment(self.model, root / 'parent')
            parent = parameter_digest(self.model, True)
            child_id = dict(run_id='child', parent=parent)
            child = self.run_segment(self.model, root / 'child', end_step=1, identity=child_id)
            self.assertEqual(child['initial_adapter'], parent)
            state = self.recovery(root / 'child')
            self.assertTrue(state['optimizer']['state'])
            self.assertTrue(all(float(v['step']) == 1 for v in state['optimizer']['state'].values()))
            self.run_segment(self.model, root / 'child', end_step=2, identity=child_id)
            state = self.recovery(root / 'child')
            self.assertTrue(all(float(v['step']) == 2 for v in state['optimizer']['state'].values()))

    def test_uncommitted_updates_are_retained_but_not_double_counted(self):
        original = rt.accumulate_gradients
        count = 0

        def fail_second(*args, **kwargs):
            nonlocal count
            count += 1
            if count == 2:
                raise RuntimeError('injected interruption')
            return original(*args, **kwargs)

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            baseline = copy.deepcopy(self.model)
            with patch.object(rt, 'accumulate_gradients', fail_second):
                with self.assertRaisesRegex(RuntimeError, 'injected'):
                    self.run_segment(self.model, root / 'interrupted')
            self.assertEqual(self.recovery(root / 'interrupted')['step'], 0)
            failed_journal = next((root / 'interrupted/segments').glob('*.jsonl'))
            old_bytes = failed_journal.read_bytes()
            final = self.run_segment(self.model, root / 'interrupted')
            expected = self.run_segment(baseline, root / 'baseline')
            self.assertEqual(final['final_adapter'], expected['final_adapter'])
            self.assertEqual(failed_journal.read_bytes(), old_bytes)
            self.assertEqual(len(final['discarded_uncommitted_history']), 1)
            self.assertEqual(final['discarded_uncommitted_history'][0]['step'], 1)
            self.assertEqual(len(final['cumulative_history']), 4)
            self.assertEqual(sum(r['supervised_tokens'] for r in final['cumulative_history']), 20)
            receipts = [json.loads(p.read_text()) for p in (root / 'interrupted/segments').glob('*.receipt.json')]
            failed = next(r for r in receipts if r['status'] == 'failed')
            self.assertEqual(failed['uncommitted_finished_updates'], 1)
            self.assertGreater(failed['process_seconds'], 0)

    def test_identity_tampering_and_completed_reentry(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            first = self.run_segment(self.model, root)
            checkpoint = root / 'checkpoint_4/adapter_model.safetensors'
            original = checkpoint.read_bytes()
            second = self.run_segment(copy.deepcopy(self.model), root)
            self.assertEqual(second['segment_updates'], 0)
            self.assertEqual(first['final_adapter'], second['final_adapter'])
            self.assertEqual(checkpoint.read_bytes(), original)
            with self.assertRaisesRegex(ValueError, 'identity changed'):
                self.run_segment(self.model, root, identity={'run_id': 'other'})
            checkpoint.write_bytes(original + b'tamper')
            with self.assertRaisesRegex(ValueError, 'bytes changed'):
                self.run_segment(self.model, root)

    def test_exact_same_gradient_and_optimizer_recipe_as_original_train(self):
        old_model = copy.deepcopy(self.model)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); (root / 'old').mkdir()
            old_history, _ = original_train(old_model, self.rows, self.schedule, self.lrs,
                self.tokenizer, root / 'old', identity=self.identity,
                checkpoint_steps={4}, device='cpu')
            result = self.run_segment(self.model, root / 'new')
            self.assertEqual(result['final_adapter'], parameter_digest(old_model, True))
            old_pointer = json.loads((root / 'old/recovery/latest.json').read_text())
            old_state = torch.load(root / 'old/recovery' / old_pointer['file'], weights_only=True)
            self.assert_tree_equal(self.recovery(root / 'new')['optimizer'], old_state['optimizer'])
            for old, new in zip(old_history, result['cumulative_history']):
                for key in ('step', 'row_indices', 'learning_rate', 'response_nll',
                            'gradient_norm', 'supervised_tokens', 'processed_tokens'):
                    self.assertEqual(old[key], new[key])

    def test_sixteen_update_safety_commit_and_parent_checkpoint_policy(self):
        self.schedule = [[0, 1]] * 32; self.lrs = learning_rates(32)
        original = rt.accumulate_gradients; calls = 0

        def fail_eighteenth(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 18:
                raise RuntimeError('after committed16 and uncommitted17')
            return original(*args, **kwargs)

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with patch.object(rt, 'accumulate_gradients', fail_eighteenth):
                with self.assertRaisesRegex(RuntimeError, 'committed16'):
                    self.run_segment(self.model, root, end_step=32)
            self.assertEqual(self.recovery(root)['step'], 16)
            final = self.run_segment(self.model, root, end_step=32)
            self.assertEqual(final['step'], 32)
            self.assertEqual(set(final['checkpoints']), {'0', '32'})
            self.assertEqual([r['step'] for r in final['cumulative_history']], list(range(1, 33)))
            self.assertEqual([r['step'] for r in final['discarded_uncommitted_history']], [17])
            self.assertEqual(len(list((root / 'recovery').glob('*.pt'))), 1)


if __name__ == '__main__':
    unittest.main()

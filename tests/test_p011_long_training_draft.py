"""New synthetic long-recipe checks, never a scientific model or old corpus."""
import copy
import tempfile
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from experiments.p011 import long_training as lt
from experiments.p011.data_contract import whole_schedule
from experiments.sft_allocation_midpoint import checkpoint


class LongTrainingDraft(unittest.TestCase):
    @staticmethod
    def inputs():
        rows = []
        for i in range(8):
            ids = [10, 11] + [20 + i] * 9999 + [151645, 198]
            rows.append(dict(path_id=str(i), input_ids=ids,
                labels=[-100, -100] + ids[2:-1] + [-100], n_processed=len(ids),
                assistant_start=2, assistant_end=len(ids)-1, n_supervised=10000,
                eos_token_id=151645, template_final_newline_supervised=False))
        return rows, whole_schedule(rows, 190000)

    def test_fixed_arms_and_learning_rate_endpoints(self):
        self.assertEqual(set(lt.ARMS), {'S-L15', 'S-F15', 'S-L3'})
        for arm, recipe in lt.ARMS.items():
            rates = lt.learning_rates(100, arm)
            self.assertEqual(rates[4], recipe['peak_lr'])
            self.assertAlmostEqual(rates[0], recipe['peak_lr'] / 5)
            self.assertAlmostEqual(rates[-1], recipe['peak_lr'] * .1)
        self.assertEqual(lt.ARMS['S-F15']['mode'], 'full')
        self.assertEqual(len(lt.TARGETS), 7)

    def test_whole_answer_dose_and_actual_pass_order(self):
        rows, plan = self.inputs()
        result = lt.validate_plan(rows, plan, lt.learning_rates(3, 'S-L15'), 'S-L15')
        self.assertEqual((result['B'], result['U'], result['q']), (190000, 3, 2))
        self.assertEqual(sum(plan['exposures']), 19)

    def test_reordered_first_epoch_fails_before_training(self):
        rows, plan = self.inputs()
        plan['updates'][0][0], plan['updates'][0][1] = plan['updates'][0][1], plan['updates'][0][0]
        with self.assertRaisesRegex(ValueError, 'Whole-pass'):
            lt.validate_plan(rows, plan, lt.learning_rates(3, 'S-L15'), 'S-L15')

    def test_truncation_or_supervised_template_suffix_rejected(self):
        original, plan = self.inputs()
        for mutate in (lambda x: x['labels'].__setitem__(-1, 198),
                       lambda x: x['input_ids'].__setitem__(-2, 151643),
                       lambda x: x.update(n_supervised=9999)):
            rows = copy.deepcopy(original)
            mutate(rows[0])
            with self.assertRaises(ValueError):
                lt.validate_plan(rows, plan, lt.learning_rates(3, 'S-L15'), 'S-L15')

    def test_token_normalized_gradient_includes_eos_without_padding(self):
        import torch
        class Toy(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.logits = torch.nn.Parameter(torch.arange(7, dtype=torch.float32) / 10)
                self.lengths = []
            def forward(self, input_ids, attention_mask, use_cache):
                self.lengths.append(input_ids.shape[1])
                assert attention_mask.eq(1).all() and not use_cache
                return SimpleNamespace(logits=self.logits.expand(1, input_ids.shape[1], 7))
        m = Toy()
        rows = [dict(input_ids=[0, 1, 2, 6], labels=[-100, -100, 2, 6], n_supervised=2),
                dict(input_ids=[0, 1, 3, 4, 6], labels=[-100, -100, 3, 4, 6], n_supervised=3)]
        calls = []
        loss = lt.accumulate(m, rows, lambda: calls.append(True))
        logits = m.logits.detach().clone().requires_grad_()
        expected = torch.nn.functional.cross_entropy(logits.expand(5, 7), torch.tensor([2,6,3,4,6]))
        expected.backward()
        self.assertAlmostEqual(loss, expected.item(), places=6)
        self.assertTrue(torch.allclose(m.logits.grad, logits.grad, atol=1e-7))
        self.assertEqual(m.lengths, [4, 5])
        self.assertEqual(len(calls), 2)

    def test_terminal_state_before_export_for_full_and_adapter_modes(self):
        import torch
        class Tiny(torch.nn.Module):
            def __init__(self, mode):
                super().__init__()
                self.w = torch.nn.Parameter(torch.tensor([.2, .3]))
                self.mode, self.merged = mode, False
            def merge_and_unload(self, safe_merge):
                assert self.mode == 'lora' and safe_merge
                self.merged = True
                return self
            def save_pretrained(self, dest, safe_serialization):
                assert self.w.dtype == torch.bfloat16
                (dest / 'synthetic_weights.bin').write_bytes(b'not-a-real-model')
        class Tokenizer:
            def save_pretrained(self, dest):
                (dest / 'tokenizer.json').write_text('{}')
        class Journal:
            def __init__(self): self.events = []
            def begin(self, name, payload): self.events.append(('begin', name))
            def end(self, name, payload): self.events.append(('end', name))
            def commit(self): pass
            def check(self): pass
        rows, plan = self.inputs()
        for arm in ('S-L15', 'S-F15'):
            m = Tiny(lt.ARMS[arm]['mode'])
            opt = torch.optim.AdamW(m.parameters(), lr=.1)
            j = Journal()
            def synthetic_gradient(model, rows, check):
                check()
                model.w.sum().backward()
                return .5
            with tempfile.TemporaryDirectory() as tmp, \
                    patch.object(lt, 'accumulate', synthetic_gradient), \
                    patch.object(torch.cuda, 'synchronize'), \
                    patch.object(torch.cuda, 'max_memory_allocated', return_value=0):
                identity = {'arm': arm, 'input_plan_sha256': lt.digest(plan)}
                out = lt.train_terminal(m, Tokenizer(), opt, rows, plan, lt.learning_rates(3, arm), arm, tmp, j, identity)
                state = torch.load(Path(tmp)/'checkpoint_0003/state.pt', weights_only=True)
                self.assertEqual(state['schema'], 'p011_complete_training_state_v1')
                self.assertEqual(state['adaptation_mode'], lt.ARMS[arm]['mode'])
                self.assertEqual(state['adapter']['w'].dtype, torch.float32)
                self.assertEqual(state['optimizer']['state'][0]['step'].item(), 3)
                self.assertEqual(out['actual_supervised_tokens'], 190000)
                self.assertLess(j.events.index(('end','terminal_state')), j.events.index(('begin','terminal_model_export')))
                self.assertEqual(m.merged, arm == 'S-L15')
                with self.assertRaises(FileExistsError):
                    checkpoint.save(tmp, state)


if __name__ == '__main__':
    unittest.main()

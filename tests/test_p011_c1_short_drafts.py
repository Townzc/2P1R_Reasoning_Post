"""New leaf-function fixtures only; no real corpus processing/model call."""
import math
from types import SimpleNamespace
import unittest

from experiments.p011 import c1_nll as nll
from experiments.p011 import short_generation as short
from experiments.p010.teacher_contract import seed_for
from experiments.sft_allocation_midpoint.common import digest


def saved(pid, attempt, good=True, text=None):
    return {'candidate_id': f'{pid}::attempt{attempt:02d}', 'problem_id': pid,
            'attempt': attempt, 'answer_text': text or f'answer {attempt}',
            'gold_supported': True, 'stop': {'stop_reason': 'native_eos'},
            'score': {'score': {'box_extracted': True, 'parsed': True, 'correct': good}},
            'usable': good}


class C1Draft(unittest.TestCase):
    @staticmethod
    def groups():
        groups = {}
        for teacher in ('t15', 't7', 't72'):
            rows, encoded = [], []
            for i in range(3200):
                pid = f'p{i}'
                rows.append({'problem_id': pid, 'path_id': pid + '::attempt01', 'attempt': 1,
                             'teacher': teacher, 'unverified_fallback': teacher != 't15' and i == 0})
                encoded.append({'problem_id': pid, 'path_id': pid + '::attempt01',
                                'input_ids': [1, 2, i + 3, 151643],
                                'labels': [-100, -100, i + 3, 151643],
                                'n_processed': 4, 'n_prompt': 2, 'n_supervised': 2})
            for n in (400, 3200):
                a, b = rows[:n], encoded[:n]
                config = {'n': n, 'seed': 17, 'updates': 1024, 'targets': 2097148,
                          'model': nll.MODEL, 'encoded_rows_sha256': digest(b),
                          'training_rows_sha256': digest(a)}
                groups[f'{teacher}_n{n}'] = {'rows': a, 'encoded': b, 'config': config}
        return groups

    def test_six_groups_exact_identity_deduplicate_tokens_not_fallback(self):
        unique, membership = nll.inventory(self.groups())
        self.assertEqual(len(unique), 3200)
        self.assertEqual(sum(map(len, membership.values())), 10800)
        self.assertFalse(membership['t15_n400'][0]['unverified_fallback'])
        self.assertTrue(membership['t7_n400'][0]['unverified_fallback'])
        self.assertEqual(membership['t15_n400'][0]['sequence_sha256'],
                         membership['t7_n400'][0]['sequence_sha256'])

    def test_changed_original_config_is_rejected_before_forward(self):
        groups = self.groups()
        groups['t7_n400']['config']['seed'] = 29
        with self.assertRaises(ValueError):
            nll.inventory(groups)

    def test_original_mask_and_terminal_eos(self):
        row = {'input_ids': [42, 43, 5, 151643], 'labels': [-100, -100, 5, 151643],
               'n_processed': 4, 'n_prompt': 2, 'n_supervised': 2}
        self.assertEqual(nll.checked_sequence(row)['target_positions'], [2, 3])
        for changed in ({'labels': [-100, 43, 5, 151643]}, {'n_prompt': 0},
                        {'input_ids': [42, 43, 5, 151645]}, {'n_supervised': 1}):
            with self.assertRaises(ValueError):
                nll.checked_sequence({**row, **changed})

    def test_forward_shift_mask_eos_and_no_gradient(self):
        import torch
        class Toy(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.weight = torch.nn.Parameter(torch.zeros(1))
                self.calls = 0
            def forward(self, input_ids, attention_mask, use_cache, return_dict):
                self.calls += 1
                assert not torch.is_grad_enabled() and not use_cache and return_dict
                assert attention_mask.tolist() == [[1, 1, 1, 1]]
                logits = torch.zeros(1, 4, 7)
                logits[0, 1, 5] = 2.
                logits[0, 2, 6] = 3.
                return SimpleNamespace(logits=logits)
        model = Toy().eval()
        task = {'input_ids': [1, 2, 5, 6], 'labels': [-100, -100, 5, 6],
                'target_positions': [2, 3], 'supervised_tokens': 2}
        task['sequence_sha256'] = digest({k: task[k] for k in ('input_ids', 'labels')})
        scored = nll.forward_one(model, task)
        for observed, logit in zip(scored['token_nll'], (2., 3.)):
            self.assertAlmostEqual(observed, math.log(math.exp(logit) + 6) - logit, places=6)
        self.assertEqual(model.calls, 1)
        self.assertIsNone(model.weight.grad)
        model.train()
        with self.assertRaises(ValueError):
            nll.forward_one(model, task)
        self.assertEqual(model.calls, 1)

    def test_token_weighted_mean_and_fallback_separate(self):
        confirmed = {k: {'sequence_sha256': k, 'token_nll': xs, 'nll_sum': sum(xs),
                         'mean_nll': sum(xs) / len(xs), 'supervised_tokens': len(xs)}
                     for k, xs in [('a', [1., 1.]), ('b', [3.]) ]}
        groups = {'example': [{'sequence_sha256': 'a', 'unverified_fallback': False},
                              {'sequence_sha256': 'b', 'unverified_fallback': True}]}
        out = nll.descriptive_summary(groups, confirmed)['groups']['example']
        self.assertAlmostEqual(out['all']['token_weighted_nll'], 5 / 3)
        self.assertAlmostEqual(out['all']['perplexity'], math.exp(5 / 3))
        self.assertEqual(out['all']['answer_mean_nll_quantiles']['0.5'], 2.)
        self.assertEqual(out['fallback']['answers'], 1)
        self.assertEqual(out['nonfallback']['token_weighted_nll'], 1.)

    def test_missing_or_nonfinite_values_never_become_zero(self):
        groups = {'g': [{'sequence_sha256': 'a', 'unverified_fallback': False}]}
        with self.assertRaises(ValueError):
            nll.descriptive_summary(groups, {})
        bad = {'a': {'sequence_sha256': 'a', 'token_nll': [float('nan')],
                     'nll_sum': float('nan'), 'mean_nll': float('nan'), 'supervised_tokens': 1}}
        with self.assertRaises(ValueError):
            nll.descriptive_summary(groups, bad)

    def test_quantiles_linear_and_empty_fallback_null(self):
        self.assertEqual(nll.linear_quantile([1., 3., 7., 9.], .25), 2.5)
        x = {'a': {'sequence_sha256': 'a', 'token_nll': [2.], 'nll_sum': 2.,
                   'mean_nll': 2., 'supervised_tokens': 1}}
        out = nll.descriptive_summary({'g': [{'sequence_sha256': 'a', 'unverified_fallback': False}]}, x)
        self.assertIsNone(out['groups']['g']['fallback']['perplexity'])


class ShortDraft(unittest.TestCase):
    def test_original_seed_stop_params_and_only_temperature_changes(self):
        row = short.request('p', 3, [1, 2, 3], 1.)
        self.assertEqual(row['request']['seed'], seed_for('p::attempt03'))
        self.assertEqual(row['sampling']['temperature'], 1.)
        self.assertEqual(row['sampling']['stop_token_ids'], [151645, 151643])
        self.assertEqual(row['sampling']['max_tokens'], 1024)
        queue = short.b_requests([f'p{i}' for i in range(400)], {f'p{i}': [1] for i in range(400)})
        self.assertEqual(len(queue), 6400)
        self.assertEqual(queue[16]['request']['candidate_id'], 'p1::attempt01')

    def test_new_temperature_K1_is_not_old_S1_answer(self):
        ids = [f'p{i}' for i in range(400)]
        records = {f'{p}::attempt{a:02d}': saved(p, a, a != 1) for p in ids for a in range(1, 17)}
        out = short.b_selection(ids, records)
        self.assertEqual(out['selected_ids']['1'][0], 'p0::attempt02')
        self.assertEqual(out['nesting_conflicts'], [])
        self.assertTrue(set(out['selected_ids']['4']).issubset(out['selected_ids']['8']))

    def test_conflicting_fallback_is_retained_and_reported(self):
        ids = [f'p{i}' for i in range(400)]
        records = {f'{p}::attempt{a:02d}': saved(p, a, not (p == 'p0' and a <= 4))
                   for p in ids for a in range(1, 17)}
        out = short.b_selection(ids, records)
        self.assertEqual(out['selected_ids']['1'][0], 'p0::attempt01')
        self.assertEqual(out['nesting_conflicts'], ['p0'])
        self.assertTrue(out['requires_owner_disposition'])
        self.assertFalse(out['training_admitted'])

    def test_missing_prefix_does_not_skip_to_later_correct_attempt(self):
        obj = {'p::attempt02': saved('p', 2)}
        self.assertEqual(short.confirmed_first_four('p', obj), {'state': 'missing', 'next_attempt': 1})
        out = short.c2_prefix(['p'], obj, {}, set())
        self.assertEqual(out['blocked_missing_old_T72'], 'p')
        self.assertFalse(out['new_T72_generation_allowed'])

    def test_c2_preserves_order_reuse_overlap_and_stops_exact400(self):
        ids = [f'p{i}' for i in range(405)]
        records = {f'{p}::attempt01': saved(p, 1) for p in ids}
        out = short.c2_prefix(ids, records, records, {'p0', 'p1'})
        self.assertTrue(out['complete'])
        self.assertEqual([r['problem_id'] for r in out['selected']], ids[:400])
        self.assertEqual(out['S1_overlap'], 2)
        self.assertEqual(len(out['examined']), 400)

    def test_c2_does_not_generate_for_known_T72_failure(self):
        old = {f'bad::attempt{a:02d}': saved('bad', a, False) for a in range(1, 5)}
        old['next::attempt01'] = saved('next', 1)
        out = short.c2_prefix(['bad', 'next'], old, {}, set())
        self.assertEqual(out['next_T15_request'], {'problem_id': 'next', 'attempt': 1})
        self.assertEqual(out['examined'], ['bad'])


if __name__ == '__main__':
    unittest.main()

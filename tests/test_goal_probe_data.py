import copy
from collections import Counter
import itertools
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from experiments.post_e036_goal_probe import data
from src.countdown_smoke import safe_parse, value, verify_expression


class BoundaryTokenizer:
    """Reversible fixture with retokenization and a two-token operator suffix."""
    def encode(self, text, add_special_tokens=False):
        if text.endswith(' /'):
            return list(map(ord, text[:-2])) + [1000, 2000]
        for i, op in enumerate('+-*'):
            if text.endswith(' ' + op):
                return list(map(ord, text[:-2])) + [1100 + i]
        return list(map(ord, text))

    def decode(self, ids, **kwargs):
        mapping = {1000: ' ', 2000: '/', 1100: ' +', 1101: ' -', 1102: ' *'}
        return ''.join(mapping[x] if x in mapping else chr(x) for x in ids)


class GoalProbeDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.excluded, cls.leakage = data.protected_identities()
        cls.groups, cls.audit = data.make_groups(cls.excluded)

    def test_finite_deterministic_balanced_unique_switch_domain(self):
        other, audit = data.make_groups(self.excluded)
        self.assertEqual(self.groups, other)
        self.assertEqual(self.audit, audit)
        self.assertEqual(len(self.groups), 24)
        self.assertEqual(self.audit['correct_operator_counts'], {op:12 for op in data.OPS})
        self.assertGreaterEqual(self.audit['skeleton_families'], 8)
        self.assertEqual(sum(not g['hole_path'] for g in self.groups), 12)
        for group in self.groups:
            self.assertTrue(all(1 <= n <= 40 for n in group['numbers']))
            self.assertEqual(len(set(group['numbers'])), 4)
            self.assertNotIn(tuple(sorted(group['numbers'])), self.excluded)
            self.assertEqual(len({t['target'] for t in group['targets']}), 2)
            self.assertEqual(len({t['expected_operator'] for t in group['targets']}), 2)
            for target in group['targets']:
                self.assertTrue(10 <= target['target'] <= 100)
                self.assertTrue(verify_expression(target['expression'], group['numbers'], target['target']))
                hits = []
                for op in data.OPS:
                    try:
                        if value(safe_parse(group['template'].replace('?', op))) == target['target']:
                            hits.append(op)
                    except ZeroDivisionError:
                        pass
                self.assertEqual(hits, [target['expected_operator']])
        bad = copy.deepcopy(self.groups)
        bad[0]['targets'][0]['expected_operator'] = '!'
        with self.assertRaises(ValueError):
            data.validate_groups(bad)
        with self.assertRaises(RuntimeError):
            data.make_groups(attempts_per_slot=0)

    def test_interfaces_isolate_target_pairs_and_keep_original_free_compute_styles(self):
        f, h, c = [data.interface_rows(self.groups, interface) for interface in 'FHC']
        self.assertEqual(len({r['problem_id'] for r in f+h+c}), 144)
        for free, hole, compute in zip(f, h, c):
            common = (f'Use the numbers {", ".join(map(str, free["numbers"]))} exactly once each with +, -, *, / '
                      f'and parentheses to make {free["target"]}.')
            self.assertEqual(free['prompt'], common + ' Show calculations, then write Answer: followed by one expression.')
            self.assertTrue(hole['prompt'].startswith(common + ' Template: '))
            self.assertEqual(compute['prompt'], f'Evaluate {compute["expression"]}. Show calculations, then write Answer: followed by the exact value.')
            self.assertNotIn(' to make ', compute['prompt'])
            self.assertNotIn('Template:', free['prompt'])
            self.assertNotIn('other target', hole['prompt'])
        for a,b in zip(h[::2], h[1::2]):
            self.assertEqual(a['template'], b['template'])
            self.assertEqual(a['numbers'], b['numbers'])
            # All prompt variation is confined to the declared target field.
            a_stem, a_tail = a['prompt'].split(f' to make {a["target"]}.', 1)
            b_stem, b_tail = b['prompt'].split(f' to make {b["target"]}.', 1)
            self.assertEqual((a_stem,a_tail), (b_stem,b_tail))

    def test_full_candidate_lcp_handles_merge_and_multitoken_without_lookahead(self):
        rows = data.interface_rows(self.groups, 'H')
        tokenizer = BoundaryTokenizer()
        for row in rows:
            context = data.operator_context(row, tokenizer)
            self.assertTrue(context['available'])
            self.assertTrue(context['boundary_retokenized'])
            self.assertEqual(len(context['candidates']['/']), 2)
            self.assertNotIn('?', context['answer_prefix'])
            self.assertEqual(context['answer_prefix'], 'Answer: ' + row['template'].split('?')[0])
            for op in data.OPS:
                combined = context['context_ids'] + context['candidates'][op]
                self.assertEqual(combined, tokenizer.encode(context['full_context_text'] + op))
                self.assertEqual(tokenizer.decode(combined), context['full_context_text'] + op)
            switched = data.operator_context(dict(row, expected_operator='UNUSED'), tokenizer)
            self.assertEqual(context['context_ids'], switched['context_ids'])
            self.assertEqual(context['candidates'], switched['candidates'])
        a,b = [data.operator_context(r, tokenizer) for r in rows[:2]]
        self.assertEqual(a['answer_prefix'], b['answer_prefix'])
        class CollisionTokenizer(BoundaryTokenizer):
            def encode(self, text, **kwargs):
                return [1, 2]
        self.assertFalse(data.operator_context(rows[0], CollisionTokenizer())['available'])
        class PrefixOverlapTokenizer(BoundaryTokenizer):
            def encode(self, text, **kwargs):
                return {'+':[1,2], '-':[1,2,3], '*':[1,4], '/':[1,5]}.get(text[-1], [1])
        overlap = data.operator_context(rows[0], PrefixOverlapTokenizer())
        self.assertFalse(overlap['available'])
        self.assertIn('overlap', overlap['reason'])

    def test_support_audit_distinguishes_target_and_program_support(self):
        rows = [dict(numbers=[12,5,3,2], target=target, expression=expr, rendering_id=i)
                for target,expr,i in [(19,'((12 - 5) * 3) - 2',0),
                                      (19,'((12 - 5) * 3) - 2',1),
                                      (49,'((12 + 5) * 3) - 2',0),
                                      (19,'3 * (12 - 5) - 2',0)]]
        audit = data.training_support(rows)
        self.assertEqual(audit['distinct_targets_per_multiset_histogram'], {'2':1})
        self.assertEqual(audit['different_ordered_programs_per_number_target_histogram'], {'1':1,'2':1})
        supported = [r for r in audit['distinct_targets_per_number_partial_skeleton'] if r['count']==2]
        self.assertEqual(len(supported), 1)
        self.assertEqual(supported[0]['skeleton'], '(((12 ? 5) * 3) - 2)')
        self.assertEqual(sum(r['rows'] for r in audit['joint_target_operator_skeleton_surface']),4)

    def test_identity_exclusion_reads_no_sealed_question_contents(self):
        opened = []
        original = Path.open
        def track(path, *args, **kwargs):
            opened.append(str(path))
            if any(term in str(path) for term in ('holdout.', 'holdout_', 'test_iid', 'dev_matched.jsonl', 'dev_broad.jsonl')):
                raise AssertionError('Protected question body opened')
            return original(path, *args, **kwargs)
        with patch.object(Path, 'open', track):
            excluded, audit = data.protected_identities()
        self.assertEqual(excluded, self.excluded)
        self.assertFalse(audit['reserved_question_contents_read'])
        self.assertEqual(audit['allocation']['holdout_reserved']['count'], 2048)
        self.assertGreater(len(opened), 0)
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileExistsError):
                data.prepare('not-read', directory)


if __name__ == '__main__':
    unittest.main()

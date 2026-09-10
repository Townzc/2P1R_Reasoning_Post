import unittest
import tempfile
import json
from pathlib import Path

from src.real_math_audit import (answer_status, assign_partitions, final_answer,
                                grid_statistics, group_records, last_boxed,
                                scalar, stratified_order, stratified_take)


class RealMathAuditTests(unittest.TestCase):
    def test_jsonl_unicode_line_separators_inside_strings(self):
        from src.sft_data import read_jsonl
        rows = [{'problem': 'a\u2028b\u2029c'}, {'problem': 'next'}]
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'rows.jsonl'
            p.write_text(''.join(json.dumps(r, ensure_ascii=False)+'\n' for r in rows))
            self.assertEqual(read_jsonl(p), rows)

    def test_nested_box(self):
        self.assertEqual(last_boxed(r'old \boxed{2}; final \boxed{\frac{3}{4}}.'), r'\frac{3}{4}')
        self.assertIsNone(last_boxed(r'\boxed{\frac{3}{4}'))
        self.assertEqual(final_answer('work\n#### 7', 'gsm8k'), '7')
        self.assertIsNone(final_answer('The answer is probably 7.', 'gsm8k'))

    def test_conservative_equivalence(self):
        self.assertEqual(answer_status('1,000', '1000'), 'agree')
        self.assertEqual(answer_status(r'\dfrac{1}{2}', '0.5'), 'agree')
        self.assertEqual(answer_status('2', '3'), 'disagree')
        self.assertEqual(answer_status(r'\sqrt{4}', '2'), 'unresolved')
        self.assertEqual(answer_status('1,2', '12'), 'unresolved')
        self.assertEqual(answer_status('', ''), 'unresolved')
        self.assertIsNone(scalar("__import__('os').system('false')"))
        self.assertIsNone(scalar('1/0'))
        self.assertEqual(answer_status(r'\left(1,2\right)', '(1,2)'), 'agree')

    def test_number_variants_linked_before_split(self):
        rows = [dict(id='a', problem='Amy bought 15 apples and sold 3 apples. How many apples remain?'),
                dict(id='b', problem='Amy bought 25 apples and sold 4 apples. How many apples remain?'),
                dict(id='c', problem='Factor the integer 391 into two prime numbers.')]
        groups, edges = group_records(rows)
        self.assertEqual(groups['a'], groups['b'])
        self.assertNotEqual(groups['a'], groups['c'])
        self.assertTrue(any(e['kind'] == 'number_masked_candidate' for e in edges))

    def test_official_test_takes_precedence(self):
        rows = [dict(id='test', dataset='gsm8k', original_split='test', problem='Q', stratum='g'),
                dict(id='train', dataset='gsm8k', original_split='train', problem='Q', stratum='g')]
        c = {'math_levels': [1, 2, 3], 'seed': 5,
             'development_parents': {'gsm8k': 0, 'math': 0},
             'audit_parents': {'gsm8k': 0, 'math': 0},
             'reserved_fresh_parents': {'gsm8k': 0, 'math': 0}}
        assign_partitions(rows, c, {'train': 'shared', 'test': 'shared'})
        self.assertEqual(rows[1]['partition'], 'excluded')
        self.assertEqual(rows[0]['partition'], 'official_test')

    def test_zero_solution_denominators_not_backfilled(self):
        ps = [{'id': 'a', 'rank': 1}, {'id': 'b', 'rank': 2}]
        accepted = {'a': [dict(n_supervised=10, n_processed=15)]}
        g = grid_statistics(ps, accepted, [2], [1, 4])
        self.assertEqual(g[1]['acquired_p'], 2)
        self.assertEqual(g[1]['zero_solution_p'], 1)
        self.assertEqual(g[1]['target_reached_p'], 0)
        self.assertEqual(g[1]['target_pair_shortfall'], 7)
        self.assertEqual(g[1]['one_pass_supervised_tokens'], 10)

    def test_balanced_nested_order_independent_of_outcomes(self):
        rows = [dict(id=str(i), stratum=str(i % 3)) for i in range(30)]
        one = stratified_order(rows, 42, 'test')
        two = stratified_order(list(reversed(rows)), 42, 'test')
        self.assertEqual(one, two)
        self.assertEqual(len({r['stratum'] for r in one[:3]}), 3)
        self.assertEqual(len({r['id'] for r in one}), 30)

    def test_small_stratum_not_exhausted_in_early_partition(self):
        rows = [dict(id=str(i), stratum='rare' if i < 19 else 'common') for i in range(2908)]
        dev = stratified_take(rows, 256, 42, 'dev')
        self.assertEqual(sum(r['stratum'] == 'rare' for r in dev), 2)
        left = [r for r in rows if r not in dev]
        draw = stratified_take(left, 512, 42, 'draw')
        fresh = stratified_take([r for r in left if r not in draw], 512, 42, 'fresh')
        self.assertGreater(sum(r['stratum'] == 'rare' for r in draw), 0)
        self.assertGreater(sum(r['stratum'] == 'rare' for r in fresh), 0)
        self.assertFalse({r['id'] for r in draw} & {r['id'] for r in fresh})


if __name__ == '__main__':
    unittest.main()

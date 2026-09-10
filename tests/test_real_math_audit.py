import unittest

from src.real_math_audit import (answer_status, assign_partitions, final_answer,
                                grid_statistics, group_records, last_boxed,
                                scalar, stratified_order)


class RealMathAuditTests(unittest.TestCase):
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


if __name__ == '__main__':
    unittest.main()

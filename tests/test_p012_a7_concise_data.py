import unittest
from pathlib import Path

from experiments.p012.a7_concise_data import (
    TEMPLATE_SHA256, attempt_seed, eligibility, fallback_limit_exceeded,
    literal_prompt, strip_terminal_tokens, target_words,
)
from experiments.p012.evaluation import sha256_file


class A7FrozenConstructionTests(unittest.TestCase):
    def test_literal_math_braces_and_inserted_placeholders_are_preserved(self):
        template = Path('experiments/p012/a7_concise_prompt.txt').read_text()
        problem = r'Solve x^{2}=4; literal {long_solution} and {N}.'
        solution = r'Therefore \boxed{2}; literal {raw_problem}.'
        rendered = literal_prompt(template, 30, problem, solution)
        self.assertIn(problem, rendered)
        self.assertIn(solution, rendered)
        self.assertIn(r'answer inside \boxed{}.', rendered)
        self.assertIn('use about 30 words', rendered)
        self.assertTrue(rendered.endswith(solution+'\n'))

    def test_template_hash_is_the_approved_codeblock(self):
        self.assertEqual(sha256_file(Path('experiments/p012/a7_concise_prompt.txt')), TEMPLATE_SHA256)

    def test_rounding_is_half_up_not_bankers(self):
        self.assertEqual(target_words('x '*25), 30)
        self.assertEqual(target_words('x '*24), 20)
        self.assertEqual(target_words('x '*35), 40)
        self.assertEqual(target_words('x '*3), 20)

    def test_all_2048_attempt_seeds_are_unique_and_one_based(self):
        seeds=[attempt_seed(i,a) for i in range(1,513) for a in range(1,5)]
        self.assertEqual(len(set(seeds)), 2048)
        self.assertEqual((seeds[0],seeds[-1]), (7005,9052))
        with self.assertRaises(ValueError): attempt_seed(0,1)
        with self.assertRaises(ValueError): attempt_seed(1,5)

    def test_correct_box_is_required_with_normal_termination(self):
        self.assertTrue(eligibility(r'Answer: \boxed{2}', '2', 'stop', [])['eligible'])
        self.assertFalse(eligibility('Answer: 2', '2', 'stop', [])['eligible'])
        self.assertFalse(eligibility(r'\boxed{2}', '2', 'length', [])['eligible'])
        self.assertFalse(eligibility(r'\boxed{3}', '2', 'stop', [])['eligible'])

    def test_last_box_and_special_tokens(self):
        self.assertFalse(eligibility(r'\boxed{2} then \boxed{3}', '2', 'stop', [])['eligible'])
        self.assertFalse(eligibility(r'<think>\boxed{2}', '2', 'stop', [])['eligible'])
        self.assertFalse(eligibility(r'<|image|>\boxed{2}', '2', 'stop', ['<|image|>'])['eligible'])
        self.assertTrue(eligibility(r'We use $x^2$ and \boxed{2}.', '2', 'stop', [])['eligible'])

    def test_no_per_row_conciseness_gate(self):
        self.assertTrue(eligibility('Explanation. '*1000+r'\boxed{2}', '2', 'stop', [])['eligible'])

    def test_only_trailing_terminators_are_stripped(self):
        self.assertEqual(strip_terminal_tokens([1,99,2,99,99],[99]), [1,99,2])

    def test_fallback_limit_is_strictly_greater_than_26(self):
        self.assertFalse(fallback_limit_exceeded(26))
        self.assertTrue(fallback_limit_exceeded(27))


if __name__ == '__main__':
    unittest.main()

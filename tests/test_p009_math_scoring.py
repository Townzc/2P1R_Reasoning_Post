import unittest
from experiments.learning_regime_p009.math_scoring import last_box,decide,score,VERSION


class MathScoringTests(unittest.TestCase):
    def test_last_explicit_box(self):
        self.assertEqual(last_box(r'old \boxed{2}; final \boxed{3}')['answer'],'3')

    def test_nested_and_escaped_braces(self):
        self.assertEqual(last_box(r'\boxed{\frac{1}{2}}')['answer'],r'\frac{1}{2}')
        self.assertEqual(last_box(r'\boxed{\{1,2\}}')['answer'],r'\{1,2\}')

    def test_final_malformed_never_backfills(self):
        self.assertIsNone(last_box(r'\boxed{2} later \boxed{3')['answer'])

    def test_symbolic_false_not_overridden(self):
        x=decide('2',last_box(r'\boxed{2}'),dict(status='compared',equivalent=False),stop_reason='native_eos')
        self.assertFalse(x['correct']);self.assertFalse(x['fallback_used'])

    def test_only_parse_failure_falls_back(self):
        x=decide(r'\left(x\right)',last_box(r'\boxed{(x)}'),dict(status='parse_failure',equivalent=None),stop_reason='native_eos')
        self.assertTrue(x['correct']);self.assertTrue(x['fallback_used'])

    def test_caps_wrong_even_with_correct_box(self):
        self.assertFalse(score('2',r'\boxed{2}',stop_reason='length_cap')['correct'])

    def test_missing_box_incorrect(self):
        self.assertFalse(score('2','answer is 2',stop_reason='native_eos')['correct'])

    def test_environment_failure_is_not_score(self):
        with self.assertRaises(ValueError):
            decide('2',last_box(r'\boxed{2}'),dict(status='dependency_mismatch'),stop_reason='native_eos')

    def test_unparsed_wrong_box_cannot_enter_wrong_teacher_condition(self):
        x=decide('2',last_box(r'\boxed{nonsense}'),dict(status='parse_failure',equivalent=None),stop_reason='native_eos')
        self.assertFalse(x['correct']);self.assertFalse(x['teacher_label_eligible'])
        self.assertFalse(x['parsed'])

    def test_real_symbolic_equivalence_in_separate_process(self):
        x=score(r'\frac{1}{2}',r'reasoning then \boxed{0.5}',stop_reason='native_eos')
        self.assertTrue(x['correct']);self.assertFalse(x['fallback_used'])

    def test_real_symbolic_non_equivalence_in_separate_process(self):
        x=score('2',r'\boxed{3}',stop_reason='native_eos')
        self.assertFalse(x['correct']);self.assertFalse(x['fallback_used'])


if __name__=='__main__':unittest.main()

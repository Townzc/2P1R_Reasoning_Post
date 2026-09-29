import unittest
from experiments.public_math_pilot_v1.analyze_runtime import outcome_bounds, paired_bounds, run_catalog


class AnalysisTests(unittest.TestCase):
    def test_unknown_keeps_official_denominator_and_question_grouping(self):
        result=outcome_bounds([[True]*8,[False]*8,[None]*8],8)
        self.assertEqual(result['expected_outputs'],24)
        self.assertEqual(result['correct'],8)
        self.assertEqual(result['wrong'],8)
        self.assertEqual(result['unresolved'],8)
        self.assertEqual(result['average_lower'],1/3)
        self.assertEqual(result['average_upper'],2/3)
        self.assertIsNone(result['point_estimate'])
        self.assertEqual(len(result['per_question_lower']),3)
        self.assertEqual(result['pass_at_draws_lower'],1/3)
        self.assertEqual(result['pass_at_draws_upper'],2/3)

    def test_pass_at8_differs_from_average_at8(self):
        result=outcome_bounds([[True]+[False]*7,[False]*8],8)
        self.assertEqual(result['average_lower'],1/16)
        self.assertEqual(result['pass_at_draws_lower'],.5)
        with self.assertRaises(ValueError):outcome_bounds([[True]*7],8)

    def test_paired_bootstrap_zero_and_unresolved_bounds(self):
        resolved=outcome_bounds([[True]*8,[False]*8],8)
        same=paired_bounds(resolved,resolved,.975)
        self.assertEqual(same['paired_bootstrap_interval'],[0.,0.])
        unresolved=outcome_bounds([[True]*8,[None]*8],8)
        bounded=paired_bounds(unresolved,unresolved,.975)
        self.assertEqual(bounded['question_count'],2)
        self.assertEqual(bounded['mean_difference_lower'],-.5)
        self.assertEqual(bounded['mean_difference_upper'],.5)
        self.assertEqual(bounded['paired_bootstrap_interval'],[-1.,1.])

    def test_score_catalog_matches_full_generation_budget(self):
        jobs=run_catalog();self.assertEqual(len(jobs),54)
        self.assertEqual(len({j['name'] for j in jobs}),54)
        sizes={'dev':512,'math500':500,'gsm8k':1319}
        self.assertEqual(sum(sizes[j['dataset']] for j in jobs),31203)


if __name__=='__main__':unittest.main()

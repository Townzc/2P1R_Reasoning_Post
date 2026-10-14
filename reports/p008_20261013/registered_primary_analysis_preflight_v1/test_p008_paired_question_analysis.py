import unittest
import numpy as np
from scripts.p008_paired_question_analysis import paired_percentile


class PairedQuestionAnalysisTest(unittest.TestCase):
    def test_identical_models_have_exact_zero_interval(self):
        point, ci = paired_percentile([[0,1,0,1],[0,1,0,1]], [[-1,1]], draws=301)
        np.testing.assert_array_equal(point,[0]);np.testing.assert_array_equal(ci,[[0],[0]])

    def test_constant_complete_difference_is_100pp(self):
        point, ci = paired_percentile([[0]*9,[1]*9],[[-1,1]],draws=201)
        np.testing.assert_array_equal(point,[100]);np.testing.assert_array_equal(ci,[[100],[100]])

    def test_shared_questions_cancel_equal_interactions(self):
        rows=[[0,1,1,0,1],[1,0,0,1,0],[0,1,1,0,1],[1,0,0,1,0]]
        point, ci = paired_percentile(rows,[[1,-1,-1,1]],draws=503)
        np.testing.assert_allclose(point,[0],atol=1e-12)
        np.testing.assert_allclose(ci,[[0],[0]],atol=1e-12)

    def test_weighted_draw_mean_and_reproducibility(self):
        rows=[[0,0,0,0],[1,1,1,1],[0,0,0,0],[0,0,0,0]]
        a=paired_percentile(rows,[[-.5,.5,-.5,.5]],draws=211)
        b=paired_percentile(rows,[[-.5,.5,-.5,.5]],draws=211)
        np.testing.assert_array_equal(a[0],[50]);np.testing.assert_array_equal(a[1],[[50],[50]])
        np.testing.assert_array_equal(a[0],b[0]);np.testing.assert_array_equal(a[1],b[1])

    def test_nonconstant_difference_matches_question_mean_and_has_uncertainty(self):
        point, ci=paired_percentile([[0,0,0,0],[1,0,0,0]],[[-1,1]],draws=1000)
        np.testing.assert_array_equal(point,[25]);self.assertLess(ci[0,0],25);self.assertGreater(ci[1,0],25)

    def test_rejects_invalid_or_unaligned_inputs(self):
        for rows,coef in [([[0,.5],[1,0]],[[-1,1]]),([],[[1]]),([[0,1]],[[1,2]]),([[0,1]],[[np.nan]])]:
            with self.assertRaises(ValueError):paired_percentile(rows,coef,draws=200)
        with self.assertRaises(ValueError):paired_percentile([[0,1]],[[1]],draws=1)


if __name__ == '__main__':
    unittest.main()

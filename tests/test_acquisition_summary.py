import unittest
from scripts.summarize_acquisition_students import contrasts, CELLS, SEEDS


class PairedPolicySummary(unittest.TestCase):
    def fixture(self):
        return {f'{cell}_s{seed}': {'q1': False, 'q2': True}
                for cell in CELLS for seed in SEEDS}

    def test_interaction_keeps_direction_and_paired_seed_average(self):
        p = self.fixture()
        for seed in SEEDS:
            p[f'depth_p0_s{seed}'] = {'q1': False, 'q2': False}
            p[f'depth_p4_s{seed}'] = {'q1': True, 'q2': True}
        r = contrasts(p)
        self.assertEqual(r['depth_minus_breadth_p0']['mean_difference_pp'], -50)
        self.assertEqual(r['depth_minus_breadth_p4']['mean_difference_pp'], 50)
        self.assertEqual(r['price_interaction']['mean_difference_pp'], 100)
        self.assertEqual(r['price_interaction']['conditional_question_interval_pp'], [100, 100])

    def test_unknown_never_becomes_false(self):
        p = self.fixture()
        p['breadth_p0_s17']['q1'] = None
        with self.assertRaises(ValueError):
            contrasts(p)

    def test_missing_condition_or_reordered_identity_is_not_silently_dropped(self):
        p = self.fixture()
        del p['depth_p4_s23']
        with self.assertRaises(ValueError):
            contrasts(p)
        p = self.fixture()
        p['depth_p4_s23'] = {'q2': True, 'q3': False}
        with self.assertRaises(ValueError):
            contrasts(p)


if __name__ == '__main__':
    unittest.main()

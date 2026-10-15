import unittest
from unittest.mock import patch

from experiments.learning_regime_p009 import stage1_analysis as a


class Stage1Analysis(unittest.TestCase):
    def setUp(self):
        self.nc = [f'gsm8k/test/{i:05d}' for i in range(1319)]
        self.s1 = [f'math/test/{i:05d}' for i in range(500)]

    @staticmethod
    def scores(ids, count):
        return {k:i < count for i,k in enumerate(ids)}

    def test_nc_integer_threshold_and_direction(self):
        low = self.scores(self.nc, 600)
        self.assertFalse(a.nc_result(self.nc,low,self.scores(self.nc,665))['stop_all_positive_regimes'])
        self.assertTrue(a.nc_result(self.nc,low,self.scores(self.nc,666))['stop_all_positive_regimes'])
        self.assertFalse(a.nc_result(self.nc,low,self.scores(self.nc,500))['stop_all_positive_regimes'])

    def test_unknown_missing_extra_and_numeric_verdicts_rejected(self):
        original = self.scores(self.s1,250)
        mutations = [dict(original, extra=False), {k:v for k,v in original.items() if k!=self.s1[0]},
                     dict(original, **{self.s1[0]:None}), dict(original, **{self.s1[0]:1})]
        for value in mutations:
            with self.assertRaises(ValueError):a.checked_outcomes('S1',self.s1,value)

    def test_s2_and_duplicate_frozen_ids_rejected(self):
        with self.assertRaises(ValueError):a.checked_outcomes('S2',self.s1,self.scores(self.s1,250))
        with self.assertRaises(ValueError):a.checked_outcomes('S1',self.s1[:-1]+[self.s1[0]],self.scores(self.s1,250))

    def first(self, delta, admitted=True):
        return a.first_pair_decision(self.nc,self.scores(self.nc,650),self.scores(self.nc,650),
            self.s1, dict(n400=self.scores(self.s1,250),n3200=self.scores(self.s1,250+delta)),
            s1_G0_accepted=admitted)

    def test_futility_strict_two_pp_and_g0_not_futility(self):
        self.assertTrue(self.first(9)['measured_futility'])
        self.assertFalse(self.first(10)['measured_futility'])
        no = a.first_pair_decision(self.nc,self.scores(self.nc,650),self.scores(self.nc,650),s1_G0_accepted=False)
        self.assertEqual(no['decision'],'stop_no_eligible_positive_regime')
        self.assertFalse(no['measured_futility'])
        with self.assertRaises(ValueError):self.first(30,False)

    def test_post_nc_outcomes_rejected(self):
        with self.assertRaises(ValueError):
            a.first_pair_decision(self.nc,self.scores(self.nc,600),self.scores(self.nc,700),
                self.s1,dict(n400=self.scores(self.s1,250),n3200=self.scores(self.s1,300)),s1_G0_accepted=True)

    def data(self, d17=25,d29=13,n1600=270):
        counts=(240,250,n1600,250+d17,250,250+d29)
        return {k:self.scores(self.s1,n) for k,n in zip(a.S1_KEYS,counts)}

    def complete(self, data):
        return a.complete_s1(self.nc,self.scores(self.nc,650),self.scores(self.nc,650),
            self.s1,data,s1_G0_accepted=True)

    @patch.object(a,'paired_bootstrap',return_value=dict(lower95_pp=1.,upper95_pp=9.))
    def test_g1_two_seeds_and_nstar_boundaries(self,_):
        passed=self.complete(self.data());self.assertTrue(passed['G1_passed']);self.assertEqual(passed['selected_n_star'],400)
        self.assertFalse(self.complete(self.data(d17=24))['G1_passed'])
        self.assertFalse(self.complete(self.data(d29=12))['G1_passed'])
        self.assertEqual(self.complete(self.data(n1600=269))['selected_n_star'],1600)

    @patch.object(a,'paired_bootstrap',return_value=dict(lower95_pp=0.,upper95_pp=9.))
    def test_lower_zero_is_not_positive(self,_):
        self.assertFalse(self.complete(self.data())['G1_passed'])

    def test_missing_auxiliary_endpoint_blocks_g1(self):
        data=self.data();del data['s1_17_n100']
        with self.assertRaises(ValueError):self.complete(data)

    def test_real_synthetic_bootstrap_degenerate_pair(self):
        # A mathematical limiting case tests the actual 10000 paired draws;
        # no real experiment scores, model, raw parser or symbolic scorer.
        low=self.scores(self.s1,0);high=self.scores(self.s1,500)
        result=a.paired_bootstrap(list(reversed(self.s1)),low,high)
        self.assertEqual((result['observed_delta_pp'],result['lower95_pp'],result['upper95_pp']),(100.,100.,100.))
        self.assertEqual(result['policy']['replicates'],10000)


if __name__=='__main__':unittest.main()

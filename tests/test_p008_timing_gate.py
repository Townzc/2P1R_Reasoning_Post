import copy
import unittest
from experiments.sft_allocation_p008.timing_gate import estimate


def fixture():
    s=dict(worker_seconds_through_terminal=4000,
        completed_update_mtimes=[1000+i*2 for i in range(256)],
        optimizer_seconds=[1.5]*256, processed_tokens=[2500]*256,
        first_eval_intent_mtime=1520,block_boundary_seconds=32,local_step_write_seconds=2)
    return {'a':s,'b':copy.deepcopy(s)}, {'t8':dict(processed_tokens=5120000,updates=2048,max_seconds=9560)}


class TimingGateTest(unittest.TestCase):
    def run_gate(self,s,c):return estimate(s,3500,c,expected_t1=['a','b'],expected_t8=['t8'])
    def test_valid_measurements_never_implicitly_admit(self):
        s,c=fixture();v=self.run_gate(s,c)
        self.assertTrue(v['engineering_criterion_passed'])
        self.assertFalse(v['N2_closed']);self.assertFalse(v['runtime_admission'])
        self.assertEqual(v['components']['a']['noncompute_seconds_per_update'],(510-255*1.5+2)/255)
    def test_slower_host_not_averaged_away(self):
        s,c=fixture();s['b']['block_boundary_seconds']=256*5
        v=self.run_gate(s,c);self.assertFalse(v['engineering_criterion_passed'])
        self.assertGreater(v['maxima']['m'],5)
    def test_first_update_compute_not_subtracted_from_255_gap_span(self):
        s,c=fixture();s['a']['optimizer_seconds'][0]=80
        v=self.run_gate(s,c)
        self.assertEqual(v['components']['a']['noncompute_seconds_per_update'],v['components']['b']['noncompute_seconds_per_update'])
        self.assertGreater(v['components']['a']['compute_seconds_per_processed_token'],v['components']['b']['compute_seconds_per_processed_token'])
    def test_missing_unfavorable_sample_cannot_pass(self):
        s,c=fixture();del s['b']
        with self.assertRaises(ValueError):self.run_gate(s,c)
    def test_outcomes_are_not_admissible_inputs(self):
        s,c=fixture();s['a']['correct']=1000
        with self.assertRaises(ValueError):self.run_gate(s,c)
    def test_changed_caps_or_steps_rejected(self):
        for field,value in [('max_seconds',16000),('updates',1024)]:
            s,c=fixture();c['t8'][field]=value
            with self.assertRaises(ValueError):self.run_gate(s,c)
    def test_nonfinite_or_inconsistent_time_rejected(self):
        s,c=fixture();s['a']['block_boundary_seconds']=float('nan')
        with self.assertRaises(ValueError):self.run_gate(s,c)
        s,c=fixture();s['a']['optimizer_seconds']=[4]*256
        with self.assertRaises(ValueError):self.run_gate(s,c)
    def test_shorter_rows_cannot_reduce_fixed_per_update_compute(self):
        s,c=fixture();c['t8']['processed_tokens']=2560000
        v=self.run_gate(s,c)['predictions']['t8']
        self.assertEqual(v['compute_seconds'],2048*1.5)
        self.assertGreater(v['compute_seconds'],v['compute_token_seconds'])
    def test_longer_rows_still_pay_token_compute(self):
        s,c=fixture();c['t8']['processed_tokens']=10240000
        v=self.run_gate(s,c)['predictions']['t8']
        self.assertEqual(v['compute_seconds'],v['compute_token_seconds'])
        self.assertGreater(v['compute_seconds'],v['compute_step_seconds'])
    def test_entire_candidate_roster_required(self):
        s,c=fixture();c['extra']=c['t8']
        with self.assertRaises(ValueError):self.run_gate(s,c)


if __name__=='__main__':unittest.main()

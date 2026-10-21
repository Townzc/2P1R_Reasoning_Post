import copy,importlib.util,json,unittest
from pathlib import Path
from experiments.p011.b_remaining import numeric,path

SPEC=Path('reports/p011_20261020/b_remaining_runtime_v1/SPEC.json')
class TestAdmission(unittest.TestCase):
    def setUp(self):self.spec=json.loads(SPEC.read_text());self.v=self.spec['prospective_students_and_score_window']
    def test_two_sequential_reserves(self):
        result=numeric.verify_scenario(self.v);self.assertEqual(result['B_after_mandatory_attempt_reservations_usd'],'18.38');self.assertFalse(result['student_calls_authorized'])
    def test_rate_growth_rejected(self):
        self.v['hourly_rate_usd']='5.0'
        with self.assertRaises(ValueError):numeric.verify_scenario(self.v)
    def test_future_student_window_cannot_be_shortened(self):
        self.v['students']['B3']['full_window_seconds']-=1
        with self.assertRaises(ValueError):numeric.verify_scenario(self.v)
    def test_14utc_cannot_override_full_future_windows(self):
        self.v['latest_continuation_dispatch_epoch']=1792591200
        with self.assertRaises(ValueError):numeric.verify_scenario(self.v)
    def test_old_prefix_cannot_change(self):
        job=next(iter(self.spec['jobs'].values()));job['prefix_files']=copy.deepcopy(job['prefix_files']);job['prefix_files'].pop(next(iter(job['prefix_files'])))
        with self.assertRaises(ValueError):path.validate(self.spec)
    def test_old_scoring_window_not_continuation(self):
        next(iter(self.spec['jobs'].values()))['limits']['score_seconds']=62000
        with self.assertRaises(ValueError):path.validate(self.spec)
    def test_exact_named_keys_exclude_old_attempts(self):
        s=importlib.util.spec_from_file_location('p011_b_remaining_io','scripts/p011_b_remaining_io.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
        job=next(iter(self.spec['jobs'].values()));keys=m.expected_records(job)
        self.assertEqual(len(keys),46);self.assertTrue(all('remaining_r2' in k for k in keys))
        self.assertFalse(any('/batch/004' in k for k in keys));self.assertIn('b/generation_remaining_r2/prefix_transport/004',keys)

if __name__=='__main__':unittest.main()

import ast,unittest,tempfile
from pathlib import Path
from unittest.mock import patch
from experiments.p011 import fallback_numeric,fallback_path
ROOT=Path(__file__).resolve().parents[1]
def fn(name,f):
 return next(n for n in ast.parse((ROOT/name).read_text()).body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==f)
class NewControl(unittest.TestCase):
 def test_original_training_body_identical(self):
  self.assertEqual(ast.dump(fn('experiments/p011/b_student_training.py','train_and_merge')),ast.dump(fn('experiments/p011/fallback_training.py','train_and_merge')))
 def test_original_endpoint_body_identical(self):
  self.assertEqual(ast.dump(fn('experiments/p011/b_student_execution.py','evaluate')),ast.dump(fn('experiments/p011/fallback_execution.py','evaluate')))
 def test_original_endpoint_oracle_only_namespace(self):
  a=ast.dump(fn('experiments/p011/b_student_evidence.py','verify_endpoint')).replace('b/student/','fallback/student/')
  self.assertEqual(a,ast.dump(fn('experiments/p011/fallback_evidence.py','verify_endpoint')))
 def test_forecast_logs_overruns(self):
  p=dict(kind='student',category='B',measurement_exceptions=0,projection_multiplier=1.2,uncalibrated_future_seconds=600,
   worker_start_epoch=10,worker_seconds=4400,full_result_seconds=37465,result_cutoff_epoch=20,
   training_cycle_seconds=[1000],batch_cycle_seconds=[1000],hourly_rate_usd='4.3952',startup_seconds=600,
   platform_seconds=4460,reserved_usd='6.18',prior_B_reserved_usd='100')
  self.assertTrue(fallback_numeric.forecast(p,64,10,[],[],100)['forecast_only'])
 def test_shared_cap_keeps_all_new_exposure(self):
  b={'observed_epoch':100,'new_epoch_actual_charged_usd':'0','source_evidence_files':{}};j={'logical_id':'new','limits':{'reserved_usd':'6.18'}}
  r=[dict(logical_id='old',app_id='ap-a',hard_compute_envelope_usd='145',active=False)]
  with self.assertRaises(ValueError):fallback_path.budget_check(ROOT,{},j,b,r,{'containers':[]},100)
 def test_eight_slots_counts_pending_and_unmatched(self):
  b={'observed_epoch':100,'new_epoch_actual_charged_usd':'0','source_evidence_files':{}};j={'logical_id':'new','limits':{'reserved_usd':'6.18'}}
  r=[dict(logical_id=str(i),app_id='ap-a',hard_compute_envelope_usd='1',active=True) for i in range(7)]
  with self.assertRaises(ValueError):fallback_path.budget_check(ROOT,{},j,b,r,{'containers':[{'app_id':'ap-other'}]},100)
if __name__=='__main__':unittest.main()

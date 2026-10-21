import unittest,ast,json,tempfile
from pathlib import Path
from scripts.p011_long_owner_closed_io import window,prior_stage,path
class ActualWindow(unittest.TestCase):
 def test_short_actual_window_does_not_fail_prediction(self):
  j={'limits':dict(worker_seconds=100,closeout_seconds=200,score_seconds=7200,full_result_window_seconds=400)}
  remaining,deadline=window('score',j,250,{'worker_start_epoch':1})
  self.assertEqual((remaining,deadline),(51,301))
 def test_expired_actual_window_rejected(self):
  j={'limits':dict(worker_seconds=100,closeout_seconds=200,score_seconds=7200,full_result_window_seconds=400)}
  with self.assertRaises(TimeoutError):window('score',j,302,{'worker_start_epoch':1})
 def test_collect_and_scientific_oracle_only_directory_change(self):
  r=Path(__file__).resolve().parents[1]
  def f(n,k):return next(x for x in ast.parse((r/n).read_text()).body if isinstance(x,ast.FunctionDef) and x.name==k)
  for k in ['original','collect','audit']:
   a=ast.dump(f('scripts/p011_long_owner_io.py',k)).replace('long_io_r1','long_owner_closeout_r1')
   self.assertEqual(a,ast.dump(f('scripts/p011_long_owner_closed_io.py',k)))
 def test_only_exact_unstarted_infrastructure_parent_allows_one_new_stage(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);job='long_baseline_S-L15_s17_owner_r1'
   self.assertIsNone(prior_stage(root,'collect',job))
   old=root/path.LOCAL/'long_io_r1/collect'/job;old.mkdir(parents=True)
   (old/'ATTEMPT.json').write_text('{}')
   (old/'FAILED.json').write_text(json.dumps({'message':'Every original call node must be successful with actual container identity'}))
   self.assertEqual(prior_stage(root,'collect',job)['infrastructure_retry_number'],1)
   (old/'evidence.tar').write_bytes(b'partial')
   with self.assertRaises(ValueError):prior_stage(root,'collect',job)
if __name__=='__main__':unittest.main()

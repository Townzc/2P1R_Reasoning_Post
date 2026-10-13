import unittest
from copy import deepcopy
from experiments.sft_allocation_p008.student_runtime import validate_plan
from experiments.sft_allocation_p008.contract import lrs

class StudentContractTest(unittest.TestCase):
 def setUp(self):
  self.rows=[dict(path_id=str(i)) for i in range(512)]
  self.encoded=[dict(n_supervised=1024 if i<511 else 1023,n_processed=1026 if i<511 else 1025,
    n_prompt=2,problem_id=str(i),path_id=str(i),response_hash=str(i)) for i in range(512)]
  self.schedule=[[2*i,2*i+1] for i in range(256)]
  self.plan=dict(lrs=lrs(256),updates=self.schedule,row_path_ids=[r['path_id'] for r in self.rows],
    row_exposures=[1]*512,zero_exposure_answers=0,supervised_targets=524287,targets_are_frozen_before_student_scores=True)
  self.config=dict(updates=256,training_multiple=1,targets=524287,seed=17)
 def test_valid_full_answer_plan(self):
  b=validate_plan(self.rows,self.encoded,self.plan,self.config)
  self.assertEqual(b['supervised_response_tokens'],524287);self.assertEqual(b['optimizer_updates'],256)
 def test_biased_exposure_rejected_even_exact_target(self):
  p=deepcopy(self.plan);p['updates'][0]=[0,0];p['row_exposures'][0]=2;p['row_exposures'][1]=0;p['zero_exposure_answers']=1
  with self.assertRaises(ValueError):validate_plan(self.rows,self.encoded,p,self.config)
 def test_old_rebound_lr_rejected(self):
  p=deepcopy(self.plan);p['lrs'][-1]=6e-5
  with self.assertRaises(ValueError):validate_plan(self.rows,self.encoded,p,self.config)
 def test_inconsistent_horizon_rejected(self):
  c=deepcopy(self.config);c['updates']=2048
  with self.assertRaises(ValueError):validate_plan(self.rows,self.encoded,self.plan,c)

if __name__=='__main__':unittest.main()

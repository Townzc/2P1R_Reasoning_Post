import ast,unittest,copy
from pathlib import Path
from unittest.mock import patch
from experiments.p011.c2_numeric import forecast
from experiments.p011 import c2_student_training as train,c2_student_execution as execution,c2_student_evidence as evidence
from experiments.learning_regime_p009.training_plan import UPDATES,TARGETS,LR_VECTOR_SHA256
from experiments.sft_allocation_midpoint.common import digest

class NewC2Student(unittest.TestCase):
 def policy(self):
  return dict(kind='generation',category='C',new_generation_batches=11,measurement_exceptions=0,projection_multiplier=1.2,uncalibrated_future_seconds=600,worker_start_epoch=1000,worker_seconds=1500,full_result_seconds=38000,result_cutoff_epoch=100000,training_cycle_seconds=[],batch_cycle_seconds=[20],hourly_rate_usd='4.3952',startup_seconds=600,platform_seconds=1560,reserved_usd='2.64',prior_C_reserved_usd='6.38')
 def test_remaining_c_after_both_c1_attempts(self):
  x=forecast(self.policy(),0,11,[],[],1000);self.assertEqual(x['prior_C_reserved_usd'],'6.38');self.assertEqual(x['batches_left'],11)
 def test_no_other_category(self):
  p=self.policy();p['category']='B'
  with self.assertRaises(ValueError):forecast(p,0,11,[],[],1000)
 def test_no_self_calibration_or_extra_batch(self):
  p=self.policy();p['measurement_exceptions']=1
  with self.assertRaises(ValueError):forecast(p,0,11,[],[],1000)
  p=self.policy()
  with self.assertRaises(ValueError):forecast(p,0,12,[],[],1000)
 def test_full_reserve_counts_failed_c1(self):
  p=self.policy();p['prior_C_reserved_usd']='10'
  with self.assertRaises(ValueError):forecast(p,0,11,[],[],1000)
 def config(self):
  ids=[f'p{i}' for i in range(400)];rows=[{'problem_id':p,'path_id':p+'::attempt02'} for p in ids];plan={'example':'fake'}
  c=dict(run_id='C2a',experiment='P011',category='C',teacher='t15',temperature=.8,seed=17,P=400,K=1,P_cov=400,n=400,common_ordered400=ids,selected_ids=[r['path_id'] for r in rows],model=train.MODELS['qwen'],first_common_usable_prefix=True,unverified_fallback_questions=[],selection_sha256='a'*64,S1_overlap=123,updates=UPDATES,targets=TARGETS,encoded_rows_sha256=digest(rows),plan_sha256=digest(plan),lr_vector_sha256=LR_VECTOR_SHA256)
  return c,rows,plan
 def test_two_exact_teachers_and_same_roster(self):
  c,r,p=self.config()
  with patch.object(train,'validate_plan',return_value={'checked':True}):
   self.assertEqual(train.checked_recipe(c,r,p)['cell']['S1_overlap'],123)
   c['run_id']='C2b';c['teacher']='t72';self.assertEqual(train.checked_recipe(c,r,p)['cell']['teacher'],'t72')
 def test_no_fallback_or_replacement(self):
  c,r,p=self.config();c['unverified_fallback_questions']=['p1']
  with patch.object(train,'validate_plan',return_value={}):
   with self.assertRaises(ValueError):train.checked_recipe(c,r,p)
  c,r,p=self.config();c['common_ordered400'][0]='replacement'
  with patch.object(train,'validate_plan',return_value={}):
   with self.assertRaises(ValueError):train.checked_recipe(c,r,p)
 def test_endpoint_exit_and_c2_record_names(self):
  p=type('P',(),{'is_alive':lambda s:False,'exitcode':0})();self.assertEqual(execution.require_exited(p,('complete',{},[1]*64)),({},[1]*64))
  self.assertTrue(all(k.startswith('c2/student/C2a/') for k in evidence.expected_record_keys('C2a')))

if __name__=='__main__':unittest.main()

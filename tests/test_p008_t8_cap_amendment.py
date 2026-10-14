"""In-memory review fixtures only; no acceptance files or cloud/model calls."""
import ast,copy,unittest
from pathlib import Path
from experiments.sft_allocation_midpoint.common import read,digest
from experiments.sft_allocation_midpoint.guard import RunGuard,GuardError
from experiments.sft_allocation_p008.student_t8_cap_binding import (
 validate_student_binding,validate_owner,register_amendment,reserve_supplement,
 verify_supplement,AMENDMENT_KEY,supplement_key,ORIGINAL,FAILED,expected_mapping)

P='reports/p008_20261013/student_t8_cap_9600_v1/ADMISSION.json'
def fixture():
 s=read(P);plan=s['original_spec']['plan'];c=s['configs'][s['runs'][0]]
 g=copy.deepcopy(s['original_g1_releases'][str(c['draw'])]['gates'])
 files={'memory-only-fixture.py':'e'*64}
 review=dict(verdict='PASS',review_commit='f'*40,review_report_sha256='c'*64,source_files=files,spec_sha256=digest(s))
 g.update(runtime_review=dict(review,scope='t8-cap-9600-runtime'),cap_owner=s['owner'],t8_timing_proposal=s['original_failed_timing_proposal'])
 p=g['t8_timing_proposal']
 g['t8_numeric_review']=dict(review,scope='t8-cap-9600-numeric',passed=True,N2_closed=True,
   original_N2_passed=False,post_hoc_engineering_deviation=True,accepted_runs=s['runs'],
   worker_caps={n:9600 for n in s['runs']},proposal_digest=digest(p),common_plan_gate_sha256=s['common_plan_gate_sha256'])
 g['t1_terminal_records']=[dict(campaign=x['campaign'],run_id=x['run_id'],terminal=p['provenance'][n]['terminal']) for n,x in expected_mapping(s['original_spec']).items()]
 g['t1_terminal_records'] += [dict(campaign=ORIGINAL,run_id=n,terminal=p['failed_attempts_retained'][n]['terminal']) for n in FAILED]
 return [plan,c,dict(source_files=files,spec_sha256=digest(s),gates=g),s]

def rebind(a):
 a[2]['spec_sha256']=digest(a[3])
 for k in ('runtime_review','t8_numeric_review'):a[2]['gates'][k]['spec_sha256']=digest(a[3])

class Store(dict):
 def put(self,k,v,*,skip_if_exists=False):
  if skip_if_exists and k in self:return False
  self[k]=copy.deepcopy(v);return True

def claim(a,db,attempt='one'):
 plan,c,rel,s=a;g=RunGuard(db,plan);t=plan['created_epoch']+1;g.register(now_epoch=t)
 ad=g.admit(dict(run_id=c['run_id'],config_sha256=digest(c),source_sha256=digest(rel['source_files']),data_sha256=c['input_sha256']),attempt_id=attempt,now_epoch=t,max_runtime_seconds=9630)
 return g,ad

class Amendment(unittest.TestCase):
 def test_all_eight_original_configs_pass_only_with_both_scoped_reviews(self):
  for n in read(P)['runs']:
   a=fixture();a[1]=a[3]['configs'][n]
   old=a[3]['original_g1_releases'][str(a[1]['draw'])]['gates']
   for k in ('required_terminals','pool_terminals','student_completion_owner','student_slot_transfer','upload'):a[2]['gates'][k]=old[k]
   self.assertTrue(validate_student_binding(*a))
 def test_new_code_only_or_old_numeric_cannot_admit(self):
  for k,v in [('scope','t8-numeric'),('N2_closed',False),('passed',False),('worker_caps',{}),('source_files',{})]:
   a=fixture();a[2]['gates']['t8_numeric_review'][k]=v
   with self.assertRaises(ValueError):validate_student_binding(*a)
 def test_exact_owner_cap_budget_required_even_after_rehash(self):
  for k,v in [('new_cap_seconds',9601),('additional_reservation_cents',0),('stage_cap_cents',26604),('automatic_retry',True)]:
   a=fixture();a[3]['owner'][k]=v;rebind(a)
   with self.assertRaises(ValueError):validate_student_binding(*a)
 def test_original_failure_and_all_host_inputs_cannot_be_rewritten(self):
  for k,v in [('engineering_criterion_passed',True),('failed_host_dropped',True),('new_model_calls',1)]:
   a=fixture();a[2]['gates']['t8_timing_proposal'][k]=v;rebind(a)
   with self.assertRaises(ValueError):validate_student_binding(*a)
 def test_missing_host_terminal_rejected(self):
  a=fixture();a[2]['gates']['t1_terminal_records'].pop()
  with self.assertRaises(ValueError):validate_student_binding(*a)
 def test_amended_disclosure_cannot_be_removed(self):
  for k in ('original_N2_passed','post_hoc_engineering_deviation'):
   a=fixture();a[2]['gates']['t8_numeric_review'][k]=not a[2]['gates']['t8_numeric_review'][k]
   with self.assertRaises(ValueError):validate_student_binding(*a)
 def test_scientific_config_and_registered_plan_never_modified(self):
  for what in ('config','plan'):
   a=fixture()
   if what=='config':a[1]['max_seconds']=9600
   else:a[0]['slots'][a[1]['run_id']]['reserved_cents']=1258
   rebind(a)
   with self.assertRaises(ValueError):validate_student_binding(*a)
 def test_effective_cap_reservation_and_protected_funds_enforced(self):
  for k,v in [('worker_cap_seconds',9601),('additional_total_cents',0),('new_slot_reservation_cents',1253),('soft_margin_seconds',0),('stage_cap_cents',27000)]:
   a=fixture();a[3][k]=v;rebind(a)
   with self.assertRaises(ValueError):validate_student_binding(*a)
  a=fixture();a[3]['project_budget']['workspace_metered_usd']='184';rebind(a)
  with self.assertRaises(ValueError):validate_student_binding(*a)
 def test_real_unique_claim_blocks_new_or_legacy_competitor(self):
  a=fixture();db=Store();_,ad=claim(a,db);register_amendment(db,a[3]);reserve_supplement(db,a[3],ad)
  self.assertEqual(verify_supplement(db,a[3],a[1]['run_id'])['supplement_reserved_cents'],5)
  for attempt in ('old-entry','new-entry'):
   with self.assertRaises(GuardError):claim(a,db,attempt)
 def test_partial_reservation_failure_burns_slot_and_never_retries(self):
  a=fixture();db=Store();_,ad=claim(a,db)
  with self.assertRaises(ValueError):reserve_supplement(db,a[3],ad)
  with self.assertRaises(GuardError):claim(a,db,'second')
 def test_supplement_is_create_only_and_binds_original_claim(self):
  a=fixture();db=Store();_,ad=claim(a,db);register_amendment(db,a[3]);register_amendment(db,a[3]);reserve_supplement(db,a[3],ad)
  with self.assertRaises(ValueError):reserve_supplement(db,a[3],ad)
  db[supplement_key(a[1]['run_id'])]['original_claim_sha256']='0'*64
  with self.assertRaises(ValueError):verify_supplement(db,a[3],a[1]['run_id'])
 def test_conflicting_global_amendment_is_not_overwritten(self):
  a=fixture();db=Store({AMENDMENT_KEY:{'wrong':True}})
  with self.assertRaises(ValueError):register_amendment(db,a[3])
  self.assertEqual(db[AMENDMENT_KEY],{'wrong':True})
 def test_original_runtime_bytes_and_scientific_call_unchanged(self):
  old=read('reports/p008_20261013/student_t8_runtime_preflight_v1/SOURCE_BUNDLE.json')
  from experiments.sft_allocation_midpoint.common import sha
  for n,h in old.items():self.assertEqual(sha(n),h,n)
  s=Path('experiments/sft_allocation_p008/modal_students_t8_cap.py').read_text();tree=ast.parse(s)
  fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='student_work')
  vals={k.arg:ast.literal_eval(k.value) for k in fn.decorator_list[0].keywords if k.arg in ('timeout','startup_timeout','retries','max_containers')}
  self.assertEqual(vals,dict(timeout=9660,startup_timeout=600,retries=0,max_containers=8))
  self.assertIn('start+9600',s);self.assertIn('with dispatch_lock(root):',s)
  self.assertLess(s.index('reserve_supplement(claims,spec,admitted)'),s.index('result=execute('))
  self.assertIn('from experiments.sft_allocation_p008.frozen_lr_block_student_runtime import run as execute',s)
  self.assertIn('result=execute(assets,inputs,out,journal,identity)',s)
  self.assertEqual(s.count('call=fn.spawn('),1)

if __name__=='__main__':unittest.main()

"""New D4/full3200 durable-score checks only, no GPU or real symbolic calls."""
import ast,copy,importlib.util,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from experiments.p010 import e3_contract as c,e3_scoring as s,e3_runtime as rt
from experiments.p010.common import read,dump,sha
from tests.test_p010_student_scoring import FakePool

def rows():
 out=[]
 for label in ('t06','t10'):
  for i in range(200):
   for attempt in range(1,9):
    pid=f'synthetic/{i:03d}';out.append(dict(id=f'p010_e3/{label}/{pid}::attempt{attempt:02d}',
     evaluation=label,problem_id=pid,attempt=attempt,gold='1',answer_segment='\\boxed{1}' if attempt<5 else '\\boxed{2}',
     stop_reason='length_cap' if attempt==8 else 'native_eos',original_gold_row_sha256='a'*64,original_decoded_record_sha256='b'*64))
 return out

class FullChecks(unittest.TestCase):
 def test_D4_reject_transfer_not_generic_approved(self):
  v=read('.local/p010_20261019/r1/OWNER_E3_D4_DECISION.json');c.validate_d4(v)
  v=copy.deepcopy(v);v['approved']=True
  with self.assertRaises(ValueError):c.validate_d4(v)
 def test_D1_coverage_required_not_old_full_reserve(self):
  with self.assertRaises(ValueError):c.forecast(0,0,[],[38.1],457.34,model_loaded=False,charged_G='44')
  good=c.forecast(0,0,[],[38.1],457.34,model_loaded=False,charged_G='24.03')
  self.assertEqual(good['new_reserved_usd'],'11.13');self.assertEqual(good['G_cap_usd'],'50')
 def test_nonfinite_or_negative_settlement_rejected(self):
  for x in ('NaN','-1','Infinity'):
   with self.assertRaises(ValueError):c.forecast(0,0,[],[38.1],457.34,model_loaded=False,charged_G=x)
 def test_all_3200_once_and_shared_pairs(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'new';value=s.score_once(p,rows(),{'synthetic':True},60,pool_factory=FakePool)
   check=s.verify_saved_scores(p,rows(),{'synthetic':True},60)
   self.assertTrue(check['passed']);self.assertEqual(value['outputs'],3200)
   self.assertEqual(value['temperatures']['t06']['correct'],800);self.assertEqual(value['unique_symbolic_pairs'],2)
   self.assertEqual(len(list((p/'chunks').iterdir())),32)
   with self.assertRaises(FileExistsError):s.score_once(p,rows(),{'synthetic':True},60,pool_factory=FakePool)
 def test_old_temperature_or_ninth_attempt_rejected(self):
  a=rows();a[0]['evaluation']='t08'
  with self.assertRaises(ValueError):s.checked_rows(a)
  a=rows();a[0]['attempt']=9
  with self.assertRaises(ValueError):s.checked_rows(a)
 def test_unknown_boolean_not_zero(self):
  a=rows();results=[dict(id=x['id'],score={'correct':False}) for x in a];results[123]['score']['correct']=None
  with self.assertRaises(ValueError):s.checked_summary(a,results)
 def test_second_temperature_failure_keeps_first_1600(self):
  class Broken(FakePool):
   def score_rows(self,part):
    if len(self.ids)>=1600:raise RuntimeError('synthetic second-temperature failure')
    return super().score_rows(part)
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'new'
   with self.assertRaises(RuntimeError):s.score_once(p,rows(),{'synthetic':True},60,pool_factory=Broken)
   self.assertEqual(read(p/'FAILED.json')['confirmed_chunk_rows'],1600)
   self.assertFalse((p/'COMPLETED.json').exists())
 def test_resealed_pair_mismatch_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'new';s.score_once(p,rows(),{'synthetic':True},60,pool_factory=FakePool)
   f=p/'chunks/00000/RESULT.json';v=read(f);v['rows'][0]['score']['correct']=False
   import json
   f.write_text(json.dumps(v));g=p/'chunks/00000/COMPLETED.json';v=read(g);v['result_sha256']=sha(f);g.write_text(json.dumps(v))
   with self.assertRaises(ValueError):s.verify_saved_scores(p,rows(),{'synthetic':True},60)
 def test_entry_fixed_caps_and_audit_fences_visible_in_actual_AST(self):
  p=Path('experiments/p010/modal_e3.py');tree=ast.parse(p.read_text());fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
  source=ast.get_source_segment(p.read_text(),fn)
  for text in ('validate_d4(owner)','D1_hourly_coverage_scope_accepted','all_old_T08_outputs_reused_without_rescoring',"slots != 0",'validate_settlement(spec,read(b[','store.put(KEY + \'/dispatch\''):
   self.assertIn(text,source)
  self.assertLess(source.index('validate_settlement('),source.index('worker.spawn('))
  self.assertLess(source.index('store.put(KEY'),source.index('worker.spawn('))

# Reuse only fixture constructors from old completed tests, never their test methods.
p=Path('.local/p010_20261019/r1/e3_execution_draft_r1/test_e3_worker_body.py')
spec=importlib.util.spec_from_file_location('new_D1_worker_fixture',p);fixtures=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixtures)
sys.modules['experiments.p010.e3_contract']=c;fixtures.c=c;fixtures.rt=rt
class D1Body(fixtures.ActualBody):
 def invoke(self):
  import types
  with patch.dict(sys.modules,self.modules),patch.object(rt,'verify',lambda *a:None),patch.object(rt.time,'time',return_value=1):
   return rt.generate(self.inputs,self.out,self.model,{'synthetic':True},0,1800,
    {'original_full_batch_seconds':[38.1],'observed_pre_first_batch_seconds':457.34},self.charge,
    self.store,types.SimpleNamespace(commit=lambda:None))
 def test_D1_charge_propagates_into_every_new_actual_worker_forecast(self):
  self.charge='24.03';v=self.invoke();self.assertEqual(v['new_outputs'],3200)
  fs=[read(p) for p in (self.out/'forecasts').rglob('*.json')]
  self.assertEqual(len(fs),14);self.assertTrue(all(x['D1_charged_G_usd']=='24.03' for x in fs))
 def test_unsettled_original_G_stops_actual_body_before_model(self):
  self.charge='44'
  with self.assertRaises(ValueError):self.invoke()
  self.assertEqual(self.calls,[])

if __name__=='__main__':
 suite=unittest.defaultTestLoader.loadTestsFromTestCase(FullChecks)
 for n in ['test_D1_charge_propagates_into_every_new_actual_worker_forecast','test_unsettled_original_G_stops_actual_body_before_model']:suite.addTest(D1Body(n))
 result=unittest.TextTestRunner(verbosity=2).run(suite);sys.exit(not result.wasSuccessful())

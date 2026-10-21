import unittest,copy,ast
from pathlib import Path
from scripts.p011_long_owner_call_io import call_quiescence
class CallQuiescence(unittest.TestCase):
 def setUp(self):
  self.sub={'app_id':'ap-own','call_id':'fc-own'};self.node={'function_call_id':'fc-own','function_name':'job','task_id':'ta-own','status':'SUCCESS','children':[]}
 def test_other_job_container_does_not_hide_owned_zero(self):
  p=call_quiescence(self.sub,'job',{'state':'running'},[{'container_id':'ta-other','app_id':'ap-own'}],[self.node],10)
  self.assertEqual(p['owned_containers'],0);self.assertEqual(p['other_app_containers'],1);self.assertTrue(p['whole_app_stopped_not_claimed'])
 def test_unknown_provider_shape_rejected(self):
  with self.assertRaises(ValueError):call_quiescence(self.sub,'job',{},[{'unknown':'ta-own'}],[self.node],10)
 def test_own_task_still_active_rejected(self):
  with self.assertRaises(ValueError):call_quiescence(self.sub,'job',{},[{'container_id':'ta-own','app_id':'ap-own'}],[self.node],10)
 def test_unknown_call_or_child_rejected(self):
  for key,value in [('function_call_id','fc-foreign'),('function_name','other'),('status','PENDING'),('task_id','')]:
   n=copy.deepcopy(self.node);n[key]=value
   with self.assertRaises(ValueError):call_quiescence(self.sub,'job',{},[],[n],10)
  n=copy.deepcopy(self.node);n['children']=[dict(self.node,status='TIMEOUT')]
  with self.assertRaises(ValueError):call_quiescence(self.sub,'job',{},[],[n],10)
 def test_scientific_oracle_and_scorer_bodies_unchanged(self):
  root=Path(__file__).resolve().parents[1]
  def f(file,name):return next(x for x in ast.parse((root/file).read_text()).body if isinstance(x,ast.FunctionDef) and x.name==name)
  # Only the provider-proof filename differs in the original scientific oracle.
  for name in ['audit','score']:
   a=ast.dump(f('scripts/p011_long_owner_io.py',name)).replace('PROVIDER_STOPPED0.json','PROVIDER_CALL_QUIESCENT.json')
   self.assertEqual(a,ast.dump(f('scripts/p011_long_owner_call_io.py',name)))
if __name__=='__main__':unittest.main()

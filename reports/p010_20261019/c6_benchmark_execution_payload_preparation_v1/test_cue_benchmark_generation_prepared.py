import importlib.util,unittest,tempfile,sys,time,types
from pathlib import Path
from unittest.mock import patch
from experiments.p010.common import read
p=Path('.local/p010_20261019/r1/cue_benchmark_generation_prepared.py')
s=importlib.util.spec_from_file_location('generation',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Store(dict):
 def put(self,key,value,skip_if_exists):
  if key in self:return False
  self[key]=value;return True
class Volume:
 def commit(self):pass
class FakeLLM:
 invalid=False;calls=0;observed=[]
 def __init__(self,**kwargs):self.llm_engine=types.SimpleNamespace(vllm_config={})
 def generate(self,rows,params,use_tqdm):
  type(self).calls+=1;type(self).observed=params
  out=[types.SimpleNamespace(prompt_token_ids=row['prompt_token_ids'],outputs=[types.SimpleNamespace(token_ids=[1,151643],text='x',finish_reason='stop',stop_reason=151643)]) for row in rows]
  return out[:-1] if type(self).invalid else out

def fixtures():
 rows=[dict(candidate_id=f'cue/sample0/math/{i}',problem_id=f'math/{i}',source_row_sha256='a'*64,
   input_ids=[1],sampling=dict(seed=i%4,max_tokens=1024)) for i in range(256)]
 roster=dict(run='base_math',rows=rows,new_outputs=256,reused=[],aliases=[])
 config=dict(new_outputs=256,observed_batch_seconds=[1],worker_seconds=1800,reserved_usd='3.26')
 binding=dict(parent=None,remote_path='/fixture/no-model-files');key='cue/benchmark_r1/base_math';claim=dict(run='base_math');store=Store({key+'/claim':claim})
 return roster,config,binding,key,claim,store
class Generation(unittest.TestCase):
 def setUp(self):FakeLLM.calls=0;FakeLLM.invalid=False;FakeLLM.observed=[]
 def execute(self,out,values):
  roster,config,binding,key,claim,store=values;start=time.time()
  fake=types.ModuleType('vllm');fake.LLM=FakeLLM;fake.SamplingParams=lambda **kwargs:kwargs
  with patch.dict(sys.modules,{'vllm':fake}),patch.object(m,'check_persisted_model',return_value={'fake_fixture_only':True}),patch('experiments.learning_regime_p009.high_throughput_v1.engine_kwargs',return_value={}),patch('experiments.learning_regime_p009.high_throughput_v1.actual_engine',return_value={'fake_fixture_only':True}):
   return m.generate(out,roster,binding,config,store,key,claim,Volume(),start,start+1800,'0')
 def test_actual_body_saves_raw_and_exact_params_once(self):
  with tempfile.TemporaryDirectory() as td:
   values=fixtures();result=self.execute(Path(td),values)
   self.assertEqual(result['new_outputs'],256);self.assertEqual(FakeLLM.calls,1)
   self.assertEqual([x['seed'] for x in FakeLLM.observed],[i%4 for i in range(256)])
   self.assertEqual(len(read(Path(td)/'raw/00000.json')),256)
   self.assertIn(values[3]+'/batch_done/00000',values[5])
 def test_malformed_outputs_preserved_without_ack(self):
  with tempfile.TemporaryDirectory() as td:
   values=fixtures();FakeLLM.invalid=True
   with self.assertRaises(ValueError):self.execute(Path(td),values)
   self.assertEqual(len(read(Path(td)/'raw/00000.json')),255)
   self.assertNotIn(values[3]+'/batch_done/00000',values[5])
 def test_reserved_batch_prevents_second_generation(self):
  with tempfile.TemporaryDirectory() as td:
   values=fixtures();values[5][values[3]+'/batch/00000']={'prior':True}
   with self.assertRaises(RuntimeError):self.execute(Path(td),values)
   self.assertEqual(FakeLLM.calls,0)
 def test_all_observations_and_category_cap_remain_binding(self):
  _,c,*_=fixtures();c['observed_batch_seconds']=[2,100]
  self.assertEqual(m.scenario(0,0,[],c,'0')['maximum_seconds'],100)
  with self.assertRaises(ValueError):m.scenario(0,0,[],c,'14')
  with self.assertRaises(TimeoutError):m.scenario(1500,0,[],c,'0')
if __name__=='__main__':unittest.main()

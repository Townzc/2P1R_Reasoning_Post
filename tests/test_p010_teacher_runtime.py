import copy
import json
from pathlib import Path
import tempfile
import time
import types
import unittest
from unittest.mock import patch
from experiments.p010.common import dump,read,MODELS
from experiments.p010.teacher_contract import canonical_request,validate_queue,bounded_forecast


class TeacherChecks(unittest.TestCase):
    def test_duplicate_and_changed_seed_reject(self):
        r=canonical_request('p',2,'t15',[1,2])
        with self.assertRaises(ValueError):validate_queue([r,r],'t15')
        bad=dict(r,seed=r['seed']+1)
        with self.assertRaises(ValueError):validate_queue([bad],'t15')
        with self.assertRaises(ValueError):canonical_request('p',17,'t15',[1,2])
        with self.assertRaises(ValueError):canonical_request('p',1,'t15',[1]*1025)
    def test_real_measurement_must_fit_original_time(self):
        with self.assertRaises(ValueError):bounded_forecast('t72',10,[],1)
        with self.assertRaises(TimeoutError):bounded_forecast('t72',1000,[100],100)
        self.assertLess(bounded_forecast('t72',600,[10,20],30)['projected_usd'],24)
    def test_actual_runtime_persists_eos_at_cap_and_caches_vocab(self):
        from experiments.p010.teacher_runtime import run
        class Tok:
            lengths=0
            all_special_ids=[151643,151645]
            eos_token_id=151645
            def __len__(self):self.lengths+=1;return 152064
            def apply_chat_template(self,*a,**kw):return [1,2]
            def decode(self,ids,**kw):return r'Final \boxed{1}'
        tok=Tok()
        class Engine:
            llm_engine=types.SimpleNamespace(vllm_config=types.SimpleNamespace(parallel_config=types.SimpleNamespace(tensor_parallel_size=1)))
            def __init__(self,**kw):pass
            def generate(self,prompts,params,**kw):
                return [types.SimpleNamespace(prompt_token_ids=[1,2],outputs=[types.SimpleNamespace(token_ids=[17]*1023+[151645],text='raw backend',finish_reason='length',stop_reason=None)]) for _ in prompts]
        class Pool:
            attempts=[];startups=[]
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def score_rows(self,rows):return {'rows':[{'id':r['id'],'score':{'correct':True,'parsed':True,'box_extracted':True}} for r in rows]}
        class Store:
            def __init__(self):self.data={}
            def put(self,k,v,**kw):
                if k in self.data:return False
                self.data[k]=v;return True
            def get(self,k):return {'claim':1}
        gpu=types.SimpleNamespace(device_count=lambda:1,get_device_name=lambda i:'H100',get_device_properties=lambda i:types.SimpleNamespace(total_memory=80*1024**3))
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);inp=root/'inputs';inp.mkdir();out=root/'out';out.mkdir()
            dump(inp/'MATH_SOURCE.json',[{'problem_id':'p','problem':'test','solution':r'\boxed{1}'}]);dump(inp/'MATH_ROSTERS.json',{})
            dump(inp/'t15_fixed_requests.json',[canonical_request('p',2,'t15',[1,2])])
            modules={'torch':types.SimpleNamespace(cuda=gpu),'transformers':types.SimpleNamespace(AutoTokenizer=types.SimpleNamespace(from_pretrained=lambda *a,**k:tok)),'vllm':types.SimpleNamespace(LLM=Engine,SamplingParams=lambda **kw:kw)}
            asset=dict(remote_path=tmp,files={},model_id=MODELS['t15'][0],revision=MODELS['t15'][1])
            with patch.dict('sys.modules',modules),patch('experiments.learning_regime_p009.high_throughput_v1.actual_engine',return_value={}),patch('experiments.learning_regime_p009.math_scoring_pool.SymbolicPool',Pool):
                result=run('t15',inp,asset,out,Store(),types.SimpleNamespace(commit=lambda:None),time.time(),time.time()+100)
            self.assertEqual(result['completed_unique_new_outputs'],1)
            row=read(out/'derived/00000.json')[0]
            self.assertTrue(row['usable']);self.assertEqual(row['stop']['stop_reason'],'native_eos')
            self.assertEqual(read(out/'raw/00000.json')[0]['finish_reason'],'length')
            self.assertEqual(tok.lengths,1)
            self.assertTrue((out/'intents/00000.json').exists())

if __name__=='__main__':unittest.main()

import copy
import tempfile
import time
import types
import unittest
from pathlib import Path
from unittest.mock import patch
from experiments.p010.common import dump,read,sha,digest,MODELS
from experiments.p010.teacher_transport import completion
from experiments.p010.teacher_contract import canonical_request,sampling
from experiments.p010.teacher_remainder_binding import check_owner


class Tok:
    eos_token_id=151645
    all_special_ids=[151645,151643]
    calls=0
    def get_vocab(self):self.calls+=1;return {'one':17,'eos':151645,'end':151643}
    def apply_chat_template(self,*a,**kw):return [1,2]
    def decode(self,ids,**kw):return r'Final \boxed{1}'


class TransportTests(unittest.TestCase):
    def test_only_known_no_eos_model_vocab_cap_is_preserved(self):
        raw={'token_ids':[17]*1023+[151810],'finish_reason':'length','stop_reason':None}
        original=copy.deepcopy(raw)
        stop,proof=completion(raw,Tok(),{17,151645,151643},152064,{151645,151643})
        self.assertEqual(stop['stop_reason'],'length_cap')
        self.assertEqual(proof['unmapped_model_token_ids'],[151810])
        self.assertEqual(raw,original)

    def test_other_unmapped_and_model_out_of_range_are_not_relaxed(self):
        for ids,reason in [([151810,151645],'stop'),([151810]*1024,'stop'),
                           ([152064]*1024,'length'),([17]*1022+[151810,151645],'length')]:
            with self.assertRaises(ValueError):
                completion({'token_ids':ids,'finish_reason':reason},Tok(),{17,151645},152064,{151645})

    def test_native_eos_at_cap_keeps_original_frozen_rule(self):
        stop,proof=completion({'token_ids':[17]*1023+[151645],'finish_reason':'length'},
                              Tok(),{17,151645},152064,{151645})
        self.assertEqual(stop['stop_reason'],'native_eos')
        self.assertFalse(proof['unmapped_model_token_ids'])

    def test_t7_owner_exception_is_required_and_exactly_bound(self):
        spec={'t7_remainder_proposal':{'existing_raw':256,'no_replay':True}}
        owner={'scope':'p010-T7-unattempted-suffix','approved':True,
               'proposal_sha256':digest(spec['t7_remainder_proposal']),
               'direct_owner_message':'synthetic test only, never admission',
               'new_output_replay_allowed':False,'extra_G_reserve_usd':'5.50'}
        check_owner(owner,spec)
        for bad in [None,dict(owner,approved=False),dict(owner,proposal_sha256='bad'),dict(owner,extra_G_reserve_usd='9')]:
            with self.assertRaises(ValueError):check_owner(bad,spec)

    def test_actual_new_body_reuses256_without_generate_and_vocab_once(self):
        from experiments.p010.teacher_runtime_v3 import run
        from experiments.learning_regime_p009.stage0_generation_engine_v2 import returned_records
        tok=Tok();generated=[]
        def outputs(count):
            return [types.SimpleNamespace(prompt_token_ids=[1,2],outputs=[types.SimpleNamespace(
                token_ids=[17,17,151645],text='raw backend',finish_reason='stop',stop_reason=None)]) for _ in range(count)]
        class Engine:
            llm_engine=types.SimpleNamespace(vllm_config=types.SimpleNamespace(parallel_config=types.SimpleNamespace(tensor_parallel_size=1)))
            def __init__(self,**kw):pass
            def generate(self,prompts,params,**kw):generated.extend(prompts);return outputs(len(prompts))
        class Pool:
            attempts=[];startups=[]
            def __enter__(self):return self
            def __exit__(self,*a):pass
            def score_rows(self,rows):return {'rows':[{'id':r['id'],'score':{'correct':True,'parsed':True,'box_extracted':True}} for r in rows]}
        class Store:
            data=None
            def __init__(self):self.data={}
            def get(self,k):return {'claim':1}
            def put(self,k,v,**kw):
                if k in self.data:return False
                self.data[k]=v;return True
        gpu=types.SimpleNamespace(device_count=lambda:1,get_device_name=lambda i:'H100',
            get_device_properties=lambda i:types.SimpleNamespace(total_memory=80*1024**3))
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);inp=root/'inputs';inp.mkdir();out=root/'out';out.mkdir()
            ids=[f'p{i}' for i in range(257)];queue=[canonical_request(p,1,'t7',[1,2]) for p in ids]
            dump(inp/'MATH_SOURCE.json',[dict(problem_id=p,problem='test',solution=r'\boxed{1}') for p in ids])
            dump(inp/'MATH_ROSTERS.json',{'s1':{'400':[],'3200':ids}})
            dump(inp/'t7_fixed_requests.json',queue);dump(root/'config.json',{'vocab_size':152064})
            raw=returned_records(queue[:256],[sampling(r) for r in queue[:256]],outputs(256));dump(root/'parent_raw.json',raw)
            prefix=dict(rows=queue[:256],raw=raw,failed_interval_proxy_seconds=5,raw_file_sha256=sha(root/'parent_raw.json'))
            modules={'torch':types.SimpleNamespace(cuda=gpu),'transformers':types.SimpleNamespace(AutoTokenizer=types.SimpleNamespace(from_pretrained=lambda *a,**k:tok)),
                     'vllm':types.SimpleNamespace(LLM=Engine,SamplingParams=lambda **kw:kw)}
            assets=dict(remote_path=d,files={},model_id=MODELS['t7'][0],revision=MODELS['t7'][1])
            with patch.dict('sys.modules',modules),patch('experiments.learning_regime_p009.high_throughput_v1.actual_engine',return_value={}),patch('experiments.learning_regime_p009.math_scoring_pool.SymbolicPool',Pool):
                result=run('t7',inp,assets,out,Store(),types.SimpleNamespace(commit=lambda:None),time.time(),time.time()+3600,prefix)
            self.assertEqual(len(generated),1)
            self.assertEqual(result['completed_unique_new_outputs'],1)
            self.assertEqual(result['inherited_raw_outputs'],256)
            self.assertEqual(tok.calls,1)
            self.assertEqual((out/'raw/00000.json').read_bytes(),(root/'parent_raw.json').read_bytes())


if __name__=='__main__':unittest.main()

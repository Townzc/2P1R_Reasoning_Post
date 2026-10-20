"""New E9 boundary, actual-entry mock and saved-score checks; no real models."""
import ast
from copy import deepcopy
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch
from experiments.p010.common import read,dump,digest,manifest
from experiments.p010.e9_contract import BASELINE,limits,forecast,sampling,evaluation_jobs,verify_prompt_texts
from experiments.p010.e9_evidence import verify_endpoint,expected_record_keys,decode_record
from experiments.p010 import e9_scoring as scoring
from experiments.learning_regime_p009.math_scoring import last_box,decide
from experiments.learning_regime_p009.math_scoring_pool import pair_digest
from src.sft_data import prefix

ENGINE=dict(max_model_len=2048,enforce_eager=False,dtype='torch.bfloat16',max_num_seqs=256,
    max_num_batched_tokens=8192,enable_chunked_prefill=True,enable_prefix_caching=False,
    gpu_memory_utilization=.8,compilation_level=3,cudagraph_mode='FULL_AND_PIECEWISE',
    cudagraph_capture_sizes=[1,2,4,8,16,32,64,128,256])

class Tok:
    eos_token_id=100257
    all_special_ids=[100257]
    def __call__(self,text,**kwargs):return {'input_ids':[1,2]}
    def get_vocab(self):return {'a':1,'b':2,'eos':100257}
    def decode(self,ids,**kwargs):return r'\boxed{1}' if ids else ''

class Store:
    def __init__(self):self.values={}
    def get(self,key):return self.values.get(key)
    def put(self,key,value,skip_if_exists):
        if key in self.values:return False
        self.values[key]=value;return True

class FakePool:
    def __init__(self,root,deadline):self.cache={};self.seen=set()
    def score_rows(self,rows):
        result=[]
        for row in rows:
            assert row['id'] not in self.seen;self.seen.add(row['id'])
            extracted=last_box(row['answer_segment']);pair=None
            if row['stop_reason']=='native_eos' and extracted['answer']:
                pair=(row['gold'],extracted['answer'])
                if pair not in self.cache:self.cache[pair]=dict(pair_id=pair_digest(pair),
                    symbolic=dict(status='compared',equivalent=pair[0]==pair[1]),elapsed_seconds=.001,
                    attempt_index=len(self.cache),worker_pid=1)
            obs=self.cache[pair] if pair else None
            result.append(dict(id=row['id'],score=decide(row['gold'],extracted,obs['symbolic'] if obs else {},
                stop_reason=row['stop_reason']),symbolic_attempt=deepcopy(obs),pair_id=pair_digest(pair) if pair else None))
        return {'rows':result}
    def close(self):pass

class E9Checks(unittest.TestCase):
    def body(self,run='e9_s17_n400',exitcode=0,claimed=False,bad_text=False):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);root=Path(temp.name)
        def path(value):
            return root/str(value).lstrip('/') if str(value).startswith('/evidence/') else Path(value)
        gold={f'q{i}':dict(problem_id=f'q{i}',problem='synthetic problem '+str(i),answer='1') for i in range(500)}
        texts=[dict(problem_id=k,prompt_text=prefix(v['problem'])) for k,v in gold.items()]
        endpoint=[dict(candidate_id=f'math/{i:03d}',problem_id=t['problem_id'],input_ids=[1,2],source_row_sha256=digest(t)) for i,t in enumerate(texts)]
        inputs=path('/evidence/p010-20261019/e9_inputs');dump(inputs/'MATH_ENDPOINT.json',endpoint)
        if bad_text:texts[0]['prompt_text']+='wrong'
        dump(inputs/'PROMPT_TEXTS.json',texts)
        config={'synthetic':True};dump(inputs/run/'config.json',config)
        spec=dict(source_files={},configs={run:config},baseline_config=config,input_files=manifest(inputs),
            model=dict(remote_path=str(root/'base'),files={},vocab_size=100352),
            timing=dict(training_seconds=[1.],endpoint_seconds=[1.]))
        store=Store()
        if claimed:store.values['e9/'+run+'/claim']={'old':True}
        out=path('/evidence/p010-20261019/e9')/run
        counter=dict(process=0,joined=False,llm=0,rows=0)
        class Process:
            pid=4321
            def __init__(self,**kwargs):self.exitcode=exitcode
            def start(self):counter['process']+=1
            def join(self,timeout):counter['joined']=True
            def is_alive(self):return False
        conn=types.SimpleNamespace(poll=lambda _:True,recv=lambda:('complete',{'updates':1024},[1.]*64))
        other=types.SimpleNamespace(close=lambda:None)
        ctx=types.SimpleNamespace(Process=Process,Pipe=lambda:(conn,other))
        class LLM:
            def __init__(self,**kwargs):
                assert run==BASELINE or (counter['joined'] and exitcode==0)
                counter['llm']+=1;self.llm_engine=types.SimpleNamespace(vllm_config=None)
            def generate(self,prompts,params,use_tqdm):
                counter['rows']+=len(prompts)
                assert all(p['seed']==17 and p['max_tokens']==1024 and p['stop_token_ids']==[100257] for p in params)
                return [types.SimpleNamespace(prompt_token_ids=p['prompt_token_ids'],outputs=[types.SimpleNamespace(
                    token_ids=[1,100257],text=r'\boxed{1}',finish_reason='stop',stop_reason=100257)]) for p in prompts]
        node=next(n for n in ast.parse(Path('experiments/p010/modal_e9.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='execute')
        ns=dict(Path=path,SPEC='synthetic.json',modal=types.SimpleNamespace(Dict=types.SimpleNamespace(from_name=lambda *a,**kw:store)),
            volume=types.SimpleNamespace(reload=lambda:None,commit=lambda:None))
        exec(compile(ast.Module(body=[node],type_ignores=[]),'<actual E9 execute>','exec'),ns)
        def rd(p):return spec if str(p)=='/workspace/synthetic.json' else read(p)
        with patch('experiments.p010.common.read',side_effect=rd),patch('experiments.p010.runtime_support.source_check'),\
             patch('experiments.p010.runtime_support.hard_timer',return_value=types.SimpleNamespace(cancel=lambda:None)),\
             patch('experiments.p010.runtime_support.compact',return_value={'synthetic':True}),\
             patch('multiprocessing.get_context',return_value=ctx),\
             patch('experiments.learning_regime_p009.high_throughput_v1.actual_engine',return_value=ENGINE),\
             patch.dict('sys.modules',{'vllm':types.SimpleNamespace(LLM=LLM,SamplingParams=lambda **k:k),
                 'transformers':types.SimpleNamespace(AutoTokenizer=types.SimpleNamespace(from_pretrained=lambda *a,**kw:Tok()))}):
            try:result=ns['execute'](run,'synthetic',{},'0')
            except Exception as e:result=e
        return result,counter,store,out,endpoint,spec,gold

    def test_student_exact_worker_then_complete_endpoint_proof(self):
        result,c,store,out,rows,spec,gold=self.body()
        if isinstance(result,Exception):raise result
        self.assertEqual((result['status'],c['process'],c['rows']),('completed',1,500))
        checked=verify_endpoint(out,rows,spec,'e9_s17_n400',store.values,dict(train_seconds=[1.]*64),Tok(),gold,'0')
        self.assertEqual(checked['outputs_decoded'],500);self.assertEqual(checked['logical_stops']['greedy']['native_eos'],500)

    def test_baseline_exact_worker_has_no_training_process(self):
        result,c,store,out,rows,spec,gold=self.body(run=BASELINE)
        if isinstance(result,Exception):raise result
        self.assertEqual((c['process'],c['rows'],result['result']['training']),(0,500,None))
        checked=verify_endpoint(out,rows,spec,BASELINE,store.values,dict(train_seconds=[]),Tok(),gold,'0')
        self.assertEqual(checked['outputs_decoded'],500)
        self.assertEqual(set(store.values),set(expected_record_keys(BASELINE)))

    def test_failed_training_cannot_start_vllm(self):
        result,c,store,out,*_=self.body(exitcode=1)
        self.assertIsInstance(result,RuntimeError);self.assertEqual(c['llm'],0)
        self.assertTrue((out/'FAILURE.json').exists())

    def test_duplicate_claim_cannot_spawn_process(self):
        result,c,store,out,*_=self.body(claimed=True)
        self.assertIsInstance(result,RuntimeError);self.assertEqual(c['process'],0);self.assertFalse(out.exists())

    def test_prompt_text_hash_mismatch_blocks_before_model(self):
        result,c,store,out,*_=self.body(run=BASELINE,bad_text=True)
        self.assertIsInstance(result,ValueError);self.assertEqual(c['llm'],0)

    def test_original_training_function_unchanged(self):
        def function(p):return ast.dump(next(n for n in ast.parse(Path(p).read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='train_and_merge'))
        self.assertEqual(function('experiments/p010/training.py'),function('experiments/p010/e9_training.py'))

    def test_caps_and_budget_not_borrowed(self):
        self.assertEqual(limits(BASELINE),('I',1200,'2.52',1900))
        with self.assertRaises(ValueError):forecast(0,1,2,[1.],[1.],'0',baseline=True)
        with self.assertRaises(ValueError):forecast(0,64,2,[1.],[1.],'149')
        with self.assertRaises(TimeoutError):forecast(1000,0,2,[1.],[100.],'0',baseline=True)

    def test_EOS_at_cap_and_true_length_remain_distinct(self):
        row=dict(candidate_id='q',problem_id='q',source_row_sha256='x',input_ids=[1])
        item=dict(**{k:row[k] for k in ('candidate_id','problem_id','source_row_sha256')},prompt_token_ids=[1],
            sampling=sampling(evaluation_jobs()[0]),output_count=1,backend_text='x',token_ids=[1]*1023+[100257],finish_reason='length',stop_reason=None)
        args=(evaluation_jobs()[0],Tok(),{1,2,100257},[100257],100352)
        self.assertEqual(decode_record(row,item,*args)[0]['stop_reason'],'native_eos')
        item['token_ids']=[1]*1024
        self.assertEqual(decode_record(row,item,*args)[0]['stop_reason'],'length_cap')

    def test_single_endpoint_saved_score_and_tamper_rejection(self):
        rows=[dict(id='greedy::q'+str(i),evaluation='greedy',problem_id='q'+str(i),gold='1',answer_segment=r'\boxed{1}',
            stop_reason='length_cap' if i==499 else 'native_eos',original_gold_row_sha256='a'*64,original_decoded_record_sha256='b'*64) for i in range(500)]
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'score';scoring.score_once(root,rows,{'synthetic':True},60,pool_factory=FakePool)
            result=scoring.verify_saved_scores(root,rows,{'synthetic':True},60)
            self.assertEqual(result['endpoints']['greedy']['correct'],499)
            bad=read(root/'ALL_SCORED_ROWS.json');bad[0]['score']['correct']=False
            (root/'ALL_SCORED_ROWS.json').write_text(__import__('json').dumps(bad))
            with self.assertRaises(ValueError):scoring.verify_saved_scores(root,rows,{'synthetic':True},60)

if __name__=='__main__':unittest.main()

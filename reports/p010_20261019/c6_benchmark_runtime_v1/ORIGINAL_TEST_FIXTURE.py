"""New group lifetime, once-only, cost and scoring-view checks; no real GPU."""
import ast
from copy import deepcopy
from pathlib import Path
import tempfile,types,unittest
from unittest.mock import patch
from experiments.p010.common import read,dump,manifest,digest
from experiments.p010 import cue_benchmark_group as g
from experiments.p010.cue_benchmark_roster import RUNS,parameters
from scripts.score_p010_cue_benchmark import partitions,projected_math

ENGINE=dict(max_model_len=2048,enforce_eager=False,dtype='torch.bfloat16',max_num_seqs=256,
    max_num_batched_tokens=8192,enable_chunked_prefill=True,enable_prefix_caching=False,
    gpu_memory_utilization=.8,compilation_level=3,cudagraph_mode='FULL_AND_PIECEWISE',
    cudagraph_capture_sizes=[1,2,4,8,16,32,64,128,256])


class Store:
    def __init__(self):self.values={}
    def get(self,key):return self.values.get(key)
    def put(self,key,value,skip_if_exists):
        if key in self.values:return False
        self.values[key]=value;return True


def toy_roster(run,count):
    task='gsm' if run=='base_gsm' else 'math'
    rows=[dict(candidate_id='cue/greedy/'+task+f'/{i:05d}',problem_id='q'+str(i),
        source_row_sha256='a'*64,input_ids=[1,1249],original_input_ids=[1],cue_token_ids=[1249],
        condition='cue',evaluation='greedy',task=task,sampling=parameters(task,'greedy')) for i in range(count)]
    return dict(run=run,selected_cue=[1249],new_outputs=count,rows=rows,
        greedy_regeneration=False,new_training_updates=0,aliases=[])


class GroupChecks(unittest.TestCase):
    def body(self,failed_run=None,duplicate=False):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);root=Path(temp.name)
        def path(value):return root/str(value).lstrip('/') if str(value).startswith('/evidence/') else Path(value)
        inputs=path('/evidence/p010-20261019/cue_benchmark_inputs_r1')
        rosters={run:toy_roster(run,n) for run,n in zip(RUNS,[4500,11871,2500,2500])}
        bindings={run:dict(remote_path=str(root/'base'),files={},parent=None,new_training_updates=0,
            new_checkpoint_loads=0,new_merge_operations=0) for run in RUNS}
        store=Store();terminal=dict(status='completed')
        for run,key in [('s1_n400_math','existing_s1_samples/s1_s17_n400'),('t72_n400_math','student/t72_s17_n400_k1')]:
            bindings[run]['parent']=dict(terminal_key=key+'/terminal',terminal=terminal,original_merged_files={})
            store.values[key+'/terminal']=terminal
        for run,value in rosters.items():dump(inputs/(run+'.json'),value)
        dump(inputs/'SELECTION.json',{'synthetic':True});dump(inputs/'MODEL_BINDINGS.json',bindings)
        from experiments.p010.common import sha
        spec=dict(source_files={},input_files=manifest(inputs),selection_sha256=sha(inputs/'SELECTION.json'),
            model_bindings=bindings,observed_batch_seconds=[20.4121413230896])
        if duplicate:store.values[g.KEY+'/claim']={'old':True}
        volume=types.SimpleNamespace(reload=lambda:None,commit=lambda:None)
        history=[];calls=[];generated=[];channel={};current=[None]
        class Process:
            pid=1234
            def __init__(self,target,args):
                if current[0] is not None:assert current[0].joined
                self.args=args;self.exitcode=0;self.joined=False;current[0]=self
            def start(self):
                _,run,input_path,out_path,binding,claim,started,deadline,observed,times,prior=self.args
                calls.append(run)
                if run==failed_run:self.exitcode=1;channel['result']=('error','synthetic interrupted child');return
                result=g.generate_cell(run,out_path,read(input_path),binding,claim,started,deadline,
                    observed,times,prior,store,volume)
                channel['result']=('complete',result)
            def join(self,timeout):self.joined=True;history.append(calls[-1])
            def is_alive(self):return False
        conn=types.SimpleNamespace(poll=lambda _:True,recv=lambda:channel['result'],close=lambda:None)
        ctx=types.SimpleNamespace(Process=Process,Pipe=lambda:(conn,types.SimpleNamespace(close=lambda:None)))
        class LLM:
            def __init__(self,**kw):self.llm_engine=types.SimpleNamespace(vllm_config=None)
            def generate(self,prompts,params,use_tqdm):
                generated.extend((calls[-1],tuple(p['prompt_token_ids'])) for p in prompts)
                return [types.SimpleNamespace(prompt_token_ids=p['prompt_token_ids'],outputs=[types.SimpleNamespace(
                    token_ids=[2,151643],text='synthetic',finish_reason='stop',stop_reason=151643)]) for p in prompts]
        node=next(x for x in ast.parse(Path('experiments/p010/modal_cue_benchmark.py').read_text()).body if isinstance(x,ast.FunctionDef) and x.name=='worker')
        node.decorator_list=[]
        ns=dict(Path=path,SPEC='synthetic.json',volume=volume,
            modal=types.SimpleNamespace(Dict=types.SimpleNamespace(from_name=lambda *a,**kw:store)))
        exec(compile(ast.Module(body=[node],type_ignores=[]),'<actual original C6 group worker>','exec'),ns)
        def rd(p):return spec if str(p)=='/workspace/synthetic.json' else read(p)
        with patch('experiments.p010.common.read',side_effect=rd),patch('experiments.p010.runtime_support.source_check'),\
             patch('experiments.p010.runtime_support.hard_timer',return_value=types.SimpleNamespace(cancel=lambda:None)),\
             patch('experiments.p010.runtime_support.compact',return_value={'synthetic':True}),\
             patch('multiprocessing.get_context',return_value=ctx),\
             patch('experiments.learning_regime_p009.high_throughput_v1.actual_engine',return_value=ENGINE),\
             patch.dict('sys.modules',{'vllm':types.SimpleNamespace(LLM=LLM,SamplingParams=lambda **kw:kw)}):
            try:result=ns['worker']('synthetic-execution',{},'5.78')
            except Exception as exc:result=exc
        return result,calls,history,generated,store,path('/evidence/p010-20261019/cue/benchmark_group_r1')

    def test_actual_group_and_actual_cell_body_complete_all_once(self):
        value,calls,history,generated,store,out=self.body()
        if isinstance(value,Exception):raise value
        self.assertEqual(calls,list(RUNS));self.assertEqual(history,list(RUNS))
        self.assertEqual(len(generated),21371);self.assertEqual(len(value['result']['batch_seconds']),85)
        self.assertEqual(value['status'],'completed')
        self.assertEqual(sum('/batch_done/' in k for k in store.values),85)
        self.assertEqual(read(out/'cells/base_gsm/BEFORE_MODEL_FORECAST.json')['completed_batches'],18)
        self.assertEqual(value['result']['new_training_updates'],0)

    def test_failed_child_preserves_prefix_and_never_starts_later_cell(self):
        value,calls,history,generated,store,out=self.body(failed_run='base_gsm')
        self.assertIsInstance(value,RuntimeError);self.assertEqual(calls,['base_math','base_gsm'])
        self.assertEqual(len(generated),4500);self.assertTrue((out/'cells/base_math/RESULT.json').exists())
        self.assertEqual(store.values[g.KEY+'/terminal']['status'],'failed')

    def test_existing_group_claim_blocks_all_children(self):
        value,calls,history,generated,store,out=self.body(duplicate=True)
        self.assertIsInstance(value,RuntimeError);self.assertEqual(calls,[]);self.assertFalse(out.exists())

    def test_group_numeric_fits_after_E9_without_release(self):
        value=g.forecast(0,0,[],[20.4121413230896],'5.78')
        self.assertLess(value['total_seconds'],5370)
        self.assertEqual(value['budget']['new_reserved_usd'],'8.65')
        self.assertLess(float(value['budget']['forecast_usd']),.8*(15-5.78))
        with self.assertRaises(ValueError):g.forecast(0,0,[],[20.4121413230896],'7')

    def test_all_prior_batches_and_elapsed_are_retained(self):
        with self.assertRaises(TimeoutError):g.forecast(500,0,[],[20.4121413230896],'3.26')
        with self.assertRaises(TimeoutError):g.forecast(0,1,[200],[1],'3.26')
        with self.assertRaises(ValueError):g.forecast(0,2,[1],[1],'3.26')

    def test_persisted_model_rejects_merge_and_parent_change(self):
        binding=dict(remote_path='/not-a-model',files={},parent=None,new_training_updates=0,new_checkpoint_loads=0,new_merge_operations=1)
        with self.assertRaises(ValueError):g.model_reuse('base_math',binding,Store())
        binding['new_merge_operations']=0
        binding['parent']=dict(terminal_key='student/t72_s17_n400_k1/terminal',terminal={'status':'completed'},original_merged_files={})
        with self.assertRaises(ValueError):g.model_reuse('t72_n400_math',binding,Store())

    def test_score_projection_retains_original_text_stop_and_identity(self):
        row=dict(id='cue/sample2/math/0000',problem_id='q0',evaluation='sample2',condition='cue',
            answer_segment='original text',stop_reason='length_cap',gold='1')
        projected=projected_math([row])[0]
        self.assertEqual(projected['answer_segment'],row['answer_segment']);self.assertEqual(projected['stop_reason'],'length_cap')
        self.assertEqual(projected['original_benchmark_id'],row['id']);self.assertEqual(projected['original_evaluation'],'sample2')
        self.assertEqual(row['id'],'cue/sample2/math/0000')

    def test_new_score_partition_cannot_include_reused_conditions(self):
        rows=[]
        for label in ['greedy','sample0','sample1','sample2','sample3']:
            rows.extend(dict(condition='cue',evaluation=label,problem_id=f'q{i}') for i in range(500))
        self.assertEqual(len(partitions(rows,'s1_n400_math')),5)
        bad=deepcopy(rows);bad[0]['condition']='no_cue'
        with self.assertRaises(ValueError):partitions(bad,'s1_n400_math')
        with self.assertRaises(ValueError):partitions(rows[:-1],'s1_n400_math')


if __name__=='__main__':unittest.main()

"""New Plan-A contract and mocked full endpoint tests; no GPU or old rescoring."""
from copy import deepcopy
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch
from experiments.sft_allocation_midpoint.common import dump, read, digest
from experiments.learning_regime_p009 import p0_fast_contract as c
from experiments.learning_regime_p009 import p0_fast_runtime as rt
from experiments.learning_regime_p009.high_throughput_v1 import engine_kwargs, actual_engine


def fixture():
    plan=dict(campaign_id=c.CAMPAIGN,slots={c.RUN:dict(stage='p0_fast',reserved_cents=252)},
              stage_caps_cents={'p0_fast':252},total_cap_cents=252)
    parent=dict(run_id=c.PARENT_RUN,reserved_cents=248)
    owner=dict(scope='p009-owner-plan-A-high-throughput-full-P0',old_128_not_in_new_endpoint=True,
               new_experiment_cap_cents=10000,teacher_context=2048,seven_math_rows_unsupported=True)
    spec=dict(scope=c.SCOPE,campaign=c.CAMPAIGN,run_id=c.RUN,roles=list(c.ROLES),
        worker_seconds=1200,platform_seconds=1260,startup_seconds=600,full_window_seconds=1900,
        reserved_cents=252,parent_reserved_cents=248,new_training_updates=0,fresh_outputs=2638,
        inherited_outputs=0,batch_size=256,bootstrap_batches_total=1,engine_kwargs=engine_kwargs(),
        reference_state_sha256=c.REFERENCE_STATE,reference_identity_sha256=c.REFERENCE_IDENTITY,
        stage0_cap_cents=1000,experiment_cap_cents=10000,project_cap_cents=45000,
        protected_original_cents=5000,plan_sha256=digest(plan),source_files={'fast.py':'a'*64},
        parent_claim=parent,parent_terminal=dict(status='failed',claim_sha256=digest(parent)),
        owner_plan_A=owner,design_target='b'*40,inputs={'x':dict(bytes=1,sha256='c'*64)})
    release=dict(source_files=spec['source_files'],review_target='d'*40,
        runtime_review=dict(scope=c.SCOPE,decision='PASS-WITH-NOTES',target_commit='d'*40,
            report_commit='e'*40,report_sha256='f'*64,spec_sha256=digest(spec),
            source_files=spec['source_files'],owner_plan_A_sha256=digest(owner),
            fresh_full_P0_accepted=True,first_one_batch_bootstrap_accepted=True),
        design_review=dict(scope='p009-design-and-stage0-inputs',target_commit='b'*40,
            report_commit='e'*40,report_sha256='f'*64,decision='PASS'),
        input_readback=spec['inputs'],budget=dict(new_experiment_cap_cents=10000,
            p009_stage0_used_and_pending_cents=248,slot_reserved_cents=252,project_prior_upper_cents=26070))
    return spec,plan,release


class Store(dict):
    def put(self,k,v,skip_if_exists=False):
        if skip_if_exists and k in self:return False
        self[k]=deepcopy(v);return True


def old_records(spec):
    pre='midpoint/'+c.PARENT_CAMPAIGN+'/'
    return Store({pre+'claim/'+c.PARENT_RUN:spec['parent_claim'],
                  pre+'terminal/'+c.PARENT_RUN:spec['parent_terminal']})


class FastTests(unittest.TestCase):
    def test_exact_release_and_full_window_cost(self):
        s,p,r=fixture();c.validate_release(s,p,r)
        self.assertEqual(c.cost_cents(c.FULL_WINDOW)+20,c.RESERVED_CENTS)
        self.assertEqual(c.PARENT_RESERVED_CENTS+c.RESERVED_CENTS,500)

    def test_no_old_reserve_recycling_or_project_overflow(self):
        for field,value in [('p009_stage0_used_and_pending_cents',0),
                            ('project_prior_upper_cents',35001),('project_prior_upper_cents',-1)]:
            s,p,r=fixture();r['budget'][field]=value
            with self.assertRaises(ValueError):c.validate_release(s,p,r)

    def test_legacy_review_and_changed_engine_not_admitted(self):
        s,p,r=fixture();r['runtime_review']['scope']='p009-p0-unattempted-suffix-runtime-and-numeric'
        with self.assertRaises(ValueError):c.validate_release(s,p,r)
        s,p,r=fixture();s['engine_kwargs']['enforce_eager']=True
        r['runtime_review']['spec_sha256']=digest(s)
        with self.assertRaises(ValueError):c.validate_release(s,p,r)

    def test_no_inheritance_or_extended_bootstrap(self):
        for k,v in [('inherited_outputs',128),('bootstrap_batches_total',2),('fresh_outputs',2510),
                    ('worker_seconds',1800)]:
            s,p,r=fixture();s[k]=v;r['runtime_review']['spec_sha256']=digest(s)
            with self.assertRaises(ValueError):c.validate_release(s,p,r)

    def test_slowest_batch_and_elapsed_graph_setup_count(self):
        good=c.remaining_forecast(100,[10],11);self.assertTrue(good['admitted'])
        self.assertFalse(c.remaining_forecast(800,[10],11)['admitted'])
        slow=c.remaining_forecast(100,[10,100,1],9)
        self.assertFalse(slow['admitted']);self.assertEqual(slow['full_batch_max_seconds'],100)
        for bad in [float('nan'),float('inf'),-1]:
            with self.assertRaises(ValueError):c.remaining_forecast(bad,[1],11)

    def test_no_marker_reacquisition_or_parent_completion(self):
        s,_,_=fixture();st=old_records(s);claim=NS(claim_sha256='c'*64)
        c.fence_original(st,s,claim)
        with self.assertRaises(ValueError):c.fence_original(st,s,claim)
        st=old_records(s);st['midpoint/'+c.PARENT_CAMPAIGN+'/terminal/'+c.PARENT_RUN]={'status':'completed'}
        with self.assertRaises(ValueError):c.fence_original(st,s,claim)

    def test_actual_cuda_config_no_silent_fallback(self):
        cfg=NS(model_config=NS(max_model_len=2048,enforce_eager=False,dtype='torch.bfloat16'),
            scheduler_config=NS(max_num_seqs=256,max_num_batched_tokens=8192,enable_chunked_prefill=True),
            cache_config=NS(enable_prefix_caching=False,gpu_memory_utilization=.80),
            compilation_config=NS(level=3,cudagraph_mode=NS(name='FULL_AND_PIECEWISE'),
                cudagraph_capture_sizes=[256,128,64,32,16,8,4,2,1]))
        self.assertEqual(actual_engine(cfg)['max_num_seqs'],256)
        cfg.compilation_config.cudagraph_mode.name='NONE'
        with self.assertRaises(ValueError):actual_engine(cfg)
        altered=engine_kwargs();altered['compilation_config']['level']=0
        self.assertEqual(engine_kwargs()['compilation_config']['level'],3)

    def flow(self, *, deny_after_first=False, lose_first=False):
        base=Path('.local/p009_20261014/r1')
        with tempfile.TemporaryDirectory(dir=base,prefix='fast_mock_') as d:
            d=Path(d);inputs=d/'inputs';out=d/'out';s,_,_=fixture();st=old_records(s)
            prompts=[dict(problem_id=f'gsm8k/test/{i:05d}',input_ids=[12]) for i in range(1319)]
            dump(inputs/'qwen_gsm_zero_parity.json',dict(n=1319,eos_token_id=151643,max_context=2048,
                max_new_tokens=512,prompts=prompts))
            s.update(remote_inputs=str(inputs),inputs={},remote_base_model='unused',base_files={},
                remote_reference_checkpoint='unused',checkpoint_files={},base_revision='b'*40)
            guard=NS(prefix='midpoint/'+c.CAMPAIGN+'/',check_active=lambda *a,**k:None)
            claim=NS(run_id=c.RUN,claim_sha256='c'*64);generated=[]
            class Conn:
                def __init__(self,mode):self.mode=mode;self.part=None
                def send(self,command):
                    op,part=command
                    if op=='generate':self.part=part;generated.append([r['problem_id'] for r in part])
            def receive(conn,proc,stop):
                if conn.mode=='merge':return 'merged',{}
                if conn.part is None:return 'ready',{}
                if lose_first:raise RuntimeError('Lost response, never repeat')
                raw=[dict(problem_id=r['problem_id'],prompt_token_ids=r['input_ids'],token_ids=[12,151643],
                          finish_reason='stop') for r in conn.part];conn.part=None
                return 'outputs',raw
            original=rt.remaining_forecast
            def forecast(*args):
                f=original(*args)
                if deny_after_first:f['admitted']=False
                return f
            with patch.object(rt,'verify'),patch.object(rt,'isolated',lambda mode,paths:(Conn(mode),NS(exitcode=0))),\
                    patch.object(rt,'receive',receive),patch.object(rt,'close_process'),\
                    patch.object(rt.tempfile,'mkdtemp',return_value=str(d/'scratch')),\
                    patch.object(rt,'remaining_forecast',forecast):
                if lose_first or deny_after_first:
                    with self.assertRaises((RuntimeError,TimeoutError)):
                        rt.execute(s,out,st,guard,claim,lambda:None,time.time(),time.time()+1200)
                    self.assertEqual(len(generated),1)
                else:
                    result=rt.execute(s,out,st,guard,claim,lambda:None,time.time(),time.time()+1200)
                    self.assertEqual(result['outputs'],2638);self.assertEqual(result['inherited_outputs'],0)
                    self.assertEqual([len(x) for x in generated],[256]*5+[39]+[256]*5+[39])
                    for block in (generated[:6],generated[6:]):
                        self.assertEqual([x for part in block for x in part],[r['problem_id'] for r in prompts])
                    intents=[read(p) for p in (out/'intents').glob('*.json')]
                    self.assertEqual(sum(x['first_measurement_exception'] for x in intents),1)
                    self.assertEqual(len(result['forecasts']),11)
                    self.assertEqual(len(list((out/'correct_969/raw').glob('*.json'))),6)
            with patch.object(rt,'isolated') as engine:
                with self.assertRaises(ValueError):
                    rt.execute(s,d/'never',st,guard,claim,lambda:None,time.time(),time.time()+1200)
                engine.assert_not_called()

    def test_complete_2638_fresh_rows_and_one_bootstrap(self):self.flow()
    def test_forecast_stop_before_second_batch_no_retry(self):self.flow(deny_after_first=True)
    def test_lost_response_keeps_claim_fence_no_retry(self):self.flow(lose_first=True)


if __name__=='__main__':unittest.main()

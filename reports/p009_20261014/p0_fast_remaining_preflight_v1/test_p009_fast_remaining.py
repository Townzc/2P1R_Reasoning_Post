"""New suffix safety tests; only fake engine/ledger, no old model or scoring."""
from copy import deepcopy
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch
from experiments.sft_allocation_midpoint.common import dump, digest, read
from experiments.learning_regime_p009 import p0_fast_remaining_contract as c
from experiments.learning_regime_p009 import p0_fast_remaining_runtime as rt


def fixture():
    plan = dict(campaign_id=c.CAMPAIGN, slots={c.RUN:dict(stage='p0_fast_remaining',reserved_cents=252)},
        stage_caps_cents={'p0_fast_remaining':252},total_cap_cents=252)
    claim = dict(run_id=c.PARENT_RUN,reserved_cents=252)
    parent = dict(inputs={'a':dict(bytes=1,sha256='a'*64)})
    spec = dict(scope=c.SCOPE,campaign=c.CAMPAIGN,run_id=c.RUN,offsets=c.OFFSETS,
        worker_seconds=1200,platform_seconds=1260,startup_seconds=600,full_window_seconds=1900,
        reserved_cents=252,parent_reserved_cents=500,new_training_updates=0,suffix_outputs=2382,
        inherited_outputs=256,batch_size=256,suffix_batches=11,bootstrap_batches_total=0,
        engine_kwargs=c.engine_kwargs(),stage0_cap_cents=1000,experiment_cap_cents=10000,
        project_cap_cents=45000,protected_original_cents=5000,plan_sha256=digest(plan),
        source_files={'candidate':'a'*64},parent_spec=parent,parent_spec_sha256=digest(parent),
        parent_claim=claim,parent_terminal=dict(status='failed',claim_sha256=digest(claim)),
        parent_preservation_sha256='b'*64,parent_failed_batch_proxy_seconds=20.4121413230896,
        parent_raw_sha256='c'*64,parent_ledger_keys=[])
    review = dict(scope=c.SCOPE,decision='PASS-WITH-NOTES',target_commit='d'*40,report_commit='e'*40,
        report_sha256='f'*64,source_files=spec['source_files'],spec_sha256=digest(spec),
        parent_preservation_sha256='b'*64,bounded_suffix_only=True,
        native_eos_cap_metadata_accepted=True,same_frozen_logical_stop=True)
    release = dict(runtime_review=review,review_target='d'*40,source_files=spec['source_files'],
        budget=dict(p009_stage0_used_and_pending_cents=500,slot_reserved_cents=252,
            new_experiment_cap_cents=10000,project_prior_upper_cents=26070),input_readback=parent['inputs'])
    return spec, plan, release


class Store(dict):
    def put(self,key,value,skip_if_exists=False):
        if skip_if_exists and key in self:
            return False
        self[key] = deepcopy(value)
        return True


class RemainingTests(unittest.TestCase):
    def test_scoped_release_and_all_sunk_reservations(self):
        s,p,r = fixture(); c.validate_release(s,p,r)
        self.assertEqual(c.cost_cents(c.FULL_WINDOW)+20,252)
        self.assertEqual(c.RESERVED_CENTS+c.PARENT_RESERVED_CENTS,752)

    def test_old_review_does_not_admit_suffix(self):
        for k,v in (('scope','p009-p0-high-throughput-full-runtime-and-bootstrap-numeric'),
                    ('native_eos_cap_metadata_accepted',False),('same_frozen_logical_stop',False)):
            s,p,r=fixture();r['runtime_review'][k]=v
            with self.assertRaises(ValueError):c.validate_release(s,p,r)

    def test_no_budget_recycling_or_unallocated_borrow(self):
        for k,v in (('p009_stage0_used_and_pending_cents',248),('slot_reserved_cents',251),
                    ('project_prior_upper_cents',35001)):
            s,p,r=fixture();r['budget'][k]=v
            with self.assertRaises(ValueError):c.validate_release(s,p,r)

    def test_no_prefix_regeneration_or_changed_batch_or_bootstrap(self):
        for k,v in (('offsets',{'base_638':0,'correct_969':0}),('batch_size',32),
                    ('inherited_outputs',0),('bootstrap_batches_total',1),('worker_seconds',1800)):
            s,p,r=fixture();s[k]=v;r['runtime_review']['spec_sha256']=digest(s)
            with self.assertRaises(ValueError):c.validate_release(s,p,r)

    def test_slowest_all_observations_and_setup_elapsed(self):
        self.assertTrue(c.remaining_forecast(100,[20.4121413230896],11)['admitted'])
        self.assertFalse(c.remaining_forecast(700,[20.4121413230896],11)['admitted'])
        f=c.remaining_forecast(100,[20.4121413230896,90,1],9)
        self.assertFalse(f['admitted']);self.assertEqual(f['max_interval_seconds'],90)
        self.assertFalse(f['parent_proxy_is_completed_batch'])

    def test_failed_marker_write_cannot_be_reacquired(self):
        s,_,_=fixture();st=Store();claim=NS(claim_sha256='d'*64)
        c.fence_parent(st,s,claim)
        with self.assertRaises(ValueError):c.fence_parent(st,s,claim)

    def flow(self,deny_first=False,lose_first=False):
        with tempfile.TemporaryDirectory(dir='.local/p009_20261014/r1',prefix='remaining_mock_') as d:
            d=Path(d);s,_,_=fixture();s['parent_spec'].update(remote_inputs=str(d/'inputs'),inputs={},
                remote_base_model='unused',base_files={},remote_reference_checkpoint='unused',checkpoint_files={})
            prompts=[dict(problem_id=f'gsm8k/test/{i:05d}',input_ids=[12]) for i in range(1319)]
            dump(d/'inputs/qwen_gsm_zero_parity.json',dict(n=1319,eos_token_id=151643,
                max_context=2048,max_new_tokens=512,prompts=prompts))
            generated=[];st=Store();guard=NS(prefix='midpoint/'+c.CAMPAIGN+'/',check_active=lambda *a,**k:None)
            claim=NS(run_id=c.RUN,claim_sha256='d'*64)
            class Conn:
                def __init__(self,mode):self.mode=mode;self.part=None
                def send(self,command):
                    op,rows=command
                    if op=='generate':self.part=rows;generated.append([r['problem_id'] for r in rows])
            def receive(conn,process,stop):
                if conn.mode=='merge':return 'merged',{}
                if conn.part is None:return 'ready',{}
                if lose_first:raise RuntimeError('Lost original response')
                rows=[dict(problem_id=r['problem_id'],prompt_token_ids=r['input_ids'],
                    token_ids=[12,151643],finish_reason='stop',stop_reason=None) for r in conn.part]
                conn.part=None;return 'outputs',rows
            original=rt.remaining_forecast
            def forecast(*a):
                f=original(*a)
                if deny_first:f['admitted']=False
                return f
            with patch.object(rt,'verify'),patch.object(rt,'check_parent',return_value={'unscored':True}),\
                    patch.object(rt,'isolated',lambda mode,paths:(Conn(mode),NS(exitcode=0))),\
                    patch.object(rt,'receive',receive),patch.object(rt,'close_process'),\
                    patch.object(rt.tempfile,'mkdtemp',return_value=str(d/'scratch')),\
                    patch.object(rt,'remaining_forecast',forecast):
                if deny_first or lose_first:
                    with self.assertRaises((RuntimeError,TimeoutError)):
                        rt.execute(s,d/'out',st,guard,claim,lambda:None,time.time(),time.time()+1200)
                    self.assertEqual(len(generated),0 if deny_first else 1)
                else:
                    out=rt.execute(s,d/'out',st,guard,claim,lambda:None,time.time(),time.time()+1200)
                    self.assertEqual(out['suffix_outputs'],2382);self.assertEqual(out['inherited_outputs'],256)
                    self.assertEqual([len(x) for x in generated],[256]*4+[39]+[256]*5+[39])
                    self.assertEqual([x for part in generated[:5] for x in part],
                                     [r['problem_id'] for r in prompts[256:]])
                    self.assertEqual([x for part in generated[5:] for x in part],
                                     [r['problem_id'] for r in prompts])
                    self.assertEqual(len(out['forecasts']),11)
                    self.assertFalse(any(read(p)['bootstrap_exception'] for p in (d/'out/intents').glob('*.json')))
                with patch.object(rt,'isolated') as engine:
                    with self.assertRaises(ValueError):
                        rt.execute(s,d/'never',st,guard,claim,lambda:None,time.time(),time.time()+1200)
                    engine.assert_not_called()

    def test_complete_2382_unique_suffix_no_saved_prefix_replay(self):self.flow()
    def test_forecast_failure_before_first_generation_no_exception(self):self.flow(deny_first=True)
    def test_lost_response_keeps_marker_and_never_replays(self):self.flow(lose_first=True)


if __name__=='__main__':unittest.main()

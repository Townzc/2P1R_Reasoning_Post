"""New suffix-only fixtures; no model and no old P0 test suite rerun."""
from copy import deepcopy
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from experiments.sft_allocation_midpoint.common import dump, read, sha, digest, manifest
from experiments.learning_regime_p009 import p0_suffix_contract as c
from experiments.learning_regime_p009 import p0_suffix_runtime as runtime

BASE = Path('.local/p009_20261014/r1')


def prompts():
    return dict(n=1319,eos_token_id=151643,max_context=2048,max_new_tokens=512,
        prompts=[dict(problem_id=f'gsm8k/test/{i:05d}',input_ids=[12]) for i in range(1319)])


def raw(rows):
    return [dict(problem_id=r['problem_id'],prompt_token_ids=r['input_ids'],
        token_ids=[12,151643],finish_reason='stop',stop_reason=151643,backend_text='x') for r in rows]


def release_fixture():
    plan = dict(campaign_id=c.CAMPAIGN,slots={c.RUN:dict(stage='p0_suffix',reserved_cents=326)})
    parent_claim = dict(run_id=c.PARENT_RUN,reserved_cents=248)
    spec = dict(scope=c.SCOPE,campaign=c.CAMPAIGN,run_id=c.RUN,worker_seconds=1800,
        platform_seconds=1860,startup_seconds=600,full_window_seconds=2500,reserved_cents=326,
        parent_reserved_cents=248,offsets=dict(c.OFFSETS),suffix_outputs=2510,reused_outputs=128,
        new_training_updates=0,plan_sha256=digest(plan),source_files={'new.py':'a'*64},
        parent_claim=parent_claim,parent_terminal=dict(status='failed',claim_sha256=digest(parent_claim)),
        parent_spec=dict(inputs={'x':dict(bytes=1,sha256='b'*64)}),parent_preservation_sha256='c'*64)
    spec['parent_spec_sha256'] = digest(spec['parent_spec'])
    release = dict(source_files=spec['source_files'],review_target='d'*40,
        runtime_review=dict(scope=c.SCOPE,decision='PASS-WITH-NOTES',target_commit='d'*40,
            report_commit='e'*40,report_sha256='f'*64,spec_sha256=digest(spec),
            source_files=spec['source_files'],parent_preservation_sha256='c'*64,bounded_suffix_only=True),
        budget=dict(new_experiment_cap_cents=10000,p009_stage0_used_and_pending_cents=248,
            slot_reserved_cents=326,project_prior_upper_cents=26070),input_readback=spec['parent_spec']['inputs'])
    return spec,plan,release


class Store(dict):
    def put(self,key,value,skip_if_exists=False):
        if skip_if_exists and key in self:
            return False
        self[key]=deepcopy(value);return True


class SuffixTests(unittest.TestCase):
    def test_exact_release_and_old_reserve_retained(self):
        s,p,r=release_fixture();c.validate_release(s,p,r)
        r['budget']['p009_stage0_used_and_pending_cents']=0
        with self.assertRaises(ValueError):c.validate_release(s,p,r)

    def test_parent_completed_or_offset_replay_rejected(self):
        for key,value in [('offsets',dict(base_638=0,correct_969=0)),('worker_seconds',1900)]:
            s,p,r=release_fixture();s[key]=value;r['runtime_review']['spec_sha256']=digest(s)
            with self.assertRaises(ValueError):c.validate_release(s,p,r)
        s,p,r=release_fixture();s['parent_terminal']['status']='completed'
        r['runtime_review']['spec_sha256']=digest(s)
        with self.assertRaises(ValueError):c.validate_release(s,p,r)

    def test_exact_review_binding_and_project_budget(self):
        s,p,r=release_fixture();r['runtime_review']['spec_sha256']='0'*64
        with self.assertRaises(ValueError):c.validate_release(s,p,r)
        s,p,r=release_fixture();r['budget']['project_prior_upper_cents']=35001
        with self.assertRaises(ValueError):c.validate_release(s,p,r)

    def test_forecast_retains_slowest_and_fails_closed(self):
        first=c.remaining_forecast(45,[11.793591022491455],80)
        self.assertTrue(first['admitted'])
        slow=c.remaining_forecast(45,[11.793591022491455,30,1],79)
        self.assertFalse(slow['admitted'])
        self.assertEqual(slow['full_batch_max_seconds'],30)
        with self.assertRaises(ValueError):c.remaining_forecast(0,[float('nan')],80)

    def test_prefix_lineage_and_unknown_unit_rejected(self):
        with tempfile.TemporaryDirectory(dir=BASE,prefix='suffix_fixture_') as d:
            d=Path(d);inp=d/'inputs';ev=d/'evidence';ev.mkdir()
            ps=prompts();dump(inp/'qwen_gsm_zero_parity.json',ps)
            pre='midpoint/'+c.PARENT_CAMPAIGN+'/'
            claim=dict(run_id=c.PARENT_RUN,reserved_cents=248);ledger={pre+'claim/'+c.PARENT_RUN:claim}
            for offset in range(0,128,32):
                part=ps['prompts'][offset:offset+32];name=f'base_638_{offset:04d}'
                path=ev/'base_638/raw'/f'{offset:04d}.json';dump(path,raw(part))
                unit=dict(problem_ids=[x['problem_id'] for x in part],prompt_sha256=digest(part))
                done=dict(count=32,raw_sha256=sha(path))
                dump(ev/'intents'/f'{name}.json',unit);dump(ev/'completed'/f'{name}.json',done)
                ledger[pre+c.PARENT_RUN+'/unit/'+name]=unit;ledger[pre+c.PARENT_RUN+'/done/'+name]=done
            forecast=dict(admitted=False,observed_batches=4,future_batches=80,full_batch_max_seconds=11.8)
            dump(ev/'forecasts/004.json',forecast);fm=manifest(ev);dump(ev/'failure_manifest.json',fm)
            terminal=dict(status='failed',claim_sha256=digest(claim),evidence_sha256=digest(fm))
            ledger[pre+'terminal/'+c.PARENT_RUN]=terminal
            s=dict(parent_files=manifest(ev),parent_failure_manifest_file_sha256=sha(ev/'failure_manifest.json'),
                parent_terminal=terminal,parent_claim=claim,parent_ledger_digest=digest(ledger),failed_forecast=forecast)
            proof=c.check_parent(s,ev,ledger,inp);self.assertEqual(proof['saved_outputs'],128)
            ledger[pre+c.PARENT_RUN+'/unit/base_638_0128']={'attempted':True}
            s['parent_ledger_digest']=digest(ledger)
            with self.assertRaisesRegex(ValueError,'Unknown/unacknowledged'):
                c.check_parent(s,ev,ledger,inp)

    def test_all_suffix_batches_once_and_no_inherited_id_generated(self):
        with tempfile.TemporaryDirectory(dir=BASE,prefix='suffix_flow_') as d:
            d=Path(d);inp=d/'inputs';out=d/'out'
            dump(inp/'qwen_gsm_zero_parity.json',prompts())
            store=Store();generated=[]
            spec=dict(parent_spec=dict(remote_inputs=str(inp),inputs={},remote_base_model='base',
                base_files={},remote_reference_checkpoint='checkpoint',checkpoint_files={}),
                parent_ledger_keys=[],parent_terminal={'status':'failed'},
                failed_forecast={'full_batch_max_seconds':11.8})
            guard=SimpleNamespace(plan={'campaign_id':c.CAMPAIGN},prefix='midpoint/'+c.CAMPAIGN+'/',
                                  check_active=lambda *a,**k:None)
            admission=SimpleNamespace(run_id=c.RUN,claim_sha256='a'*64)
            class Conn:
                def __init__(self,mode):self.mode=mode;self.part=None
                def send(self,command):
                    kind,part=command
                    if kind=='generate':self.part=part;generated.append([x['problem_id'] for x in part])
            def isolated(mode,paths):return Conn(mode),SimpleNamespace(exitcode=0)
            def receive(conn,proc,stop):
                if conn.mode=='merge':return 'merged',{}
                if conn.part is None:return 'ready',{}
                result=raw(conn.part);conn.part=None;return 'outputs',result
            with patch.object(runtime,'verify'),patch.object(runtime,'check_parent',return_value={'saved_outputs':128}),\
                    patch.object(runtime,'isolated',isolated),patch.object(runtime,'receive',receive),\
                    patch.object(runtime,'close_process'),patch.object(runtime.tempfile,'mkdtemp',return_value=str(d/'scratch')):
                result=runtime.execute(spec,out,store,guard,admission,lambda:None,time.time(),time.time()+1800)
            self.assertEqual(result['suffix_batches'],80)
            self.assertEqual(sum(map(len,generated)),2510)
            self.assertEqual(generated[0][0],'gsm8k/test/00128')
            self.assertEqual(generated[37][-1],'gsm8k/test/01318')
            self.assertEqual(generated[38][0],'gsm8k/test/00000')
            self.assertEqual(len(list((out/'base_638/raw').glob('*.json'))),38)
            self.assertEqual(len(list((out/'correct_969/raw').glob('*.json'))),42)
            # The original parent marker prevents any second execute before an engine starts.
            with patch.object(runtime,'verify'),patch.object(runtime,'check_parent',return_value={'saved_outputs':128}),\
                    patch.object(runtime,'isolated') as engine:
                with self.assertRaisesRegex(ValueError,'suffix marker'):
                    runtime.execute(spec,d/'never',store,guard,admission,lambda:None,time.time(),time.time()+1800)
                engine.assert_not_called()


if __name__=='__main__':unittest.main()

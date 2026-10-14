"""New entry/binding fixtures only: no Modal, model, upload or real scoring.

Synthetic runtime reviews exist only in memory and never authorize a call.
"""
import ast
from copy import deepcopy
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from experiments.sft_allocation_midpoint.common import read,digest,sha
from experiments.learning_regime_p009 import stage0_generation_binding as binding
from experiments.learning_regime_p009.stage0_generation_contract import MODELS,DATASETS,SLOTS,slot_checked
from experiments.learning_regime_p009.high_throughput_v1 import engine_kwargs

WD=Path.cwd()
R=Path('.local/p009_20261014/r1')
ENTRY=Path('experiments/learning_regime_p009/modal_stage0_generation.py')


class Store:
    def __init__(self):self.rows={}
    def get(self,k,default=None):return deepcopy(self.rows.get(k,default))
    def put(self,k,v,skip_if_exists=False):
        if skip_if_exists and k in self.rows:return False
        self.rows[k]=deepcopy(v);return True


class EntryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=R);self.addCleanup(self.tmp.cleanup)
        now=time.time()
        self.plan=dict(campaign_id=binding.CAMPAIGN,created_epoch=now-60,deadline_epoch=now+10000,
            slots={n:dict(stage='stage0_generation',reserved_cents=s['reserved_cents']) for n,s in SLOTS.items()},
            stage_caps_cents={'stage0_generation':867},total_cap_cents=867)
        original=read('reports/p009_20261014/stage0_generation_core_preflight_v1/CANDIDATE.json')
        files=read(R/'stage0_inputs_r1/MANIFEST.json')
        self.spec=dict(scope=binding.SCOPE,campaign=binding.CAMPAIGN,engine_kwargs=engine_kwargs(),
            datasets=DATASETS,slots={n:slot_checked(n) for n in SLOTS},prior_reserved_cents=1004,
            stage0_cap_cents=2000,experiment_cap_cents=11000,total_new_reserved_cents=867,
            project_cap_cents=45000,protected_original_cents=5000,new_training_updates=0,
            fresh_outputs=14450,p0_regeneration=0,first_paid_batch_exceptions=3,maximum_concurrent_workers=3,
            internal_only_amendment_sha256=binding.AMENDMENT_SHA,original_P0_oracle_sha256=binding.P0_ORACLE_SHA,
            plan_sha256=digest(self.plan),source_files=original['source_files'],
            inputs={d['file']:files[d['file']] for d in DATASETS.values()},
            models={n:dict(m,files={'fixture':dict(bytes=1,sha256='0'*64)},remote_path='/evidence/fixture/'+n)
                    for n,m in MODELS.items()},required_P0_records={'fixture_p0':{'status':'completed'}},
            P0_app_ids=['ap-one','ap-two','ap-three','ap-four'])
        self.release=dict(source_files=self.spec['source_files'],review_target='0'*40,
            runtime_review=dict(scope=binding.SCOPE,decision='PASS',target_commit='0'*40,
                report_commit='1'*40,report_sha256='1'*64,spec_sha256=digest(self.spec),
                source_files=self.spec['source_files'],first_paid_batch_exceptions_accepted=3,
                total_new_reserved_cents=867,internal_only_amendment_sha256=binding.AMENDMENT_SHA),
            internal_only_review=read(R/'P0_INTERNAL_ONLY_AMENDMENT_ACCEPTED.json'),
            p0_integrity_review=read(R/'P0_ACTUAL_A2_INTEGRITY_ACCEPTED.json'),
            budget=dict(prior_reserved_cents=1004,new_slots_reserved_cents=867,stage0_cap_cents=2000,
                experiment_cap_cents=11000,project_prior_upper_cents=26070),
            input_readback=deepcopy(self.spec['inputs']),olmo_model_readback=deepcopy(self.spec['models']['olmo']['files']),
            dispatch_app_id='ap-fixture',execution_commit='2'*40)
        self.run='teacher_p2_p3';self.store=Store();self.store.rows.update(deepcopy(self.spec['required_P0_records']))
        self.timer=SimpleNamespace(daemon=False,start=lambda:None,cancel=lambda:setattr(self,'cancelled',True))
        self.cancelled=False;self.calls=0;self.model_error=False
        self.mark()

    def mark(self):
        value=binding.marker(self.spec,self.run,self.release)
        for key in [binding.dispatch_key(self.run)]+[binding.dataset_key(n) for n in SLOTS[self.run]['datasets']]:
            self.store.rows[key]=deepcopy(value)

    def execute(self,spec,run,out,store,guard,claim,commit,start,stop):
        self.calls+=1
        self.assertEqual(stop-start,slot_checked(run)['worker_seconds'])
        self.assertEqual(store.get(guard.prefix+'intent/'+run),binding.intent(spec,run))
        if self.model_error:raise RuntimeError('synthetic engine failure')
        return dict(synthetic_only=True,new_training_updates=0)

    def worker(self):
        node=next(x for x in ast.parse(ENTRY.read_text()).body if isinstance(x,ast.FunctionDef) and x.name=='worker')
        def mapped(value):
            if str(value)=='/workspace':return WD
            if str(value)=='/evidence':return Path(self.tmp.name)/'evidence'
            return Path(value)
        def fixture_read(value):
            if str(value).startswith('/workspace/'):return deepcopy(self.spec)
            return read(value)
        namespace=dict(Path=mapped,SPEC='fixture_admission.json',slot_checked=slot_checked,SLOTS=SLOTS,
            modal=SimpleNamespace(Dict=SimpleNamespace(from_name=lambda *a,**k:self.store)),
            volume=SimpleNamespace(reload=lambda:None,commit=lambda:None))
        exec(compile(ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[])),str(ENTRY),'exec'),namespace)
        with patch('threading.Timer',return_value=self.timer), \
             patch('experiments.sft_allocation_midpoint.common.read',side_effect=fixture_read), \
             patch('experiments.sft_allocation_p008.evidence_bundle.pack',return_value=None), \
             patch('experiments.learning_regime_p009.stage0_generation_runtime.execute',side_effect=self.execute):
            return namespace['worker'](deepcopy(self.plan),self.run,deepcopy(self.release))

    def test_teacher_actual_entry_completes_once(self):
        result=self.worker();self.assertEqual(result['receipt']['status'],'completed')
        self.assertEqual(result['receipt']['actual_cost_cents'],399);self.assertTrue(self.cancelled)
        with self.assertRaises(RuntimeError):self.worker()
        self.assertEqual(self.calls,1)

    def test_qwen_actual_entry_uses_900_seconds(self):
        self.run='qwen_p3';self.mark();self.assertEqual(self.worker()['receipt']['actual_cost_cents'],216)

    def test_olmo_actual_entry_uses_1200_seconds(self):
        self.run='olmo_p3';self.mark();self.assertEqual(self.worker()['receipt']['actual_cost_cents'],252)

    def test_model_exception_persists_failed_claim(self):
        self.model_error=True
        with self.assertRaises(RuntimeError):self.worker()
        self.assertEqual(self.store.get('midpoint/'+binding.CAMPAIGN+'/terminal/'+self.run)['status'],'failed')
        with self.assertRaises(RuntimeError):self.worker()
        self.assertEqual(self.calls,1);self.assertTrue(self.cancelled)

    def test_malformed_readback_fails_before_registration(self):
        self.release['input_readback']={}
        with self.assertRaises(ValueError):self.worker()
        self.assertEqual(self.calls,0);self.assertTrue(self.cancelled)
        self.assertFalse(any('/claim/' in k or k.endswith('/campaign') for k in self.store.rows))

    def test_no_model_when_a_single_dataset_fence_is_missing(self):
        del self.store.rows[binding.dataset_key('teacher_math_zero')]
        with self.assertRaises(ValueError):self.worker()
        self.assertEqual(self.calls,0);self.assertTrue(self.cancelled)

    def test_changed_old_p0_proof_prevents_new_claim(self):
        self.store.rows['fixture_p0']={'status':'failed'}
        with self.assertRaises(ValueError):self.worker()
        self.assertEqual(self.calls,0)

    def test_code_only_review_cannot_admit(self):
        self.release['runtime_review']['scope']='p009-stage0-generation-core-code-and-provisional-numeric'
        with self.assertRaises(ValueError):self.worker()
        self.assertEqual(self.calls,0)

    def test_unreviewed_bootstrap_cannot_admit(self):
        self.release['runtime_review']['first_paid_batch_exceptions_accepted']=0
        with self.assertRaises(ValueError):self.worker()

    def test_new_review_does_not_replace_exact_owner_scope(self):
        self.release['internal_only_review']['report_sha256']='f'*64
        with self.assertRaises(ValueError):self.worker()

    def test_old_reservations_cannot_be_recycled(self):
        self.release['budget']['prior_reserved_cents']=0
        with self.assertRaises(ValueError):self.worker()

    def test_project_protection_binds_before_model(self):
        self.release['budget']['project_prior_upper_cents']=34001
        with self.assertRaises(ValueError):self.worker()
        self.assertEqual(self.calls,0)

    def test_wrong_engine_configuration_rejected(self):
        self.spec=deepcopy(self.spec);self.spec['engine_kwargs']['enforce_eager']=True
        with self.assertRaises(ValueError):self.worker()

    def test_original_three_unused_slot_order(self):
        binding.require_unused({},'teacher_p2_p3',self.plan)
        with self.assertRaises(ValueError):binding.require_unused({},'qwen_p3',self.plan)
        records={binding.dispatch_key('teacher_p2_p3'):binding.marker(self.spec,'teacher_p2_p3',self.release)}
        binding.require_unused(records,'qwen_p3',self.plan)

    def test_unknown_dispatch_and_terminal_cannot_be_skipped(self):
        pre='midpoint/'+binding.CAMPAIGN+'/'
        for records in [{pre+'campaign':None},{binding.dispatch_key('teacher_p2_p3'):None},
                        {binding.dispatch_key('teacher_p2_p3'):binding.marker(self.spec,'teacher_p2_p3',self.release),
                         pre+'terminal/teacher_p2_p3':None}]:
            with self.assertRaises(ValueError):binding.require_unused(records,'qwen_p3',self.plan)

    def test_any_original_attempt_record_blocks_dispatch(self):
        pre='midpoint/'+binding.CAMPAIGN+'/'
        for suffix in ['claim/teacher_p2_p3','intent/teacher_p2_p3','terminal/teacher_p2_p3',
                       'dispatch/teacher_p2_p3','attempt/teacher_p2_p3/x','teacher_p2_p3/unit/x']:
            with self.assertRaises(ValueError):binding.require_unused({pre+suffix:None},'teacher_p2_p3',self.plan)


if __name__=='__main__':unittest.main()

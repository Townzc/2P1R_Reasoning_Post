"""New funded-version checks only; fake I/O and in-memory review fixtures."""
import ast
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import sys
import time
import unittest
from unittest.mock import patch
from experiments.sft_allocation_midpoint.common import read,digest
from experiments.learning_regime_p009 import stage0_generation_contract as old
from experiments.learning_regime_p009 import stage0_generation_contract_v2 as c
from experiments.learning_regime_p009 import stage0_generation_binding_v2 as b
from experiments.learning_regime_p009 import stage0_generation_engine_v2 as engine

class FundedTests(unittest.TestCase):
    def fixture(self):
        s=read('reports/p009_20261014/stage0_generation_runtime_preflight_v1/ADMISSION.json')
        plan=read('reports/p009_20261014/stage0_generation_runtime_preflight_v1/PLAN.json')
        plan.update(total_cap_cents=1637,stage_caps_cents={'stage0_generation':1637},
            slots={n:dict(stage='stage0_generation',reserved_cents=v['reserved_cents']) for n,v in c.SLOTS.items()})
        s.update(scope=b.SCOPE,slots={n:c.slot_checked(n) for n in c.SLOTS},
            stage0_cap_cents=4000,experiment_cap_cents=13000,total_new_reserved_cents=1637,
            plan_sha256=digest(plan),owner_budget_amendment_sha256=b.OWNER_BUDGET_SHA,
            sampling_constructor_proof_sha256=b.SAMPLING_PROOF_SHA)
        r=Path('.local/p009_20261014/r1')
        release=dict(source_files=s['source_files'],review_target='0'*40,
            runtime_review=dict(scope=b.SCOPE,decision='PASS',target_commit='0'*40,
                report_commit='1'*40,report_sha256='2'*64,spec_sha256=digest(s),source_files=s['source_files'],
                first_paid_batch_exceptions_accepted=3,total_new_reserved_cents=1637,
                owner_budget_amendment_sha256=b.OWNER_BUDGET_SHA,
                isolated_wheel_constructor_evidence_accepted=True,
                sampling_constructor_proof_sha256=b.SAMPLING_PROOF_SHA,
                internal_only_amendment_sha256=b.AMENDMENT_SHA),
            internal_only_review=read(r/'P0_INTERNAL_ONLY_AMENDMENT_ACCEPTED.json'),
            p0_integrity_review=read(r/'P0_ACTUAL_A2_INTEGRITY_ACCEPTED.json'),
            budget=dict(prior_reserved_cents=1004,new_slots_reserved_cents=1637,
                stage0_cap_cents=4000,experiment_cap_cents=13000,project_prior_upper_cents=26070),
            input_readback=s['inputs'],olmo_model_readback=s['models']['olmo']['files'])
        return s,plan,release

    def test_full_reservations(self):
        self.assertEqual([c.slot_checked(n)['reserved_cents'] for n in c.SLOTS],[985,326,326])
        self.assertEqual(4000-c.PRIOR_RESERVED_CENTS-sum(v['reserved_cents'] for v in c.SLOTS.values()),1359)
        self.assertEqual([c.slot_checked(n)['full_window_seconds'] for n in c.SLOTS],[7900,2500,2500])

    def test_timing_boundary_not_guarantee(self):
        self.assertTrue(c.remaining_forecast('teacher_p2_p3',240,[120],43)['admitted'])
        self.assertFalse(c.remaining_forecast('teacher_p2_p3',300,[180],43)['admitted'])
        self.assertFalse(c.remaining_forecast('qwen_p3',1771,[1],1)['admitted'])

    def test_scientific_rosters_unchanged(self):
        self.assertEqual(c.DATASETS,old.DATASETS);self.assertEqual(c.MODELS,old.MODELS)
        self.assertEqual({n:v['datasets'] for n,v in c.SLOTS.items()},{n:v['datasets'] for n,v in old.SLOTS.items()})
        for name in c.DATASETS:
            self.assertEqual(c.sampling(name,dict(seed=17)),old.sampling(name,dict(seed=17)))

    def test_valid_owner_exact_binding(self):
        s,p,r=self.fixture()
        for run in c.SLOTS:self.assertEqual(b.validate_release(s,p,run,r),c.slot_checked(run))

    def test_old_budget_and_review_refused(self):
        s,p,r=self.fixture();r['runtime_review']['scope']='p009-stage0-generation-exact-runtime-and-numeric'
        with self.assertRaises(ValueError):b.validate_release(s,p,'teacher_p2_p3',r)
        s,p,r=self.fixture();r['budget']['stage0_cap_cents']=2000
        with self.assertRaises(ValueError):b.validate_release(s,p,'teacher_p2_p3',r)

    def test_proof_and_project_limit_refused(self):
        s,p,r=self.fixture();r['runtime_review']['isolated_wheel_constructor_evidence_accepted']=False
        with self.assertRaises(ValueError):b.validate_release(s,p,'teacher_p2_p3',r)
        s,p,r=self.fixture();r['budget']['project_prior_upper_cents']=32001
        with self.assertRaises(ValueError):b.validate_release(s,p,'teacher_p2_p3',r)

    def test_same_campaign_fences_and_unknown_records(self):
        s,p,r=self.fixture();prefix='midpoint/'+b.CAMPAIGN+'/'
        self.assertEqual(b.CAMPAIGN,'p009-stage0-generation-20261014-r1')
        b.require_unused({},'teacher_p2_p3',p)
        for records in [{prefix+'mystery':1},{prefix+'claim/teacher_p2_p3':{}},
                        {prefix+'campaign':dict(p,total_cap_cents=867)}]:
            with self.assertRaises(ValueError):b.require_unused(records,'teacher_p2_p3',p)

    def test_platform_caps_follow_worker_caps(self):
        tree=ast.parse(Path('experiments/learning_regime_p009/modal_stage0_generation_v2.py').read_text())
        caps={n.name:next(ast.literal_eval(k.value) for d in n.decorator_list if isinstance(d,ast.Call)
              for k in d.keywords if k.arg=='timeout') for n in tree.body
              if isinstance(n,ast.FunctionDef) and n.name in ('teacher_work','qwen_work','olmo_work')}
        self.assertEqual(caps,dict(teacher_work=7260,qwen_work=1860,olmo_work=1860))

    def engine_probe(self,reject=False):
        calls=[];messages=[];model=c.MODELS['teacher']
        conn=SimpleNamespace(send=lambda x:messages.append(x),recv=lambda:('close',None),close=lambda:None)
        config=SimpleNamespace(model_config=SimpleNamespace(hf_config=SimpleNamespace(
            vocab_size=model['vocab_size'],architectures=[model['architecture']],eos_token_id=151645)))
        def params(**kw):
            calls.append('params')
            if reject:raise ValueError('synthetic invalid constructor')
        def llm(**kw):calls.append('model');return SimpleNamespace(llm_engine=SimpleNamespace(vllm_config=config))
        with patch.dict('os.environ',{'VLLM_USE_V1':'1'}), \
             patch.dict(sys.modules,{'vllm':SimpleNamespace(LLM=llm,SamplingParams=params)}), \
             patch.object(engine,'software',return_value={}), \
             patch.object(engine,'actual_engine',return_value={}), \
             patch.object(engine,'load_rows',return_value=[dict(seed=17),dict(seed=29)]):
            if reject:
                with self.assertRaises(ValueError):engine.child(conn,'teacher_p2_p3',dict(model='fixture',tokenizer='fixture',inputs='fixture'))
            else:engine.child(conn,'teacher_p2_p3',dict(model='fixture',tokenizer='fixture',inputs='fixture'))
        return calls,messages

    def test_all_constructor_checks_before_model(self):
        calls,messages=self.engine_probe()
        self.assertEqual(calls,['params']*6+['model'])
        self.assertEqual(messages[0][1]['sampling_constructor_validation']['counts'],
            dict(math_procurement=2,teacher_gsm_zero=2,teacher_math_zero=2))

    def test_bad_constructor_never_loads_model(self):
        calls,messages=self.engine_probe(True);self.assertEqual(calls,['params'])
        self.assertEqual(messages[0][0],'error')

if __name__=='__main__':unittest.main()

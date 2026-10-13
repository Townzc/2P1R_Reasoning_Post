"""New continuation gates/fencing fixtures; no old oracle or provider calls."""
import ast
import copy
import math
from pathlib import Path
import unittest

from experiments.sft_allocation_midpoint.common import digest
from experiments.sft_allocation_midpoint.guard import GuardError, RunGuard
from experiments.sft_allocation_p008.continuation_binding import (
    CAMPAIGN, RUN, PARENT, CHILD_DEADLINE, PROBE,
    validate_continuation_binding, probe_forecast)
from experiments.sft_allocation_p008.continuation_guard import ContinuationActiveCheck
from experiments.sft_allocation_p008.contract import DEADLINE_EPOCH
from tests.test_midpoint_guard import FakeAtomicStore, plan as oldplan, intent


def fixture():
    plan=dict(campaign_id=CAMPAIGN, created_epoch=CHILD_DEADLINE-12000,
              deadline_epoch=CHILD_DEADLINE,total_cap_cents=1200,
              stage_caps_cents={'continuation':1200},
              slots={RUN:dict(stage='continuation',reserved_cents=1200)})
    cfg=dict(run_id=RUN,role='pool_continuation',draw=2,high_multiple=8,
             max_seconds=7200,max_physical_attempts=16384,input_directory='pool_inputs',
             prefix_directory='parent_prefix',input_sha256='a'*64,prefix_manifest_sha256='b'*64)
    original={'synthetic_parent_plan':True};bound={'synthetic_original_intent':True}
    claim=dict(attempt_id='old_attempt',plan_sha256=digest(original),intent_sha256=digest(bound))
    terminal=dict(status='failed');p='midpoint/'+PARENT+'/'
    deps={p+'campaign':original,p+'claim/pool_d2':claim,p+'intent/pool_d2':bound,
          p+'attempt/pool_d2/old_attempt':claim,p+'terminal/pool_d2':terminal,
          p+'terminal/pool_d1':dict(status='completed')}
    owner=dict(draws_retained=2,remaining_only=True,child_deadline_utc='2026-10-13T20:00:00Z',
               worker_cap_seconds=7200,additional_reserved_usd=12,P008_total_reserved_usd=249.68,
               code_and_data_review_required_before_run=True)
    spec=dict(plan_sha256=digest(plan),config_sha256=digest(cfg),source_files={'synthetic.py':'c'*64},
              stage_reserved_cents=24968,prior_reserved_cents=23768,stage_cap_cents=25000,
              project_ceiling_cents=45000,protected_cents=5000,global_deadline_epoch=DEADLINE_EPOCH,
              probe_policy=copy.deepcopy(PROBE),owner_authorization=owner,parent_records=deps,
              reconciliation=dict(physical_attempts=3992,physical_batches=146,returned_tokens=1190193,
                                  physical_raw_unknown=0,parent_terminal=terminal,parent_claim=claim,
                                  pending_wallets=[],unattempted_pending_candidate_ids=[],passed=True))
    release=dict(source_files=spec['source_files'],spec_sha256=digest(spec),gates=dict(
        runtime_review=dict(verdict='PASS',scope='pool-continuation-runtime',review_commit='d'*40,
                            review_report_sha256='e'*64,source_files=spec['source_files'],spec_sha256=digest(spec)),
        upload=dict(passed=True,input_sha256='a'*64,prefix_manifest_sha256='b'*64),parent_provider_released=True))
    return plan,cfg,release,spec


class BindingTests(unittest.TestCase):
    def test_exact_fixture_accepts(self):
        self.assertTrue(validate_continuation_binding(*fixture()))

    def test_scope_limits_cannot_be_rehashed_away(self):
        for field,value in [('max_seconds',7199),('draw',1),('max_physical_attempts',20000),('prefix_directory','other')]:
            p,c,r,s=fixture();c[field]=value;s['config_sha256']=digest(c);r['spec_sha256']=digest(s)
            with self.subTest(field=field),self.assertRaises(ValueError):validate_continuation_binding(p,c,r,s)

    def test_old_or_new_unapproved_deadline_rejected(self):
        for delta in (-10800,3600):
            p,c,r,s=fixture();p['deadline_epoch']+=delta;s['plan_sha256']=digest(p);r['spec_sha256']=digest(s)
            with self.assertRaises(ValueError):validate_continuation_binding(p,c,r,s)

    def test_review_must_cover_exact_worker_not_core(self):
        p,c,r,s=fixture();r['gates']['runtime_review']['scope']='continuation-core'
        with self.assertRaises(ValueError):validate_continuation_binding(p,c,r,s)

    def test_readback_and_release_required(self):
        for key in ('upload','parent_provider_released'):
            p,c,r,s=fixture()
            if key=='upload':r['gates'][key]['prefix_manifest_sha256']='f'*64
            else:r['gates'][key]=False
            with self.assertRaises(ValueError):validate_continuation_binding(p,c,r,s)

    def test_parent_dependency_set_is_exact(self):
        p,c,r,s=fixture();s['parent_records'].pop('midpoint/'+PARENT+'/intent/pool_d2')
        r['spec_sha256']=digest(s);r['gates']['runtime_review']['spec_sha256']=digest(s)
        with self.assertRaises(ValueError):validate_continuation_binding(p,c,r,s)

    def test_unknown_or_pending_parent_is_rejected(self):
        for key,value in [('physical_raw_unknown',1),('pending_wallets',['x']),('unattempted_pending_candidate_ids',['x'])]:
            p,c,r,s=fixture();s['reconciliation'][key]=value;r['spec_sha256']=digest(s)
            r['gates']['runtime_review']['spec_sha256']=digest(s)
            with self.assertRaises(ValueError):validate_continuation_binding(p,c,r,s)


class ProbeTests(unittest.TestCase):
    def test_no_free_speedup_or_dropped_overhead(self):
        r=probe_forecast([.1,.2,.3],7100)
        self.assertAlmostEqual(r['predicted_seconds'],7069.860247199257)
        self.assertTrue(r['passed']);self.assertTrue(r['proxy_not_upper_bound'])

    def test_slowest_sample_and_actual_remaining_time(self):
        r=probe_forecast([.1,2.,.1],7100)
        self.assertFalse(r['passed'])
        self.assertFalse(probe_forecast([.1,.1,.1],7069)['passed'])

    def test_invalid_or_selectively_missing_samples_rejected(self):
        for values in ([.1,.2],[.1,.2,math.nan],[.1,.2,15],[.1,-.2,.1]):
            with self.assertRaises(ValueError):probe_forecast(values,7200)


class FreshParentsTests(unittest.TestCase):
    def setUp(self):
        self.store=FakeAtomicStore();self.g=RunGuard(self.store,oldplan());self.g.register(now_epoch=1000)
        self.a=self.g.admit(intent(),attempt_id='worker',now_epoch=1100,max_runtime_seconds=100)
        self.deps={'original/failed_terminal':{'status':'failed'},'original/claim':{'id':'a'}}
        self.store.records.update(copy.deepcopy(self.deps))
        self.checker=ContinuationActiveCheck(self.g,self.deps,clock=lambda:1101)
        self.addCleanup(self.checker.close)

    def check(self):self.checker.check_active(self.a,spent_cents=0,next_cost_cents=500)

    def test_parent_is_fresh_and_not_cached(self):
        self.check();self.store.records['original/claim']={'id':'b'}
        with self.assertRaisesRegex(GuardError,'dependency changed'):self.check()

    def test_parent_read_failure_fences_forever(self):
        get=self.store.get
        def bad(k):
            if k=='original/failed_terminal':raise OSError('failed transport')
            return get(k)
        self.store.get=bad
        with self.assertRaises(OSError):self.check()
        self.store.get=get
        with self.assertRaisesRegex(GuardError,'cannot be reused'):self.check()

    def test_all_child_and_parent_keys_read_each_time_without_writes(self):
        before=copy.deepcopy(self.store.records);seen=[];get=self.store.get
        self.store.get=lambda k:(seen.append(k),get(k))[1]
        self.check();self.check()
        self.assertEqual(before,self.store.records)
        self.assertEqual(seen.count('original/claim'),2)
        self.assertEqual(len(seen),2*(4+len(self.g.plan['slots'])+len(self.deps)))

    def test_child_terminal_and_clock_still_enforced(self):
        self.check();self.g.finish(self.a,status='completed',evidence_sha256='f'*64,actual_cost_cents=500,finished_epoch=1102)
        with self.assertRaises(GuardError):self.check()


class NoDispatchTests(unittest.TestCase):
    def test_worker_timer_starts_before_binding_and_model(self):
        tree=ast.parse(Path('experiments/sft_allocation_p008/modal_pool_continuation.py').read_text())
        work=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='work')
        text=ast.unparse(work)
        self.assertLess(text.index('timer.start()'),text.index('validate_continuation_binding(plan'))
        self.assertLess(text.index("if not measurement['passed']"),text.index('result = run('))
        self.assertIn('7200 + 700',ast.unparse(tree))
        self.assertIn('retries=0',ast.unparse(tree))


if __name__=='__main__':unittest.main()

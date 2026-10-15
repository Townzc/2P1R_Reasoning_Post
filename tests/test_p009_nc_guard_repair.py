"""New real-RunGuard integration plus synthetic repair admission boundaries.

New proxy/review objects are test-only and are never saved as acceptances.
No provider/model/scorer/state loading or old test suite is invoked.
"""
import ast
import copy
import time
import unittest
import uuid
from pathlib import Path
from experiments.sft_allocation_midpoint.common import read,digest
from experiments.sft_allocation_midpoint.guard import RunGuard,GuardError
from experiments.learning_regime_p009 import stage1_nc_guard_repair_binding as b

ROOT=Path('.local/p009_20261014/r1')


class Store(dict):
    def put(self,key,value,skip_if_exists=False):
        if skip_if_exists and key in self:return False
        self[key]=copy.deepcopy(value);return True


def fixture():
    s=read(ROOT/'stage1_nc_guard_repair_candidate_r1/ADMISSION_DRAFT.json')
    p=read(ROOT/'stage1_nc_guard_repair_candidate_r1/PLAN.json')
    original=read(ROOT/'stage1_nc_replacement_r1/runs'/b.RUN/'dispatch_intent.json')['release']
    c=dict(id=1,user=dict(login='Townzc'),author_association='OWNER',created_at='2026-10-15T06:24:00Z',
        html_url='https://github.com/Townzc/2P1R_Reasoning_Post/issues/13#issuecomment-1',
        body='【Owner 代理决定】 '+b.REQUEST+' SYNTHETIC TEST ONLY. Approve one bounded repair because the original call made no claim or scientific updates; retain all original fences, science, caps and independent audit.')
    d=dict(comment=c,decision='APPROVE_ONE_REPAIR',spec_sha256=digest(s),comment_sha256=digest(c),
        raw_comment_file_sha256='1'*64,single_new_call=True,new_reserved_cents=655,science_and_decision_rules_unchanged=True)
    rev=dict(scope=b.SCOPE,source_files=s['source_files'],spec_sha256=digest(s),timing_sha256=digest(s['timing']),
        preclaim_proof_file_sha256=s['preclaim_proof_file_sha256'],preclaim_manifest_file_sha256=s['preclaim_manifest_file_sha256'],
        owner_authority_file_sha256=s['overnight_authority_file_sha256'],owner_proxy_comment_sha256=digest(c),
        original_guard_four_field_schema=True,original_fences_and_failed_parents_retained=True,
        no_prior_replacement_training_or_endpoint=True,one_new_entry_call_only=True,
        prior_stage1_reserved_cents=1965,new_reserved_cents=655,first_paid_measurement_exceptions=0,
        decision='PASS',target_commit='a'*40,report_commit='b'*40,report_sha256='c'*64)
    rel=dict(original_replacement_release=original,source_files=s['source_files'],input_readback=s['inputs'],
        owner_proxy_decision=d,runtime_review=rev,review_target='a'*40,
        budget=dict(stage1_prior_reserved_cents=1965,new_reserved_cents=655,stage1_cap_cents=5000,
            experiment_cap_cents=13000,project_prior_upper_cents=26610))
    return s,p,rel


class RealGuardIntegration(unittest.TestCase):
    def setUp(self):self.s,self.p,self.r=fixture();self.db=Store();self.g=RunGuard(self.db,self.p);self.now=self.p['created_epoch']+1;self.g.register(now_epoch=self.now)
    def test_reproduces_original_error_without_claim(self):
        with self.assertRaisesRegex(GuardError,'invalid intent fields'):
            self.g.admit(b.old.intent(self.s['original_replacement_spec'],b.RUN),attempt_id='legacy',now_epoch=self.now,max_runtime_seconds=4500)
        self.assertEqual(set(self.db),{'midpoint/'+b.CAMPAIGN+'/campaign'})
    def test_real_guard_accepts_exact_four_fields_and_refuses_replay(self):
        i=b.intent(self.s,b.RUN);self.assertEqual(set(i),{'run_id','config_sha256','source_sha256','data_sha256'})
        claim=self.g.admit(i,attempt_id='new',now_epoch=self.now,max_runtime_seconds=4500)
        self.assertEqual(claim.run_id,b.RUN)
        with self.assertRaisesRegex(GuardError,'already claimed'):
            self.g.admit(i,attempt_id='again',now_epoch=self.now,max_runtime_seconds=4500)
    def test_actual_new_worker_claim_statements_use_real_guard(self):
        tree=ast.parse(Path('experiments/learning_regime_p009/modal_stage1_nc_guard_repair.py').read_text())
        work=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='work')
        body=next(x for x in work.body if isinstance(x,ast.Try)).body
        selected=[]
        for node in body:
            if isinstance(node,ast.Assign) and any(isinstance(x,ast.Name) and x.id in ('guard','claim') for x in node.targets):selected.append(node)
            elif isinstance(node,ast.Expr) and isinstance(node.value,ast.Call) and isinstance(node.value.func,ast.Attribute) and isinstance(node.value.func.value,ast.Name) and node.value.func.value.id=='guard':selected.append(node)
        self.assertEqual(len(selected),3)
        env=dict(RunGuard=RunGuard,store=Store(),plan=self.p,intent=b.intent,spec=self.s,run=b.RUN,uuid=uuid,time=time,stop=time.time()+4500)
        exec(compile(ast.fix_missing_locations(ast.Module(body=selected,type_ignores=[])),'actual_worker_claim_fragment','exec'),env)
        self.assertEqual(env['claim'].run_id,b.RUN)
        self.assertEqual(len(env['store']),4)
    def test_parent_and_owner_fields_retained_outside_guard_intent(self):
        self.assertEqual(self.s['original_dispatch_marker']['owner_exception_sha256'],b.old.OWNER_FILE_SHA)
        terminal='midpoint/'+b.old.PARENT_CAMPAIGN+'/terminal/'+b.old.PARENT_RUN
        self.assertEqual(self.s['required_records'][terminal]['status'],'failed')
        self.assertIn('preclaim_proof',self.s)


class RepairAdmission(unittest.TestCase):
    def setUp(self):self.s,self.p,self.r=fixture()
    def check(self):return b.validate(self.s,self.p,b.RUN,self.r)
    def test_exact_synthetic_new_binding(self):self.assertEqual(self.check()['targets'],2097148)
    def test_no_proxy_or_wrong_author(self):
        self.r['owner_proxy_decision']['comment']['user']['login']='other'
        with self.assertRaises(ValueError):self.check()
    def test_expired_proxy_comment_refused(self):
        self.r['owner_proxy_decision']['comment']['created_at']='2026-10-15T14:00:00Z'
        with self.assertRaises(ValueError):self.check()
    def test_proxy_cannot_waive_exact_audit(self):
        self.r['runtime_review']=self.r['original_replacement_release']['runtime_review']
        with self.assertRaises(ValueError):self.check()
    def test_prior_claim_or_false_zero_work_refused(self):
        self.s['preclaim_proof']['claim']=True
        with self.assertRaises(ValueError):self.check()
    def test_original_source_immutable(self):
        self.s['source_files']['experiments/sft_allocation_midpoint/guard.py']='f'*64
        with self.assertRaises(ValueError):self.check()
    def test_no_automatic_reservation_release(self):
        self.r['budget']['stage1_prior_reserved_cents']=1310
        with self.assertRaises(ValueError):self.check()
    def test_new_fences_are_distinct_and_permanent(self):
        records={k:v for k,v in self.s['preclaim_records'].items() if k.startswith('midpoint/'+b.CAMPAIGN+'/')}
        logical={k:v for k,v in self.s['required_records'].items() if k.startswith('midpoint/p009-stage1-logical/')}
        b.require_unused(records,b.RUN,self.p,logical,self.s)
        with self.assertRaises(ValueError):b.require_unused({**records,b.dispatch_key(b.RUN):{}},b.RUN,self.p,logical,self.s)
        with self.assertRaises(ValueError):b.require_unused(records,b.RUN,self.p,{**logical,b.logical_key(b.RUN):{}},self.s)
    def test_full_oracle_scientific_body_unchanged(self):
        def funcs(path):
            s=Path(path).read_text().replace('p009_stage1_NC_guard_repair_full_oracle_v1','p009_stage1_NC_replacement_full_oracle_v1')
            return [ast.dump(n,include_attributes=False) for n in ast.parse(s).body if isinstance(n,ast.FunctionDef)]
        self.assertEqual(funcs('scripts/audit_p009_stage1_nc_guard_repair.py'),funcs('scripts/audit_p009_stage1_nc_replacement.py'))


if __name__=='__main__':unittest.main()

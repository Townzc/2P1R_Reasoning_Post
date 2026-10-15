"""New replacement boundaries; synthetic reviews, no provider/model/state/scoring."""
import ast
import copy
import unittest
from pathlib import Path
from experiments.sft_allocation_midpoint.common import read,digest
from experiments.learning_regime_p009 import stage1_nc_replacement_binding as b
from experiments.learning_regime_p009.stage1_nc_replacement_contract import *

ROOT=Path('.local/p009_20261014/r1')


def fixture():
    spec=read(ROOT/'stage1_nc_replacement_candidate_r1/ADMISSION_DRAFT.json')
    plan=read(ROOT/'stage1_nc_replacement_candidate_r1/PLAN.json')
    review=dict(scope=SCOPE,source_files=spec['source_files'],spec_sha256=digest(spec),
        timing_sha256=digest(spec['timing']),owner_authority_file_sha256=OWNER_FILE_SHA,
        parent_packet_target=PARENT_TARGET,parent_packet_manifest_sha256=PARENT_MANIFEST_SHA,
        parent_preservation_file_sha256=PARENT_PRESERVED_SHA,
        input_basis_file_sha256=spec['input_basis_file_sha256'],input_archive_file_sha256=spec['input_archive_file_sha256'],
        all_20_training_hosts_included=True,failed_parent_interval_retained_as_proxy=True,
        uncalibrated_timing_proxy_scope_accepted=True,training_process_exit_before_vllm=True,
        new_reserved_cents=655,prior_stage1_reserved_cents=1310,first_paid_measurement_exceptions=0,
        independent_failed_parent_replacement_accepted=True,decision='PASS',target_commit='a'*40,
        report_commit='b'*40,report_sha256='c'*64)
    parent=dict(scope=PARENT_SCOPE,target_commit=PARENT_TARGET,decision='PASS',actual_n400_integrity='PASS',
        failed_n3200_preservation='PASS',paired_NC_gate_available=False,S1_admitted=False,
        parent_manifest_sha256=PARENT_MANIFEST_SHA,failed_preservation_sha256=PARENT_PRESERVED_SHA,
        nc400_state_sha256=NC400_STATE_SHA,report_commit='d'*40,report_sha256='e'*64)
    release=dict(original_release=read(ROOT/'stage1_nc_r1/runs/nc_s17_n3200/dispatch_intent.json')['release'],
        source_files=spec['source_files'],input_readback=spec['inputs'],runtime_review=review,
        parent_disposition_review=parent,review_target='a'*40,
        budget=dict(stage1_prior_reserved_cents=1310,new_reserved_cents=655,stage1_cap_cents=5000,
                    experiment_cap_cents=13000,project_prior_upper_cents=26230))
    return spec,plan,release


class NewReplacementAdmission(unittest.TestCase):
    def setUp(self):self.s,self.p,self.r=fixture()
    def check(self):return b.validate(self.s,self.p,RUN,self.r)
    def test_actual_schema_with_synthetic_review(self):self.assertEqual(self.check()['targets'],2097148)
    def test_failed_parent_cannot_be_relabelled(self):
        self.s['original_NC_records']['midpoint/'+PARENT_CAMPAIGN+'/terminal/'+PARENT_RUN]['status']='completed'
        with self.assertRaises(ValueError):self.check()
    def test_no_owner_scope_broadening(self):
        self.s['owner_authority']['independent_calls']=2
        with self.assertRaises(ValueError):self.check()
    def test_no_original_source_change(self):
        self.s['source_files']['experiments/learning_regime_p009/stage1_training_core.py']='0'*64
        with self.assertRaises(ValueError):self.check()
    def test_no_original_claim_reuse(self):
        with self.assertRaises(ValueError):b.validate(self.s,self.p,PARENT_RUN,self.r)
    def test_exact_new_review_not_old_acceptance(self):
        self.r['runtime_review']=self.r['original_release']['runtime_review']
        with self.assertRaises(ValueError):self.check()
    def test_actual_failed_parent_outcome_review_required(self):
        self.r['parent_disposition_review']['failed_n3200_preservation']='PENDING'
        with self.assertRaises(ValueError):self.check()
    def test_no_failure_reservation_release(self):
        self.r['budget']['stage1_prior_reserved_cents']=655
        with self.assertRaises(ValueError):self.check()
    def test_no_endpoint_or_dose_change(self):
        self.s['configs'][RUN]['targets']=2097152
        with self.assertRaises(ValueError):self.check()
    def test_failed_last_proxy_not_dropped(self):
        self.s['timing']['training_block_seconds'].pop()
        with self.assertRaises(ValueError):self.check()
    def test_complete_fresh_slot_and_permanent_partial_fences(self):
        logical={'midpoint/p009-stage1-logical/'+x+'/dispatch':{'provider_app_id':'original-'+x} for x in (PARENT_RUN,ORIGINAL_NC400)}
        b.require_unused({},RUN,self.p,logical)
        b.require_unused({'midpoint/'+CAMPAIGN+'/campaign':self.p},RUN,self.p,logical)
        with self.assertRaises(ValueError):b.require_unused({b.dispatch_key(RUN):{}},RUN,self.p,logical)
        with self.assertRaises(ValueError):b.require_unused({},RUN,self.p,{**logical,b.logical_key(RUN):{}})
        with self.assertRaises(ValueError):b.require_unused({},RUN,self.p,{**logical,'midpoint/p009-stage1-logical/unknown':{}})
    def test_parent_fence_key_is_distinct(self):
        self.assertNotEqual(b.logical_key(RUN),'midpoint/p009-stage1-logical/'+PARENT_RUN+'/dispatch')
        self.r.update(dispatch_app_id='new-app',execution_commit='f'*40)
        self.assertTrue(b.marker(self.s,RUN,self.r)['failed_parent_stays_failed'])


class ScientificBodyUnchanged(unittest.TestCase):
    def same(self,old,new,replace=()):
        a=Path(old).read_text();c=Path(new).read_text()
        for x,y in replace:c=c.replace(x,y)
        def nodes(s):return [ast.dump(n,include_attributes=False) for n in ast.parse(s).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))]
        self.assertEqual(nodes(a),nodes(c))
    def test_original_training_body(self):
        self.same('experiments/learning_regime_p009/stage1_nc_training_process.py','experiments/learning_regime_p009/stage1_nc_replacement_training_process.py')
    def test_original_runtime_body(self):
        self.same('experiments/learning_regime_p009/stage1_nc_runtime.py','experiments/learning_regime_p009/stage1_nc_replacement_runtime.py', [('stage1_nc_replacement_training_process','stage1_nc_training_process')])
    def test_full_state_raw_oracle_body(self):
        self.same('scripts/audit_p009_stage1_nc.py','scripts/audit_p009_stage1_nc_replacement.py',[('p009_stage1_NC_replacement_full_oracle_v1','p009_stage1_NC_full_oracle_v1')])
    def test_whole_worker_timer_and_claim_body(self):
        def worker(path):
            t=Path(path).read_text().replace('stage1_nc_replacement_binding','stage1_nc_binding').replace('stage1_nc_replacement_runtime','stage1_nc_runtime')
            return ast.dump(next(n for n in ast.parse(t).body if isinstance(n,ast.FunctionDef) and n.name=='work'),include_attributes=False)
        self.assertEqual(worker('experiments/learning_regime_p009/modal_stage1_nc.py'),worker('experiments/learning_regime_p009/modal_stage1_nc_replacement.py'))


if __name__=='__main__':unittest.main()

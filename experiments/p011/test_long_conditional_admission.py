"""Only new conditional-admission behavior; no old science/test invocation."""
import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from experiments.p011 import long_conditional_path as p
from experiments.sft_allocation_midpoint.common import read, sha, digest


class ConditionalAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.root=Path(__file__).resolve().parents[2]
        self.old=read(self.root/p.ORIGINAL_SPEC)
        self.spec=copy.deepcopy(self.old)
        self.spec['jobs']={k:self.old['jobs'][k] for k in p.INITIAL_JOBS}
        self.spec.update(original_numeric_decision='PASS-WITH-CONDITIONS',initial_allowed_jobs=list(p.INITIAL_JOBS),conditional_evidence_files={n:sha(self.root/n) for n in (p.ORIGINAL_SPEC,p.DISPOSITION,p.F15_PROOF)})

    def test_original_conditional_scope_is_honest(self):
        self.assertEqual(p.conditional_evidence(self.spec,self.root)['jobs'],self.old['jobs'])
        self.spec['original_numeric_decision']='PASS'
        with self.assertRaises(ValueError):p.conditional_evidence(self.spec,self.root)

    def test_cancelled_L3_cannot_be_restored(self):
        k='long_A7_S-L3_s17_r1';self.spec['jobs'][k]=self.old['jobs'][k]
        with self.assertRaises(ValueError):p.conditional_evidence(self.spec,self.root)

    def test_original_job_dose_cannot_change(self):
        self.spec['jobs']=copy.deepcopy(self.spec['jobs']);self.spec['jobs'][p.INITIAL_JOBS[0]]['B']+=1
        with self.assertRaises(ValueError):p.conditional_evidence(self.spec,self.root)

    def test_original_source_cannot_change(self):
        self.spec['source_files']['experiments/p011/long_training.py']='0'*64
        with self.assertRaises(ValueError):p.conditional_evidence(self.spec,self.root)

    def test_F15_proof_condition_is_enforced(self):
        self.spec['conditional_evidence_files'][p.F15_PROOF]='0'*64
        with self.assertRaises(ValueError):p.conditional_evidence(self.spec,self.root)

    def test_only_initial_ids_bypass_later_selection(self):
        for k in p.INITIAL_JOBS:self.assertIsNone(p.selection(self.old['jobs'][k],None))
        for k in ('long_A1_S-L15_s17_r1','long_A7_S-L3_s17_r1'):
            with self.assertRaises(ValueError):p.selection(self.old['jobs'][k],None)

    def test_old_three_smoke_flag_cannot_replace_reduced_actual_A3(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'review.md';f.write_text('new actual selection test fixture')
            v=dict(decision='PASS',target_commit='a'*40,report_sha256=sha(f),local_report_path=str(f),scope='p011-long-reduced-smoke-student-selection',selection_rule_unchanged=True,conditional_disposition_sha256=p.DISPOSITION_SHA,chosen_arm='S-L15',allowed_logical_ids=['long_A1_S-L15_s17_r1'],all_three_smokes_and_two_baselines_A3_accepted=True,mandatory_order_and_budget_feasibility_explicitly_decided=True)
            job=self.old['jobs']['long_A1_S-L15_s17_r1']
            with self.assertRaises(ValueError):p.selection(job,v)
            v['both_retained_smokes_and_single_baseline_A3_accepted']=True
            self.assertEqual(p.selection(job,v)['chosen_arm'],'S-L15')

    def test_D_requires_explicit_both_or_none_feasibility(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'review.md';f.write_text('new D selection test fixture');job=self.old['jobs']['long_D1_S-F15_s17_r1']
            v=dict(decision='PASS',target_commit='a'*40,report_sha256=sha(f),local_report_path=str(f),scope='p011-long-reduced-smoke-student-selection',selection_rule_unchanged=True,conditional_disposition_sha256=p.DISPOSITION_SHA,chosen_arm='S-F15',allowed_logical_ids=[p.logical(job)],both_retained_smokes_and_single_baseline_A3_accepted=True,mandatory_order_and_budget_feasibility_explicitly_decided=True)
            with self.assertRaises(ValueError):p.selection(job,v)
            v['D_both_or_none_feasibility_accepted']=True
            self.assertEqual(p.selection(job,v)['chosen_arm'],'S-F15')

    def test_conditional_report_does_not_masquerade_as_new_source_PASS(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'review.md';f.write_text('conditional original fixture')
            v=dict(decision='PASS-WITH-CONDITIONS',target_commit='a'*40,report_sha256=sha(f),local_report_path=str(f))
            with patch.object(p,'validate',return_value=self.spec):
                with self.assertRaises(ValueError):p.reviewed(self.spec,f,v)


if __name__=='__main__':unittest.main()

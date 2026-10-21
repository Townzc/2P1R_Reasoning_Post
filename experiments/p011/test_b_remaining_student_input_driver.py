"""New driver authorization/identity tests only; no encoder or model calls."""
import copy,importlib.util,tempfile,unittest
from pathlib import Path
from experiments.sft_allocation_midpoint.common import dump,sha,digest

f=Path(__file__).resolve().parents[2]/'scripts/prepare_p011_b_remaining_student_inputs.py'
s=importlib.util.spec_from_file_location('new_B_remaining_input_driver',f)
driver=importlib.util.module_from_spec(s);s.loader.exec_module(driver)

class StudentInputDriverTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        generation='B_generation_t10_400x16_r2_continuation';io=self.root/driver.inputs.LOCAL/'b_remaining_io_r2'
        self.rows={'one':{'fake':'record'}};self.selection={'fake':'selection'}
        self.proof={'passed':True,'endpoint':{'technical_unknown':0,'outputs':6400}}
        self.done={'read_only_saved_score_proof':{'passed':True},'records_sha256':digest(self.rows),'selection_sha256':digest(self.selection)}
        evidence={}
        for folder,name,obj in [('audit','COMPLETE_PROOF.json',self.proof),('score','COMPLETED.json',self.done),('score','RECORDS.json',self.rows),('score','SELECTION.json',self.selection)]:
            p=io/folder/generation/name;dump(p,obj);evidence[str(p.relative_to(self.root))]=sha(p)
        self.report=self.root/'actual_report.md';self.report.write_text('Synthetic actual reviewer report')
        self.review=dict(decision='PASS',target_commit='b'*40,report_sha256=sha(self.report),local_report_path=str(self.report),scope='p011-B-complete6400-generation-and-selection-actual-A3',complete_result_evidence_files=evidence,original_generation_report_sha256='0c1a9a1fc335381bdcabe78037e6bc3ca45d0ae922e8ea6f1879cbceb4e1d7ac',independent_original_token_decode_and_correctness_checks_accepted=True,all6400_outputs_and_unmapped_exclusions_accepted=True,actual_selection_and_Pcov_accepted=True)

    def check(self):return driver.actual_generation_A3(self.root,self.proof,self.done,self.rows,self.selection,self.review)

    def test_exact_actual_result_binding_accepted(self):
        self.assertEqual(self.check(),self.review['complete_result_evidence_files'])

    def test_source_PASS_cannot_substitute_actual_A3(self):
        self.review['scope']='p011-B-remaining-generation-selection-complete-path-CR'
        with self.assertRaises(ValueError):self.check()

    def test_missing_independent_replay_not_accepted(self):
        self.review['independent_original_token_decode_and_correctness_checks_accepted']=False
        with self.assertRaises(ValueError):self.check()

    def test_changed_saved_file_blocks(self):
        p=self.root/next(iter(self.review['complete_result_evidence_files']));p.write_text('{}')
        with self.assertRaises(ValueError):self.check()

    def test_partial_output_count_blocks(self):
        self.proof['endpoint']['outputs']=6399
        with self.assertRaises(ValueError):self.check()

    def test_changed_records_are_not_rescored_or_accepted(self):
        self.rows['another']={}
        with self.assertRaises(ValueError):self.check()


if __name__=='__main__':unittest.main()

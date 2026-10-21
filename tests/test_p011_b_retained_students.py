"""New retained-student admission/asset integration checks; synthetic inputs only."""
import copy
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from experiments.p011 import b_students_path as path
from scripts import p011_b_students_io as io
from experiments.sft_allocation_midpoint.common import dump, read, sha, digest
from tests.test_p011_b_full_path import spec as synthetic_spec, Store


def candidate():
    value=synthetic_spec('student');value['jobs'].pop('B_B2_s17_r1')
    value.update(budget_owner_decision_sha256=path.BUDGET_OWNER_SHA,
        prior_failed_C1={'files':{'fixture':'only'}},failed_attempt_bindings={'Bfailed':'fixture'},
        generation_actual_A3_report_sha256='1'*64,student_input_CR_report_sha256='2'*64,
        student_input_manifest_sha256='3'*64)
    for job in value['jobs'].values():
        job['resources']={'gpu':'H100','cpu':4,'memory_mib':32768}
        job['resource_rates_usd_per_hour']={'H100':'3.95','cpu_core':'.04730','GiB':'.008'}
        job['limits'].update(worker_seconds=4400,platform_seconds=4460,startup_seconds=600,
            closeout_seconds=32405,score_seconds=25200,full_result_window_seconds=37465,
            hourly_rate_usd='4.39520',reserved_usd='6.18')
    return value


class RetainedStudentChecks(unittest.TestCase):
    def test_retained_identity_and_actual_result_bindings_are_required(self):
        value=candidate();self.assertIs(path.validate(value),value)
        for name in ('B_generation_t10_400x16_r1','B_B2_s17_r1'):
            with self.assertRaises(ValueError):path.phase_for_job(name)
        for name in ('generation_actual_A3_report_sha256','student_input_CR_report_sha256','student_input_manifest_sha256'):
            changed=copy.deepcopy(value);changed[name]='pending'
            with self.assertRaises(ValueError):path.validate(changed)
        changed=copy.deepcopy(value);changed['jobs']['B_B2_s17_r1']=changed['jobs']['B_B1_s17_r1']
        with self.assertRaises(ValueError):path.validate(changed)

    def test_whole_pair_budget_rejects_second_student_overrun_before_first(self):
        value=candidate();steps=path.remaining_student_budget(value,[],'6.02')
        self.assertEqual([x['prior_B_reserved_usd'] for x in steps],['6.02','12.20'])
        value['jobs']['B_B3_s17_r1']['limits']['reserved_usd']='6.25'
        with self.assertRaises(ValueError):path.remaining_student_budget(value,[],'6.02')

    def test_failed_first_student_is_not_released_or_replayed(self):
        value=candidate();records=[{'logical_id':'B_B1_s17_r1','status':'failed'}]
        steps=path.remaining_student_budget(value,records,'12.20')
        self.assertEqual([x['logical_id'] for x in steps],['B_B3_s17_r1'])
        self.assertEqual(steps[0]['prior_B_reserved_usd'],'12.20')
        with self.assertRaises(ValueError):path.remaining_student_budget(value,records,'12.28')

    def test_bad_original_asset_receipt_blocks_before_new_input_or_provider(self):
        with tempfile.TemporaryDirectory(dir='.local/p011_20261020/r1') as directory:
            root=Path(directory);job=candidate()['jobs']['B_B1_s17_r1']
            with patch.object(io,'original_asset_receipt',side_effect=ValueError('bad receipt')),patch.object(io,'verify') as verify,patch.object(io,'transfer') as transfer:
                with self.assertRaises(ValueError):io.upload(root,root/'out',candidate(),job,{})
                verify.assert_not_called();transfer.assert_not_called()
            self.assertFalse((root/'out').exists())

    def test_upload_reads_only_new_input_and_reuses_exact_original_model_receipt(self):
        with tempfile.TemporaryDirectory(dir='.local/p011_20261020/r1') as directory:
            root=Path(directory);value=candidate();job=value['jobs']['B_B1_s17_r1']
            prior={'status':'completed','model_revision':job['model']['revision'],
                   'files':{'model/'+n:m for n,m in job['model']['files'].items()}}
            dump(root/path.ASSET_RECEIPT,prior)
            store=Store();volume=Mock();fake=types.SimpleNamespace(
                Dict=types.SimpleNamespace(from_name=lambda *a,**k:store),
                Volume=types.SimpleNamespace(from_name=lambda *a,**k:volume))
            out=root/'out';out.mkdir()
            with patch.object(path,'ASSET_RECEIPT_SHA',sha(root/path.ASSET_RECEIPT)),patch.object(io,'verify') as verify,patch.object(io,'transfer') as transfer,patch.dict('sys.modules',{'modal':fake}):
                io.upload(root,out,value,job,{})
                self.assertEqual(transfer.call_count,1)
                self.assertEqual(transfer.call_args.args[1],path.local_inputs(root,job))
                self.assertEqual(transfer.call_args.args[3],job['input_files'])
                verify.assert_called_once_with(path.local_inputs(root,job),job['local_input_files'])
                volume.read_file.assert_not_called()
                self.assertTrue(read(out/'COMPLETED.json')['old_model_assets_not_transferred_or_read_back_again'])

    def test_missing_failed_parent_blocks_before_observation_or_spawn(self):
        with tempfile.TemporaryDirectory(dir='.local/p011_20261020/r1') as directory:
            root=Path(directory);value=candidate();name='B_B1_s17_r1';job=value['jobs'][name]
            dump(root/path.LOCAL/'b_io_r1/upload'/name/'COMPLETED.json',{'job_sha256':digest(job),'all_remote_file_bytes_read_back':True})
            report=root/'report';report.write_text('fixture')
            dump(root/'review.json',{'local_report_path':str(report),'report_sha256':sha(report)});dump(root/'budget.json',{})
            worker,observation=Mock(),Mock()
            with patch.object(path,'reviewed',return_value={}),patch.object(path.failed_attempt_ledger,'ledger',side_effect=ValueError('failed parent unbound')):
                with self.assertRaises(ValueError):path.submit(root,value,name,root/'review.json',root/'budget.json',Store(),worker,'ap-fixture',publication=lambda *a:'f'*40,observation=observation)
            observation.assert_not_called();worker.spawn.assert_not_called()

    def test_closeout_and_score_cannot_reset_original_worker_deadline(self):
        job=candidate()['jobs']['B_B1_s17_r1'];start=1792580000.;receipt={'worker_start_epoch':start}
        for mode in ('collect','audit','score'):
            _,end=io.window(mode,job,start+4401,receipt)
            self.assertEqual(end,start+4400+32405)
        with self.assertRaises(TimeoutError):io.window('score',job,start+11601,receipt)


if __name__=='__main__':unittest.main()

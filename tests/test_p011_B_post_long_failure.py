"""New failed-parent and existing-upload admission checks; no old tests rerun."""
import ast,copy,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
from tests.test_p011_b_retained_students import candidate
from tests.test_p011_b_full_path import Store
from experiments.p011 import b_students_post_long_failure_path as path
from experiments.sft_allocation_midpoint.common import dump,sha,digest

def spec():
    s=candidate()
    for n,r in [('long_A7_S-F15_s17_r2','15.63'),('long_baseline_S-L15_s17_r2','12.17')]:s['failed_attempt_bindings'][n]={'category':'A','reserved_usd':r}
    s['prior_B1_input_upload']={'path':str(Path(path.LOCAL)/'b_io_r1/upload/B_B1_s17_r1/COMPLETED.json'),'sha256':'a'*64}
    s['prior_actual_B_input_numeric_report_sha256']='acea0550f12e6600557ccc65b5d0f6ac337a2421e2a5b0331a016aae7121fa18'
    return s

class NewBindingChecks(unittest.TestCase):
    def test_new_failures_cannot_be_omitted_or_released(self):
        value=spec();self.assertIs(path.validate(value),value)
        for name in ('long_A7_S-F15_s17_r2','long_baseline_S-L15_s17_r2'):
            v=copy.deepcopy(value);v['failed_attempt_bindings'].pop(name)
            with self.assertRaises(ValueError):path.validate(v)
            v=copy.deepcopy(value);v['failed_attempt_bindings'][name]['reserved_usd']='0'
            with self.assertRaises(ValueError):path.validate(v)
    def test_upload_receipt_reuse_is_exact_and_rejects_changed_evidence(self):
        with tempfile.TemporaryDirectory(dir='.local/p011_20261020/r1') as tmp:
            root=Path(tmp);s=spec();p=root/s['prior_B1_input_upload']['path'];d={'job_sha256':digest(s['jobs']['B_B1_s17_r1']),'all_remote_file_bytes_read_back':True,'model_calls':0,'original_base_asset_receipt_sha256':path.ASSET_RECEIPT_SHA,'old_model_assets_not_transferred_or_read_back_again':True};dump(p,d);s['prior_B1_input_upload']['sha256']=sha(p)
            self.assertEqual(path.prior_B1_upload(s,root),d)
            p.write_text(p.read_text()+' ')
            with self.assertRaises(ValueError):path.prior_B1_upload(s,root)
    def test_changed_receipt_blocks_before_provider_or_spawn(self):
        with tempfile.TemporaryDirectory(dir='.local/p011_20261020/r1') as tmp:
            root=Path(tmp);s=spec();dump(root/'review.json',{});worker=Mock();observe=Mock()
            with patch.object(path,'reviewed',return_value={}),patch.object(path,'prior_B1_upload',side_effect=ValueError('changed evidence')):
                with self.assertRaises(ValueError):path.submit(root,s,'B_B1_s17_r1',root/'review.json',root/'unused_budget.json',Store(),worker,'ap-fixture',publication=lambda *a:'f'*40,observation=observe)
            observe.assert_not_called();worker.spawn.assert_not_called();self.assertFalse((root/path.LOCAL/'dispatch/B_B1_s17_r1').exists())
    def test_science_budget_window_and_worker_functions_remain_identical(self):
        def funcs(p):return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(Path(p).read_text()).body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
        a=funcs('experiments/p011/b_students_path.py');b=funcs('experiments/p011/b_students_post_long_failure_path.py')
        for name in a:
            if name not in ('validate','reviewed','submit'):self.assertEqual(a[name],b[name],name)
    def test_new_entry_and_io_use_same_exact_new_source(self):
        for n in ('experiments/p011/modal_b_students_post_long_failure.py','scripts/p011_b_students_post_long_failure_io.py','scripts/analyze_p011_b_students_post_long_failure.py'):
            t=Path(n).read_text();self.assertIn('b_students_post_long_failure_path as ',t);self.assertNotIn('b_students_path as ',t)
        self.assertEqual(path.SPEC_FILES,{'student':'reports/p011_20261020/b_students_post_long_failure_runtime_v1/SPEC.json'})

if __name__=='__main__':unittest.main()

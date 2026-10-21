"""Additional new r2 admission checks, with no corpus or provider access."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from tests.test_p011_c1_r2 import spec
from tests.test_p011_c1_execution_draft import Store
from experiments.p011.c1_r2 import admission as a, execution as c, outer
from experiments.sft_allocation_midpoint.common import dump, read, sha, digest
from scripts.p011_c1_r2_io import remaining_io_seconds


class AdmissionTests(unittest.TestCase):
    def budget(self, root):
        dump(root/'evidence.json', {'synthetic':True})
        records=[{'logical_id':'C1_original_token_base_forward_r1','app_id':'ap-original',
                  'budget':{'category':'C','new_reserved_usd':'3.74'}}]
        b={'observed_epoch':1792565000.,'all_attempted_reservations_usd':{
            'A':'0','B':'0','C':'3.74','D':'0','emergency':'0'},
            'cap_usd':'12','category':'C','overall_cap_usd':'180','protected_usd':'0',
            'budget_owner_decision_sha256':c.BUDGET_OWNER_SHA,'reserve_release_used':False,
            'owner_estimate_used_as_balance':False,
            'availability_basis':'owner_current_balance_minus_retained_P011_reserves_and_meter_growth',
            'source_evidence_files':{'evidence.json':sha(root/'evidence.json')},
            'available_after_retained_prior_reserves_usd':'10','observed_gross_resource_usd':'1',
            'usd_per_second':spec()['limits']['usd_per_second']}
        return b,records

    def test_fresh_budget_owner_scope_failed_reserve_slots_and_staleness(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);b,records=self.budget(root);s=spec();states={'ap-original':'stopped'}
            result=a.fresh_budget(s,b,records,[],states,1792565000.,root)
            self.assertEqual(result['prior_reserved_usd'],'3.74')
            self.assertEqual(result['protected_usd'],'0')
            for key,value in [('protected_usd','48'),('budget_owner_decision_sha256','0'*64),
                              ('availability_basis','old_prior_obligations'),
                              ('available_after_retained_prior_reserves_usd','2')]:
                bad=deepcopy(b);bad[key]=value
                with self.assertRaises(ValueError):a.fresh_budget(s,bad,records,[],states,1792565000.,root)
            with self.assertRaises(ValueError):a.fresh_budget(s,b,records,[],states,1792568601.,root)
            with self.assertRaises(ValueError):a.fresh_budget(s,b,records,[{'app_id':'ap-unmatched'}]*4,states,1792565000.,root)

    def test_exact_new_review_requires_both_owners_and_parent_upload(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);s=spec();s.update(input_files={'original':'a'},original_group_binding_sha256='b'*64)
            dump(root/'spec.json',s);(root/'report.md').write_text('Synthetic exact report')
            review={'scope':a.SCOPE,'decision':'PASS','target_commit':'a'*40,
                'report_sha256':sha(root/'report.md'),'local_report_path':str(root/'report.md'),
                'original_plan_commit':a.PLAN,'spec_sha256':sha(root/'spec.json'),
                'source_files':s['source_files'],'input_files':s['input_files'],
                'original_group_binding_sha256':s['original_group_binding_sha256'],
                'task_inventory_sha256':digest(s['task_inventory']),'timing_sha256':digest(s['timing']),
                'measurement_exceptions':1,'owner_decision_sha256':c.SELF_CALIBRATION_OWNER_SHA,
                'r2_owner_decision_sha256':c.R2_OWNER_SHA,'budget_owner_decision_sha256':c.BUDGET_OWNER_SHA}
            flags=('bounded_in_run_self_calibration_accepted','r1_failed_call_and_reservation_retained',
                   'original_input_upload_reuse_accepted','complete_input_A1_accepted','complete_source_closure_accepted',
                   'exact_timing_scope_accepted','original_tokens_masks_and_EOS_unchanged',
                   'untouched_base_forward_only','full_result_window_and_budget_accepted')
            review.update({x:True for x in flags});a.reviewed_path(s,root/'spec.json',review)
            for key in ('r2_owner_decision_sha256','budget_owner_decision_sha256',*flags):
                bad=dict(review);bad.pop(key)
                with self.assertRaises(ValueError):a.reviewed_path(s,root/'spec.json',bad)

    def test_spawn_failure_consumes_new_marker_without_clearing_parent(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);s=spec();s.update(input_files={'original':'a'},
                reused_input_upload={'original_spec_file_sha256':'b'*64,'original_source_files':{'old':'c'}})
            dump(root/'spec.json',s);(root/'report.md').write_text('Synthetic report')
            review={'local_report_path':str(root/'report.md'),'report_sha256':sha(root/'report.md')}
            dump(root/'review.json',review);dump(root/'budget.json',{'observed_epoch':1792565000.})
            upload={'spec_file_sha256':'b'*64,'input_files':s['input_files'],
                    'source_files':{'old':'c'},'all_remote_file_bytes_read_back':True}
            store=Store({'parent':'preserved'});worker=Mock();worker.spawn.side_effect=RuntimeError('unknown spawn')
            with patch.object(a,'reviewed_path',return_value={k:v for k,v in review.items() if k!='local_report_path'}), \
                    patch.object(a,'fresh_budget',return_value={'new_reserved_usd':'2.70'}), \
                    patch.object(outer.parent,'original_upload',return_value=upload), \
                    patch.object(outer,'load_pack',return_value=({},[])), \
                    patch.object(outer.original_lifecycle,'ledger',return_value=[]), \
                    patch.object(outer.parent,'records_with_failed_parent',return_value=[]), \
                    patch.object(outer.parent,'remote_fences'):
                s['prior_failed_C1']={'synthetic':True}
                args=(root,s,root/'spec.json',root/'review.json',root/'budget.json',store,worker,'ap-new')
                kwargs={'publication':lambda *_:'a'*40,'observation':lambda *_:{'containers':[],'states':{}}}
                with self.assertRaisesRegex(RuntimeError,'unknown spawn'):outer.submit(*args,**kwargs)
                self.assertIn(outer.KEY+'/dispatch',store);self.assertEqual(store['parent'],'preserved')
                with self.assertRaisesRegex(ValueError,'no replay'):outer.submit(*args,**kwargs)
                self.assertEqual(worker.spawn.call_count,1)

    def test_shared_closeout_clock_never_resets_and_no_upload_mode(self):
        s=spec();s['limits']['closeout_seconds']=7200
        start=1792565000.;receipt={'worker_start_epoch':start}
        self.assertEqual(remaining_io_seconds('collect',s,start+1500,receipt)[1],start+8700)
        self.assertEqual(remaining_io_seconds('audit',s,start+8699,receipt)[0],1)
        with self.assertRaises(TimeoutError):remaining_io_seconds('audit',s,start+8700,receipt)
        with self.assertRaises(ValueError):remaining_io_seconds('upload',s,start,None)


if __name__=='__main__':unittest.main()

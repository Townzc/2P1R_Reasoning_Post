"""New fake-only C2 complete-path integration/guard checks; no production."""
import copy,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
from experiments.p011 import c2_path as p
from scripts import p011_c2_io as io,analyze_p011_c2 as analysis
from experiments.sft_allocation_midpoint.common import dump,sha,digest
from tests.test_p011_b_current_admission import candidate as b_fixture


def candidate(count=264):
    s,j=b_fixture();j=copy.deepcopy(j);s=copy.deepcopy(s)
    j.pop('owner_B16_sha256');j.update(category='C',new_request_count=count,new_generation_batches=(count+255)//256)
    j['limits'].update(score_seconds=28000,closeout_seconds=35205,full_result_window_seconds=37665)
    s['jobs']={p.logical(j):j};return s,j


class NewFullC2(unittest.TestCase):
    def test_exact_variable_window_and_category(self):
        for n in (1,264,2800):
            s,j=candidate(n);p.validate(s)
            self.assertEqual(p.policy(j,1792560000,'6.38')['new_generation_batches'],(n+255)//256)
        s,j=candidate();j['category']='B'
        with self.assertRaises(ValueError):p.validate(s)

    def test_queue_count_or_self_calibration_exception_blocks(self):
        for change in ({'new_request_count':2801},{'new_generation_batches':25}):
            s,j=candidate();j.update(change)
            with self.assertRaises(ValueError):p.validate(s)
        s,j=candidate();s['measurement_exceptions']=1
        with self.assertRaises(ValueError):p.validate(s)

    def test_no_B16_override_or_B_job_namespace(self):
        s,j=candidate();self.assertEqual(p.key(j),'c2/generation')
        self.assertEqual(p.phase_for_job('C2_C2a_s17_r1'),'student')
        with self.assertRaises(ValueError):p.phase_for_job('B_B1_s17_r1')
        with self.assertRaises(ValueError):p.phase_for_job('C2_C2c_s17_r1')

    def test_all_dynamic_batch_records_and_window_fence(self):
        _,j=candidate(2800);names=io.expected_records(j)
        self.assertEqual(len(names),26);self.assertIn('c2/generation/window',names)
        self.assertIn('c2/generation/batch_done/010',names)
        self.assertNotIn('c2/generation/batch_done/011',names)

    def test_retained_C1_success_and_failure_charge_C_category(self):
        s,j=candidate();now=1792560000.
        records=[{'logical_id':name,'app_id':'ap-'+name,'budget':{'category':'C','new_reserved_usd':value},
            'saved_provider':{'state':'stopped','owned_containers':0}} for name,value in [('oldfailed','3.74'),('oldcomplete','2.64')]]
        totals={key:'0' for key in p.shared.CAPS};totals['C']='6.38'
        obs={'containers':[],'states':{r['app_id']:'stopped' for r in records}}
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'proof').write_text('fake')
            budget=dict(observed_epoch=now,all_attempted_reservations_usd=totals,category='C',cap_usd='12',
                overall_cap_usd='180',protected_usd='0',budget_owner_decision_sha256=p.BUDGET_OWNER_SHA,
                reserve_release_used=False,owner_estimate_used_as_balance=False,
                availability_basis='owner_current_balance_minus_retained_P011_reserves_and_meter_growth',
                hourly_rate_usd='4.39520',source_evidence_files={'proof':sha(root/'proof')},
                available_after_retained_prior_reserves_usd='10',observed_gross_resource_usd='300')
            result=p.budget_check(root,s,j,budget,records,obs,now)
            self.assertEqual(result['prior_reserved_usd'],'6.38');self.assertEqual(result['category'],'C')
            with self.assertRaises(ValueError):p.budget_check(root,s,j,{**budget,'all_attempted_reservations_usd':{**totals,'C':'2.64'}},records,obs,now)

    def test_no_closeout_clock_reset_after_collection(self):
        _,j=candidate();start=1792560000.;receipt={'worker_start_epoch':start}
        limits=j['limits'];end=start+limits['worker_seconds']+limits['closeout_seconds']
        for mode in ('collect','audit','score'):
            _,actual=io.window(mode,j,start+1801,receipt);self.assertEqual(actual,end)
        with self.assertRaises(TimeoutError):io.window('score',j,end-28004,receipt)

    def test_actual_endpoint_is_a_list_not_dict_wrapper(self):
        rows=[{'problem_id':str(i),'candidate_id':str(i),'input_ids':[1,2],'source_row_sha256':'a'*64} for i in range(500)]
        self.assertEqual(analysis.endpoint_ids(rows),[str(i) for i in range(500)])
        with self.assertRaises(ValueError):analysis.endpoint_ids({'rows':rows})

    def test_missing_full_review_cannot_be_promoted_from_source_CR(self):
        s,j=candidate()
        with patch.object(p.shared,'fixed_report',return_value={}):
            with self.assertRaises((ValueError,FileNotFoundError)):
                p.reviewed(s,Path('does-not-exist'),{'scope':'p011-C2-generation-student-complete-path-CR'})

if __name__=='__main__':unittest.main()

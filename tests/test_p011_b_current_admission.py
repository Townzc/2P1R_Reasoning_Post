"""New narrow accounting/parent regression checks; no old methods or data run."""
import ast,copy,tempfile,unittest
from decimal import Decimal,ROUND_CEILING
from pathlib import Path
from unittest.mock import Mock,patch
from experiments.p011 import b_current_path as p
from scripts import p011_b_current_io as io
from experiments.sft_allocation_midpoint.common import dump,sha,digest
from tests.test_p011_b_full_path import spec as old_spec,Store

def candidate():
    s=old_spec();s['budget_owner_decision_sha256']=p.BUDGET_OWNER_SHA;s['prior_failed_C1']={'files':{'required':'fixture'}}
    j=s['jobs']['B_generation_t10_400x16_r1']
    j['resources']={'gpu':'H100','cpu':4,'memory_mib':32768}
    j['resource_rates_usd_per_hour']={'H100':'3.95','cpu_core':'.04730','GiB':'.008'}
    j['timing'].update(batch_cycle_seconds=[22.100826501846313],future_allowance_seconds=600)
    j['limits'].update(worker_seconds=1800,platform_seconds=1860,startup_seconds=600,
        closeout_seconds=69205,score_seconds=62000,full_result_window_seconds=71665,
        hourly_rate_usd='4.39520',reserved_usd='3.01')
    return s,j

class NewCurrentBAdmission(unittest.TestCase):
    def test_original_science_and_IO_bodies_unchanged(self):
        def functions(path):return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(Path(path).read_text()).body if isinstance(n,ast.FunctionDef)}
        old=functions('experiments/p011/b_path.py');new=functions('experiments/p011/b_current_path.py')
        for name in ('logical','key','local_inputs','policy','body_worker','worker_body','terminate_owned_descendants'):
            self.assertEqual(old[name],new[name],name)
        for oldname,newname in [('experiments/p011/modal_b.py','experiments/p011/modal_b_current.py'),('scripts/p011_b_io.py','scripts/p011_b_current_io.py')]:
            self.assertEqual(Path(oldname).read_text(),Path(newname).read_text().replace('b_current_path as path','b_path as path').replace('b_current_path as run','b_path as run'))

    def test_whole_resources_and_original_scoring_window(self):
        s,j=candidate();p.validate(s)
        v=p.b_numeric.forecast(p.policy(j,1792560000,'0'),0,25,[],[],1792560000)
        self.assertAlmostEqual(v['forecast_total_seconds'],1383.0247950553894)
        self.assertEqual(v['predicted_usd'],'2.43');self.assertEqual(v['reserved_usd'],'3.01')
        broken=copy.deepcopy(s);broken['jobs'][p.logical(j)]['limits']['hourly_rate_usd']='3.95'
        with self.assertRaises(ValueError):p.validate(broken)
        broken=copy.deepcopy(s);broken['budget_owner_decision_sha256']='0'*64
        with self.assertRaises(ValueError):p.validate(broken)

    def test_current_owner_accounting_retains_failed_C_and_stale_blocks(self):
        s,j=candidate();now=1792560000.
        with tempfile.TemporaryDirectory(dir='.local/p011_20261020/r1') as d:
            root=Path(d);(root/'proof').write_text('fixture')
            totals={k:'0' for k in p.shared.CAPS};totals['C']='3.74'
            records=[{'logical_id':'C1failed','app_id':'ap-old','budget':{'category':'C','new_reserved_usd':'3.74'},'saved_provider':{'state':'stopped','owned_containers':0}}]
            obs={'containers':[],'states':{'ap-old':'stopped'}}
            budget=dict(observed_epoch=now,all_attempted_reservations_usd=totals,category='B',cap_usd='20',overall_cap_usd='180',protected_usd='0',budget_owner_decision_sha256=p.BUDGET_OWNER_SHA,reserve_release_used=False,owner_estimate_used_as_balance=False,availability_basis='owner_current_balance_minus_retained_P011_reserves_and_meter_growth',hourly_rate_usd='4.39520',source_evidence_files={'proof':sha(root/'proof')},available_after_retained_prior_reserves_usd='10',observed_gross_resource_usd='300')
            x=p.budget_check(root,s,j,budget,records,obs,now);self.assertEqual(x['all_attempted_reservations_usd']['C'],'3.74')
            for change in ({'observed_epoch':now-3601},{'protected_usd':'48'},{'reserve_release_used':True},{'budget_owner_decision_sha256':'x'},{'available_after_retained_prior_reserves_usd':'nan'}):
                with self.assertRaises((ValueError,ArithmeticError)):p.budget_check(root,s,j,{**budget,**change},records,obs,now)

    def test_unknown_and_unmatched_slots_are_not_free(self):
        s,j=candidate();now=1792560000.
        totals={k:'0' for k in p.shared.CAPS};totals['C']='3.74'
        records=[{'logical_id':'C1unknown','app_id':None,'budget':{'category':'C','new_reserved_usd':'3.74'}}]
        budget=dict(observed_epoch=now,all_attempted_reservations_usd=totals)
        with self.assertRaises(ValueError):p.budget_check('.',s,j,budget,records,{'containers':[{'app_id':'ap-other'}]*3,'states':{}},now)

    def test_missing_preserved_parent_stops_before_observation_and_spawn(self):
        s,j=candidate();name=p.logical(j)
        with tempfile.TemporaryDirectory(dir='.local/p011_20261020/r1') as d:
            root=Path(d);dump(root/p.LOCAL/'b_io_r1/upload'/name/'COMPLETED.json',{'job_sha256':digest(j),'all_remote_file_bytes_read_back':True})
            report=root/'report';report.write_text('fixture');dump(root/'review.json',{'local_report_path':str(report),'report_sha256':sha(report)});dump(root/'budget.json',{})
            obs,worker=Mock(),Mock()
            with patch.object(p,'reviewed',return_value={}),patch.object(p.lifecycle,'ledger',return_value=[]):
                with self.assertRaises((TypeError,ValueError,KeyError)):p.submit(root,s,name,root/'review.json',root/'budget.json',Store(),worker,'ap-one',publication=lambda *a:'f'*40,observation=obs)
            obs.assert_not_called();worker.spawn.assert_not_called()

    def test_closeout_uses_original_absolute_clock_and_reserves_whole_score(self):
        _,j=candidate();start=1792560000.;receipt={'worker_start_epoch':start}
        for mode in ('collect','audit','score'):
            _,end=io.window(mode,j,start+1801,receipt);self.assertEqual(end,start+1800+69205)
        with self.assertRaises(TimeoutError):io.window('score',j,start+9001,receipt)
        self.assertEqual(p.CUTOFF-j['limits']['full_result_window_seconds'],1792573535)

if __name__=='__main__':unittest.main()

import ast,copy,json,tempfile,unittest
from pathlib import Path
from experiments.p011 import owner_post_retry_accounting as a
from experiments.sft_allocation_midpoint.common import sha
ROOT=Path(__file__).resolve().parents[1]

class PostRetryOptional(unittest.TestCase):
    def setUp(self):
        folder=ROOT/'.local/p011_20261020/r1/new_optional_after_retry_fixture_checks';folder.mkdir(exist_ok=True)
        self.tmp=tempfile.TemporaryDirectory(dir=folder);self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        f=self.root/a.retry.RETRY_SPEC;f.parent.mkdir(parents=True);f.write_text(json.dumps(dict(failed_parent_files={})))
        self.rates=dict(gpu_hour_cost_h100='3.95',cpu_hour_cost='.0473',mem_gib_hour_cost='.008',egress_gib_cost='.04',volume_storage_gib_month_cost='.09')
        self.job=dict(logical_id='long_A4_S-F15_s17_owner_r1',cell='A4',category='A',resources=dict(cpu=4,memory_mib=98304),limits=dict(worker_seconds=16200,platform_seconds=16260,startup_seconds=600,artifact_max_bytes=50000000000))
        self.spec=dict(initial_jobs=[a.PARENT],owner_amendment_sha256='owner');self.rows=[]
        for name in [a.PARENT,a.RETRY,'fallback_t72_clean_s17_n400_k1_r1','fallback_t72_clean_s17_n3200_k1_r1']:
            j=copy.deepcopy(self.job);j.update(logical_id=name,cell='A1' if name in (a.PARENT,a.RETRY) else 'control')
            self.rows.append(dict(logical_id=name,app_id=name,job=j,active=name==a.RETRY,failed=name==a.PARENT,completed_worker_seconds=1000,artifact_bytes_bound=500000))
        (self.root/'rates.json').write_text(json.dumps(self.rates));(self.root/'report.json').write_text('[]')
        self.budget=dict(observed_epoch=100,owner_amendment_sha256='owner',rates=self.rates,rates_file='rates.json',meter_report_file='report.json',source_evidence_files={n:sha(self.root/n) for n in ['rates.json','report.json']},new_epoch_app_observed_charges_usd={r['app_id']:None for r in self.rows})
    def check(self,rows=None,obs=None):return a.check(self.root,self.spec,self.job,self.budget,self.rows if rows is None else rows,{'containers':[]} if obs is None else obs,101)
    def test_all_original_controls_and_retry_included(self):
        x=self.check();self.assertEqual(x['provider_slots'],1);self.assertGreater(float(x['epoch_unsettled_compute_upper_bound_usd']),22.99)
        with self.assertRaises(ValueError):self.check(rows=[r for r in self.rows if r['logical_id']!=a.RETRY])
        with self.assertRaises(ValueError):self.check(rows=self.rows[:-1])
    def test_order_and_unknown_slots_still_enforced(self):
        self.job['cell']='A3'
        with self.assertRaises(ValueError):self.check()
        self.job['cell']='A4'
        with self.assertRaises(ValueError):self.check(obs={'containers':[dict(app_id=str(i)) for i in range(8)]})
    def test_actual_charge_cannot_be_erased_by_closed_receipt(self):
        (self.root/'report.json').write_text(json.dumps([dict(object_id=a.PARENT,cost='151')]));self.budget['source_evidence_files']['report.json']=sha(self.root/'report.json');self.budget['new_epoch_app_observed_charges_usd'][a.PARENT]='151'
        with self.assertRaisesRegex(ValueError,'hard cap'):self.check()
    def test_worker_and_oracle_science_functions_unchanged(self):
        def f(path,name):return next(n for n in ast.parse((ROOT/path).read_text()).body if isinstance(n,ast.FunctionDef) and n.name==name)
        self.assertEqual(ast.dump(f('experiments/p011/modal_long_owner.py','make_worker')),ast.dump(f('experiments/p011/modal_long_owner_post_retry_optional.py','make_worker')))
        for name in ['collect','audit','score']:
            self.assertEqual(ast.dump(f('scripts/p011_long_owner_closed_io.py',name)),ast.dump(f('scripts/p011_long_owner_post_retry_optional_io.py',name)))

if __name__=='__main__':unittest.main()

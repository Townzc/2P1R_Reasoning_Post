import ast,copy,json,tempfile,unittest
from pathlib import Path
from experiments.p011 import owner_retry_accounting as a,long_owner_retry_path as retry,long_owner_path as original
from experiments.sft_allocation_midpoint.common import sha,digest
ROOT=Path(__file__).resolve().parents[1]

class A1InfrastructureRetry(unittest.TestCase):
    def setUp(self):
        folder=ROOT/'.local/p011_20261020/r1/new_retry_fixture_checks';folder.mkdir(exist_ok=True)
        self.tmp=tempfile.TemporaryDirectory(dir=folder);self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.rates=dict(gpu_hour_cost_h100='3.95',cpu_hour_cost='.0473',mem_gib_hour_cost='.008',egress_gib_cost='.04',volume_storage_gib_month_cost='.09')
        self.job=dict(logical_id=a.RETRY,cell='A1',category='A',resources=dict(cpu=4,memory_mib=98304),limits=dict(worker_seconds=16200,platform_seconds=16260,startup_seconds=600,artifact_max_bytes=50000000000))
        names=[a.PARENT,'fallback_t72_clean_s17_n400_k1_r1','fallback_t72_clean_s17_n3200_k1_r1']
        self.spec=dict(required_original_jobs=names,owner_amendment_sha256='owner',failed_parent_files={})
        self.rows=[]
        for name in names:
            j=copy.deepcopy(self.job);j['logical_id']=name
            self.rows.append(dict(logical_id=name,app_id=name,job=j,active=False,failed=name==a.PARENT,completed_worker_seconds=3000,artifact_bytes_bound=500000))
        (self.root/'rates.json').write_text(json.dumps(self.rates));(self.root/'report.json').write_text('[]')
        self.budget=dict(observed_epoch=100,owner_amendment_sha256='owner',rates=self.rates,rates_file='rates.json',meter_report_file='report.json',new_epoch_app_observed_charges_usd={x['app_id']:None for x in self.rows},source_evidence_files={n:sha(self.root/n) for n in ['rates.json','report.json']})
    def check(self,**kw):return a.check(self.root,self.spec,self.job,self.budget,kw.get('rows',self.rows),kw.get('obs',{'containers':[]}),kw.get('now',101))
    def test_failed_elapsed_not_old_reservation_or_invoice(self):
        x=self.check();self.assertTrue(x['failed_parent_elapsed_upper_bound_not_invoice']);self.assertTrue(x['old_failed_reserved_envelope_not_charged']);self.assertLess(float(x['epoch_unsettled_compute_upper_bound_usd']),20);self.assertEqual(len(x['controls_included']),2)
    def test_one_retry_and_original_failure_required(self):
        with self.assertRaises(ValueError):self.check(rows=self.rows+[dict(self.rows[0],logical_id=a.RETRY)])
        self.rows[0]['failed']=False
        with self.assertRaises(ValueError):self.check()
    def test_actual_app_cost_overrides_lower_duration_bound(self):
        (self.root/'report.json').write_text(json.dumps([dict(object_id=a.PARENT,cost='151')]))
        self.budget['source_evidence_files']['report.json']=sha(self.root/'report.json');self.budget['new_epoch_app_observed_charges_usd'][a.PARENT]='151'
        with self.assertRaisesRegex(ValueError,'hard cap'):self.check()
    def test_unknown_slots_and_freshness(self):
        with self.assertRaises(ValueError):self.check(obs={'containers':[dict(app_id=str(i)) for i in range(8)]})
        with self.assertRaises(ValueError):self.check(now=3701)
    def test_failure_binding_rejects_tampered_claim(self):
        intent=dict(logical_id=a.PARENT);error=dict(message='Original source/dispatch/report/window differs',observed_epoch=3100)
        proof=dict(job=a.PARENT,stable_inventory=True,terminal=None,claim=dict(dispatch_sha256=digest(intent),worker_start_epoch=100),original_failure_observed_epoch=3100,failed_duration_upper_bound_seconds=3000,copied_bytes=20,excluded_files=[])
        (self.root/'p.json').write_text(json.dumps(proof));spec=dict(failed_parent_files={'p.json':sha(self.root/'p.json')},failed_parent_preservation='p.json')
        self.assertEqual(a.checked_failure(self.root,spec,intent,error),(3000,20))
        proof['claim']['dispatch_sha256']='wrong';(self.root/'p.json').write_text(json.dumps(proof))
        with self.assertRaises(ValueError):a.checked_failure(self.root,spec,intent,error)
    def test_original_worker_oracle_and_score_functions_reused(self):
        self.assertIs(retry.worker_body,original.worker_body)
        def f(file,name):return next(n for n in ast.parse((ROOT/file).read_text()).body if isinstance(n,ast.FunctionDef) and n.name==name)
        for name in ['collect','audit','score']:
            self.assertEqual(ast.dump(f('scripts/p011_long_owner_closed_io.py',name)),ast.dump(f('scripts/p011_long_owner_retry_io.py',name)))
        old=f('experiments/p011/modal_long_owner.py','make_worker');new=f('experiments/p011/modal_long_owner_retry.py','make_worker')
        for n in ast.walk(new):
            if isinstance(n,ast.ImportFrom):
                for alias in n.names:
                    if alias.name=='long_owner_retry_path':alias.name='long_owner_path'
        self.assertEqual(ast.dump(old),ast.dump(new));self.assertIn('path.original.SPEC',(ROOT/'experiments/p011/modal_long_owner_retry.py').read_text())

if __name__=='__main__':unittest.main()

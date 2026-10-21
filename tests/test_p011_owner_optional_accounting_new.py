import ast
import copy
import json
import tempfile
import unittest
from pathlib import Path
from experiments.p011 import owner_epoch_accounting as a
from experiments.sft_allocation_midpoint.common import sha


class OptionalAccounting(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.rates = dict(gpu_hour_cost_h100='3.95', cpu_hour_cost='.04730',
            mem_gib_hour_cost='.008', egress_gib_cost='.04', volume_storage_gib_month_cost='.09')
        self.job = dict(logical_id='optional_A4', cell='A4', resources=dict(cpu=4,memory_mib=98304),
            limits=dict(worker_seconds=16200,platform_seconds=16260,startup_seconds=600,artifact_max_bytes=50000000000))
        self.spec = dict(initial_jobs=['initial'],owner_amendment_sha256='owner')
        self.records = []
        for name in ['initial', 'fallback_t72_clean_s17_n400_k1_r1', 'fallback_t72_clean_s17_n3200_k1_r1']:
            j = copy.deepcopy(self.job); j.update(logical_id=name,cell='original')
            self.records.append(dict(logical_id=name,app_id=name,job=j,active=False,completed_worker_seconds=100))
        (self.root/'rates.json').write_text(json.dumps(self.rates))
        (self.root/'report.json').write_text('[]')
        self.budget = dict(observed_epoch=100,owner_amendment_sha256='owner',rates_file='rates.json',
            meter_report_file='report.json',rates=self.rates,
            new_epoch_app_observed_charges_usd={r['app_id']:None for r in self.records},
            source_evidence_files={n:sha(self.root/n) for n in ('rates.json','report.json')})

    def run_check(self, records=None, obs=None, now=101):
        return a.check(self.root,self.spec,self.job,self.budget,
            self.records if records is None else records, {'containers':[]} if obs is None else obs,now)

    def test_completed_controls_tighten_bound_not_invoice(self):
        result=self.run_check()
        self.assertEqual(len(result['controls_included']),2)
        self.assertTrue(result['completed_worker_duration_is_not_an_invoice'])
        self.assertTrue(all(v is None for v in result['new_epoch_app_observed_charges_usd'].values()))
        self.assertLess(float(result['epoch_unsettled_compute_upper_bound_usd']),10)

    def test_eight_unknown_provider_slots_reject(self):
        with self.assertRaises(ValueError):self.run_check(obs={'containers':[{'app_id':str(i)} for i in range(8)]})

    def test_no_missing_control_or_original(self):
        with self.assertRaises(ValueError):self.run_check(records=self.records[:-1])

    def test_order_rejects_A3_before_A4(self):
        self.job['cell']='A3'
        with self.assertRaises(ValueError):self.run_check()

    def test_expired_or_late_dispatch_rejects(self):
        with self.assertRaises(ValueError):self.run_check(now=3701)
        with self.assertRaises(ValueError):self.run_check(now=a.original.LATEST_DISPATCH+1)

    def test_actual_meter_and_hard_cap_both_bound(self):
        (self.root/'report.json').write_text(json.dumps([{'object_id':'initial','cost':'151'}]))
        self.budget['source_evidence_files']['report.json']=sha(self.root/'report.json')
        self.budget['new_epoch_app_observed_charges_usd']['initial']='151'
        with self.assertRaises(ValueError):self.run_check()

    def test_fabricated_actual_summary_rejected(self):
        self.budget['new_epoch_app_observed_charges_usd']['initial']='0'
        with self.assertRaises(ValueError):self.run_check()

    def test_worker_and_oracle_functions_unchanged(self):
        root=Path(__file__).resolve().parents[1]
        def f(file,name):return next(n for n in ast.parse((root/file).read_text()).body if isinstance(n,ast.FunctionDef) and n.name==name)
        self.assertEqual(ast.dump(f('experiments/p011/modal_long_owner.py','make_worker')),
                         ast.dump(f('experiments/p011/modal_long_owner_optional.py','make_worker')))
        for name in ('collect','audit','score'):
            self.assertEqual(ast.dump(f('scripts/p011_long_owner_closed_io.py',name)),
                             ast.dump(f('scripts/p011_long_owner_optional_io.py',name)))


if __name__=='__main__':unittest.main()

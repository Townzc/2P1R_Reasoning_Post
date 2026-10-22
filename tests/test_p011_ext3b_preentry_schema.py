"""New pre-dispatch schema/failure-carry regressions; no scientific execution."""
import ast
from copy import deepcopy
from decimal import Decimal
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

from experiments.p011 import ext4b_path as path
from experiments.p011.ext4b_runtime_contract import cost_window,actual_origin,entry_cli_directory,JOBS
from experiments.p011.owner_0205_common import read,digest


class PreentrySchema(unittest.TestCase):
    def setUp(self):
        self.spec=read('reports/p011_20261020/ext3b_preentry_schema_runtime_v3/SPEC.json')
        self.job=JOBS[0]

    def budget(self):
        failed=self.spec['preentry_schema_failures'][self.job]
        prior=(Decimal(str(failed['entry_seconds']))+60)*Decimal('4.90720')/3600
        check=cost_window('4.90720',prior,'5')
        return {'observed_epoch':1000,'pair_cap_usd':'90','per_cell_cap_usd':'45',
                'requested_job':self.job,'requested_attempt':1,'slots_after_requested':3,
                'hourly_rate_usd':'4.90720','retained_noncompute_usd':'5',
                'preentry_failed_compute_upper_usd':str(prior),
                'preentry_failed_reported_tagged_usd':None,
                'preentry_failure_binding_sha256':digest(failed),
                'prior_job_compute_upper_usd':str(prior),
                'other_cell_retained_upper_usd':'45',
                'pair_total_upper_usd':str(Decimal(check['cumulative_cell_upper_usd'])+45),
                'check':check}

    def test_both_live_entry_and_budget_use_the_proven_parser(self):
        def function(p,name):
            return next(n for n in ast.parse(Path(p).read_text()).body if isinstance(n,ast.FunctionDef) and n.name==name)
        old=function('.local/p011_20261020/r1/continue_current_budget_receipts_once.py','shared_slots')
        new=function('experiments/p011/provider_slots.py','shared_slots')
        self.assertEqual(ast.dump(old),ast.dump(new)) # Reuse six already-passed cases without rerunning them.
        for p in ['experiments/p011/ext4b_path.py','scripts/record_p011_ext4b_budget.py']:
            tree=ast.parse(Path(p).read_text())
            self.assertTrue(any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='shared_slots' for n in ast.walk(tree)))
            self.assertFalse(any(isinstance(n,ast.Subscript) and isinstance(n.slice,ast.Constant) and n.slice.value in ('State','Tasks') for n in ast.walk(tree)))

    def test_preentry_compute_bound_reduces_first_worker_window(self):
        budget=self.budget()
        with patch.object(path,'read',return_value=self.spec):
            result=path.budget_check(budget,self.job,1,1001)
        self.assertLess(result['worker_seconds'],28684)
        self.assertLessEqual(Decimal(result['cumulative_cell_upper_usd']),45)
        self.assertIsNone(budget['preentry_failed_reported_tagged_usd'])

    def test_preentry_cost_cannot_be_reset_or_rebound(self):
        for field,value in [('preentry_failure_binding_sha256','wrong'),('prior_job_compute_upper_usd','0'),('preentry_failed_compute_upper_usd','0')]:
            budget=self.budget();budget[field]=value
            with patch.object(path,'read',return_value=self.spec),self.assertRaises(ValueError):path.budget_check(budget,self.job,1,1001)

    def test_only_exact_completed_actual_manifest_can_carry(self):
        self.assertEqual(actual_origin(self.spec)['actual_job_manifest_sha256'],'bf556ba4e18ab52b6613d6e86eec207ec6dedab9937accb2b754f94368453a24')
        bad=deepcopy(self.spec);bad['unchanged_actual_input_binding']['spec_sha256']='wrong'
        with self.assertRaises(ValueError):actual_origin(bad)

    def test_first_model_entry_uses_new_cli_and_future_resume_keeps_old_route(self):
        self.assertEqual(entry_cli_directory(self.spec,self.job,1),'cli_preentry2')
        self.assertEqual(entry_cli_directory(self.spec,self.job,2),'cli')
        with self.assertRaises(ValueError):entry_cli_directory(self.spec,self.job,3)
        source=Path('scripts/run_p011_ext4b_once.py').read_text()
        self.assertLess(source.index('create(fence,'),source.index('subprocess.Popen('))
        io=Path('scripts/p011_ext4b_io.py').read_text()
        self.assertIn("cli_directory=intent.get('entry_cli_subdirectory','cli')",io)
        self.assertIn("if cli_directory not in ('cli','cli_preentry2')",io)

    def test_scientific_local_oracle_score_and_timing_bodies_unchanged(self):
        for filename,names in [('scripts/p011_ext4b_io.py',['audit','score']),('experiments/p011/ext4b_path.py',['timing','terminal_archive'])]:
            old=ast.parse(subprocess.check_output(['git','show','c1a73d322e65e1ce5c4545befd366e9f8b6787a2:'+filename],text=True))
            new=ast.parse(Path(filename).read_text())
            for name in names:
                a=next(n for n in old.body if isinstance(n,ast.FunctionDef) and n.name==name)
                b=next(n for n in new.body if isinstance(n,ast.FunctionDef) and n.name==name)
                self.assertEqual(ast.dump(a),ast.dump(b))


if __name__=='__main__':unittest.main()

import ast
from copy import deepcopy
from decimal import Decimal
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from experiments.p011 import forced_answer_relaunch as retry
from experiments.p011.forced_answer import CELLS
from scripts.run_p011_forced_answer_retry_once import launch_command, MODULE


class RelaunchBoundary(unittest.TestCase):
    def budget(self):
        return {'observed_epoch':1000,'hourly_rate_usd':'4.39520',
                'failed_first_compute_upper_usd':'0.8','failed_first_reported_tagged_usd':'0.2',
                'original_epoch_prior_nonforced_tagged_usd':'100.02287004',
                'prior_unattributed_cost_allowance_usd':'20.02',
                'active_or_pending_or_unknown_model_slots':0,'all_original_attempts_terminal':True,
                'failed_first_app_id':'ap-uPchVni8aP1OGmdNeMFyhL','total_forced_task_cap_usd':'12',
                'original_noncompute_allowance_usd':'1.50','new_noncompute_allowance_usd':'1.50'}

    def test_failed_cost_and_both_noncompute_allowances_reduce_new_timer(self):
        b=self.budget();result=retry.checked_budget(b,1001)
        self.assertLessEqual(Decimal(result['cumulative_task_upper_usd']),Decimal(12))
        self.assertEqual(result['both_noncompute_allowances_usd'],'3.00')
        b['failed_first_compute_upper_usd']='2.0'
        self.assertLess(retry.checked_budget(b,1001)['worker_hard_seconds'],result['worker_hard_seconds'])

    def test_stale_missing_money_and_invalid_slots_rejected(self):
        for changes in [{'observed_epoch':-3000},{'failed_first_compute_upper_usd':'0.1'},
                        {'original_epoch_prior_nonforced_tagged_usd':'119'},
                        {'active_or_pending_or_unknown_model_slots':8},
                        {'active_or_pending_or_unknown_model_slots':-1},
                        {'failed_first_compute_upper_usd':'11'},
                        {'total_forced_task_cap_usd':'24'}]:
            with self.subTest(changes=changes):
                b=self.budget();b.update(changes)
                with self.assertRaises(ValueError):retry.checked_budget(b,1001)

    def test_parent_requires_no_claim_no_cells_and_exact_stopped_app(self):
        with tempfile.TemporaryDirectory(dir='.local/p011_20261020/r1') as temp:
            root=Path(temp);(root/'collect').mkdir()
            rows={'claim':None,'terminal':None,**{'cell/'+c:None for c in CELLS}}
            def write(name,value):(root/'collect'/name).write_text(json.dumps(value))
            write('NAMED_RECORDS.json',rows);write('COMPLETED.json',{'cell_statuses':{c:'not_started' for c in CELLS}})
            write('PROVIDER_STOPPED0.json',{'app_id':'parent','state':'stopped','owned_containers':0})
            spec={'parent_evidence':[],'parent_app_id':'parent'}
            with patch.object(retry,'PARENT',root):
                self.assertEqual(retry.checked_parent(spec),rows)
                rows['claim']={'started':1};write('NAMED_RECORDS.json',rows)
                with self.assertRaises(ValueError):retry.checked_parent(spec)
                rows['claim']=None;rows['cell/baseline']={'status':'started'};write('NAMED_RECORDS.json',rows)
                with self.assertRaises(ValueError):retry.checked_parent(spec)

    def test_qualified_entry_and_independent_watchdog_source(self):
        command=launch_command('review','budget')
        self.assertEqual(command[1:4],['run','-m',MODULE])
        source=Path('scripts/run_p011_forced_answer_retry_once.py').read_text()
        tree=ast.parse(source)
        functions={n.name:n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef)}
        self.assertIn('cost_watch',functions)
        self.assertNotIn('modal.Dict',ast.unparse(functions['cost_watch']))
        self.assertIn('timeout=20',source)
        self.assertIn(".get('imported')",source)

    def test_analysis_science_body_and_original_cell_function_preserved(self):
        old=ast.parse(Path('scripts/analyze_p011_forced_answer.py').read_text())
        new=ast.parse(Path('scripts/analyze_p011_forced_answer_retry.py').read_text())
        for name in ['rates','main']:
            a=next(n for n in old.body if isinstance(n,ast.FunctionDef) and n.name==name)
            b=next(n for n in new.body if isinstance(n,ast.FunctionDef) and n.name==name)
            for tree in [a,b]:
                for node in ast.walk(tree):
                    if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='admit':
                        node.args[2]=ast.Constant('scope-locator-only')
            self.assertEqual(ast.dump(a,include_attributes=False),ast.dump(b,include_attributes=False))
        cell=Path('experiments/p011/forced_answer_retry_cell.py').read_text()
        self.assertIn('original.run(a.cell, a.deadline)',cell)
        self.assertNotIn('generate(',cell)
        self.assertNotIn('AutoTokenizer',cell)


if __name__=='__main__':unittest.main()

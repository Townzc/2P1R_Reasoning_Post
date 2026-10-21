"""New formal owner/ledger/locator boundaries; no original suite is repeated."""
import ast
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.p011 import long_current_path as p
from scripts import p011_long_current_io as io
from experiments.sft_allocation_midpoint.common import dump, sha, digest
from tests.test_p011_long_repair_r1 import spec as original_fixture

ROOT = Path(__file__).resolve().parents[1]


def fixture():
    s = original_fixture('S-L15')
    s.update(budget_owner_decision_sha256=p.BUDGET_OWNER_SHA,
             prior_failed_C1={'fixture': True}, failed_attempt_bindings={'B': {'fixture': True}},
             actual_input_directory=p.LOCAL_INPUT_DIRECTORY, actual_input_binding_sha256='d'*64)
    j = next(iter(s['jobs'].values()))
    m = j['model']
    for name in ('generation_config.json', 'tokenizer.json', 'tokenizer_config.json'):
        m['files'][name] = {'bytes': 1, 'sha256': 'a'*64}
    m['local_audit_asset_files'] = copy.deepcopy(m['files'])
    m['preflight_asset_readback'] = {
        'path': str(Path(p.LOCAL)/'long_preflight_io_r1/model_uploads'/m['revision']/'COMPLETED.json'),
        'sha256': 'c'*64}
    return s, j


def functions(path):
    return {n.name: ast.dump(n, include_attributes=False)
            for n in ast.parse((ROOT/path).read_text()).body if isinstance(n, ast.FunctionDef)}


class CurrentFormal(unittest.TestCase):
    def test_exact_owner_actual_input_and_metadata_required(self):
        s, _ = fixture()
        p.validate(s)
        for field in ('budget_owner_decision_sha256', 'prior_failed_C1',
                      'failed_attempt_bindings', 'actual_input_directory', 'actual_input_binding_sha256'):
            bad = copy.deepcopy(s)
            bad[field] = None
            with self.assertRaises(ValueError): p.validate(bad)
        for mutation in ('missing', 'weight', 'different'):
            bad = copy.deepcopy(s); m = next(iter(bad['jobs'].values()))['model']
            if mutation == 'missing': del m['local_audit_asset_files']['tokenizer.json']
            if mutation == 'weight': m['local_audit_asset_files']['model.safetensors'] = {'bytes': 1, 'sha256': 'a'*64}
            if mutation == 'different': m['local_audit_asset_files']['config.json']['sha256'] = 'f'*64
            with self.assertRaises(ValueError): p.validate(bad)

    def test_formal_science_and_selection_AST_unchanged(self):
        old = functions('experiments/p011/long_path.py')
        new = functions('experiments/p011/long_current_path.py')
        for name in ('logical', 'key', 'policy', 'selection', 'worker_body', 'terminate_owned_descendants'):
            self.assertEqual(old[name], new[name], name)
        old = functions('scripts/p011_long_io.py'); new = functions('scripts/p011_long_current_io.py')
        for name in ('window', 'original', 'transfer', 'collect', 'score', 'main'):
            self.assertEqual(old[name], new[name], name)

    def test_entry_analysis_import_only_and_original_logical_fences(self):
        for old, new in [('experiments/p011/modal_long.py', 'experiments/p011/modal_long_current.py'),
                         ('scripts/analyze_p011_long_pair.py', 'scripts/analyze_p011_long_current_pair.py')]:
            expected = (ROOT/old).read_text().replace('import long_path as', 'import long_current_path as')
            self.assertEqual(expected, (ROOT/new).read_text())
        source = (ROOT/'experiments/p011/long_current_path.py').read_text()
        self.assertIn('failed_attempt_ledger.ledger(root,spec)', source)
        self.assertIn('parent.records_with_failed_parent', source)
        self.assertIn('parent.remote_fences(root,spec,store)', source)
        self.assertIn('failed_attempt_ledger.remote_fences(root,spec,store)', source)
        self.assertNotIn('records=lifecycle.ledger(root)', source)

    def test_completed_input_locator_and_metadata_only_local_audit(self):
        source = (ROOT/'scripts/p011_long_current_io.py').read_text()
        self.assertEqual(source.count('/path.LOCAL_INPUT_DIRECTORY/'), 2)
        self.assertNotIn("/'long_inputs_r1'/", source)
        self.assertIn("verify(assets,job['model']['local_audit_asset_files'])", source)
        self.assertNotIn("verify(assets,job['model']['files'])", source)
        upload = functions('scripts/p011_long_current_io.py')['upload']
        self.assertNotIn("value='assets'", upload)
        body = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name=='upload')
        lines = ast.get_source_segment(source, body)
        self.assertLess(lines.index('reused_assets(root,job)'), lines.index('store=modal.Dict'))

    def test_reuse_exact_complete_asset_receipt_no_weights_needed(self):
        _, j = fixture()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); m = j['model']; target = root/m['preflight_asset_readback']['path']
            dump(target, dict(model_files=m['files'], remote_path=m['remote_path'], all_remote_file_bytes_read_back=True))
            m['preflight_asset_readback']['sha256'] = sha(target)
            self.assertEqual(io.reused_assets(root,j), sha(target))
            self.assertFalse((root/m['local_path']).exists())
            changed = json.loads(target.read_text()); changed['all_remote_file_bytes_read_back'] = False
            target.write_text(json.dumps(changed))
            with self.assertRaises(ValueError): io.reused_assets(root,j)
            m['preflight_asset_readback']['sha256'] = sha(target)
            with self.assertRaises(ValueError): io.reused_assets(root,j)

    def test_current_budget_retains_failed_reserves_and_rejects_stale_old_scope(self):
        s,j = fixture(); totals = dict(A='0',B='3.01',C='6.38',D='0',emergency='0')
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); dump(root/'budget_source.json',{'synthetic':True})
            b=dict(observed_epoch=1000,all_attempted_reservations_usd=totals,category='A',cap_usd='115',
                   overall_cap_usd='180',protected_usd='0',budget_owner_decision_sha256=p.BUDGET_OWNER_SHA,
                   reserve_release_used=False,owner_estimate_used_as_balance=False,
                   availability_basis='owner_current_balance_minus_retained_P011_reserves_and_meter_growth',
                   hourly_rate_usd=j['limits']['hourly_rate_usd'],source_evidence_files={'budget_source.json':sha(root/'budget_source.json')},
                   available_after_retained_prior_reserves_usd='10',observed_gross_resource_usd='300')
            with patch.object(p.shared,'accounting',return_value=(totals,0)):
                checked=p.budget_check(root,s,j,b,[],dict(containers=[],states={}),1001)
                self.assertEqual(checked['all_attempted_reservations_usd'],totals)
                self.assertEqual(checked['protected_usd'],'0')
                for field,value in [('protected_usd','48'),('budget_owner_decision_sha256','bad'),
                                    ('observed_epoch',-4000),('observed_epoch',float('nan')),
                                    ('available_after_retained_prior_reserves_usd','NaN'),
                                    ('reserve_release_used',True)]:
                    bad=copy.deepcopy(b);bad[field]=value
                    with self.assertRaises(ValueError):p.budget_check(root,s,j,bad,[],dict(containers=[],states={}),1001)
            with patch.object(p.shared,'accounting',return_value=(totals,4)):
                with self.assertRaises(ValueError):p.budget_check(root,s,j,b,[],dict(containers=[],states={}),1001)
            full=copy.deepcopy(totals);full['A']='114';b['all_attempted_reservations_usd']=full
            with patch.object(p.shared,'accounting',return_value=(full,0)):
                with self.assertRaises(ValueError):p.budget_check(root,s,j,b,[],dict(containers=[],states={}),1001)

    def test_exact_review_needs_current_bindings_and_two_new_flags(self):
        s,_=fixture()
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'spec.json';dump(f,s)
            rev=dict(scope=p.SCOPE,original_plan_commit=p.shared.PLAN,spec_sha256=sha(f),source_files=s['source_files'],
                jobs_sha256=digest(s['jobs']),measurement_exceptions=0,budget_owner_decision_sha256=p.BUDGET_OWNER_SHA,
                prior_failed_C1_sha256=digest(s['prior_failed_C1']),failed_attempt_bindings_sha256=digest(s['failed_attempt_bindings']),
                actual_input_directory=p.LOCAL_INPUT_DIRECTORY,actual_input_binding_sha256=s['actual_input_binding_sha256'])
            flags=('complete_source_closure_accepted','OT3_actual_A1_accepted','AM_actual_A1_accepted',
                'endpoint_native_inputs_A1_accepted','all_original_complete_timing_sources_accepted',
                'full_state_raw_scoring_window_and_budget_accepted','remote_paths_traced_to_producers',
                'current_owner_budget_and_failed_reservations_accepted','completed_numeric_gold_inputs_and_prior_asset_reuse_accepted')
            rev.update({k:True for k in flags})
            with patch.object(p.shared,'fixed_report',return_value={'synthetic':True}):
                p.reviewed(s,f,rev)
                for k in (*flags[-2:],'actual_input_binding_sha256','failed_attempt_bindings_sha256'):
                    bad=copy.deepcopy(rev);bad[k]=None
                    with self.assertRaises(ValueError):p.reviewed(s,f,bad)


if __name__=='__main__':unittest.main()

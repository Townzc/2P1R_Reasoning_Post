"""Execute the real worker AST with actual input schema and mocked cloud/model I/O.

Review objects below are in-memory synthetic fixtures, never admission records.
No fixture calls Modal, loads weights, generates tokens or mutates original data.
"""
import ast
from copy import deepcopy
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from experiments.sft_allocation_midpoint.common import read, digest, sha
from experiments.learning_regime_p009 import p0_entry_repair_binding as binding

WD = Path.cwd()
OLD_ENTRY = Path('experiments/learning_regime_p009/modal_p0_fast_remaining.py')
NEW_ENTRY = Path('experiments/learning_regime_p009/modal_p0_entry_repair.py')
ROOT = Path('reports/p009_20261014/p0_fast_remaining_preflight_v1')


class Store:
    def __init__(self):
        self.rows = {}
    def get(self, key, default=None):
        return deepcopy(self.rows.get(key, default))
    def put(self, key, value, skip_if_exists=False):
        if skip_if_exists and key in self.rows:
            return False
        self.rows[key] = deepcopy(value)
        return True


class EntryRepairTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir='.local/p009_20261014/r1')
        self.addCleanup(self.tmp.cleanup)
        self.plan = read(ROOT/'PLAN.json')
        self.spec = read('reports/p009_20261014/p0_fast_remaining_preflight_v1/ADMISSION.json')
        self.spec.update(stage0_cap_cents=2000, experiment_cap_cents=11000,
            parent_reserved_cents=752, original_two_failed_reserved_cents=500,
            owner_budget_amendment_sha256='1'*64)
        self.release = dict(source_files=self.spec['source_files'],review_target='0'*40,
            input_readback=deepcopy(self.spec['parent_spec']['inputs']),
            budget=dict(p009_stage0_used_and_pending_cents=752, slot_reserved_cents=252,
                new_experiment_cap_cents=11000, effective_stage0_cap_cents=2000,
                project_prior_upper_cents=26070),
            runtime_review=dict(scope=self.spec['scope'], decision='PASS',target_commit='0'*40,
                report_commit='0'*40, report_sha256='0'*64,
                source_files=self.spec['source_files'],spec_sha256=digest(self.spec),
                parent_preservation_sha256=self.spec['parent_preservation_sha256'],
                bounded_suffix_only=True,native_eos_cap_metadata_accepted=True,
                same_frozen_logical_stop=True,stage0_cap_cents=2000,
                experiment_cap_cents=11000,owner_budget_amendment_sha256='1'*64))
        proof = dict(claims=0, terminals=0, unit_intents=0, new_outputs=0,
            unknown_generation=0, model_loaded=False, volume_absent=True,
            all_original_apps_stopped=True, original_256_untouched=True,
            failed_terminal_fabricated=False, original_call_failed=True,
            original_call_id='fc-fixture', original_error=dict(type='KeyError',
                error="'inputs'", retry_authorized=False),
            actual_campaign_records={'midpoint/'+binding.CAMPAIGN+'/campaign':self.plan})
        self.spec['preclaim_failure'] = dict(repair_scope=binding.REPAIR_SCOPE,
            zero_work_proof=proof, zero_work_proof_file_sha256='0'*64,
            prior_failed_call_reserved_cents=252)
        self.release['runtime_review'].update(spec_sha256=digest(self.spec),
            preclaim_entry_schema_repair_accepted=True, preclaim_proof_sha256='0'*64)
        self.release['dispatch_app_id'] = 'ap-fixture'
        self.store = Store()
        self.store.put(binding.DISPATCH_KEY, binding.dispatch_marker(self.spec, self.release))
        self.timer = SimpleNamespace(daemon=False, start=lambda:None, cancel=lambda:setattr(self, 'cancelled', True))
        self.cancelled = False
        self.model_calls = 0
        self.execute_error = False

    def execute(self, spec, out, store, guard, claim, commit, start, stop):
        self.model_calls += 1
        intent = store.get(guard.prefix+'intent/'+binding.RUN)
        self.assertEqual(intent['data_sha256'], digest(self.spec['parent_spec']['inputs']))
        self.assertEqual(stop-start, 1200)
        if self.execute_error:
            raise RuntimeError('synthetic model-path error')
        return dict(synthetic_fixture=True)

    def worker(self, path):
        tree = ast.parse(path.read_text())
        node = next(x for x in tree.body if isinstance(x, ast.FunctionDef) and x.name=='finite_work')
        node.decorator_list = []
        def mapped(value):
            value = str(value)
            if value == '/workspace':
                return WD
            if value == '/evidence':
                return Path(self.tmp.name)/'evidence'
            return Path(value)
        def fixture_read(path):
            if str(path).startswith('/workspace/'):
                return deepcopy(self.spec)
            return read(path)
        namespace = dict(Path=mapped, SPEC='fixture_admission.json',
            WORKER_SECONDS=1200, RESERVED_CENTS=252, RUN=binding.RUN,
            CAMPAIGN=binding.CAMPAIGN, validate_release=lambda *a:None,
            modal=SimpleNamespace(Dict=SimpleNamespace(from_name=lambda *a,**k:self.store)),
            volume=SimpleNamespace(reload=lambda:None, commit=lambda:None))
        exec(compile(ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[])),str(path),'exec'),namespace)
        with patch('threading.Timer', return_value=self.timer), \
             patch('experiments.sft_allocation_midpoint.common.read', side_effect=fixture_read), \
             patch('experiments.sft_allocation_p008.evidence_bundle.pack', return_value=None), \
             patch(('experiments.learning_regime_p009.p0_fast_remaining_runtime.execute' if path==OLD_ENTRY else
                    'experiments.learning_regime_p009.p0_entry_repair_runtime.execute'), side_effect=self.execute):
            return namespace['finite_work'](deepcopy(self.plan),deepcopy(self.release))

    def test_original_worker_reproduces_actual_preclaim_failure(self):
        self.assertNotIn('inputs',self.spec)
        with self.assertRaisesRegex(KeyError,'inputs'):
            self.worker(OLD_ENTRY)
        self.assertIn('midpoint/'+binding.CAMPAIGN+'/campaign',self.store.rows)
        self.assertFalse(any('/claim/' in k for k in self.store.rows))
        self.assertEqual(self.model_calls,0)
        self.assertFalse(self.cancelled)  # original uncovered pre-claim timer path

    def test_actual_fixed_worker_uses_nested_manifest_and_completes(self):
        result = self.worker(NEW_ENTRY)
        self.assertEqual(result['receipt']['status'],'completed')
        self.assertEqual(self.model_calls,1)
        self.assertTrue(self.cancelled)

    def test_readback_mismatch_aborts_before_registration(self):
        self.release['input_readback']={}
        with self.assertRaises(ValueError): self.worker(NEW_ENTRY)
        self.assertEqual(self.model_calls,0)
        self.assertFalse(any(k.endswith('/campaign') for k in self.store.rows))
        self.assertTrue(self.cancelled)

    def test_missing_nested_manifest_cancels_timer_without_claim(self):
        del self.spec['parent_spec']['inputs']
        self.release['runtime_review']['spec_sha256']=digest(self.spec)
        with self.assertRaises((ValueError,KeyError)): self.worker(NEW_ENTRY)
        self.assertEqual(self.model_calls,0)
        self.assertTrue(self.cancelled)

    def test_model_path_failure_is_terminal_and_cannot_repeat(self):
        self.execute_error=True
        with self.assertRaisesRegex(RuntimeError,'synthetic'): self.worker(NEW_ENTRY)
        self.assertEqual(self.store.get('midpoint/'+binding.CAMPAIGN+'/terminal/'+binding.RUN)['status'],'failed')
        with self.assertRaises(RuntimeError): self.worker(NEW_ENTRY)
        self.assertEqual(self.model_calls,1)
        self.assertTrue(self.cancelled)

    def test_conflicting_top_level_alias_rejected(self):
        self.spec['inputs']={}
        with self.assertRaises(ValueError): binding.admission_intent(self.spec,self.release)

    def test_only_exact_original_registration_allowed(self):
        good={'midpoint/'+binding.CAMPAIGN+'/campaign':self.plan}
        binding.registration_only(good,self.plan)
        for kind in ('claim','intent','unit','terminal','entry_schema_repair_dispatch'):
            bad=dict(good);bad['midpoint/'+binding.CAMPAIGN+'/'+kind]=None
            with self.assertRaises(ValueError): binding.registration_only(bad,self.plan)
        with self.assertRaises(ValueError): binding.registration_only({},self.plan)

    def test_old_review_does_not_accept_repair(self):
        del self.release['runtime_review']['preclaim_entry_schema_repair_accepted']
        with self.assertRaises(ValueError): self.worker(NEW_ENTRY)
        self.assertTrue(self.cancelled)
        self.assertEqual(self.model_calls,0)

    def test_uncovered_failed_call_budget_refused(self):
        self.release['budget']['p009_stage0_used_and_pending_cents']=500
        with self.assertRaises(ValueError): self.worker(NEW_ENTRY)
        self.assertEqual(self.model_calls,0)

    def test_owner_amended_budget_and_same_time_gate(self):
        self.assertEqual(752+252,1004)
        self.assertLessEqual(1004,binding.STAGE0_CAP_CENTS)
        self.assertTrue(binding.remaining_forecast(0,[20.4121413230896],11)['admitted'])
        self.assertFalse(binding.remaining_forecast(1000,[20.4121413230896],11)['admitted'])
        self.release['runtime_review']['experiment_cap_cents']=10000
        with self.assertRaises(ValueError): self.worker(NEW_ENTRY)

    def test_foreign_dispatch_refuses_admission(self):
        self.store.rows[binding.DISPATCH_KEY]['provider_app_id']='ap-different'
        with self.assertRaises(ValueError): self.worker(NEW_ENTRY)
        self.assertEqual(self.model_calls,0)
        self.assertFalse(any('/claim/' in k for k in self.store.rows))


if __name__=='__main__':
    unittest.main()

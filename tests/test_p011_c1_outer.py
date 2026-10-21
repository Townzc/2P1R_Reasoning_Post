"""New outer-lifecycle fixtures only; all model/provider operations are mocked."""
import copy
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch, Mock

from experiments.p011 import c1_outer as o, c1_admission as a, c1_execution as c, c1_nll
from experiments.sft_allocation_midpoint.common import dump, read, sha, digest
# Fixture functions only. No old TestCase or successful old test is executed.
from tests.test_p011_c1_execution_draft import spec, roster, forward, Store


class Fixture:
    def __init__(self, root):
        self.root = root
        self.s = spec()
        (root/'synthetic.py').write_text('# test only\n')
        (root/'report.md').write_text('Synthetic test report. Not an actual acceptance.\n')
        self.tasks, self.members = roster(3)
        self.s.update(source_files={'synthetic.py': sha(root/'synthetic.py')}, input_files={},
            original_group_binding_sha256='c'*64, task_inventory={'journal_chunks': 1})
        self.sp = root/'spec.json'
        dump(self.sp, self.s)
        self.review = {'decision': 'PASS', 'target_commit': 'd'*40,
            'local_report_path': str(root/'report.md'), 'report_sha256': sha(root/'report.md'),
            'scope': a.SCOPE, 'original_plan_commit': a.PLAN, 'spec_sha256': sha(self.sp),
            'source_files': self.s['source_files'], 'input_files': {},
            'original_group_binding_sha256': 'c'*64,
            'task_inventory_sha256': digest(self.s['task_inventory']),
            'timing_sha256': digest(self.s['timing']), 'measurement_exceptions': 0}
        for key in ('complete_input_A1_accepted', 'complete_source_closure_accepted',
                    'exact_timing_scope_accepted', 'original_tokens_masks_and_EOS_unchanged',
                    'untouched_base_forward_only', 'full_result_window_and_budget_accepted'):
            self.review[key] = True
        dump(root/'review.json', self.review)
        dump(root/'meter.json', {'synthetic_only': True})
        self.budget = {'observed_epoch': time.time(),
            'all_attempted_reservations_usd': {k: '0' for k in a.CAPS},
            'cap_usd': '12', 'category': 'C', 'overall_cap_usd': '180', 'protected_usd': '48',
            'reserve_release_used': False, 'owner_estimate_used_as_balance': False,
            'availability_basis': 'delayed_gross_plus_retained_reserves_conservative_floor',
            'source_evidence_files': {'meter.json': sha(root/'meter.json')},
            'available_after_retained_prior_reserves_usd': '55', 'observed_gross_resource_usd': '300'}
        dump(root/'budget.json', self.budget)
        dump(root/o.LOCAL/'c1_io_r1'/'upload'/'COMPLETED.json', {
            'spec_file_sha256': sha(self.sp), 'input_files': self.s['input_files'],
            'source_files': self.s['source_files'], 'all_remote_file_bytes_read_back': True})
        self.store = Store()
        self.worker = Mock()
        self.worker.spawn.return_value.object_id = 'fc-synthetic'
        self.worker.spawn.return_value.get.return_value = {'synthetic_return': True}
        self.volume = Mock()
        self.timer = Mock()

    def submit(self):
        with patch.object(o, 'load_pack', return_value=(self.tasks, self.members)):
            return o.submit(self.root, self.s, self.sp, self.root/'review.json',
                self.root/'budget.json', self.store, self.worker, 'ap-synthetic',
                publication=lambda *args: 'e'*40,
                observation=lambda *args: {'containers': [], 'states': {}, 'observed_epoch': time.time()})

    def worker_call(self, loader=None):
        intent, report = self.worker.spawn.call_args.args
        def mock_loader(s, out, deadline):
            dump(out/'MODEL_LOADED.json', {'model': s['model'], 'forward': s['forward'],
                'optimizer_created': False, 'adapter_loaded': False, 'new_tokenization': False})
            return object()
        with patch.object(o, 'load_pack', return_value=(self.tasks, self.members)), \
                patch.object(c1_nll, 'forward_one', side_effect=forward):
            return o.worker_body(self.s, self.sp, self.root, intent, report,
                self.store, self.volume, lambda seconds: self.timer,
                out=self.root/'remote', inputs=self.root/'synthetic_inputs', loader=loader or mock_loader)


class C1OuterTests(unittest.TestCase):
    def test_real_outer_body_complete_and_readonly_proof(self):
        with tempfile.TemporaryDirectory() as d:
            f = Fixture(Path(d)); f.submit(); receipt = f.worker_call()
            self.assertEqual(receipt['result']['unique_sequences'], 3)
            proof = {'app_id': 'ap-synthetic', 'state': 'stopped',
                'owned_containers': 0, 'observed_epoch': time.time()}
            with patch.object(c1_nll, 'forward_one', side_effect=AssertionError('No repeated forward')):
                result = o.c1_artifacts.check_complete(f.s, receipt, proof, f.store, o.KEY,
                    receipt['claim'], f.root/'remote'/'payload', f.tasks, f.members, receipt['basis'])
            self.assertTrue(result['receipt_verified'])
            self.assertEqual(set(o.complete_record_keys(f.s)), set(f.store))
            f.timer.cancel.assert_called_once()

    def test_disconnect_consumes_dispatch_and_never_respawns(self):
        with tempfile.TemporaryDirectory() as d:
            f = Fixture(Path(d)); f.worker.spawn.return_value.get.side_effect = ConnectionError('synthetic')
            with self.assertRaises(ConnectionError): f.submit()
            error = read(f.root/o.LOCAL/'dispatch'/o.LOGICAL/'RETURN_ERROR.json')
            self.assertTrue(error['cloud_failure_not_inferred'])
            with self.assertRaises(ValueError): f.submit()
            f.worker.spawn.assert_called_once()

    def test_spawn_exception_keeps_pending_intent_and_remote_fence(self):
        with tempfile.TemporaryDirectory() as d:
            f = Fixture(Path(d)); f.worker.spawn.side_effect = RuntimeError('synthetic spawn response lost')
            with self.assertRaises(RuntimeError): f.submit()
            records = o.ledger(f.root)
            self.assertNotIn('app_id', records[0])
            totals, slots = a.accounting(records, [], {})
            self.assertEqual(slots, 1); self.assertEqual(totals['C'], '1.95')
            self.assertIn(o.KEY+'/dispatch', f.store)

    def test_stale_review_blocks_before_any_intent_or_model(self):
        with tempfile.TemporaryDirectory() as d:
            f = Fixture(Path(d)); (f.root/'report.md').write_text('changed')
            with self.assertRaises(ValueError): f.submit()
            self.assertFalse((f.root/o.LOCAL/'dispatch').exists())
            f.worker.spawn.assert_not_called(); self.assertFalse(f.store)

    def test_altered_worker_source_fails_before_claim(self):
        with tempfile.TemporaryDirectory() as d:
            f = Fixture(Path(d)); f.submit(); (f.root/'synthetic.py').write_text('changed')
            with self.assertRaises(ValueError): f.worker_call()
            self.assertNotIn(o.KEY+'/claim', f.store)
            self.assertNotIn(o.KEY+'/terminal', f.store)
            self.assertFalse((f.root/'remote').exists())
            f.timer.cancel.assert_called_once()

    def test_failed_loader_is_permanent_failed_without_summary(self):
        with tempfile.TemporaryDirectory() as d:
            f = Fixture(Path(d)); f.submit()
            def fail(*args): raise RuntimeError('synthetic loader failure')
            with self.assertRaises(RuntimeError): f.worker_call(fail)
            self.assertEqual(f.store[o.KEY+'/terminal']['status'], 'failed')
            self.assertTrue((f.root/'remote'/'payload'/'FAILED.json').exists())
            self.assertFalse((f.root/'remote'/'payload'/'DESCRIPTIVE_SUMMARY.json').exists())
            with self.assertRaises(ValueError): f.worker_call()

    def test_late_worker_does_not_claim_or_load(self):
        with tempfile.TemporaryDirectory() as d:
            f = Fixture(Path(d)); f.submit()
            intent = f.worker.spawn.call_args.args[0]
            intent['dispatch_epoch'] -= 601
            f.store[o.KEY+'/dispatch'] = copy.deepcopy(intent)
            with self.assertRaises(ValueError): f.worker_call()
            self.assertNotIn(o.KEY+'/claim', f.store)

    def test_provider_failure_is_unknown_and_has_no_retry(self):
        with tempfile.TemporaryDirectory() as d:
            with patch.object(o.subprocess, 'check_output', side_effect=['[]', TimeoutError('synthetic')]) as call:
                proof = o.provider(Path(d), [{'app_id': 'ap-pending'}])
            self.assertEqual(proof['states'], {'ap-pending': 'unknown'})
            self.assertEqual(call.call_count, 2)

    def test_closed_app_requires_identity_state_and_zero_owned(self):
        info = {'app_id': 'ap-x', 'lifecycle': {'state': 'stopped'}}
        with self.assertRaises(ValueError): o.closed_provider('ap-y', info, [], time.time())
        with self.assertRaises(ValueError): o.closed_provider('ap-x', info, [{'app_id': 'ap-x'}], time.time())
        self.assertEqual(o.closed_provider('ap-x', info, [], time.time())['owned_containers'], 0)


if __name__ == '__main__':
    unittest.main()

"""CPU-only guards; inspect frozen references and synthetic accounting, not new outputs."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import audit_absent_boundary_outputs as audit
from scripts import audit_replication_outputs as historical


class AbsentBoundaryOutputAuditTest(unittest.TestCase):
    def test_new_queue_reconstructs_and_preserves_original_dev_without_dev_blocks_copy(self):
        jobs = historical.selected_jobs(audit.DEFAULT_QUEUE, data_validator=audit.validate_data)
        self.assertEqual(set(jobs), {'paths', 'gcm'})
        for spec in jobs.values():
            cfg, manifest = spec['config'], spec['data_manifest']
            self.assertEqual(cfg['seed'], 31)
            self.assertEqual(manifest['status'], 'FROZEN_ABSENT_BOUNDARY_V1')
            self.assertNotIn('dev_blocks.json', manifest['files_sha256'])
            self.assertEqual(manifest['training_questions'], 128)
            budget = manifest['budget_per_arm'][cfg['arm']]
            self.assertEqual(budget['supervised_response_tokens'], 277760)
            self.assertNotEqual(budget['supervised_response_tokens'], 267456)

    def test_missing_jobs_fail_without_creating_report(self):
        queue = historical.read_json(audit.DEFAULT_QUEUE)
        for job in queue['comparison']:
            job['run_id'] = 'never_executed_absent_audit_test_'+job['run_id']
        with tempfile.TemporaryDirectory() as temporary:
            queue_path, out = Path(temporary)/'queue.json', Path(temporary)/'report'
            queue_path.write_text(json.dumps(queue))
            with self.assertRaisesRegex(FileNotFoundError, 'no completed outputs'):
                audit.run(queue_path, out)
            self.assertFalse(out.exists())
            self.assertEqual(list(Path(temporary).iterdir()), [queue_path])

    def test_new_entry_rejects_historical_pair_and_old_entry_rejects_new_pair(self):
        with self.assertRaisesRegex(ValueError, 'frozen seed31 identity-absent'):
            historical.selected_jobs(historical.DEFAULT_QUEUE, data_validator=audit.validate_data)
        with self.assertRaisesRegex(ValueError, 'does not descend'):
            historical.selected_jobs(audit.DEFAULT_QUEUE)

    def test_original_dev_blocks_hash_is_checked_even_without_copy(self):
        cfg = historical.read_json('configs/absent_boundary_seed31/paths.json')
        original = audit.sha256_file
        def altered(path):
            return '0'*64 if Path(path).name == 'dev_blocks.json' else original(path)
        with patch.object(audit, 'sha256_file', side_effect=altered):
            with self.assertRaisesRegex(ValueError, 'parent development bytes differ: dev_blocks'):
                audit.validate_data(cfg)

    def test_manifest_and_matching_audit_budgets_must_agree(self):
        cfg = historical.read_json('configs/absent_boundary_seed31/paths.json')
        original = historical.read_json
        def altered(path):
            result = original(path)
            if Path(path).name == 'matching_audit.json':
                result = copy.deepcopy(result)
                result['arms']['paths']['supervised_response_tokens'] += 1
            return result
        with patch.object(historical, 'read_json', side_effect=altered):
            with self.assertRaisesRegex(ValueError, 'accounting or matching claims differ'):
                audit.validate_data(cfg)

    def dose_fixture(self, root):
        manifest = historical.read_json('runs/absent_boundary_seed31_20260909_r1/manifest.json')
        expected = manifest['budget_per_arm']['paths']
        verified = {'steps': 1024, 'supervised_response_tokens': expected['supervised_response_tokens']}
        spec = {'config': {'arm': 'paths'}, 'data_manifest': manifest}
        (root/'actual_budget.json').write_text(json.dumps(expected))
        (root/'budget_report.json').write_text(json.dumps({**expected, 'scope': 'synthetic accounting test'}))
        history = [{'step': index, **dose} for index, dose in enumerate(expected['per_update'], 1)]
        (root/'train_history.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in history))
        return verified, spec, history

    def test_dynamic_frozen_dose_accepts_synthetic_exact_accounting(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            verified, spec, _ = self.dose_fixture(root)
            audit.check_boundary_dose(verified, spec, root)
            with self.assertRaisesRegex(ValueError, 'fixed pilot'):
                historical.check_pilot_dose(verified, spec, root)

    def test_partial_actual_accounting_cannot_pass(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            verified, spec, _ = self.dose_fixture(root)
            actual = historical.read_json(root/'actual_budget.json')
            del actual['problem_exposures']
            (root/'actual_budget.json').write_text(json.dumps(actual))
            with self.assertRaisesRegex(ValueError, 'full accounting differs'):
                audit.check_boundary_dose(verified, spec, root)

    def test_per_update_shift_rejected_even_when_total_tokens_equal(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            verified, spec, history = self.dose_fixture(root)
            before = sum(row['supervised_tokens'] for row in history)
            history[0]['supervised_tokens'] += 1
            history[1]['supervised_tokens'] -= 1
            self.assertEqual(before, sum(row['supervised_tokens'] for row in history))
            (root/'train_history.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in history))
            with self.assertRaisesRegex(ValueError, 'per-update token sequence differs'):
                audit.check_boundary_dose(verified, spec, root)

    def test_equal_completed_totals_do_not_replace_frozen_plan(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            verified, spec, _ = self.dose_fixture(root)
            for name in ('actual_budget.json', 'budget_report.json'):
                data = historical.read_json(root/name)
                data['padding_tokens'] += 1
                (root/name).write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, 'full accounting differs'):
                audit.check_boundary_dose(verified, spec, root)


if __name__ == '__main__':
    unittest.main()

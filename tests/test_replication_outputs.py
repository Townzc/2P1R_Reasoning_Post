"""Regression checks use completed seed17 files; no new model outputs or GPU."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import audit_replication_outputs as audit
from scripts import verify_pilot_outputs as output_verifier


class ReplicationOutputAuditTest(unittest.TestCase):
    queue = Path('configs/pilot_v1/queue.json')

    def test_completed_original_pair_known_counts_and_frozen_strata(self):
        with tempfile.TemporaryDirectory() as root:
            out = Path(root)/'audit'
            result = audit.run(self.queue, out)
            self.assertEqual(result['training_seed'], 17)
            self.assertEqual(result['generations_per_arm'], {'paths': 400, 'gcm': 400})
            self.assertEqual(result['total_generations'], 800)
            self.assertEqual(set(result['run_ids']), {'paths', 'gcm'})
            self.assertEqual(len(list(out.glob('*/*.audit.jsonl'))), 8)
            overall = result['matched_overall']
            self.assertEqual(overall['paired_greedy_final_expression'], {
                'problems': 64, 'both_correct': 11, 'paths_only': 12,
                'gcm_only': 7, 'neither_correct': 34, 'paths_minus_gcm_count': 5})
            self.assertEqual(overall['paired_greedy_complete_trace'], {
                'problems': 64, 'both_verified': 8, 'paths_only': 13,
                'gcm_only': 6, 'neither_verified': 37, 'paths_minus_gcm_count': 7})
            self.assertEqual(overall['arms']['paths']['sample_success_count_histogram'],
                             {'0': 31, '1': 11, '2': 11, '3': 5, '4': 6})
            self.assertEqual(overall['arms']['gcm']['sample_success_count_histogram'],
                             {'0': 42, '1': 4, '2': 2, '3': 2, '4': 14})
            self.assertEqual(overall['arms']['paths']['sample_trace_verified_generations'], 59)
            self.assertEqual(overall['arms']['gcm']['sample_trace_verified_generations'], 57)
            self.assertEqual(result['matched_strata']['has_input_one']['true']['arms']['paths']['sample_problems_with_any_success'], 22)
            self.assertEqual(result['matched_strata']['has_input_one']['true']['arms']['gcm']['sample_problems_with_any_success'], 12)
            self.assertEqual(result['matched_strata']['any_reference_identity']['false']['paired_greedy_final_expression']['paths_minus_gcm_count'], 5)
            self.assertEqual(len(result['matched_strata']['block_id']), 16)
            for path, digest in result['audit_files_sha256'].items():
                self.assertEqual(audit.sha256_file(out/path), digest)
            self.assertEqual(result['frozen_development_hashes_verified'], audit.DEV_SHA256)
            self.assertEqual(audit.sha256_file(audit.LABELS), result['frozen_label_sha256'])
            stored = json.loads((out/'summary.json').read_text())
            self.assertEqual(stored, result)
            with self.assertRaises(FileExistsError):
                audit.run(self.queue, out)

    def test_default_replication_data_preserves_dev_and_parent_hashes(self):
        jobs = audit.selected_jobs(audit.DEFAULT_QUEUE)
        self.assertEqual(set(jobs), {'paths', 'gcm'})
        for spec in jobs.values():
            self.assertEqual(spec['config']['seed'], 23)
            self.assertEqual(spec['config']['eval_seed'], 17)
            parent = spec['data_manifest']['parent']
            self.assertEqual(parent['manifest_sha256'], audit.PARENT_MANIFEST_SHA256)
            for name, digest in audit.DEV_SHA256.items():
                self.assertEqual(parent['preserved_files_sha256'][name], digest)

    def test_not_run_pair_fails_without_writing_a_report(self):
        queue = json.loads(self.queue.read_text())
        queue['comparison'] = [job for job in queue['comparison'] if any(arm in job['run_id'] for arm in ('paths', 'gcm'))]
        for job in queue['comparison']:
            job['run_id'] = 'never_executed_trace_test_'+job['run_id']
        with tempfile.TemporaryDirectory() as root:
            q, out = Path(root)/'queue.json', Path(root)/'report'
            q.write_text(json.dumps(queue))
            with self.assertRaisesRegex(FileNotFoundError, 'no completed outputs'):
                audit.run(q, out)
            self.assertFalse(out.exists())

    def test_frozen_label_hash_tamper_refused(self):
        with patch.object(audit, 'LABELS_SHA256', '0'*64):
            with self.assertRaisesRegex(ValueError, 'stratum labels changed'):
                audit.pinned_labels()

    def test_development_bytes_tamper_refused_before_outputs(self):
        original = audit.sha256_file
        def altered(path):
            return '0'*64 if Path(path).name == 'dev_matched.jsonl' else original(path)
        with patch.object(audit, 'sha256_file', side_effect=altered):
            with self.assertRaisesRegex(ValueError, 'development bytes differ'):
                audit.selected_jobs(self.queue)

    def test_parent_claim_tamper_refused(self):
        original = audit.read_json
        def altered(path):
            value = original(path)
            if Path(path).name == 'manifest.json' and value.get('paired_seed') == 23:
                value = copy.deepcopy(value)
                value['parent']['manifest_sha256'] = '0'*64
            return value
        with patch.object(audit, 'read_json', side_effect=altered):
            with self.assertRaisesRegex(ValueError, 'does not descend'):
                audit.selected_jobs(audit.DEFAULT_QUEUE)

    def test_changed_prediction_score_rejected_by_prerequisite_verifier(self):
        original = output_verifier.read_jsonl
        def altered(path):
            values = original(path)
            if Path(path).name == 'final_dev_greedy.jsonl' and 'pilot_v1_paths_seed17_r1' in str(path):
                values = copy.deepcopy(values)
                values[0]['correct'] = not values[0]['correct']
            return values
        with tempfile.TemporaryDirectory() as root:
            out = Path(root)/'audit'
            with patch.object(output_verifier, 'read_jsonl', side_effect=altered):
                with self.assertRaisesRegex(ValueError, 'Saved score disagrees'):
                    audit.run(self.queue, out)
            self.assertFalse(out.exists())

    def test_recipe_difference_beyond_arm_rejected(self):
        original = audit.read_json
        def altered(path):
            value = original(path)
            if Path(path).name == 'gcm.json':
                value = copy.deepcopy(value)
                value['learning_rate'] *= 2
            return value
        with patch.object(audit, 'read_json', side_effect=altered):
            with self.assertRaisesRegex(ValueError, 'recipes differ beyond arm: learning_rate'):
                audit.selected_jobs(self.queue)

    def test_cross_training_commit_pair_rejected(self):
        original = audit.verify
        def altered(path):
            result = original(path)
            if 'gcm' in Path(path).name:
                result['training_commit'] = '0'*40
            return result
        with tempfile.TemporaryDirectory() as root:
            out = Path(root)/'audit'
            with patch.object(audit, 'verify', side_effect=altered):
                with self.assertRaisesRegex(ValueError, 'different source commits'):
                    audit.run(self.queue, out)
            self.assertFalse(out.exists())

    def test_nonstandard_sample_index_rejected(self):
        original = audit.read_jsonl
        def altered(path):
            values = original(path)
            if Path(path).name == 'final_dev_sampled.jsonl':
                values = copy.deepcopy(values)
                values[0]['sample_index'] = 4
            return values
        with tempfile.TemporaryDirectory() as root:
            out = Path(root)/'audit'
            with patch.object(audit, 'read_jsonl', side_effect=altered):
                with self.assertRaisesRegex(ValueError, 'Sample indices'):
                    audit.run(self.queue, out)
            self.assertFalse(out.exists())


if __name__ == '__main__':
    unittest.main()

import copy
import json
import os
from pathlib import Path
import tempfile
import unittest

from scripts.run_pilot_queue import inspect_queue
from scripts.report_pilot import collect
from src.pilot_data import make_arms, paired_schedule
from src.pilot_runtime import load_pilot_inputs, schedule_filename, validate_pilot_job
from src.sft_data import read_jsonl, sha256_file


ROOT = Path('runs/pilot_replication_seed23_20260909_r1')
QUEUE = Path('configs/pilot_replication_seed23/queue.json')


class ReplicationTests(unittest.TestCase):
    def test_new_seed_changes_order_and_assignment_without_changing_problems(self):
        old_cfg = json.loads(Path('configs/pilot_v1/paths.json').read_text())
        new_cfg = json.loads(Path('configs/pilot_replication_seed23/paths.json').read_text())
        old_train, old_dev, old_broad, old_schedule, _ = load_pilot_inputs(old_cfg)
        train, dev, broad, schedule, _ = load_pilot_inputs(new_cfg)
        self.assertEqual((dev, broad), (old_dev, old_broad))
        self.assertEqual({r['problem_id'] for r in train}, {r['problem_id'] for r in old_train})
        self.assertNotEqual(old_schedule, schedule)
        blocks = json.loads((ROOT/'train_blocks.json').read_text())
        self.assertEqual(schedule, paired_schedule(len(blocks), 4, 23))
        expected = make_arms(blocks, 23)
        self.assertEqual(read_jsonl(ROOT/'train_gcm.jsonl'), expected['gcm'])
        self.assertNotEqual(expected['gcm'], make_arms(blocks, 17)['gcm'])
        for name, digest in json.loads((ROOT/'manifest.json').read_text())['parent']['preserved_files_sha256'].items():
            self.assertEqual(sha256_file(ROOT/name), digest)
            self.assertEqual(sha256_file(Path(old_cfg['data_dir'])/name), digest)
        allowed = {'data_dir', 'data_manifest_sha256', 'seed', 'eval_seed', 'pilot_queue'}
        self.assertEqual({k: v for k, v in old_cfg.items() if k not in allowed},
                         {k: v for k, v in new_cfg.items() if k not in allowed})
        self.assertEqual(new_cfg['eval_seed'], old_cfg['seed'])

    def test_seed17_schedule_fallback_cannot_silently_load_for_seed23(self):
        self.assertEqual(schedule_filename({'paired_seed': 17}), 'schedule_seed17.json')
        with self.assertRaises(ValueError):
            schedule_filename({'paired_seed': 23})
        with self.assertRaises(ValueError):
            schedule_filename({'paired_seed': 23, 'schedule_file': '../schedule_seed23.json'})

    def test_queue_binds_config_run_identity_and_live_contents(self):
        queue = json.loads(QUEUE.read_text())
        job = queue['comparison'][0]
        cfg = json.loads(Path(job['config']).read_text())
        self.assertEqual(validate_pilot_job(cfg, job['run_id'], job['config'])[0], QUEUE)
        with self.assertRaises(ValueError):
            validate_pilot_job(cfg, 'pilot_v1_paths_seed17_r1', job['config'])
        with self.assertRaises(ValueError):
            validate_pilot_job(dict(cfg, seed=17), job['run_id'], job['config'])
        with tempfile.TemporaryDirectory() as directory:
            copied = Path(directory)/'paths.json'
            copied.write_text(Path(job['config']).read_text())
            with self.assertRaises(ValueError):
                validate_pilot_job(cfg, job['run_id'], copied)

    def test_replication_rejects_stale_ledger_and_requires_entire_phase(self):
        queue = json.loads(QUEUE.read_text())
        ledger = {'budget_id': queue['budget_id'], 'authorized_gpu_seconds': 7200,
                  'jobs': [{'run_id': 'historical', 'status': 'completed', 'charged_seconds': 3712}]}
        summary = inspect_queue(queue, 'comparison', ledger)
        self.assertEqual(summary['remaining_seconds'], 3488)
        self.assertEqual(summary['phase_reservation_seconds'], 2130)
        for charged in (1173, 1719, 6000):
            bad = copy.deepcopy(ledger)
            bad['jobs'][0]['charged_seconds'] = charged
            with self.assertRaises(ValueError):
                inspect_queue(queue, 'comparison', bad)

    def test_reporting_two_arm_subset_of_completed_pilot_is_complete(self):
        # Existing real completed artifacts exercise the generalized reporter.
        queue = json.loads(Path('configs/pilot_v1/queue.json').read_text())
        full = collect(queue)
        queue['comparison'] = [j for j in queue['comparison']
                               if json.loads(Path(j['config']).read_text())['arm'] in ('paths', 'gcm')]
        pair = collect(queue)
        self.assertEqual(pair['comparison'], full['comparison'])
        self.assertEqual(pair['comparison']['status'], 'complete')
        self.assertEqual(len(pair['runs']), 3)  # Includes the original calibration receipt.


@unittest.skipUnless(os.environ.get('PILOT_TOKENIZER_DIR'), 'Pinned tokenizer required')
class ReplicationTokenizerTests(unittest.TestCase):
    def test_full_replication_checks_real_tokens_and_original_parent(self):
        from transformers import AutoTokenizer
        from scripts.verify_pilot import verify
        tokenizer = AutoTokenizer.from_pretrained(os.environ['PILOT_TOKENIZER_DIR'], local_files_only=True)
        cfg = json.loads(Path('configs/pilot_replication_seed23/paths.json').read_text())
        audit = verify(cfg, tokenizer)
        self.assertTrue(audit['all_per_update_structures_equal'])
        self.assertTrue(audit['all_per_example_tokens_equal'])
        self.assertEqual(audit['budget_per_arm']['supervised_response_tokens'], 267456)
        self.assertEqual(audit['budget_per_arm']['padding_tokens'], 0)


if __name__ == '__main__':
    unittest.main()

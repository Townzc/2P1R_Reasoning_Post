import copy
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest

from src.pilot_data import (allocate_groups, surface_response, make_arms,
                            paired_schedule, audit_arms, verify_row)
from scripts.run_pilot_queue import inspect_queue
from src.evaluation import score_token_caps
from src.pilot_runtime import load_pilot_inputs


def example_blocks():
    return json.loads(Path('runs/exact_matching_muldiv_4096_20260905/candidate_blocks.json').read_text())[:2]


class PilotTests(unittest.TestCase):
    def test_same_continuation_cap_scores_and_eos_are_separate(self):
        class Tokenizer:
            eos_token_id = 0
            def decode(self, tokens, **kwargs):
                return ''.join(chr(t) for t in tokens if t != 0)
        tokens = list(map(ord, 'Answer: (1+2+3+4)')) + [0, 0]
        row = {'problem_id': 'x', 'numbers': [1,2,3,4], 'target': 10}
        short, full = 5, len(tokens)
        scores = score_token_caps(tokens, Tokenizer(), row, [short, full], full)
        self.assertTrue(scores[str(short)]['truncated'])
        self.assertFalse(scores[str(short)]['correct'])
        self.assertTrue(scores[str(full)]['correct'])
        self.assertTrue(scores[str(full)]['eos'])
        self.assertEqual(scores[str(full)]['output_tokens'], full-1)
        with self.assertRaises(ValueError):
            score_token_caps(tokens, Tokenizer(), row, [full+1], full)

    def test_raw_split_precedes_path_augmentation_and_reproduces(self):
        a = allocate_groups(17, {'train': 10, 'dev': 4, 'holdout': 4}, max_number=8)
        self.assertEqual(a, allocate_groups(17, {'train': 10, 'dev': 4, 'holdout': 4}, max_number=8))
        groups = [tuple(g) for values in a.values() for g in values]
        self.assertEqual(len(groups), len(set(groups)))
        self.assertTrue(all(len(g) == 4 and tuple(sorted(g)) == g for g in groups))
        with self.assertRaises(ValueError):
            allocate_groups(17, {'train': 80}, max_number=8)

    def test_richer_surface_preserves_equations_and_final_expression(self):
        row = example_blocks()[0]['problems'][0]['paths'][0]
        variants = [surface_response(row['response'], v) for v in range(4)]
        self.assertEqual(len(set(variants)), 4)
        for response in variants:
            verify_row(dict(row, response=response))
            self.assertEqual(response.splitlines()[-1], row['response'].splitlines()[-1])
        with self.assertRaises(ValueError):
            verify_row(dict(row, response=row['response'].replace(' = ', ' = 999 + ', 1)))

    def test_paths_change_per_problem_but_gcm_is_fixed_over_cycles(self):
        rows = make_arms(example_blocks(), 17)
        schedule = paired_schedule(2, 4, 17)
        self.assertEqual(schedule, paired_schedule(2, 4, 17))
        self.assertEqual(len(schedule), 32)
        for arm in rows:
            seen = {}
            for batch in schedule:
                for i in batch:
                    r = rows[arm][i]
                    seen.setdefault(r['problem_id'], []).append(r['path_id'])
            self.assertEqual(set(map(len, seen.values())), {16})
            self.assertEqual({len(set(v)) for v in seen.values()}, {4 if arm == 'paths' else 1})

    def test_stale_ledger_and_partial_phase_budget_are_rejected(self):
        queue = {'budget_id': 'b', 'minimum_prior_charged_seconds': 1173,
                 'comparison': [{'run_id': 'a', 'max_seconds': 1050}, {'run_id': 'b', 'max_seconds': 1050}]}
        ledger = {'budget_id': 'b', 'authorized_gpu_seconds': 7200,
                  'jobs': [{'run_id': 'old', 'status': 'completed', 'charged_seconds': 1173}]}
        self.assertEqual(inspect_queue(queue, 'comparison', ledger)['phase_reservation_seconds'], 2130)
        for value in [737, 6000]:
            bad = copy.deepcopy(ledger)
            bad['jobs'][0]['charged_seconds'] = value
            with self.assertRaises(ValueError): inspect_queue(queue, 'comparison', bad)
        bad = copy.deepcopy(ledger)
        bad['jobs'][0]['status'] = 'reserved'
        with self.assertRaises(ValueError): inspect_queue(queue, 'comparison', bad)

    def test_committed_pilot_loads_and_detects_postfreeze_data_tampering(self):
        cfg = json.loads(Path('configs/pilot_v1/calibration.json').read_text())
        rows, dev, broad, schedule, _ = load_pilot_inputs(cfg)
        self.assertEqual((len(rows), len(dev), len(broad), len(schedule)), (1024, 64, 64, 1024))
        with tempfile.TemporaryDirectory() as directory:
            copy_root = Path(directory)/'data'
            shutil.copytree(cfg['data_dir'], copy_root)
            cfg = dict(cfg, data_dir=str(copy_root))
            with (copy_root/'train_paths.jsonl').open('a') as f:
                f.write('\n')
            with self.assertRaises(ValueError): load_pilot_inputs(cfg)


@unittest.skipUnless(os.environ.get('PILOT_TOKENIZER_DIR'), 'Pinned tokenizer required for integration audit')
class PilotTokenizerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from transformers import AutoTokenizer
        cls.tokenizer = AutoTokenizer.from_pretrained(os.environ['PILOT_TOKENIZER_DIR'], local_files_only=True)

    def test_exact_real_tokenizer_matching_and_all_exposures(self):
        rows = make_arms(example_blocks(), 17)
        audit = audit_arms(rows, paired_schedule(2, 4, 17), self.tokenizer)
        self.assertTrue(audit['all_per_example_tokens_equal'])
        self.assertEqual(audit['paths_gcm_structure_tv'], 0)
        self.assertEqual(len({a['supervised_response_tokens'] for a in audit['arms'].values()}), 1)
        self.assertEqual(len({a['padding_tokens'] for a in audit['arms'].values()}), 1)

    def test_changed_global_assignment_and_added_supervision_are_rejected(self):
        rows = make_arms(example_blocks(), 17)
        rows['gcm'][0] = rows['paths'][1]
        with self.assertRaises(ValueError):
            audit_arms(rows, paired_schedule(2, 4, 17), self.tokenizer)
        rows = make_arms(example_blocks(), 17)
        rows['surface'][0]['response'] += '\nExtra supervision.'
        with self.assertRaises(ValueError):
            audit_arms(rows, paired_schedule(2, 4, 17), self.tokenizer)


if __name__ == '__main__':
    unittest.main()

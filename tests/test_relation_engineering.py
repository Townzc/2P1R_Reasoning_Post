import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scripts.run_relation_engineering import check_ledger
from scripts.audit_relation_engineering_outputs import audit_predictions, audit
from src.relation_engineering import (CONFIG, validate_schedule, score_completion,
                                       summarize, load_frozen)
from src.relation_transport import make_world, allocation_schedule, views, render_prompt
from src.relation_experiment import accumulate_gradients, profile, engineering_gate
from src.sft_data import collate, shifted_loss_sum, sha256_file

CFG = json.loads(CONFIG.read_text())


class ScoringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.world = make_world(902, 1, split='unit_fixture')
        cls.row = {'problem_id': cls.world['world_id'], 'view': 'clean',
                   'prompt': cls.world['prompt'], 'answer': cls.world['answer']}

    def test_all_legal_routes_not_only_exact_anchor(self):
        for response in self.world['responses']:
            self.assertTrue(score_completion(self.row, response, True, False)['complete_correct'])

    def test_answer_only_and_no_eos_are_not_complete(self):
        score = score_completion(self.row, f"Answer : {self.world['answer']}", True, False)
        self.assertTrue(score['answer_correct']); self.assertFalse(score['complete_correct'])
        self.assertFalse(score_completion(self.row, self.world['responses'][0], False, True)['complete_correct'])

    def test_outer_whitespace_only(self):
        text = self.world['responses'][0]
        self.assertTrue(score_completion(self.row, ' \n'+text+'\n\t', True, False)['complete_correct'])
        self.assertFalse(score_completion(self.row, text.replace('E ', 'E  ', 1), True, False)['complete_correct'])

    def test_deleted_evidence_invalidates_removed_proof(self):
        w = self.world
        q, answer = views(w)['useful_delete']
        row = {**self.row, 'prompt': render_prompt(q), 'answer': answer}
        scores = [score_completion(row, t, True, False)['complete_correct'] for t in w['responses']]
        self.assertEqual(sum(scores), 1)
        self.assertTrue(scores[w['intervention']['keep_route']])

    def test_token_stream_and_identity_tampering_rejected(self):
        class Tokens:
            eos_token_id = 2
            def __len__(self): return 300
            def decode(self, ids, **kwargs): return ''.join(chr(i-3) for i in ids)
        text = self.world['responses'][0]
        ids = [ord(c)+3 for c in text]+[2]
        cfg = {**CFG, 'max_new_tokens': 1000}
        prediction = {**self.row, 'text': text, 'generated_ids': ids, 'generated_tokens': len(ids),
                      'score': score_completion(self.row, text, True, False)}
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder)/'predictions.jsonl'
            p.write_text(json.dumps(prediction)+'\n')
            self.assertEqual(len(audit_predictions(p, [self.row], Tokens(), cfg)), 1)
            for mutation in ({'text': text+'x'}, {'answer': -1}, {'generated_ids': [2]+ids},
                             {'score': {**prediction['score'], 'complete_correct': False}},
                             {'generated_ids': ids[:-1], 'generated_tokens': len(ids)-1}):
                p.write_text(json.dumps({**prediction, **mutation})+'\n')
                with self.assertRaises(ValueError): audit_predictions(p, [self.row], Tokens(), cfg)


class DoseTests(unittest.TestCase):
    def setUp(self):
        ids = [f'fixture_{i}' for i in range(32)]
        self.rows = [{'problem_id': w, 'path_id': str(r)} for w in ids for r in range(4)]
        index = {(r['problem_id'], int(r['path_id'])): i for i, r in enumerate(self.rows)}
        self.schedule = [[index[(w, r)] for w, r in zip(u['world_ids'], u['multi'])]
                         for u in allocation_schedule(ids, CFG['assignment_seed'], CFG['cycles'])['updates']]

    def test_complete_eight_cycle_allocation(self):
        validate_schedule(self.rows, self.schedule, CFG)
        self.assertEqual(len(self.schedule), 256)

    def test_missing_round_repeated_problem_and_wrong_slot_rejected(self):
        for schedule in (self.schedule[:-1], copy.deepcopy(self.schedule)):
            if len(schedule) == 256:
                schedule[0][1] = schedule[0][0]
            with self.assertRaises(ValueError): validate_schedule(self.rows, schedule, CFG)
        wrong = copy.deepcopy(self.schedule)
        wrong[0][0] = wrong[0][0]//4*4 + (wrong[0][0]+1)%4
        with self.assertRaises(ValueError): validate_schedule(self.rows, wrong, CFG)

    def test_gradients_equal_unsplit_token_normalized_objective(self):
        import torch
        class Tiny(torch.nn.Module):
            def __init__(self):
                super().__init__(); self.embed = torch.nn.Embedding(11, 7); self.linear = torch.nn.Linear(7, 11)
            def forward(self, input_ids, **kwargs):
                return SimpleNamespace(logits=self.linear(self.embed(input_ids)))
        torch.manual_seed(8)
        model = Tiny().double()
        rows = [dict(input_ids=[3,4,5,2], labels=[-100,-100,5,2], n_supervised=2),
                dict(input_ids=[6,7,8,9,2], labels=[-100,7,8,9,2], n_supervised=4)]
        batch = collate(rows, 2)
        target_loss = shifted_loss_sum(model(batch['input_ids']).logits, batch['labels'])/6
        target_loss.backward()
        reference = [p.grad.clone() for p in model.parameters()]
        for micro in (1,2):
            model.zero_grad(set_to_none=True)
            actual = accumulate_gradients(model, rows, 2, micro, 'cpu')
            self.assertAlmostEqual(actual, target_loss.item(), places=6)
            for p, expected in zip(model.parameters(), reference):
                torch.testing.assert_close(p.grad, expected, rtol=1e-6, atol=1e-7)

    def test_profile_window_and_strict_gate(self):
        history = [dict(seconds=10 if i<8 else 2, supervised_tokens=404, processed_tokens=4548,
                        peak_allocated_mib=100, peak_reserved_mib=110) for i in range(256)]
        result = profile(history, CFG)
        self.assertEqual(result['supervised_tokens_per_second'], 202)
        self.assertEqual(result['profile_updates'], 64)
        stats = {'n': 32, 'complete_correct': 32, 'truncated': 0}
        self.assertTrue(engineering_gate(CFG, 256, result, stats, .1)['passed'])
        self.assertFalse(engineering_gate(CFG, 255, result, stats, .1)['passed'])
        self.assertFalse(engineering_gate(CFG, 256, result, {**stats, 'complete_correct': 31}, .1)['passed'])
        self.assertFalse(engineering_gate(CFG, 256, result, stats, float('nan'))['passed'])


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)/'ledger.json'
        self.ledger = {'budget_id': 'unit', 'authorized_gpu_seconds': 7200,
                       'jobs': [{'run_id': f'old_{i}', 'status': 'completed', 'charged_seconds': 1 if i<14 else 5726} for i in range(15)]}
        self.path.write_text(json.dumps(self.ledger))
        # A retained real E011 directory now exists. Budget unit fixtures must
        # not reuse a historical experiment identity or depend on its absence.
        self.cfg = {**CFG, 'run_id': f'fixture_{self.path.parent.name}',
                    'expected_ledger_sha256': hashlib.sha256(self.path.read_bytes()).hexdigest()}
        self.budget = {'budget_id': 'unit', 'authorized_gpu_seconds': 7200, 'gpus': 1}

    def test_whole_phase_fits_without_reserving(self):
        before = self.path.read_bytes()
        result = check_ledger(self.cfg, self.path, self.budget)
        self.assertEqual(result['remaining_seconds'], 1460)
        self.assertEqual(result['maximum_reservation_seconds'], 735)
        self.assertEqual(self.path.read_bytes(), before)

    def test_absent_stale_reserved_and_used_ledgers_block(self):
        with self.assertRaises(ValueError): check_ledger(self.cfg, self.path.parent/'absent', self.budget)
        variants = []
        stale = copy.deepcopy(self.ledger); stale['jobs'][-1]['charged_seconds'] -= 1024; variants.append(stale)
        reserved = copy.deepcopy(self.ledger); reserved['jobs'][0]['status'] = 'reserved'; variants.append(reserved)
        used = copy.deepcopy(self.ledger); used['jobs'][0]['run_id'] = self.cfg['run_id']; variants.append(used)
        for ledger in variants:
            self.path.write_text(json.dumps(ledger))
            with self.assertRaises(ValueError): check_ledger(self.cfg, self.path, self.budget)

    def test_shortened_cap_and_authorization_change_block(self):
        with self.assertRaises(ValueError): check_ledger({**self.cfg, 'max_seconds': 1460}, self.path, self.budget)
        with self.assertRaises(ValueError): check_ledger(self.cfg, self.path, {**self.budget, 'authorized_gpu_seconds': 8000})

    def test_watchdog_rechecks_hash_and_full_cap_under_lock_without_child(self):
        from scripts.run_bounded import main
        budget_path = self.path.parent/'budget.json'
        budget_path.write_text(json.dumps(self.budget))
        argv = ['run_bounded', '--run-id', 'fixture_under_lock', '--ledger', str(self.path),
                '--budget', str(budget_path), '--max-seconds', '720', '--expected-ledger-sha256',
                '0'*64, '--require-full-cap', '--', 'unused-child']
        with patch('scripts.run_bounded.shutil.which', return_value='timeout'), patch('scripts.run_bounded.subprocess.Popen') as child:
            with patch('sys.argv', argv), self.assertRaisesRegex(ValueError, 'under lock'):
                main()
            argv[argv.index('0'*64)] = self.cfg['expected_ledger_sha256']
            argv[argv.index('720')] = '1460'
            with patch('sys.argv', argv), self.assertRaisesRegex(RuntimeError, 'no shortened job'):
                main()
            child.assert_not_called()
        self.assertEqual(json.loads(self.path.read_text()), self.ledger)


class OutputAuditTests(unittest.TestCase):
    def test_complete_synthetic_receipt_and_corruption_rejection(self):
        # Generated fixture certificates, never model predictions or experimental results.
        class Tokens:
            eos_token_id = 2
            def __len__(self): return 300
            def decode(self, ids, **kwargs): return ''.join(chr(i-3) for i in ids)
        w = make_world(903, 2, split='unit_fixture')
        base = {'problem_id': w['world_id'], 'view': 'clean', 'prompt': w['prompt'], 'answer': w['answer']}
        text = w['responses'][0]; ids = [ord(c)+3 for c in text]+[2]
        prediction = {**base, 'text': text, 'generated_ids': ids, 'generated_tokens': len(ids),
                      'score': score_completion(base, text, True, False)}
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); out = root/'synthetic_e011'; out.mkdir()
            data_dir = root/'input'; data_dir.mkdir(); (data_dir/'manifest.json').write_text('{}')
            cfg = {**CFG, 'run_id': out.name, 'data_dir': str(data_dir), 'steps': 2,
                   'train_count': 1, 'dev_views': ['clean'], 'overfit_required_correct': 1,
                   'max_new_tokens': 1000, 'profile_warmup': 0, 'profile_updates': 2}
            budget = {'per_update': [{'supervised_tokens': 2, 'processed_tokens': 5}]*2}
            history = [dict(step=i+1, seconds=.2, response_nll=.1, grad_norm=1,
                            supervised_tokens=2, processed_tokens=5, peak_allocated_mib=10,
                            peak_reserved_mib=12) for i in range(2)]
            throughput = profile(history, cfg); stats = summarize([prediction])
            metrics = {'steps': 2, 'train': stats, 'baseline_dev_clean': stats,
                       'dev_by_view': {'clean': stats}, 'throughput': throughput,
                       'train_reference_nll': {'reference_count': 1, 'supervised_tokens': 2, 'response_loss_sum': .2, 'nll': .1},
                       'engineering_gate': engineering_gate(cfg, 2, throughput, stats, .1)}
            files = {'run_manifest.json': {'status': 'completed', 'steps_completed': 2, 'config': cfg,
                        'source_files_sha256': {}, 'data_manifest_sha256': sha256_file(data_dir/'manifest.json')},
                     'actual_budget.json': budget, 'planned_budget.json': budget, 'throughput.json': throughput,
                     'metrics.json': metrics, 'evaluation_metrics.json': metrics,
                     'resource_receipt.json': {'run_id': cfg['run_id'], 'status': 'completed', 'exit_code': 0,
                           'max_seconds': 720, 'charged_seconds': 2, 'elapsed_seconds': 1.5},
                     'checkpoint_manifest.json': {'kind': 'model_weights_only_not_optimizer_or_rng_resume',
                                                  'files': {'synthetic.safetensors': {}}}}
            for name, obj in files.items(): (out/name).write_text(json.dumps(obj))
            for name in ('base_dev_clean.jsonl', 'final_train.jsonl', 'final_dev.jsonl'):
                (out/name).write_text(json.dumps(prediction)+'\n')
            (out/'train_history.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in history))
            frozen = (cfg, {'source_files_sha256': {}}, [], {'train': [base], 'dev': [base]},
                      [{'n_supervised': 2}], [[0], [0]], budget)
            with patch('scripts.audit_relation_engineering_outputs.load_frozen', return_value=frozen):
                self.assertTrue(audit(out, Tokens())['verified_compact_outputs'])
                for name, mutation in (
                    ('run_manifest.json', {'status': 'failed'}),
                    ('resource_receipt.json', {'charged_seconds': 1000}),
                    ('throughput.json', {'profile_complete': False}),
                    ('metrics.json', {'steps': 1}),
                    ('checkpoint_manifest.json', {'files': {}}),
                ):
                    (out/name).write_text(json.dumps({**files[name], **mutation}))
                    with self.assertRaises(ValueError): audit(out, Tokens())
                    (out/name).write_text(json.dumps(files[name]))


@unittest.skipUnless(os.environ.get('RELATION_ENGINEERING_TOKENIZER_DIR'), 'Prepared-data regression requires the pinned local tokenizer')
class ReleaseTests(unittest.TestCase):
    def test_published_compact_subset_and_exact_full_dose(self):
        from scripts.audit_family_matching import verified_tokenizer
        tokenizer, _ = verified_tokenizer(Path(os.environ['RELATION_ENGINEERING_TOKENIZER_DIR']))
        cfg, manifest, rows, evaluation, encoded, schedule, budget = load_frozen(tokenizer)
        self.assertEqual(len(rows), 128); self.assertEqual(len(evaluation['dev']), 48)
        self.assertEqual(budget['supervised_response_tokens'], 103424)
        self.assertEqual(budget['processed_nonpadding_tokens'], 1164288)
        self.assertEqual(budget['padding_tokens'], 0)
        self.assertEqual(set(budget['problem_exposures'].values()), {32})
        self.assertEqual(set(budget['row_exposures'].values()), {8})


if __name__ == '__main__':
    unittest.main()

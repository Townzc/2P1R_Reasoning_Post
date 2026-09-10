"""Synthetic raw records exercise E015's independent audit without model loading."""
import copy
from contextlib import ExitStack, nullcontext
import json
import math
import os
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch

import torch

from analyses.e014 import reference_measurement, stream_hash, token_hash
from analyses.e015_audit import (ARTIFACTS, CHECKPOINT_CONFIG, PHASES, audit,
                                 audit_all_reference, audited_learning_rate)
from src.real_math_engineering import engineering_gate, score_completion, summarize
from src.relation_experiment import profile
from src.sft_data import budget_report, update_schedule


class Tokens:
    eos_token_id = 2
    pad_token_id = 2
    eos_token = '<eos>'

    def __len__(self):
        return 300

    def decode(self, ids, **kwargs):
        return ''.join(chr(i - 3) for i in ids)


def measured_reference(case, mismatch=False, tie=False):
    target = case['target_ids']
    logits = torch.full((len(case['prompt_ids']) + len(target), 300), -3.0)
    for j, token in enumerate(target):
        logits[len(case['prompt_ids']) + j - 1, token] = 5
    if mismatch or tie:
        logits[len(case['prompt_ids']) - 1, 0] = 5 if tie else 6
    record = reference_measurement(logits, case, [{'kind': 'reference_eos',
        'target_position': len(target) - 1, 'alternative_id': None}])
    shifted = logits[len(case['prompt_ids']) - 1:-1]
    logp = torch.log_softmax(shifted, -1)
    gold = shifted.gather(1, torch.tensor(target)[:, None])[:, 0]
    values, ids = shifted.topk(2, dim=-1)
    other = torch.where(ids[:, 0] == torch.tensor(target), values[:, 1], values[:, 0])
    record['argmax_log_probability'] = logp.max(-1).values.tolist()
    record['target_minus_argmax_logit'] = (gold - shifted.max(-1).values).tolist()
    record['target_minus_best_other_logit'] = (gold - other).tolist()
    return record


class CompleteAuditFixture(unittest.TestCase):
    def setUp(self):
        torch.set_num_threads(1)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.run = root / 'run'
        self.run.mkdir()
        self.inputs = root / 'inputs'
        self.inputs.mkdir()
        self.release = root / 'release.json'
        self.release.write_text('{}')
        self.cfg = {'run_id': 'fixture_e015', 'max_seconds': 360, 'guard_seconds': 15,
                    'model_vocab_size': 300}
        self.old_cfg = {'train_count': 32, 'steps': 256, 'batch_size': 4, 'microbatch_size': 1,
                        'profile_warmup': 8, 'profile_updates': 64, 'max_new_tokens': 768,
                        'overfit_required_correct': 31, 'overfit_max_nll': .1}
        train = [{'problem_id': f'p{i}', 'prompt': f'fixture {i}', 'answer': '1',
                  'response': r'\boxed{1}'} for i in range(32)]
        self.encoded, self.cases, predictions, references = [], [], [], []
        for i, row in enumerate(train):
            prompt = [7, 8, 9]
            target = [ord(c) + 3 for c in row['response']] + [2]
            self.encoded.append({'problem_id': row['problem_id'], 'input_ids': prompt + target,
                                 'n_prompt': len(prompt), 'n_supervised': len(target),
                                 'n_processed': len(prompt) + len(target),
                                 'path_id': '0', 'response_hash': token_hash(target)})
            case = {'problem_id': row['problem_id'], 'row_index': i, 'prompt_ids': prompt,
                    'target_ids': target, 'prompt_ids_sha256': token_hash(prompt),
                    'target_ids_sha256': token_hash(target), 'selected_for_batch1': False}
            self.cases.append(case)
            predictions.append({**row, 'text': row['response'], 'generated_ids': target,
                                'generated_tokens': len(target),
                                'score': score_completion(row, row['response'], True, False)})
            references.append(measured_reference(case))
        schedule = update_schedule(32, 256, 4, 17)
        planned = json.loads(json.dumps(budget_report(self.encoded, schedule, 1)))
        # Literal vector construction independently fixes the 192/64 boundary.
        expected_lr = [5e-5] * 192 + [2.5e-5 * (1 + math.cos(j * math.pi / 64)) for j in range(1, 65)]
        history = [{'step': i + 1, 'row_indices': indices, **counts,
                    'actual_learning_rate': lr, 'response_nll': .01, 'grad_norm': .1,
                    'seconds': .01, 'peak_allocated_mib': 12.0, 'peak_reserved_mib': 16.0}
                   for i, (indices, counts, lr) in enumerate(zip(schedule, planned['per_update'], expected_lr))]
        throughput, stats = profile(history, self.old_cfg), summarize(predictions)
        count = sum(record['supervised_tokens'] for record in references)
        loss = math.fsum(record['loss_sum'] for record in references)
        self.metrics = {'steps': 256, 'train': stats, 'throughput': throughput,
                        'train_reference_nll': {'response_loss_sum': loss, 'supervised_tokens': count,
                                                'reference_count': 32, 'nll': loss / count},
                        'reference_top1_correct': count, 'reference_eos_top1_correct': 32,
                        'lr_accounting': {'nonzero_lr_updates': 255, 'summed_lr': math.fsum(expected_lr)},
                        'engineering_gate': engineering_gate(self.old_cfg, 256, throughput, stats, loss / count)}
        for name, rows in [('train_history.jsonl', history), ('final_train.jsonl', predictions),
                           ('reference_tokens.jsonl', references)]:
            self.write_rows(name, rows)
        self.write_json('planned_budget.json', planned)
        self.write_json('actual_budget.json', planned)
        self.write_json('throughput.json', throughput)
        self.write_json('metrics.json', self.metrics)
        self.write_json('base_reference_nll.json', {'response_loss_sum': count * .2,
                        'supervised_tokens': count, 'reference_count': 32, 'nll': .2})
        self.checkpoint_files = {}
        original_names = json.loads(Path('runs/gsm8k_overfit_e013_r1/checkpoint_manifest.json').read_text())['files']
        for name in original_names:
            content = (json.dumps({**CHECKPOINT_CONFIG, 'dtype': 'float32'}).encode()
                       if name == 'config.json' else ('fixture ' + name).encode())
            self.checkpoint_files[name] = content
        import hashlib
        checkpoint = {'kind': 'weights_only_not_optimizer_rng_resume', 'files': {
            name: {'bytes': len(content), 'sha256': hashlib.sha256(content).hexdigest()}
            for name, content in self.checkpoint_files.items()}}
        self.write_json('checkpoint_manifest.json', checkpoint)
        self.original_checkpoint = root / 'original_checkpoint.json'
        self.original_checkpoint.write_text(json.dumps(checkpoint))
        phases = {key: .1 for key in PHASES}
        phases['training'] = sum(record['seconds'] for record in history)
        self.write_json('phase_timings.json', {'completed_phases_seconds': phases, 'process_wall_seconds': 4.0})
        self.write_json('resource_receipt.json', {'run_id': self.cfg['run_id'], 'status': 'completed',
                        'exit_code': 0, 'max_seconds': 360, 'elapsed_seconds': 4.1, 'charged_seconds': 5})
        (self.inputs / 'manifest.json').write_text(json.dumps({'source_files_sha256': {}}))
        self.manifest = {'status': 'completed', 'phase': 'E015', 'config': self.cfg,
                         'release_sha256': stream_hash(self.release), 'source_files_sha256': {},
                         'steps_completed': 256, 'training_updates': 256, 'model_execution_performed': True,
                         'weights': 'fresh_pinned_Qwen2.5_1.5B_base', 'parameter_dtype': 'float32',
                         'autocast_dtype': 'bfloat16', 'attention': 'sdpa', 'tf32': False,
                         'optimizer': 'AdamW_foreach_false', 'official_test_evaluation': False,
                         'development_evaluation': False}
        self.rehash()
        self.state = (self.cfg, self.old_cfg, train, self.encoded, schedule, planned, self.cases)
        self.patches = [patch('analyses.e015_audit.load_release', return_value=self.state),
                        patch('analyses.e015_audit.RELEASE', self.release),
                        patch('analyses.e015_audit.INPUTS', self.inputs),
                        patch('analyses.e015_audit.ORIGINAL_CHECKPOINT', self.original_checkpoint)]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)

    def write_json(self, name, value):
        (self.run / name).write_text(json.dumps(value))

    def write_rows(self, name, rows):
        (self.run / name).write_text(''.join(json.dumps(row) + '\n' for row in rows))

    def read_rows(self, name):
        return [json.loads(line) for line in (self.run / name).read_text().split('\n') if line]

    def rehash(self):
        self.manifest['artifact_sha256'] = {name: stream_hash(self.run / name) for name in ARTIFACTS}
        self.write_json('run_manifest.json', self.manifest)

    def checked(self):
        return audit(Tokens(), self.run)

    def test_complete_compact_fixture_and_actual_checkpoint_evidence(self):
        result = self.checked()
        self.assertEqual(result['updates_checked'], 256)
        self.assertEqual(result['raw_generation_streams_checked'], 32)
        self.assertEqual(result['reference_targets_checked'], sum(len(case['target_ids']) for case in self.cases))
        self.assertFalse(result['checkpoint_weights_rehashed'])
        self.assertFalse(result['independent_checkpoint_backup_verified'])
        folder = self.run / 'checkpoint_final'
        folder.mkdir()
        for name, content in self.checkpoint_files.items():
            (folder / name).write_bytes(content)
        self.assertTrue(self.checked()['checkpoint_weights_rehashed'])
        (folder / 'model-00001-of-00002.safetensors').write_bytes(b'tampered')
        with self.assertRaises(ValueError):
            self.checked()

    def test_learning_rate_boundaries_and_invalid_steps(self):
        self.assertEqual(audited_learning_rate(192), 5e-5)
        self.assertLess(audited_learning_rate(193), 5e-5)
        self.assertGreater(audited_learning_rate(255), 0)
        self.assertEqual(audited_learning_rate(256), 0)
        for step in (0, 257, True, 1.5):
            with self.subTest(step=step), self.assertRaises(ValueError):
                audited_learning_rate(step)

    def test_rehashed_history_lr_order_dose_and_nonfinite_corruption(self):
        original = self.read_rows('train_history.jsonl')
        variants = [(191, 'actual_learning_rate', audited_learning_rate(193)),
                    (192, 'actual_learning_rate', 5e-5), (255, 'actual_learning_rate', 1e-9),
                    (0, 'row_indices', [0, 1, 2, 3]), (0, 'supervised_tokens', 1),
                    (0, 'response_nll', float('nan')), (0, 'seconds', 0)]
        for index, key, value in variants:
            bad = copy.deepcopy(original)
            bad[index][key] = value
            self.write_rows('train_history.jsonl', bad)
            self.rehash()
            with self.subTest(key=key, index=index), self.assertRaises(ValueError):
                self.checked()

    def test_rehashed_prediction_score_and_missing_row_fail(self):
        rows = self.read_rows('final_train.jsonl')
        bad = copy.deepcopy(rows)
        bad[0]['score']['terminated_correct'] = False
        for variant in (bad, rows[:-1]):
            self.write_rows('final_train.jsonl', variant)
            self.rehash()
            with self.assertRaises(ValueError):
                self.checked()

    def test_rehashed_reference_arrays_shift_and_vocabulary_corruption(self):
        original = self.read_rows('reference_tokens.jsonl')
        for field, value in [('argmax_log_probability', [0]), ('target_minus_argmax_logit', [1]),
                             ('target_minus_best_other_logit', [-1]), ('argmax_ids', [300]),
                             ('target_nll', [-1])]:
            bad = copy.deepcopy(original)
            bad[0][field][0] = value[0]
            self.write_rows('reference_tokens.jsonl', bad)
            self.rehash()
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.checked()
        bad = copy.deepcopy(original)
        bad[0]['queries'][0]['causal_logit_index'] += 1
        self.write_rows('reference_tokens.jsonl', bad)
        self.rehash()
        with self.assertRaises(ValueError):
            self.checked()

    def test_extra_dev_decode_is_rejected_without_manifest_claim(self):
        (self.run / 'final_dev.jsonl').write_text('{}\n')
        with self.assertRaises(ValueError):
            self.checked()

    def test_aggregate_gate_receipt_and_checkpoint_allowlist_are_checked(self):
        self.metrics['engineering_gate']['passed'] = not self.metrics['engineering_gate']['passed']
        self.write_json('metrics.json', self.metrics)
        self.rehash()
        with self.assertRaises(ValueError):
            self.checked()
        self.metrics['engineering_gate']['passed'] = not self.metrics['engineering_gate']['passed']
        self.write_json('metrics.json', self.metrics)
        self.rehash()
        receipt = json.loads((self.run / 'resource_receipt.json').read_text())
        receipt['charged_seconds'] = 4
        self.write_json('resource_receipt.json', receipt)
        with self.assertRaises(ValueError):
            self.checked()
        receipt['charged_seconds'] = 5
        self.write_json('resource_receipt.json', receipt)
        checkpoint = json.loads((self.run / 'checkpoint_manifest.json').read_text())
        checkpoint['files'].pop('tokenizer.json')
        self.write_json('checkpoint_manifest.json', checkpoint)
        self.rehash()
        with self.assertRaises(ValueError):
            self.checked()

    def test_valid_wrong_top_one_and_zero_margin_tie_are_distinct(self):
        for kwargs in ({'mismatch': True}, {'tie': True}):
            record = measured_reference(self.cases[0], **kwargs)
            audit_all_reference(record, self.cases[0], 300)
            self.assertNotEqual(record['argmax_ids'][0], self.cases[0]['target_ids'][0])
            if kwargs.get('tie'):
                self.assertEqual(record['target_minus_argmax_logit'][0], 0)

    def test_complete_worker_file_lifecycle_passes_independent_audit(self):
        """Exercise worker serialization/phase ownership; fake computation is explicit."""
        from analyses.e015 import worker
        fixture = self
        self.cfg.update(self.old_cfg, seed=17, learning_rate=5e-5, weight_decay=.01,
                        expected_ledger_sha256='fixture-ledger')
        baseline = json.loads((self.run / 'base_reference_nll.json').read_text())
        predictions = self.read_rows('final_train.jsonl')
        history_template = self.read_rows('train_history.jsonl')
        parent = self.run.parent
        output = parent / 'runs' / self.cfg['run_id']
        output.mkdir(parents=True)
        preflight = parent / 'worker_preflight.json'
        source = {'source_commit': '0' * 40, 'source_worktree_dirty': False, 'source_files_sha256': {}}
        preflight.write_text(json.dumps({'phase': 'E015', 'source_commit': source['source_commit'],
            'release_sha256': stream_hash(self.release), 'server': {'model': {'all_files_verified': True}},
            'accounting': {'ledger_sha256': 'fixture-ledger'}, 'tokenizer': {},
            'rental': {'power_on_at_utc': '2026-09-10T00:00:00+00:00', 'time_source': 'provider_timestamp'}}))

        class FakeModel(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.weight = torch.nn.Parameter(torch.zeros(1))
                self.config = types.SimpleNamespace(vocab_size=300, use_cache=False)

            def cuda(self):
                return self

            def gradient_checkpointing_enable(self, **kwargs):
                pass

            def gradient_checkpointing_disable(self):
                pass

            def forward(self, input_ids, **kwargs):
                # A synthetic oracle only supplies controlled logits for serialization QA.
                logits = torch.full((*input_ids.shape, 300), -3.0)
                logits[:, :-1].scatter_(2, input_ids[:, 1:, None], 5.0)
                return types.SimpleNamespace(logits=logits)

            def save_pretrained(self, path, **kwargs):
                Path(path).mkdir()
                for name, content in fixture.checkpoint_files.items():
                    (Path(path) / name).write_bytes(content)

        def fake_training(model, optimizer, encoded, schedule, cfg, pad_id, log, history):
            for original in history_template:
                row = {**original, 'seconds': 1e-6}
                history.append(row)
                log.write(json.dumps(row) + '\n')
            return history

        def fake_generation(model, tokenizer, rows, cfg, path):
            with Path(path).open('x') as stream:
                for record in predictions:
                    stream.write(json.dumps(record) + '\n')
            return predictions

        tensor = torch.tensor
        def cpu_tensor(*args, **kwargs):
            if str(kwargs.get('device', '')).startswith('cuda'):
                kwargs['device'] = 'cpu'
            return tensor(*args, **kwargs)

        cwd = Path.cwd()
        try:
            os.chdir(parent)
            with ExitStack() as stack:
                for target, value in (
                    ('analyses.e015.load_release', self.state),
                    ('analyses.e015.provenance', source),
                    ('analyses.e015.rental_window', {}),
                    ('analyses.e015.reference_nll', baseline),
                    ('torch.cuda.is_available', True),
                    ('torch.cuda.synchronize', None),
                    ('torch.cuda.reset_peak_memory_stats', None),
                ):
                    stack.enter_context(patch(target, return_value=value))
                stack.enter_context(patch('analyses.e015.RELEASE', self.release))
                stack.enter_context(patch('analyses.e015.signal.signal'))
                stack.enter_context(patch('analyses.e015.train_updates', side_effect=fake_training))
                stack.enter_context(patch('analyses.e015.generate', side_effect=fake_generation))
                stack.enter_context(patch('torch.tensor', side_effect=cpu_tensor))
                stack.enter_context(patch('torch.autocast', side_effect=lambda *a, **k: nullcontext()))
                stack.enter_context(patch.object(Tokens, 'save_pretrained', lambda *a, **k: None, create=True))
                loader = stack.enter_context(patch('transformers.AutoModelForCausalLM.from_pretrained',
                                                  return_value=FakeModel()))
                stack.enter_context(patch.dict('os.environ', {'CS294_BOUNDED_RUN_ID': self.cfg['run_id']}))
                worker(types.SimpleNamespace(preflight=str(preflight), tokenizer_dir='synthetic-not-a-model'), Tokens())
                loader.assert_called_once()
                self.assertTrue(loader.call_args.kwargs['local_files_only'])
            phases = json.loads((output / 'phase_timings.json').read_text())
            elapsed = phases['process_wall_seconds'] + .001
            (output / 'resource_receipt.json').write_text(json.dumps({
                'run_id': self.cfg['run_id'], 'status': 'completed', 'exit_code': 0, 'max_seconds': 360,
                'elapsed_seconds': elapsed, 'charged_seconds': math.ceil(elapsed)}))
            checked = audit(Tokens(), output)
            self.assertEqual(checked['updates_checked'], 256)
            self.assertTrue(checked['checkpoint_weights_rehashed'])
            self.assertFalse(checked['independent_checkpoint_backup_verified'])
            manifest = json.loads((output / 'run_manifest.json').read_text())
            self.assertEqual(set(manifest['artifact_sha256']), ARTIFACTS)
            self.assertEqual(set(phases['completed_phases_seconds']), PHASES)
        finally:
            os.chdir(cwd)


if __name__ == '__main__':
    unittest.main()

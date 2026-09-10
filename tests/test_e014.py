"""Small CPU fixtures for E014 indexing, cached decoding, provenance and audits."""
from contextlib import nullcontext
import copy
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch

import torch
from transformers import GenerationConfig, Qwen2Config, Qwen2ForCausalLM

from analyses.e014 import (distribution_record, make_cases, probe_queries,
    reference_measurement, stream_hash, token_hash, verify_checkpoint, worker,
    effective_generation_config, check_generation_settings)
from analyses.e014_audit import audit, audit_reference, checked_difference
from analyses.e014 import diagnosis
from src.real_math_engineering import score_completion
from src.real_math_experiment import generate
from src.sft_data import shifted_loss_sum


def case_fixture():
    return {'problem_id': 'fixture', 'prompt_ids': [7, 8, 9], 'target_ids': [4, 5, 2],
            'selected_for_batch1': True, 'prompt_ids_sha256': token_hash([7, 8, 9])}


class ReferenceMeasurements(unittest.TestCase):
    def setUp(self):
        torch.set_num_threads(1)
        self.case = case_fixture()
        self.streams = {'original_batch8': [4, 6, 2], 'replay_batch8': [4, 6, 2],
                        'selected_batch1': [4, 5, 2]}
        self.logits = torch.zeros(6, 16)
        # The correct causal rows are 2, 3, 4. Row 5 must never supervise EOS.
        self.logits[2, 4] = 7
        self.logits[3, 6] = 6
        self.logits[4, 2] = 5
        self.logits[5, 15] = 20
        self.record = reference_measurement(self.logits, self.case, probe_queries(self.case, self.streams))

    def test_shift_matches_independent_training_loss_including_eos(self):
        labels = torch.tensor([[-100, -100, -100, 4, 5, 2]])
        expected = shifted_loss_sum(self.logits[None], labels).item()
        self.assertAlmostEqual(self.record['loss_sum'], expected, places=5)
        self.assertEqual(self.record['argmax_ids'], [4, 6, 2])
        self.assertEqual(self.record['target_top1_correct'], 2)
        self.assertTrue(self.record['eos_is_argmax'])
        self.assertEqual(self.record['queries'][0]['causal_logit_index'], 4)

    def test_first_difference_uses_only_shared_reference_prefix(self):
        event = self.record['queries'][1]
        self.assertEqual(event['target_position'], 1)
        self.assertEqual(event['causal_logit_index'], 3)
        self.assertEqual(event['context_ids_sha256'], token_hash([7, 8, 9, 4]))
        self.assertEqual(event['alternative_id'], 6)
        self.assertLess(event['target_minus_alternative_logit'], 0)

    def test_exact_match_still_probes_reference_eos(self):
        q = probe_queries(self.case, {'matched': [4, 5, 2]})
        self.assertEqual(q, [{'kind': 'reference_eos', 'target_position': 2, 'alternative_id': None}])

    def test_early_eos_is_a_real_first_difference(self):
        q = probe_queries(self.case, {'early': [4, 2]})
        self.assertEqual(q[1]['target_position'], 1)
        self.assertEqual(q[1]['alternative_id'], 2)

    def test_unselected_rows_only_probe_eos(self):
        case = {**self.case, 'selected_for_batch1': False}
        self.assertEqual(len(probe_queries(case, self.streams)), 1)

    def test_low_mean_loss_can_hide_wrong_terminal_top_one(self):
        case = {**self.case, 'target_ids': [4] * 199 + [2]}
        logits = torch.full((203, 16), -20.0)
        logits[2:202, 4] = 20
        logits[201] = -20; logits[201, 6] = 1; logits[201, 2] = 0
        r = reference_measurement(logits, case, probe_queries(case, {}))
        self.assertLess(r['reference_nll'], .01)
        self.assertFalse(r['eos_is_argmax'])

    def test_tie_rank_is_distinct_from_argmax_identity(self):
        d = distribution_record(torch.zeros(16), 5, 0)
        self.assertEqual(d['target_rank_strict_greater'], 1)
        self.assertFalse(d['target_is_argmax'])
        self.assertEqual(d['argmax_id'], 0)
        self.assertEqual(d['target_minus_alternative_logit'], 0)

    def test_nonfinite_logits_and_out_of_range_positions_fail(self):
        bad = self.logits.clone(); bad[3, 6] = float('nan')
        with self.assertRaises(ValueError):
            reference_measurement(bad, self.case, probe_queries(self.case, self.streams))
        with self.assertRaises(ValueError):
            reference_measurement(self.logits, self.case,
                [{'kind': 'bad', 'target_position': 3, 'alternative_id': None}])

    def test_independent_reference_auditor_accepts_consistent_record(self):
        audit_reference(self.record, self.case, self.streams, 16)

    def test_independent_auditor_rejects_shift_loss_and_query_tampering(self):
        variants = []
        for key, value in [('target_ids', [4, 5, 3]), ('loss_sum', 0), ('eos_is_argmax', False),
                           ('target_top1_correct', 3), ('argmax_ids', [4, 6, 16])]:
            bad = copy.deepcopy(self.record); bad[key] = value; variants.append(bad)
        for key, value in [('causal_logit_index', 5), ('target_position', 0),
                           ('context_ids_sha256', 'wrong'), ('target_rank_strict_greater', 0),
                           ('target_log_probability', -100), ('target_minus_argmax_logit', 100),
                           ('conditioning', 'generated_prefix')]:
            bad = copy.deepcopy(self.record); bad['queries'][0][key] = value; variants.append(bad)
        for bad in variants:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                audit_reference(bad, self.case, self.streams, 16)

    def test_raw_comparison_checks_length_and_token_mismatches(self):
        checked_difference({'identical': False, 'common_prefix_tokens': 2, 'a_token': None, 'b_token': 3},
                           [1, 2], [1, 2, 3])
        with self.assertRaises(ValueError):
            checked_difference({'identical': True, 'common_prefix_tokens': 2, 'a_token': None, 'b_token': None},
                               [1, 2], [1, 2, 3])


class FrozenChecks(unittest.TestCase):
    def test_actual_saved_defaults_resolve_to_registered_cache_and_cap(self):
        saved = GenerationConfig(bos_token_id=151643, eos_token_id=151643, max_new_tokens=2048)
        tokenizer = types.SimpleNamespace(eos_token_id=151643)
        cfg = {'max_new_tokens': 768}
        settings = effective_generation_config(saved, tokenizer, cfg)
        check_generation_settings(settings, cfg)
        self.assertEqual(settings['max_new_tokens'], 768)
        self.assertTrue(settings['use_cache'])
        # Older original-base metadata and resaved metadata must resolve equally.
        saved.transformers_version = '4.37.0'
        self.assertEqual(effective_generation_config(saved, tokenizer, cfg), settings)

    def test_model_default_merging_is_detected_instead_of_silently_changed(self):
        saved = GenerationConfig(eos_token_id=151643, use_cache=False)
        settings = effective_generation_config(saved, types.SimpleNamespace(eos_token_id=151643), {'max_new_tokens': 768})
        self.assertFalse(settings['use_cache'])
        with self.assertRaises(ValueError): check_generation_settings(settings, {'max_new_tokens': 768})

    def test_checkpoint_hash_size_extra_and_symlink_guards(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); ckpt = root / 'checkpoint'; ckpt.mkdir()
            weight = ckpt / 'weights.bin'; weight.write_bytes(b'fixed weights')
            manifest = root / 'checkpoint_manifest.json'
            manifest.write_text(json.dumps({'kind': 'weights_only_not_optimizer_rng_resume',
                'files': {'weights.bin': {'bytes': weight.stat().st_size, 'sha256': stream_hash(weight)}}}))
            digest = stream_hash(manifest)
            with patch('analyses.e014.ORIGINAL', root):
                self.assertTrue(verify_checkpoint(ckpt, digest)['all_files_verified'])
                weight.write_bytes(b'wrong weights')
                with self.assertRaises(ValueError): verify_checkpoint(ckpt, digest)
                weight.write_bytes(b'fixed weights')
                extra = ckpt / 'extra'; extra.write_text('x')
                with self.assertRaises(ValueError): verify_checkpoint(ckpt, digest)
                extra.unlink(); target = root / 'outside'; weight.rename(target); weight.symlink_to(target)
                with self.assertRaises(ValueError): verify_checkpoint(ckpt, digest)

    def test_selection_is_all_failures_plus_first_two_controls(self):
        train = [{'problem_id': f'p{i}'} for i in range(32)]
        encoded = [{**r, 'input_ids': [9, 4, 2], 'n_prompt': 1} for r in train]
        original = [{**r, 'generated_ids': [4, 2], 'score': {'terminated_correct': i >= 8}}
                    for i, r in enumerate(train)]
        cfg = {'selected_failed_ids': [f'p{i}' for i in range(8)],
               'selected_control_ids': ['p8', 'p9'], 'single_example_decode_order': [f'p{i}' for i in range(10)]}
        cases = make_cases(train, encoded, original, cfg)
        self.assertEqual(sum(c['selected_for_batch1'] for c in cases), 10)
        for bad in ({**cfg, 'selected_control_ids': ['p9', 'p10']},
                    {**cfg, 'single_example_decode_order': list(reversed(cfg['single_example_decode_order']))}):
            with self.assertRaises(ValueError): make_cases(train, encoded, original, bad)

    def test_worker_cannot_load_pretrained_model_without_bound_wrapper(self):
        with patch('analyses.e014.load_release', return_value=({'run_id': 'never_launched_fixture'}, None)), \
             patch.dict('os.environ', {}, clear=True), \
             patch('transformers.AutoModelForCausalLM.from_pretrained') as load:
            with self.assertRaises(ValueError): worker(types.SimpleNamespace(), None)
            load.assert_not_called()


class CompletedOutputAudit(unittest.TestCase):
    def test_complete_fixture_and_rehashed_raw_score_corruption(self):
        class Tokens:
            eos_token_id = 2
            def __len__(self): return 300
            def decode(self, ids, **kwargs): return ''.join(chr(i - 3) for i in ids)
        tokenizer = Tokens()
        train = [{'problem_id': f'p{i}', 'prompt': f'fixture {i}',
                  'response': r'\boxed{1}', 'answer': '1'} for i in range(32)]
        encoded, original = [], []
        for i, row in enumerate(train):
            target = [ord(x) + 3 for x in row['response']] + [2]
            encoded.append({**row, 'input_ids': [7, 8, 9] + target, 'n_prompt': 3})
            text = r'\boxed{2}' if i < 8 else row['response']
            ids = [ord(x) + 3 for x in text] + [2]
            original.append({**row, 'text': text, 'generated_ids': ids, 'generated_tokens': len(ids),
                             'score': score_completion(row, text, True, False)})
        cfg = {'phase': 'E014', 'run_id': 'fixture', 'max_seconds': 360, 'guard_seconds': 15,
            'checkpoint_manifest_sha256': 'fixture-checkpoint', 'nll_agreement_abs_tolerance': 1e-5,
            'selected_failed_ids': [f'p{i}' for i in range(8)], 'selected_control_ids': ['p8', 'p9'],
            'single_example_decode_order': [f'p{i}' for i in range(10)]}
        cases = make_cases(train, encoded, original, cfg)
        references = []
        for case, enc in zip(cases, encoded):
            logits = torch.zeros(len(enc['input_ids']), 300)
            for j, target in enumerate(case['target_ids']): logits[2 + j, target] = 7
            streams = {'original_batch8': case['original_generated_ids'], 'replay_batch8': case['original_generated_ids']}
            if case['selected_for_batch1']: streams['selected_batch1'] = case['original_generated_ids']
            references.append(reference_measurement(logits, case, probe_queries(case, streams)))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); run = root / 'run'; run.mkdir(); inputs = root / 'inputs'; inputs.mkdir()
            original_dir = root / 'original'; original_dir.mkdir()
            (original_dir / 'metrics.json').write_text(json.dumps({'train_reference_nll': {'nll': .2}}))
            config = root / 'config.json'; config.write_text(json.dumps(cfg))
            release = root / 'release.json'; release.write_text('{}')
            (inputs / 'manifest.json').write_text(json.dumps({'source_files_sha256': {}}))
            (inputs / 'cpu_evidence.json').write_text(json.dumps({'effective_generation_config': {}}))
            for name, rows in [('replay_batch8.jsonl', original), ('selected_batch1.jsonl', original[:10]),
                               ('reference_tokens.jsonl', references)]:
                (run / name).write_text(''.join(json.dumps(r) + '\n' for r in rows))
            with patch('analyses.e014.ORIGINAL', original_dir), patch('analyses.e014.CONFIG', config):
                result = diagnosis(cases, original, original[:10], references)
            (run / 'diagnosis.json').write_text(json.dumps(result))
            (run / 'phase_timings.json').write_text(json.dumps({'completed_phases_seconds': {
                'checkpoint_load': .1, 'original_batch8_replay': .1, 'selected_batch1': .1,
                'all32_reference_tokens': .1}, 'wall_seconds': 1.0}))
            artifacts = {p.name: stream_hash(p) for p in run.iterdir()}
            manifest = {'status': 'completed', 'phase': 'E014', 'config': cfg, 'source_files_sha256': {},
                'release_sha256': stream_hash(release), 'training_updates': 0, 'model_execution_performed': True,
                'checkpoint': {'all_files_verified': True, 'manifest_sha256': 'fixture-checkpoint'},
                'effective_generation_config': {}, 'artifact_sha256': artifacts}
            (run / 'run_manifest.json').write_text(json.dumps(manifest))
            (run / 'resource_receipt.json').write_text(json.dumps({'run_id': 'fixture', 'status': 'completed',
                'exit_code': 0, 'max_seconds': 360, 'elapsed_seconds': 1.4, 'charged_seconds': 2}))
            state = ({'max_new_tokens': 768}, train, encoded, {}, original, cases)
            with patch('analyses.e014_audit.load_release', return_value=(cfg, state)), \
                 patch('analyses.e014_audit.RELEASE', release), patch('analyses.e014_audit.INPUTS', inputs), \
                 patch('analyses.e014_audit.ORIGINAL', original_dir):
                checked = audit(tokenizer, run)
                self.assertEqual(checked['raw_generation_streams_checked'], 42)
                self.assertEqual(checked['reference_targets_checked'], sum(len(c['target_ids']) for c in cases))
                bad = copy.deepcopy(original[:10]); bad[0]['score']['terminated_correct'] = True
                (run / 'selected_batch1.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in bad))
                manifest['artifact_sha256']['selected_batch1.jsonl'] = stream_hash(run / 'selected_batch1.jsonl')
                (run / 'run_manifest.json').write_text(json.dumps(manifest))
                with self.assertRaises(ValueError): audit(tokenizer, run)


class TinyQwenGeneration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1); torch.manual_seed(19)
        cls.model = Qwen2ForCausalLM(Qwen2Config(vocab_size=64, hidden_size=32, intermediate_size=64,
            num_hidden_layers=2, num_attention_heads=4, num_key_value_heads=2,
            max_position_embeddings=128, eos_token_id=2, pad_token_id=2,
            bos_token_id=1, attention_dropout=0.0, use_cache=False)).eval()
        cls.model.config._attn_implementation = 'sdpa'
        cls.model.generation_config = GenerationConfig(bos_token_id=1, eos_token_id=2, max_new_tokens=2048)

    def test_left_padding_positions_and_cached_next_logits_match_unpadded(self):
        ids = torch.tensor([[2, 2, 5, 6, 7], [9, 10, 11, 12, 13]])
        masks = torch.tensor([[0, 0, 1, 1, 1], [1, 1, 1, 1, 1]])
        prepared = self.model.prepare_inputs_for_generation(ids, attention_mask=masks,
            cache_position=torch.arange(5), use_cache=True)
        self.assertEqual(prepared['position_ids'][0].tolist(), [1, 1, 0, 1, 2])
        with torch.inference_mode():
            batch = self.model(**prepared)
            single = self.model(input_ids=ids[:1, 2:], attention_mask=torch.ones(1, 3, dtype=torch.long), use_cache=True)
            torch.testing.assert_close(batch.logits[0, -1], single.logits[0, -1], atol=1e-6, rtol=1e-5)
            next_ids = torch.tensor([[8], [8]])
            nxt = self.model(input_ids=next_ids, past_key_values=batch.past_key_values,
                attention_mask=torch.cat([masks, torch.ones(2, 1, dtype=torch.long)], dim=1),
                position_ids=torch.tensor([[3], [5]]), cache_position=torch.tensor([5]), use_cache=True)
            full = self.model(input_ids=torch.tensor([[5, 6, 7, 8]]), attention_mask=torch.ones(1, 4, dtype=torch.long), use_cache=False)
            torch.testing.assert_close(nxt.logits[0, -1], full.logits[0, -1], atol=1e-6, rtol=1e-5)

    def test_exact_e013_generate_function_preserves_order_mask_eos_and_cap(self):
        class Tokenizer:
            eos_token_id = pad_token_id = 2
            def __call__(self, text, **kwargs):
                return {'input_ids': [9, 10, 11, 12, 13] if 'long' in text else [5, 6, 7]}
            def decode(self, ids, **kwargs): return ' '.join(map(str, ids))
        rows = [{'problem_id': 'short', 'prompt': 'short', 'response': 'x', 'answer': '1'},
                {'problem_id': 'long', 'prompt': 'long', 'response': 'x', 'answer': '1'}]
        cfg = {'eval_batch_size': 2, 'max_new_tokens': 8, 'max_length': 32}
        tensor = torch.tensor
        calls = []
        def observe(_model, _args, kwargs):
            calls.append({'cache': kwargs.get('use_cache'), 'length': kwargs['input_ids'].shape[1]})
        hook = self.model.register_forward_pre_hook(observe, with_kwargs=True)
        self.addCleanup(hook.remove)
        def cpu_tensor(*a, **kw):
            if kw.get('device') == 'cuda': kw['device'] = 'cpu'
            return tensor(*a, **kw)
        # Only redirect the device/context; execute the historical generator verbatim.
        with tempfile.TemporaryDirectory() as tmp, patch('torch.tensor', side_effect=cpu_tensor), \
             patch('torch.cuda.synchronize'), patch('torch.autocast', side_effect=lambda *a, **kw: nullcontext()):
            paired = generate(self.model, Tokenizer(), rows, cfg, Path(tmp) / 'paired.jsonl')
            singles = generate(self.model, Tokenizer(), rows, {**cfg, 'eval_batch_size': 1}, Path(tmp) / 'single.jsonl')
            self.assertEqual([r['problem_id'] for r in paired], ['short', 'long'])
            self.assertEqual([r['generated_ids'] for r in paired], [r['generated_ids'] for r in singles])
            self.assertTrue(all(r['generated_tokens'] <= 8 for r in paired))
            self.assertTrue(any(r['generated_tokens'] == 8 for r in paired))
            self.assertTrue(all(c['cache'] is True for c in calls))
            self.assertTrue(any(c['length'] == 1 for c in calls))
            with self.assertRaises(FileExistsError):
                generate(self.model, Tokenizer(), rows, cfg, Path(tmp) / 'paired.jsonl')
            with self.assertRaises(ValueError):
                generate(self.model, Tokenizer(), rows, {**cfg, 'max_length': 10}, Path(tmp) / 'too_long.jsonl')


if __name__ == '__main__':
    unittest.main()

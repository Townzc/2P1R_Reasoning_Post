"""Authored CPU fixtures only; no candidate execution, model load, or generation."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from experiments.q2_supervision_migration.contracts import identity_hash, reserve_batch
from experiments.q2_supervision_migration.gpu_profile import ProfileError
from experiments.q2_supervision_migration import rollout_recovery as rr


class RolloutRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.batch = reserve_batch(self.root / 'batches', run_id='authored', phase_id='C_prefix',
            batch_index=0, tasks=['authored-task'], policy_sha256='a' * 64, config_sha256='b' * 64)

    def journal(self, **kwargs):
        values = dict(prompt_ids=[[1]], completion_ids=[[2, 3]], sampled_logprobs=[[-.5, -1.25]],
                      committed_updates=0, last_loaded_step=0)
        values.update(kwargs)
        return rr.journal_backend_rollout(self.batch, **values)

    def test_raw_backend_tokens_and_behavior_probabilities_persist_without_decoding(self):
        value = self.journal()
        saved = json.loads((self.batch.directory / 'backend_rollout.json').read_text())
        self.assertEqual(saved, value)
        self.assertEqual(saved['completion_ids'], [[2, 3]])
        self.assertEqual(saved['sampled_logprobs'], [[-.5, -1.25]])
        self.assertEqual(saved['record_sha256'], identity_hash({k: v for k, v in saved.items() if k != 'record_sha256'}))
        self.assertFalse(saved['cross_process_resume_authorized'])
        self.assertFalse((self.batch.directory / 'generation_return.json').exists())

    def test_duplicate_backend_return_cannot_overwrite_or_reauthorize_generation(self):
        self.journal()
        with self.assertRaises(FileExistsError):
            self.journal()

    def test_nonfinite_logprobs_remain_explicit_standard_json_evidence_then_fail(self):
        with self.assertRaisesRegex(ProfileError, 'nonfinite'):
            self.journal(sampled_logprobs=[[float('nan'), float('-inf')]])
        saved = json.loads((self.batch.directory / 'backend_rollout.json').read_text(),
                           parse_constant=lambda x: self.fail('nonstandard JSON constant ' + x))
        self.assertEqual(saved['sampled_logprobs'], [[{'nonfinite_float_repr': 'nan'}, {'nonfinite_float_repr': '-inf'}]])

    def test_malformed_logprob_alignment_is_preserved_and_cannot_train(self):
        with self.assertRaisesRegex(ProfileError, 'token-aligned'):
            self.journal(sampled_logprobs=[[-1.]])
        saved = json.loads((self.batch.directory / 'backend_rollout.json').read_text())
        self.assertEqual(saved['sampled_logprobs'], [[-1.]])

    def test_wrong_synchronized_step_cannot_train_but_return_is_preserved(self):
        with self.assertRaisesRegex(ProfileError, 'lineage'):
            self.journal(last_loaded_step=-1)
        self.assertTrue((self.batch.directory / 'backend_rollout.json').exists())

    def test_oversize_completion_is_preserved_before_rejection(self):
        with self.assertRaisesRegex(ProfileError, 'frozen cap'):
            self.journal(max_completion_tokens=1)
        self.assertEqual(json.loads((self.batch.directory / 'backend_rollout.json').read_text())['completion_ids'], [[2, 3]])


class CheckpointInventoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.phase = Path(self.tmp.name) / 'C_prefix'
        self.cp = self.phase / 'trainer' / 'checkpoint-1'
        self.cp.mkdir(parents=True)
        for name in ('model.safetensors', 'optimizer.pt', 'scheduler.pt', 'rng_state.pth'):
            (self.cp / name).write_bytes(b'authored opaque bytes; never loaded')
        (self.cp / 'trainer_state.json').write_text(json.dumps({'global_step': 1}))
        (self.phase / 'update_0001.json').write_text(json.dumps({'committed_update': 1}))
        (self.phase / 'pre_update_0001.json').write_text(json.dumps({'step': 1, 'all_finite': True, 'gradient_tensors': 1}))

    def inventory(self):
        return rr.checkpoint_inventory(self.cp, self.phase, committed_updates=1)

    def test_hashes_actual_files_and_does_not_claim_load_or_exact_resume(self):
        first = self.inventory()
        self.assertEqual(first['trainer_global_step'], 1)
        self.assertEqual(len(first['files']), 5)
        self.assertFalse(first['cross_process_resume_authorized'])
        self.assertFalse(first['vllm_rng_captured'])
        self.assertFalse(first['checkpoint_loading_verified'])
        (self.cp / 'optimizer.pt').write_bytes(b'changed authored bytes')
        self.assertNotEqual(first['files']['optimizer.pt'], self.inventory()['files']['optimizer.pt'])

    def test_uncertain_next_optimizer_attempt_forbids_snapshot_acceptance(self):
        (self.phase / 'pre_update_0002.json').write_text(json.dumps({'step': 2, 'all_finite': True, 'gradient_tensors': 1}))
        with self.assertRaisesRegex(ProfileError, 'uncommitted'):
            self.inventory()

    def test_trainer_step_mismatch_forbids_snapshot_acceptance(self):
        (self.cp / 'trainer_state.json').write_text(json.dumps({'global_step': 0}))
        with self.assertRaisesRegex(ProfileError, 'global_step'):
            self.inventory()

    def test_missing_optimizer_state_forbids_snapshot_acceptance(self):
        (self.cp / 'optimizer.pt').rename(self.cp / 'not_optimizer.pt')
        with self.assertRaisesRegex(ProfileError, 'lacks'):
            self.inventory()

    def test_checkpoint_symlinks_are_rejected(self):
        (self.cp / 'unexpected_link').symlink_to(self.cp / 'model.safetensors')
        with self.assertRaisesRegex(ProfileError, 'link'):
            self.inventory()

    def test_file_changed_during_hashing_is_rejected(self):
        original = rr.hashlib.sha256
        target = self.cp / 'model.safetensors'
        original_model = target.read_bytes()
        mutated = False
        class MutatingDigest:
            def __init__(self): self.inner = original()
            def update(self, data):
                nonlocal mutated
                self.inner.update(data)
                # Mutate once while the model itself is hashed, not earlier
                # while commit receipts are hashed. Do not depend on filesystem
                # timestamp granularity for repeated identical writes.
                if not mutated and data == original_model:
                    target.write_bytes(original_model + b' concurrent change')
                    mutated = True
            def hexdigest(self): return self.inner.hexdigest()
        with mock.patch.object(rr.hashlib, 'sha256', side_effect=MutatingDigest):
            with self.assertRaisesRegex(ProfileError, 'changed'):
                self.inventory()


if __name__ == '__main__':
    unittest.main()

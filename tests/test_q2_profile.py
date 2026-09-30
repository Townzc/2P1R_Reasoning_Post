"""CPU authored fixtures/mocks only. Never load a model or execute dataset code."""
import argparse
import ast
import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time
import unittest
from unittest import mock

from experiments.q2_supervision_migration import gpu_profile as profile


class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.split = {'train_ids': [f'Mbpp/{i}' for i in range(8, -1, -1)], 'eval_ids': ['Mbpp/999']}
        split = self.root / 'split.json'
        split.write_text(json.dumps(self.split))
        data = self.root / 'data.jsonl'
        data.write_text('authored fixture; never executed\n')
        manifest = self.root / 'manifest.json'
        manifest.write_text('{}')
        model = self.root / 'model'
        model.mkdir()
        self.args = argparse.Namespace(execute_engineering_profile=True, max_seconds=1800,
            scorer_timeout=120, seed=0, split_json=str(split), split_sha256=profile.sha256(split),
            data_json=str(data), data_sha256=profile.sha256(data), model_path=str(model),
            model_manifest=str(manifest))

    def test_train_only_first_eight_and_overlap_rejected(self):
        self.assertEqual(profile.validate_args(self.args, system='Linux'), [f'Mbpp/{i}' for i in range(8)])
        self.split['eval_ids'] = ['Mbpp/0']
        with self.assertRaises(profile.ProfileError):
            profile.train_subset(self.split)
        self.split['eval_ids'] = ['Mbpp/999']
        self.split['train_ids'].append('Mbpp/0')
        with self.assertRaises(profile.ProfileError):
            profile.train_subset(self.split)

    def test_validation_refuses_nonlinux_unbounded_and_wrong_pin(self):
        with self.assertRaises(profile.ProfileError):
            profile.validate_args(self.args, system='Darwin')
        for value in (0, 1801, float('inf'), float('nan')):
            self.args.max_seconds = value
            with self.assertRaises(profile.ProfileError):
                profile.validate_args(self.args, system='Linux')
        self.args.max_seconds = 1800
        self.args.split_sha256 = '0' * 64
        with self.assertRaises(profile.ProfileError):
            profile.validate_args(self.args, system='Linux')

    def test_manifest_exact_files_sizes_revision_and_no_path_escape(self):
        root = Path(self.args.model_path)
        for name in ('config.json', 'tokenizer_config.json', 'model.safetensors'):
            (root / name).write_bytes(b'authored bytes, not a model')
        entries = [{'path': p.name, 'sha256': profile.sha256(p), 'bytes': p.stat().st_size}
                   for p in root.iterdir()]
        manifest = {'model_id': profile.MODEL_ID, 'revision': profile.MODEL_REVISION, 'files': entries}
        path = Path(self.args.model_manifest)
        path.write_text(json.dumps(manifest))
        self.assertEqual(len(profile.verify_model(root, path, time.monotonic() + 10)), 64)
        entries[0]['bytes'] += 1
        path.write_text(json.dumps(manifest))
        with self.assertRaises(profile.ProfileError):
            profile.verify_model(root, path, time.monotonic() + 10)
        entries[0]['path'] = '../outside'
        path.write_text(json.dumps(manifest))
        with self.assertRaises(profile.ProfileError):
            profile.verify_model(root, path, time.monotonic() + 10)

    def test_durable_record_refuses_overwrite_and_deadline(self):
        path = self.root / 'record.json'
        profile.durable_json(path, {'a': 1})
        with self.assertRaises(FileExistsError):
            profile.durable_json(path, {'a': 1})
        with self.assertRaises(TimeoutError):
            profile.check_deadline(time.monotonic() - 1)

    def test_unowned_process_group_never_signalled(self):
        proc = mock.Mock(pid=12345)
        proc._q2_owned_group = None
        with mock.patch.object(os, 'killpg') as kill:
            with self.assertRaises(profile.ProfileError):
                profile.stop_owned_group(proc)
            kill.assert_not_called()

    def test_guard_timeout_only_signals_owned_group_and_no_retry(self):
        class Child:
            pid = 12345
            returncode = None
            calls = 0
            def poll(self):
                return self.returncode
            def wait(self, timeout):
                self.calls += 1
                if self.calls == 1:
                    raise subprocess.TimeoutExpired('authored-mock', timeout)
                self.returncode = -signal.SIGTERM
                return self.returncode
        child = Child()
        factory = mock.Mock(return_value=child)
        with mock.patch.object(os, 'getpgid', return_value=child.pid), mock.patch.object(os, 'killpg') as kill:
            result = profile.launch_guarded(['not-executed'], self.root, 2, popen=factory)
        self.assertEqual(result, 1)
        factory.assert_called_once()
        self.assertTrue(factory.call_args.kwargs['start_new_session'])
        self.assertEqual([x.args[0] for x in kill.call_args_list], [child.pid, child.pid])
        receipt = json.loads((self.root / 'train_launcher_receipt.json').read_text())
        self.assertEqual(receipt['status'], 'timeout')
        self.assertFalse(receipt['scientific_result'])

    def test_start_receipt_failure_still_cleans_owned_process(self):
        child = mock.Mock(pid=23456, returncode=-15)
        child.poll.return_value = -15
        with mock.patch.object(profile, 'durable_json', side_effect=OSError('authored disk error')), \
             mock.patch.object(profile, 'stop_owned_group') as stop:
            with self.assertRaises(OSError):
                profile.launch_guarded(['not-executed'], self.root, 5,
                                       popen=mock.Mock(return_value=child))
            stop.assert_called_once_with(child)

    def test_backend_return_preserves_full_text_before_any_reward(self):
        batch = profile.reserve_batch(self.root / 'batches', run_id='fixture', phase_id='profile',
            batch_index=0, tasks=['Mbpp/0'], policy_sha256='a' * 64, config_sha256='b' * 64)
        text = 'authored text ' * 1000
        profile.record_generation_return(batch, [[1]], [[2, 3]], [text], [text + '<eos>'])
        saved = json.loads((batch.directory / 'generation_return.json').read_text())
        self.assertEqual(saved['decoded_text'], [text])
        self.assertEqual(saved['completion_ids'], [[2, 3]])
        self.assertFalse((batch.directory / 'batch.jsonl').exists())
        with self.assertRaises(FileExistsError):
            profile.record_generation_return(batch, [[1]], [[2, 3]], [text], [text + '<eos>'])

    def test_heavy_imports_are_lazy_and_config_is_finite(self):
        tree = ast.parse(Path(profile.__file__).read_text())
        names = []
        for node in tree.body:
            if isinstance(node, ast.Import):
                names.extend(n.name for n in node.names)
            elif isinstance(node, ast.ImportFrom):
                names.append(node.module or '')
        self.assertFalse(any(n.split('.')[0] in {'torch', 'trl', 'evalplus', 'datasets', 'transformers'} for n in names))
        self.assertEqual(profile.PROFILE['max_steps'], 2)
        self.assertEqual(profile.PROFILE['num_generations'], 8)
        self.assertEqual(profile.PROFILE['eval_strategy'], 'no')
        self.assertEqual(profile.PROFILE['optim'], 'adafactor')


if __name__ == '__main__':
    unittest.main()

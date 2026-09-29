import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from experiments.thursday_probe_v2 import resume_launcher as launcher
from experiments.thursday_probe_v2.resume_resources import ResumeGenerationBudget
from src.sft_data import sha256_file


class LauncherTests(unittest.TestCase):
    def test_slice_preserves_export_reserve_and_hard_guard(self):
        self.assertEqual(launcher.slice_seconds({'worker_deadline_epoch': 20000}, now=1000), 7200)
        self.assertEqual(launcher.slice_seconds({'worker_deadline_epoch': 2000}, now=1000), 985)
        self.assertIsNone(launcher.slice_seconds({'worker_deadline_epoch': 1734}, now=1000))
        self.assertEqual(launcher.slice_seconds({'worker_deadline_epoch': 1735}, now=1000), 720)

    def invoke(self, folder, worker, *, start='1970-01-01T00:16:40+00:00'):
        output = Path(folder)/'out'; ledger = Path(folder)/'old.json'
        if not ledger.exists():
            ledger.write_text('{"historical": true}\n')
        with contextlib.ExitStack() as stack:
            stack.enter_context(patch.object(launcher, 'OLD_LEDGER_HASH', sha256_file(ledger)))
            stack.enter_context(patch.object(launcher, 'source', return_value={
                'source_commit': 'published', 'source_files_sha256': {}}))
            stack.enter_context(patch.object(launcher, 'load_inputs'))
            stack.enter_context(patch.object(launcher, '_validate_initial_checkpoint', return_value={
                'parameter_digest': {'sha256': 'C0'}}))
            preflight = stack.enter_context(patch.object(launcher, 'server_preflight', return_value={'gpu': 'fixture'}))
            stack.enter_context(patch.object(launcher.importlib.metadata, 'version', return_value='0.17.1'))
            stack.enter_context(patch.object(launcher.time, 'time', return_value=1000.0))
            stack.enter_context(patch.object(launcher, '_run_worker', side_effect=worker))
            stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
            code = launcher.launch('snapshot', 'checkpoint', ledger, start, 7.98, output=output)
        return code, output, preflight

    def test_code75_continues_without_reset_and_completion_is_not_replayed(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []
            def worker(command, env, stream):
                calls.append((command, env))
                budget = ResumeGenerationBudget(Path(directory)/'out/generation_ledger.json')
                budget.reserve('batch-'+str(len(calls)), 8)
                stream.write('durable stdout\n')
                return 75 if len(calls) == 1 else 0
            code, output, preflight = self.invoke(directory, worker)
            self.assertEqual(code, 0)
            self.assertEqual(len(calls), 2)
            self.assertEqual([c.args[0]['min_free_gib'] for c in preflight.call_args_list], [4.5, 1.25])
            self.assertEqual(json.loads((output/'generation_ledger.json').read_text())['used'], 608)
            receipts = launcher._receipts(output)
            self.assertEqual([r['exit_code'] for r in receipts], [75, 0])
            self.assertEqual(calls[0][1]['THU_RESUME_BOUNDED'], launcher.RUN_ID)
            self.assertLessEqual(float(calls[0][1]['THU_RESUME_DEADLINE'])+15,
                                 float(calls[0][1]['THU_RESUME_GLOBAL_DEADLINE']))
            self.assertIn('--worker', calls[0][0])
            self.assertIn('--kill-after=15s', calls[0][0])
            inventory = json.loads((output/'export_manifest_final.json').read_text())['files']
            self.assertNotIn('export_manifest_final.json', inventory)
            for name, record in inventory.items():
                self.assertEqual(sha256_file(output/name), record['sha256'])
            def forbidden(*args):
                self.fail('Completed worker must not replay')
            self.assertEqual(self.invoke(directory, forbidden)[0], 0)

    def test_fault_and_no_progress_pause_never_retry(self):
        for exit_code in (1, 124, 137, 75):
            with self.subTest(exit_code=exit_code), tempfile.TemporaryDirectory() as directory:
                calls = []
                def worker(*args):
                    calls.append(True)
                    return exit_code
                code, output, _ = self.invoke(directory, worker)
                self.assertEqual(code, exit_code)
                self.assertEqual(len(calls), 1)
                self.assertEqual(len(launcher._receipts(output)), 1)

    def test_insufficient_useful_time_writes_no_attempt(self):
        with tempfile.TemporaryDirectory() as directory:
            # Time budget has 2100 seconds left: minus1500 export and15 guard,
            # below600 useful+120 reload. No new child is admitted.
            with patch('experiments.thursday_probe_v2.resume_resources.MAX_POWERED_SECONDS', 2100):
                def forbidden(*args):
                    self.fail('No useful time remains')
                code, output, preflight = self.invoke(directory, forbidden)
            self.assertEqual(code, 75)
            preflight.assert_not_called()
            self.assertEqual(launcher._receipts(output), [])

    def test_unreconciled_attempt_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            attempt = Path(directory)/'out/attempts/attempt_000001'
            attempt.mkdir(parents=True); (attempt/'intent.json').write_text('{}')
            with self.assertRaisesRegex(ValueError, 'Unreconciled'):
                self.invoke(directory, lambda *args: 0)
            self.assertEqual((attempt/'intent.json').read_text(), '{}')

    def test_parent_error_is_receipted_and_stops(self):
        with tempfile.TemporaryDirectory() as directory:
            def worker(*args):
                raise OSError('fixture worker failed to start')
            code, output, _ = self.invoke(directory, worker)
            self.assertEqual(code, 1)
            receipt = launcher._receipts(output)[0]
            self.assertEqual(receipt['failure']['type'], 'OSError')
            self.assertEqual(receipt['status'], 'fault_stop')


if __name__ == '__main__':
    unittest.main()

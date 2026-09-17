import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from experiments.post_e037_goal_training import launcher
from src.sft_data import sha256_file


class GoalTrainingBudgetTests(unittest.TestCase):
    def test_new_generations_start_zero_and_resume_without_reset(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'ledger.json'
            budget = launcher.GenerationBudget(path)
            self.assertEqual(budget.used, 0)
            budget.reserve('batch_000001', 8)
            self.assertEqual(launcher.GenerationBudget(path).used, 8)
            with self.assertRaisesRegex(ValueError, 'Duplicate'):
                budget.reserve('batch_000001', 8)
            budget.reserve('rest', 3592)
            with self.assertRaises(ValueError):
                budget.reserve('over', 1)
            self.assertEqual(budget.record()['historical_generation_attempts'], 4784)
            self.assertEqual(budget.record()['historical_generation_cap'], 4864)

    def test_corrupt_generation_ledger_is_not_reset(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'ledger.json'
            budget = launcher.GenerationBudget(path)
            record = budget.record(); record['used'] = 1
            path.write_text(json.dumps(record))
            with self.assertRaisesRegex(ValueError, 'inconsistent'):
                launcher.GenerationBudget(path)
            self.assertEqual(json.loads(path.read_text())['used'], 1)

    def test_rental_window_includes_idle_and_reserves_shutdown(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(launcher.time, 'time', return_value=10000):
            budget = launcher.RentalBudget(Path(directory)/'rental.json', '1970-01-01T00:00:00+00:00', 7.98)
            remaining = budget.remaining(now=600)
            self.assertEqual(remaining['powered_seconds_used'], 600)
            self.assertAlmostEqual(remaining['rental_cost_proxy_cny'], 1.33)
            self.assertEqual(remaining['hard_deadline_epoch'], 10800)
            self.assertEqual(remaining['worker_deadline_epoch'], 10200)
            self.assertFalse(remaining['estimate_is_invoice'])
            with self.assertRaisesRegex(ValueError, 'preserved'):
                launcher.RentalBudget(budget.path, '1970-01-01T00:01:00+00:00', 7.98)

    def test_closed_power_windows_and_money_are_cumulative(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(launcher.time, 'time', return_value=10000):
            path = Path(directory)/'rental.json'
            first = launcher.RentalBudget(path, '1970-01-01T00:00:00+00:00', 12.)
            first.close('1970-01-01T00:30:00+00:00')
            second = launcher.RentalBudget(path, '1970-01-01T01:00:00+00:00', 24.)
            remaining = second.remaining(now=4500)
            self.assertEqual(remaining['powered_seconds_used'], 2700)
            self.assertEqual(remaining['rental_cost_proxy_cny'], 12.)
            self.assertEqual(remaining['remaining_hard_seconds'], 2700)
            self.assertEqual(remaining['worker_deadline_epoch'], 6600)

    def test_only_next_slice_must_fit(self):
        self.assertEqual(launcher.slice_seconds({'worker_deadline_epoch': 20000}, now=1000), 3600)
        self.assertEqual(launcher.slice_seconds({'worker_deadline_epoch': 2000}, now=1000), 985)
        self.assertIsNone(launcher.slice_seconds({'worker_deadline_epoch': 1194}, now=1000))
        self.assertEqual(launcher.slice_seconds({'worker_deadline_epoch': 1195}, now=1000), 180)


class GoalTrainingLauncherTests(unittest.TestCase):
    def complete_progress(self, output, *, unavailable=0):
        from experiments.post_e037_goal_training.queue import evaluation_queue
        evaluations = [dict(name=e['name'],status='completed',completed_records=e['expected_records']) for e in evaluation_queue()]
        operators = []
        for state in ('E031','G-single','G-paired'):
            directory = output/'operator_scores'/state; directory.mkdir(parents=True)
            records = [dict(status='unavailable' if i < unavailable else 'available',
                            reason='No comparable prefix' if i < unavailable else None) for i in range(96)]
            for index, record in enumerate(records):
                launcher.atomic_json(directory/f'{index:06d}.json', record)
            aggregate = dict(state=state, status='completed', records=records,
                             recorded_contexts=96, unavailable_contexts=unavailable,
                             forward_contexts=96-unavailable, candidate_scores=4*(96-unavailable))
            launcher.atomic_json(directory.parent/(state+'.json'), aggregate)
            operators.append({k:v for k,v in aggregate.items() if k != 'records'})
        launcher.atomic_json(output/'progress.json', dict(status='completed', evaluations=evaluations, training_updates=512, runs=[dict(state=s,status='completed',completed_updates=256) for s in ('G-single','G-paired')],
            operators=operators, forward_contexts=288-3*unavailable, candidate_scores=1152-12*unavailable))

    def invoke(self, folder, worker, *, now=1000.):
        output = Path(folder)/'out'; ledger = Path(folder)/'old.json'
        if not ledger.exists():
            ledger.write_bytes(Path('reports/post_e036_goal_probe/PHASE_LEDGER.json').read_bytes())
        with contextlib.ExitStack() as stack:
            stack.enter_context(patch.object(launcher, 'source', return_value={
                'source_commit': 'a'*40, 'source_files_sha256': {'fixture.py':'published-sha'}}))
            stack.enter_context(patch.object(launcher, 'load_inputs', return_value={
                'planned_generations': 3344, 'generation_cap': 3600}))
            preflight = stack.enter_context(patch.object(launcher, 'server_preflight', return_value={'gpu':'fixture'}))
            stack.enter_context(patch.object(launcher.importlib.metadata, 'version', return_value='0.17.1'))
            stack.enter_context(patch.object(launcher.time, 'time', return_value=now))
            stack.enter_context(patch.object(launcher, '_run_worker', side_effect=worker))
            stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
            code = launcher.launch('snapshot', 'endpoints', ledger, '1970-01-01T00:16:40+00:00',
                                   7.98, 'a'*40, output=output)
        return code, output, preflight

    def test_pause_continues_and_completed_is_not_replayed(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []
            def worker(command, environment, stream):
                calls.append((command, environment))
                output = Path(environment['GOAL_TRAINING_OUTPUT'])
                budget = launcher.GenerationBudget(output/'generation_ledger.json')
                budget.reserve('batch-'+str(len(calls)), 8 if len(calls) == 1 else 3336)
                if len(calls) == 2:
                    self.complete_progress(output)
                stream.write('durable stdout\n')
                return 75 if len(calls) == 1 else 0
            code, output, preflight = self.invoke(directory, worker)
            self.assertEqual(code, 0); self.assertEqual(len(calls), 2)
            self.assertEqual(launcher.GenerationBudget(output/'generation_ledger.json').used, 3344)
            self.assertEqual([r['exit_code'] for r in launcher._receipts(output)], [75, 0])
            self.assertEqual([c.args[0]['min_free_gib'] for c in preflight.call_args_list], [1., 1.])
            command, environment = calls[0]
            self.assertIn('--kill-after=15s', command)
            self.assertEqual(command[6:9], ['experiments.post_e037_goal_training.queue', '--worker', '--snapshot'])
            self.assertEqual(environment['GOAL_TRAINING_BOUNDED'], launcher.RUN_ID)
            self.assertLessEqual(float(environment['GOAL_TRAINING_DEADLINE'])+15,
                                 float(environment['GOAL_TRAINING_GLOBAL_DEADLINE']))
            self.assertEqual(sha256_file(Path(directory)/'old.json'), launcher.HISTORICAL_PHASE_SHA256)
            summary = json.loads((output/'phase_ledger.json').read_text())
            self.assertEqual(summary['total_receipts_across_phases'], 28)
            self.assertEqual(summary['prior_charged_seconds'], 14605)
            self.assertEqual(summary['forwards']['candidate_scores'], 1152)
            self.assertFalse(summary['provider_shutdown_confirmed'])
            for name, record in json.loads((output/'export_manifest_final.json').read_text())['files'].items():
                self.assertEqual(sha256_file(output/name), record['sha256'])
            self.assertEqual(self.invoke(directory, lambda *_: self.fail('Completed queue replayed'))[0], 0)

    def test_explicit_unavailable_forward_contexts_can_complete(self):
        with tempfile.TemporaryDirectory() as directory:
            def worker(command, environment, stream):
                output = Path(environment['GOAL_TRAINING_OUTPUT'])
                launcher.GenerationBudget(output/'generation_ledger.json').reserve('all', 3344)
                self.complete_progress(output, unavailable=2)
                return 0
            code, output, _ = self.invoke(directory, worker)
            self.assertEqual(code, 0)
            self.assertEqual(launcher._forward_progress(output)['recorded_contexts'], 288)
            self.assertEqual(launcher._forward_progress(output)['unavailable_contexts'], 6)

    def test_exit_zero_without_scientific_completion_is_failed(self):
        with tempfile.TemporaryDirectory() as directory:
            code, output, _ = self.invoke(directory, lambda *_: 0)
            self.assertEqual(code, 1)
            self.assertEqual(launcher._receipts(output)[0]['status'], 'failed:1')

    def test_no_progress_and_faults_stop_without_retry(self):
        for status in (75, 1, 124, 137):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as directory:
                calls = []
                def worker(*_):
                    calls.append(True)
                    return status
                code, output, _ = self.invoke(directory, worker)
                self.assertEqual(code, status); self.assertEqual(len(calls), 1)
                self.assertEqual(len(launcher._receipts(output)), 1)

    def test_aggregate_progress_alone_does_not_trigger_reload(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []
            def worker(command, environment, stream):
                calls.append(True)
                launcher.atomic_json(Path(environment['GOAL_TRAINING_OUTPUT'])/'progress.json',
                                     dict(forward_contexts=1, candidate_scores=4))
                return 75
            code, _, _ = self.invoke(directory, worker)
            self.assertEqual(code, 75); self.assertEqual(len(calls), 1)

    def test_short_window_has_no_attempt_or_preflight(self):
        with tempfile.TemporaryDirectory() as directory:
            code, output, preflight = self.invoke(directory, lambda *_: self.fail('Out of time'), now=11090)
            self.assertEqual(code, 75); preflight.assert_not_called()
            self.assertEqual(launcher._receipts(output), [])

    def test_orphan_attempt_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'out/attempts/attempt_000001'
            path.mkdir(parents=True); (path/'intent.json').write_text('original')
            with self.assertRaisesRegex(ValueError, 'Unreconciled'):
                self.invoke(directory, lambda *_: 0)
            self.assertEqual((path/'intent.json').read_text(), 'original')

    def test_worker_failure_is_receipted(self):
        with tempfile.TemporaryDirectory() as directory:
            def worker(*_):
                raise OSError('fixture child failure')
            code, output, _ = self.invoke(directory, worker)
            self.assertEqual(code, 1)
            receipt = launcher._receipts(output)[0]
            self.assertEqual(receipt['failure']['type'], 'OSError')
            self.assertEqual(receipt['status'], 'failed:1')


if __name__ == '__main__':
    unittest.main()

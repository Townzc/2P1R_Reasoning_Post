"""CPU-only authored completion-envelope fixtures; no live worker or model calls."""
import argparse
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from experiments.q2_supervision_migration import completion_plan as cp
from experiments.q2_supervision_migration import completion_parent as parent
from experiments.q2_supervision_migration import screen_plan as sp
from experiments.q2_supervision_migration.contracts import ContractError, identity_hash
from experiments.q2_supervision_migration.gpu_profile import ProfileError, sha256


def fixture_plan():
    return sp.make_plan({'train_ids': [f'Mbpp/{i}' for i in range(250)],
                         'eval_ids': [f'Mbpp/{i}' for i in range(1000, 1128)]}, first_failure=True)


class CompletionPlanTests(unittest.TestCase):
    def test_exact_missing_controls_and_no_new_scientific_plan(self):
        scientific = fixture_plan()
        before = copy.deepcopy(scientific)
        execution = cp.make_completion_plan(scientific)
        self.assertEqual(scientific, before)
        self.assertEqual(execution['scientific_plan_sha256'], identity_hash(scientific))
        self.assertEqual(execution['phases'], ['C_prefix', 'C_future', 'R_future',
                                             'eval_C_prefix', 'eval_C_future', 'eval_R_future'])
        self.assertEqual(execution['dose'], {'optimizer_updates': 384, 'training_completions': 6144,
            'evaluation_completions': 3072, 'total_completions': 9216, 'final_checkpoints': 3})
        self.assertEqual(execution['execution_run_id'], scientific['run_id'] + '__controls_completion_2')
        self.assertFalse(execution['cross_process_resume'])
        self.assertFalse(execution['automatic_retry'])

    def test_scientific_recipe_or_old_scoring_plan_changes_are_rejected(self):
        plan = fixture_plan()
        plan['training_config'] = {**plan['training_config'], 'learning_rate': 2e-6}
        with self.assertRaises(ContractError):
            cp.make_completion_plan(plan)
        original = sp.make_plan({'train_ids': [f'Mbpp/{i}' for i in range(250)],
                                'eval_ids': [f'Mbpp/{i}' for i in range(1000, 1128)]})
        with self.assertRaises(ProfileError):
            cp.make_completion_plan(original)

    def test_failed_and_successful_prior_dose_are_preserved_separately(self):
        old = cp.PRIOR_DOSE
        self.assertEqual(sum(x['updates'] for x in [*old['completed_training'].values(), *old['failed_attempts'].values()]), 386)
        self.assertEqual(sum(x['outputs'] for x in [*old['completed_training'].values(), *old['failed_attempts'].values()]), 6224)
        self.assertFalse(old['old_failures_relabelled_or_resumed'])

    def test_cpu_gate_time_consumes_the_original_powered_window(self):
        times = cp.fixed_deadlines(1000, 11800, 2200)
        self.assertEqual(times['worker_deadline_epoch'], 11200)
        self.assertEqual(times['worker_deadline_epoch'] - 2200, 9000)
        self.assertEqual(times['shutdown_reserve_seconds'], 600)

    def test_deadline_cannot_reset_or_extend_or_start_in_future(self):
        for power, provider, now, model in [
                (1000, 11801, 2200, None), (1000, 11800, 999, None),
                (1000, 11800, 11200, None), (1000, 11800, 2200, 11201),
                (1000, 11800, 2200, float('nan')), (float('inf'), 11800, 2200, None)]:
            with self.assertRaises(ProfileError):
                cp.fixed_deadlines(power, provider, now, model)
        self.assertEqual(cp.fixed_deadlines(1000, 11800, 2200, 9000)['worker_deadline_epoch'], 9000)

    def test_phase_caps_obey_earlier_shared_deadline(self):
        self.assertEqual(cp.phase_deadline('C_prefix', 1000, 10000), 3700)
        self.assertEqual(cp.phase_deadline('eval_C_future', 1000, 10000), 2800)
        self.assertEqual(cp.phase_deadline('R_future', 1000, 1200), 1200)
        for phase, now, end in [('W_prefix', 1000, 10000), ('C_prefix', 1000, 1000)]:
            with self.assertRaises(ProfileError):
                cp.phase_deadline(phase, now, end)


class CompletionAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.plan = fixture_plan()
        self.identity = identity_hash(self.plan)
        self.commit = 'a' * 40

    def gate(self, **changes):
        body = {'passed': True, 'reward_semantics_unchanged': True,
                'source_commit': self.commit, 'plan_sha256': self.identity,
                'new_generations': 0, 'optimizer_updates': 0,
                'original_saved_outputs': 96, 'previous_known_pairs': 90, 'matched_pairs': 90,
                'resolved_pairs': 96, 'known_W_sentinels_matched': 32,
                'authored_controls_passed': ['valid', 'wrong', 'syntax', 'init', 'test_timeout'],
                'diagnoses': [{'fixture': 'R599', 'verdicts': ['pass'] * 3},
                              {'fixture': 'C260', 'verdicts': ['fail'] * 3}],
                'historical_records_relabelled': False, 'reward_semantics_changed': False,
                'reference_manifest_sha256': 'f' * 64}
        body.update(changes)
        path = self.root / 'preflight_complete.json'
        path.write_text(json.dumps(body))
        (self.root / 'cpu_launcher_receipt.json').write_text(json.dumps({'status': 'completed', 'returncode': 0}))
        return sha256(path)

    def test_gate_requires_pinned_success_and_same_source_plan_semantics(self):
        self.assertTrue(parent.verify_gate(self.root, self.gate(), self.commit, self.identity)['passed'])
        for update in [{'passed': False}, {'reward_semantics_unchanged': False}, {'source_commit': 'b' * 40},
                       {'plan_sha256': 'b' * 64}, {'new_generations': 1}, {'optimizer_updates': False}]:
            with self.assertRaises(ProfileError):
                parent.verify_gate(self.root, self.gate(**update), self.commit, self.identity)
        self.gate()
        with self.assertRaises(ProfileError):
            parent.verify_gate(self.root, '0' * 64, self.commit, self.identity)

    def test_gate_rejects_insufficient_known_coverage_controls_or_repeat_diagnosis(self):
        for update in [{'matched_pairs': 89}, {'resolved_pairs': 95}, {'known_W_sentinels_matched': 31},
                       {'authored_controls_passed': ['valid', 'wrong', 'syntax', 'init']},
                       {'diagnoses': [{'fixture': 'R599', 'verdicts': ['pass', 'fail', 'pass']},
                                      {'fixture': 'C260', 'verdicts': ['fail'] * 3}]},
                       {'historical_records_relabelled': True}]:
            with self.assertRaises(ProfileError):
                parent.verify_gate(self.root, self.gate(**update), self.commit, self.identity)

    def test_failure_receipt_or_mixed_gate_directory_is_not_pass(self):
        digest = self.gate()
        (self.root / 'cpu_launcher_receipt.json').write_text(json.dumps({'status': 'failed', 'returncode': 1}))
        with self.assertRaises(ProfileError):
            parent.verify_gate(self.root, digest, self.commit, self.identity)
        digest = self.gate()
        (self.root / 'preflight_failure.json').write_text('{}')
        with self.assertRaises(ProfileError):
            parent.verify_gate(self.root, digest, self.commit, self.identity)

    def source_fixture(self):
        package = self.root / 'experiments/q2_supervision_migration'
        package.mkdir(parents=True)
        for name in ('completion_parent.py', 'completion_plan.py', 'screen_runtime.py', 'rollout_recovery.py'):
            (package / name).write_text('# authored source; not imported\n')
        files = {str(p.relative_to(self.root)): {'bytes': p.stat().st_size, 'sha256': sha256(p)} for p in package.iterdir()}
        path = self.root / 'SOURCE_MANIFEST.json'
        path.write_text(json.dumps({'commit': self.commit, 'files': files}))
        return path, sha256(path), package

    def test_source_requires_actual_published_bytes_and_complete_module_coverage(self):
        manifest, digest, package = self.source_fixture()
        self.assertEqual(parent.verify_source(self.root, manifest, digest, self.commit)['file_count'], 4)
        (package / 'unlisted.py').write_text('# authored unlisted module\n')
        with self.assertRaisesRegex(ProfileError, 'every Q2'):
            parent.verify_source(self.root, manifest, digest, self.commit)

    def test_source_byte_changes_or_wrong_commit_are_rejected(self):
        manifest, digest, package = self.source_fixture()
        with self.assertRaises(ProfileError):
            parent.verify_source(self.root, manifest, digest, 'b' * 40)
        (package / 'screen_runtime.py').write_text('# changed authored bytes\n')
        with self.assertRaisesRegex(ProfileError, 'identity differs'):
            parent.verify_source(self.root, manifest, digest, self.commit)

    def test_reference_cache_identity_verified_without_unpickling(self):
        (self.root / 'groundtruth.pickle').write_bytes(b'authored opaque bytes; not a pickle')
        body = {'plan_sha256': self.identity, 'data_sha256': 'b' * 64,
                'task_ids': sorted(self.plan['train_ids'] + self.plan['eval_ids']),
                'sha256': sha256(self.root / 'groundtruth.pickle')}
        (self.root / 'manifest.json').write_text(json.dumps(body))
        self.assertEqual(parent.verify_references(self.root, self.plan, 'b' * 64)['task_count'], 378)
        with self.assertRaises(ProfileError):
            parent.verify_references(self.root, self.plan, 'c' * 64)

    def test_runtime_flags_forbid_worker_mode_replay_and_old_suite_repair(self):
        flags = argparse.Namespace(execute_screen=True, recover_initialization_timeout=True,
            retain_evaluation_unknowns=True, guarded_scoring_v2=True, durable_rollout_evidence=True,
            execution_attempt='controls_completion_2', recover_suite_watchdog=False,
            _worker=False, phase=None, worker_deadline_epoch=None)
        parent.verify_flags(flags)
        for key, value in [('recover_suite_watchdog', True), ('_worker', True), ('phase', 'W_prefix'),
                           ('worker_deadline_epoch', 5), ('execution_attempt', 'controls_completion_unauthorized'),
                           ('guarded_scoring_v2', False), ('durable_rollout_evidence', False)]:
            changed = copy.copy(flags)
            setattr(changed, key, value)
            with self.assertRaises(ProfileError):
                parent.verify_flags(changed)


class CompletionQueueTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.plan = fixture_plan()
        self.args = argparse.Namespace(out=str(self.root), worker_deadline_epoch=10000,
                                       plan_identity=identity_hash(self.plan))

    def launch_fixture(self, failure_phase=None, wrong_dose=False):
        calls = []
        def launch(command, out, seconds, phase):
            name = command[command.index('--phase') + 1]
            calls.append((name, seconds, phase, command))
            if name == failure_phase:
                return 1
            if name.startswith('eval_'):
                body = {'plan_sha256': self.args.plan_identity, 'state': name.removeprefix('eval_'), 'completions': 1024}
                marker = 'evaluation_complete.json'
            else:
                body = {'plan_sha256': self.args.plan_identity, 'phase': name,
                        'committed_updates': 127 if wrong_dose else 128, 'training_completions': 2048}
                marker = 'phase_complete.json'
            (out / marker).write_text(json.dumps(body))
            return 0
        return launch, calls

    def run_queue(self, launcher):
        with mock.patch.object(parent.runtime, 'remaining', return_value=9000), \
             mock.patch.object(parent.runtime, 'disk_gate'):
            return parent.run_queue(self.args, self.plan, ['authored-never-executed'],
                                    clock=lambda: 1000, launcher=launcher)

    def test_exact_serial_queue_dose_no_w_load_and_phase_deadlines(self):
        launch, calls = self.launch_fixture()
        self.assertEqual(self.run_queue(launch), 0)
        self.assertEqual([x[0] for x in calls], list(cp.PHASES))
        self.assertEqual([x[1] for x in calls], [2700, 2700, 2700, 1800, 1800, 1800])
        self.assertFalse((self.root / 'W_prefix').exists())
        complete = json.loads((self.root / 'control_completion_complete.json').read_text())
        self.assertFalse(complete['scientific_success_claimed'])
        self.assertFalse(complete['automatic_continuation'])

    def test_failed_child_stops_queue_without_retry_or_later_generation(self):
        launch, calls = self.launch_fixture(failure_phase='C_future')
        self.assertEqual(self.run_queue(launch), 1)
        self.assertEqual([x[0] for x in calls], ['C_prefix', 'C_future'])
        self.assertFalse((self.root / 'R_future').exists())
        failed = json.loads((self.root / 'completion_failure.json').read_text())
        self.assertFalse(failed['retry'])
        self.assertTrue(failed['direction_should_be_paused_if_completion_unsuccessful'])

    def test_existing_phase_directory_is_ambiguous_and_never_replayed(self):
        (self.root / 'C_prefix').mkdir()
        launch = mock.Mock()
        with self.assertRaises(FileExistsError):
            self.run_queue(launch)
        launch.assert_not_called()

    def test_zero_exit_without_full_phase_dose_is_not_success(self):
        launch, calls = self.launch_fixture(wrong_dose=True)
        with self.assertRaisesRegex(ProfileError, 'frozen dose'):
            self.run_queue(launch)
        self.assertEqual(len(calls), 1)
        self.assertFalse((self.root / 'control_completion_complete.json').exists())


if __name__ == '__main__':
    unittest.main()

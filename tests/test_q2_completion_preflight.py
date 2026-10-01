"""Authored evidence/admission checks; never execute a model-generated program."""
import json
from types import SimpleNamespace
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
from experiments.q2_supervision_migration.screen_scoring import score_pair
from experiments.q2_supervision_migration.screen_runtime import parse

class CompletionIntegrationTests(unittest.TestCase):
    def problem(self):
        return {'base_input':[[1]],'plus_input':[[2]],'entry_point':'fixture','atol':0}
    def reference(self):
        return {'base':[1],'plus':[2],'base_time':[.01],'plus_time':[.01]}
    def test_known_verdicts_never_invoke_repair(self):
        def forbidden(*a,**k): raise AssertionError('repair called for known verdict')
        with patch.dict('sys.modules',{'experiments.q2_supervision_migration.scoring_guard_v2':SimpleNamespace(diagnose_timeout=forbidden)}):
            for status in ['pass','fail']:
                result=score_pair(self.problem(),self.reference(),'authored inert text',lambda *a,**k:(status,[status=='pass']),fast_check=True,guarded_scoring_v2=True)
                self.assertEqual([result[k]['status'] for k in ['base','extra']],[status]*2)
    def test_unresolved_recovery_is_not_converted_to_reward(self):
        fake=SimpleNamespace(diagnose_timeout=lambda *a,**k:{'verified_suite_verdict':None,'observed':[],'prefix_consistent':False})
        with patch.dict('sys.modules',{'experiments.q2_supervision_migration.scoring_guard_v2':fake}):
            result=score_pair(self.problem(),self.reference(),'authored inert text',lambda *a,**k:('timeout',[]),fast_check=True,guarded_scoring_v2=True)
        self.assertEqual([result[k]['status'] for k in ['base','extra']],['timeout']*2)
    def test_original_known_fail_detail_is_not_rewritten(self):
        result=score_pair(self.problem(),self.reference(),'inert',lambda *a,**k:('fail',[False]),fast_check=True,guarded_scoring_v2=True)
        for value in result.values():
            self.assertEqual(value['status'],'fail')
            self.assertIsNone(json.loads(value['detail'])['initialization_timeout_diagnosis'])

class CollectAllDiagnosticTests(unittest.TestCase):
    """All scoring calls are authored mocks; no candidate or benchmark is executed."""
    def setUp(self):
        from experiments.q2_supervision_migration import completion_preflight as preflight
        self.p = preflight
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = Path(self.tmp.name)
        self.args = SimpleNamespace(out=str(self.out), source_commit='a' * 40,
                                    initial_root='initial', v2_root='v2', continuation_root='continuation')
        self.collector = preflight.DiagnosticCollector(self.out, time.time() + 1200)
        (self.out / 'reference_identity.json').write_text(json.dumps({'reference_manifest_sha256': 'b' * 64}))
        self.rows = []
        for b in range(6):
            for i in range(16):
                old = self.sample('Mbpp/599', f'original_{b}_{i}')
                if b * 16 + i >= 90:
                    old['extra']['status'] = 'timeout'
                self.rows.append((b, i, old, f'original_{b}_{i}'))
        self.problems = {'Mbpp/599': {}, 'Mbpp/260': {}}
        self.refs = {task: {'base': [1], 'plus': [1], 'base_time': [.01], 'plus_time': [.01]}
                     for task in self.problems}
        self.calls = []

    @staticmethod
    def sample(task, sample_id):
        return {'task_id': task, 'sample_id': sample_id,
                'base': {'status': 'pass', 'detail': ''}, 'extra': {'status': 'pass', 'detail': ''}}

    def saved(self, phase, batch, index):
        if phase.name == 'R_future':
            old = self.sample('Mbpp/599', 'R599')
            old['extra'] = {'status': 'timeout', 'detail': json.dumps({'tests_observed': 34, 'test_passes_observed': 34})}
            return old, 'failure_R'
        if phase.name == 'C_prefix':
            old = self.sample('Mbpp/260', 'C260')
            old['base'] = {'status': 'timeout', 'detail': json.dumps({'tests_observed': 0, 'test_passes_observed': 0})}
            return old, 'failure_C'
        if phase.parent.name == 'initial':
            return self.rows[batch * 16 + index][2:]
        task = 'Mbpp/599' if batch in (10, 25) else 'Mbpp/260'
        return self.sample(task, f'{phase.name}_{batch}_{index}'), 'sentinel'

    def score(self, problem, reference, code, checker, **kwargs):
        self.calls.append(code)
        return {'base': {'status': 'pass'}, 'extra': {'status': 'pass'}}

    @staticmethod
    def diagnose(problem, code, *args, **kwargs):
        if code.startswith('failure_'):
            return {'verified_suite_verdict': 'fail', 'prefix_consistent': code != 'failure_R'}
        wanted = 'pass' if code == 'def fixture(x):\n    return x' else 'fail'
        return {'verified_suite_verdict': wanted, 'prefix_consistent': True}

    def run_mocked(self, diagnose=None, score=None, inventory_error=False):
        with patch.object(self.p, 'saved_inputs', side_effect=RuntimeError('bad inventory') if inventory_error else None,
                          return_value=self.rows), patch.object(self.p, 'saved_sample', side_effect=self.saved), \
             patch.object(self.p, 'score_pair', side_effect=score or self.score):
            self.p.run_diagnostics(self.args, self.problems, self.refs, diagnose or self.diagnose,
                                   object(), self.collector)
        return self.p.summarize_diagnostics(self.args, execution_completed=True)

    def test_prefix_conflict_is_warning_and_all_checks_complete(self):
        report = self.run_mocked()
        self.assertEqual(len(self.calls), 128)
        self.assertTrue(report['diagnostics_completed'])
        self.assertTrue(report['model_admitted'])
        self.assertEqual(report['schema'], 2)
        self.assertEqual(report['blockers'], [])
        self.assertEqual(len(report['warnings']), 3)
        self.assertEqual(report['matched_pairs'], 90)
        self.assertEqual(report['known_W_sentinels_matched'], 32)

    def test_unknown_repeat_does_not_stop_later_repeats_or_select_passing(self):
        failure_calls = []
        def diagnose(problem, code, *args, **kwargs):
            if code == 'failure_R':
                failure_calls.append(code)
                return {'verified_suite_verdict': None if len(failure_calls) == 1 else 'pass',
                        'prefix_consistent': True}
            return self.diagnose(problem, code, *args, **kwargs)
        report = self.run_mocked(diagnose=diagnose)
        self.assertEqual(len(self.calls), 128)
        self.assertEqual(len(failure_calls), 3)
        self.assertTrue(report['diagnostics_completed'])
        self.assertFalse(report['model_admitted'])
        self.assertEqual(report['diagnoses'][0]['verdicts'], [None, 'pass', 'pass'])

    def test_changed_known_reward_and_exception_do_not_truncate_coverage(self):
        def score(*args, **kwargs):
            code = args[2]
            pair = self.score(*args, **kwargs)
            if code == 'original_0_0':
                raise RuntimeError('authored scorer error')
            if code == 'original_0_1':
                pair['base']['status'] = 'fail'
            if code == 'original_0_2':
                pair['extra']['status'] = 'timeout'
            return pair
        report = self.run_mocked(score=score)
        self.assertEqual(len(self.calls), 128)
        self.assertTrue(report['diagnostics_completed'])
        self.assertFalse(report['model_admitted'])
        self.assertEqual(report['resolved_pairs'], 94)
        self.assertTrue({'item_error', 'known_reward_changed', 'unresolved_score'} <=
                        {x['reason'] for x in report['blockers']})
        error = json.loads((self.out / 'checks/original96_000_00.result.json').read_text())
        self.assertIn('authored scorer error', error['error'])

    def test_inventory_error_still_checks_individually_verified_samples(self):
        report = self.run_mocked(inventory_error=True)
        self.assertEqual(len(self.calls), 128)
        self.assertTrue(report['diagnostics_completed'])
        self.assertFalse(report['model_admitted'])
        self.assertIn({'item': 'original96_inventory', 'reason': 'item_error'}, report['blockers'])

    def test_deadline_skips_without_calling_scorer_and_reports_partial(self):
        self.collector.deadline_epoch = time.time() - 1
        report = self.run_mocked()
        self.assertEqual(self.calls, [])
        self.assertFalse(report['diagnostics_completed'])
        self.assertFalse(report['model_admitted'])
        self.assertEqual(len(report['unfinished_items']), len(self.p.expected_items()))
        self.assertTrue(any(x['reason'] == 'shared_diagnostic_deadline' for x in report['blockers']))

    def test_parent_can_summarize_killed_inflight_item_and_records_are_immutable(self):
        self.collector.run('authored_valid', lambda: ({'verified_suite_verdict': 'pass'}, [], []))
        intent = self.out / 'checks/authored_wrong.intent.json'
        intent.write_text('{"item":"authored_wrong"}')
        report = self.p.summarize_diagnostics(self.args, execution_completed=False)
        self.assertIn({'item': 'authored_wrong', 'reason': 'unfinished'}, report['blockers'])
        self.assertFalse(report['diagnostics_completed'])
        self.assertFalse(report['model_admitted'])
        with self.assertRaises(FileExistsError):
            self.collector.run('authored_valid', lambda: ({}, [], []))

    def test_binary_repeat_disagreement_blocks_without_selecting_pass(self):
        calls = []
        def diagnose(problem, code, *args, **kwargs):
            if code == 'failure_R':
                calls.append(code)
                return {'verified_suite_verdict': 'fail' if len(calls) == 2 else 'pass',
                        'prefix_consistent': True}
            return self.diagnose(problem, code, *args, **kwargs)
        report = self.run_mocked(diagnose=diagnose)
        self.assertTrue(report['diagnostics_completed'])
        self.assertFalse(report['model_admitted'])
        self.assertEqual(report['diagnoses'][0]['verdicts'], ['pass', 'fail', 'pass'])

    def test_partial_json_from_killed_writer_is_retained_and_reported(self):
        (self.out / 'checks/authored_valid.result.json').write_text('{"partial":')
        report = self.p.summarize_diagnostics(self.args, execution_completed=False)
        self.assertFalse(report['model_admitted'])
        self.assertTrue(any(x['item'] == 'authored_valid' and x['reason'] == 'unreadable_result'
                            for x in report['blockers']))
        self.assertEqual((self.out / 'checks/authored_valid.result.json').read_text(), '{"partial":')

    def test_malformed_record_types_are_retained_and_do_not_stop_summary(self):
        self.collector.run('authored_wrong', lambda: ({'verified_suite_verdict': 'fail'}, [], []))
        path = self.out / 'checks/authored_valid.result.json'
        base = {'item': 'authored_valid', 'attempted': True, 'completed': True,
                'blockers': [], 'warnings': [], 'payload': {}}
        for key, value in [('completed', 1), ('attempted', 'true'),
                           ('blockers', None), ('warnings', ['warning', 1]),
                           ('payload', ['unexpected'])]:
            with self.subTest(key=key):
                raw = json.dumps({**base, key: value})
                path.write_text(raw)
                report = self.p.summarize_diagnostics(self.args, execution_completed=True)
                self.assertIn({'item': 'authored_valid', 'reason': 'invalid_record'}, report['blockers'])
                self.assertFalse(report['model_admitted'])
                self.assertEqual(report['recorded_items'], 1)
                self.assertIn('wrong', report['authored_controls_passed'])
                self.assertEqual(path.read_text(), raw)

    def test_wrong_record_identity_is_retained_and_blocks_admission(self):
        path = self.out / 'checks/authored_valid.result.json'
        raw = json.dumps({'item': 'authored_wrong', 'attempted': True, 'completed': True,
                          'blockers': [], 'warnings': [], 'payload': {}})
        path.write_text(raw)
        report = self.p.summarize_diagnostics(self.args, execution_completed=True)
        self.assertIn({'item': 'authored_valid', 'reason': 'invalid_record'}, report['blockers'])
        self.assertFalse(report['model_admitted'])
        self.assertEqual(report['recorded_items'], 0)
        self.assertEqual(path.read_text(), raw)

    def test_long_failure_fixtures_follow_regressions_and_alternate(self):
        seen = []
        original_run = self.collector.run
        def capture(name, operation):
            seen.append(name)
            return original_run(name, operation)
        self.collector.run = capture
        self.run_mocked()
        self.assertEqual(seen[-6:], ['R599_0', 'C260_0', 'R599_1', 'C260_1', 'R599_2', 'C260_2'])
        self.assertEqual(seen, self.p.expected_items())

if __name__=='__main__': unittest.main()

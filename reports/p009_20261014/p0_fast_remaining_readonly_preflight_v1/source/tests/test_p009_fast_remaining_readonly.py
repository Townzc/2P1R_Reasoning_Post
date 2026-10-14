"""New suffix lineage/status fixtures only. No RPC, model or old-copy tests."""
import copy
import importlib.util
import unittest

spec = importlib.util.spec_from_file_location(
    'remaining_readonly', 'scripts/p009_p0_fast_remaining_readonly.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class RemainderReadonly(unittest.TestCase):
    def setUp(self):
        self.s = dict(plan_sha256='plan', parent_claim={'fast': 1},
            parent_terminal={'status': 'failed'},
            parent_spec=dict(parent_claim={'eager': 1}, parent_terminal={'status': 'failed'}),
            ancestor_marker={'immutable': 'old-owner-plan-A'})
        self.claim = dict(run_id=m.RUN, attempt_id='new-attempt', plan_sha256='plan',
            stage='p0_fast_remaining', reserved_cents=252)

    def args(self, claim=None):
        c = self.claim if claim is None else claim
        terminal = dict(run_id=m.RUN, attempt_id=c['attempt_id'], status='failed',
            claim_sha256=m.digest(c))
        marker = dict(child_campaign=m.CAMPAIGN, child_run=m.RUN,
            child_claim_sha256=m.digest(c), spec_sha256=m.digest(self.s),
            parent_terminal=self.s['parent_terminal'], inherited_outputs=256,
            suffix_outputs=2382, parent_stays_failed=True)
        return [self.s, c, terminal, self.s['parent_claim'], self.s['parent_terminal'],
            marker, self.s['parent_spec']['parent_claim'],
            self.s['parent_spec']['parent_terminal'], self.s['ancestor_marker']]

    def test_status_exact_30_keys_exclude_inherited_and_include_both_ancestors(self):
        keys = m.status_keys()
        self.assertEqual(len(keys), 30)
        self.assertEqual(len(set(keys)), 30)
        self.assertNotIn(m.PREFIX+m.RUN+'/unit/base_638_0000', keys)
        self.assertIn(m.PREFIX+m.RUN+'/unit/base_638_0256', keys)
        self.assertIn(m.PREFIX+m.RUN+'/done/correct_969_1280', keys)
        for key in m.lineage_keys():
            self.assertIn(key, keys)

    def test_exact_failed_suffix_and_pre_marker_failure_accepted(self):
        args = self.args()
        m.failed_binding(*args)
        args[5] = None
        m.failed_binding(*args)

    def test_completed_or_mismatched_terminal_refused(self):
        for change in ({'status': 'completed'}, {'claim_sha256': 'wrong'}, {'attempt_id': 'wrong'}):
            args = self.args()
            args[2] = dict(args[2], **change)
            with self.assertRaises(ValueError):
                m.failed_binding(*args)

    def test_changed_plan_reservation_or_stage_refused(self):
        for change in ({'plan_sha256': 'wrong'}, {'reserved_cents': 251}, {'stage': 'p0_fast'}):
            args = self.args(dict(self.claim, **change))
            with self.assertRaises(ValueError):
                m.failed_binding(*args)

    def test_ancestor_and_original_marker_must_remain(self):
        for index in (3, 4, 6, 7, 8):
            args = self.args()
            args[index] = None
            with self.assertRaises(ValueError):
                m.failed_binding(*args)

    def test_suffix_marker_cannot_alias_different_scope_or_claim(self):
        for field in ('child_campaign', 'child_run', 'child_claim_sha256', 'spec_sha256'):
            args = self.args()
            args[5] = dict(args[5], **{field: 'different'})
            with self.assertRaises(ValueError):
                m.failed_binding(*args)
        args = self.args()
        args[5] = copy.deepcopy(args[5])
        args[5]['parent_stays_failed'] = False
        with self.assertRaises(ValueError):
            m.failed_binding(*args)


if __name__ == '__main__':
    unittest.main()

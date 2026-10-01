import unittest
from unittest import mock
from experiments.q2_supervision_migration import scoring_cpu as sc


class FixedScoringPlacementTests(unittest.TestCase):
    def test_fixed_zero_is_not_selected_using_performance(self):
        with mock.patch.object(sc.platform, 'system', return_value='Linux'), \
             mock.patch.object(sc.os, 'sched_getaffinity', create=True, side_effect=[{0, 1, 2}, {0}]), \
             mock.patch.object(sc.os, 'sched_setaffinity', create=True) as setter:
            result = sc.pin_scoring_cpu()
        setter.assert_called_once_with(0, {0})
        self.assertEqual(result['allowed_after'], [0])
        self.assertFalse(result['timers_changed'])

    def test_unavailable_cpu_is_not_silently_replaced(self):
        with mock.patch.object(sc.platform, 'system', return_value='Linux'), \
             mock.patch.object(sc.os, 'sched_getaffinity', create=True, return_value={2, 3}), \
             mock.patch.object(sc.os, 'sched_setaffinity', create=True) as setter:
            with self.assertRaisesRegex(RuntimeError, 'unavailable'):
                sc.pin_scoring_cpu()
        setter.assert_not_called()

    def test_unapplied_placement_refuses_admission(self):
        with mock.patch.object(sc.platform, 'system', return_value='Linux'), \
             mock.patch.object(sc.os, 'sched_getaffinity', create=True, return_value={0, 1}), \
             mock.patch.object(sc.os, 'sched_setaffinity', create=True):
            with self.assertRaisesRegex(RuntimeError, 'not applied'):
                sc.pin_scoring_cpu()

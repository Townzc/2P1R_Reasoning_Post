import unittest
from experiments.learning_regime_p009 import gates as g


class GateTests(unittest.TestCase):
    def outcomes(self, correct, n=100):
        return {str(i): i < correct for i in range(n)}

    def test_parity_boundaries_and_fail_closed_hole(self):
        a = self.outcomes(60)
        self.assertEqual(g.parity(a, self.outcomes(61))["decision"], "pass_comparable")
        self.assertEqual(g.parity(a, self.outcomes(63))["decision"], "pass_internal_only")
        self.assertEqual(g.parity(a, self.outcomes(64))["decision"], "stop_investigate_engine_difference")
        b = a.copy()
        for i in (0, 1, 2, 97, 98, 99):
            b[str(i)] = not b[str(i)]
        self.assertEqual(g.parity(a, b)["decision"], "blocked_unspecified_discordance_case")

    def test_missing_unknown_outcomes_are_not_scored(self):
        with self.assertRaises(ValueError):
            g.paired_counts({"a": True}, {"b": True})
        with self.assertRaises(ValueError):
            g.paired_counts({"a": None}, {"a": False})

    def test_g0_exact_threshold(self):
        self.assertTrue(g.g0(80, 60, 15, 100, 0))
        for values in [(79, 60, 15, 100, 0), (80, 60, 16, 100, 0), (80, 60, 15, 100, 1)]:
            self.assertFalse(g.g0(*values))

    def test_g1_requires_both_seeds_and_strict_ci(self):
        a = {"n": 1000, "delta_count": 50}
        b = {"n": 1000, "delta_count": 25}
        self.assertTrue(g.g1(a, b, .001))
        self.assertFalse(g.g1(a, b, 0))
        self.assertFalse(g.g1(a, {"n": 1000, "delta_count": 24}, .1))

    def test_nc_and_futility_boundaries(self):
        self.assertTrue(g.nc_stop(50, 1000))
        self.assertFalse(g.nc_stop(49, 1000))
        self.assertTrue(g.futility([{"n": 1000, "delta_count": 19}]))
        self.assertFalse(g.futility([{"n": 1000, "delta_count": 20}]))
        with self.assertRaises(ValueError):
            g.futility([])

    def test_nstar_does_not_round(self):
        self.assertEqual(g.n_star(690, 700, 1000), 400)
        self.assertEqual(g.n_star(689, 700, 1000), 1600)

    def test_cost_uses_full_slowest_batch_and_rounds_up(self):
        self.assertEqual(g.batch_forecast_cents([1, 3, 2], 10, 5, '.001'), 4)
        for values in ([], [0], [float('nan')]):
            with self.assertRaises(ValueError):
                g.batch_forecast_cents(values, 1, 0, '.001')

    def test_stage_budget_includes_pending_and_reservation(self):
        self.assertTrue(g.budget_gate('stage0', 100, 100, 640, 800))
        self.assertFalse(g.budget_gate('stage0', 100, 100, 641, 800))
        self.assertFalse(g.budget_gate('stage0', 100, 100, 640, 801))
        with self.assertRaises(ValueError):
            g.budget_gate('reserve', 0, 0, 1, 1)


if __name__ == '__main__':
    unittest.main()

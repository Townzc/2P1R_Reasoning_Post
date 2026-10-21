"""New D-only operational checks; no corpus/model or old successful tests."""
import ast
from copy import deepcopy
import json
from pathlib import Path
import unittest

from experiments.p011 import long_d_pair_numeric as numeric
from experiments.p011 import long_d_pair_path as path
from experiments.p011 import long_d_pair_evidence as evidence

ROOT = Path(__file__).resolve().parents[1]
SPEC = json.loads((ROOT / path.SPEC).read_text())


def functions(filename):
    tree = ast.parse((ROOT / filename).read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == 'experiments.p011.long_d_pair_numeric':
            node.module = 'experiments.p011.long_numeric'
    return {n.name: ast.dump(n, include_attributes=False) for n in tree.body
            if isinstance(n, (ast.FunctionDef, ast.ClassDef))}


class DPairRuntime(unittest.TestCase):
    def setUp(self):
        self.job = deepcopy(SPEC['jobs'][path.D_JOBS[0]])
        self.policy = path.policy(self.job, 100, '0')

    def test_elapsed_once_training_mean_endpoint_max(self):
        got = numeric.forecast(self.policy, 2, 1, [40, 2, 2], [700, 100], 110)
        mean = 44 / 3
        self.assertAlmostEqual(got['projected_total_worker_seconds'], 10 + 1.2 * (2 * mean + 700 + 963))
        self.assertEqual(got['observed_complete_training_max_seconds'], 40)
        self.assertAlmostEqual(got['training_unit_estimate_seconds'], mean)
        self.assertEqual(got['endpoint_batch_max_seconds'], 700)

    def test_historical_floor_and_uncalibrated_endpoint_floor(self):
        got = numeric.forecast(self.policy, 2, 1, [1, 2], [50], 100)
        self.assertEqual(got['training_unit_estimate_seconds'], max(self.job['timing']['training_unit_seconds']))
        self.assertEqual(got['endpoint_batch_max_seconds'], 600)
        self.assertTrue(got['endpoint_proxy_is_uncalibrated'])

    def test_nonfinite_or_bodyless_timing_rejected(self):
        for seq in ([float('nan')], [float('inf')], [0], [-1], [True]):
            with self.subTest(seq=seq), self.assertRaises(ValueError):
                numeric.forecast(self.policy, 2, 1, seq, [], 100)

    def test_delegated_scope_and_future_allowance_cannot_expand(self):
        for key, value in [('category', 'A'), ('measurement_exceptions', 1),
                           ('uncalibrated_future_seconds', 600), ('elapsed_multiplier', 1.2),
                           ('delegated_forecast_decision_sha256', '0' * 64)]:
            p = {**self.policy, key: value}
            with self.subTest(key=key), self.assertRaises(ValueError):
                numeric.forecast(p, 2, 1, [], [], 100)

    def test_fixed_hard_and_absolute_windows(self):
        with self.assertRaises(ValueError):
            numeric.forecast(self.policy, 64, 7, [], [], 900)
        p = {**self.policy, 'result_deadline_epoch': 100 + self.policy['full_result_seconds'] - 1}
        with self.assertRaises(ValueError):
            numeric.forecast(p, 1, 1, [], [], 100)

    def test_original_predicted_cost_gate_still_enforced(self):
        p = {**self.policy, 'prior_reserved_usd': '13'}
        with self.assertRaisesRegex(ValueError, '80-percent'):
            numeric.forecast(p, 64, 7, [], [], 100)

    def test_second_projection_fits_but_conservative_pair_gate_blocks(self):
        second = SPEC['jobs'][path.D_JOBS[1]]
        p = path.policy(second, 100, '11.40')
        got = numeric.forecast(p, 64, 7, [], [], 100)
        self.assertLessEqual(float(got['projected_usd']), 10.88)
        with self.assertRaisesRegex(ValueError, 'Both D full reservations'):
            path.pair_budget(SPEC, [], '0')
        with self.assertRaisesRegex(ValueError, 'Both D full reservations'):
            path.pair_budget(SPEC, [{'logical_id': path.D_JOBS[0]}], '11.40')

    def test_no_A_or_fabricated_smoke_selection(self):
        selection = path.selection(self.job, None)
        self.assertTrue(selection['no_A_smoke_selection'])
        self.assertTrue(selection['limitation_must_be_disclosed'])
        with self.assertRaises(ValueError):
            path.selection(self.job, {'decision': 'PASS'})
        with self.assertRaises(ValueError):
            path.selection({**self.job, 'cell': 'A7'}, None)

    def test_scientific_execution_and_oracle_functions_unchanged(self):
        self.assertEqual(functions('experiments/p011/long_d_pair_execution.py'),
                         functions('experiments/p011/long_lr_r2_execution.py'))
        self.assertEqual(functions('experiments/p011/long_d_pair_evidence.py'),
                         functions('experiments/p011/long_lr_r2_evidence.py'))
        self.assertEqual(functions('scripts/p011_long_d_pair_io.py'),
                         functions('scripts/p011_long_current_io.py'))
        self.assertEqual(functions('scripts/analyze_p011_long_d_pair.py'),
                         functions('scripts/analyze_p011_long_current_pair.py'))

    def test_local_oracle_uses_same_new_formula(self):
        value = numeric.forecast(self.policy, 2, 1, [40, 2, 2], [700], 110)
        evidence.replay_forecast(value, self.policy, 2, 1, [40, 2, 2], [700])
        with self.assertRaises(ValueError):
            evidence.replay_forecast({**value, 'projected_total_worker_seconds': 1}, self.policy, 2, 1, [40, 2, 2], [700])


if __name__ == '__main__':
    unittest.main()

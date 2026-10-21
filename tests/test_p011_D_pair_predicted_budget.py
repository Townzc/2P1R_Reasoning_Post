"""New checks for the explicit 87d2eba3 budget clarification only.

The unchanged original candidate supplies synthetic admission metadata. These
checks do not call model, provider, input, collector, or scoring operations.
"""
from copy import deepcopy
from decimal import Decimal
import json
from pathlib import Path
import unittest

from experiments.p011 import long_d_pair_path as path

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = json.loads((ROOT / 'reports/p011_20261020/long_d_pair_runtime_v1/SPEC.json').read_text())


class PredictedPairBudget(unittest.TestCase):
    def test_pair_keeps_full_reserves_and_checks_each_prediction(self):
        steps = path.pair_budget(ORIGINAL, [], '0')
        self.assertEqual([s['prior_D_reserved_usd'] for s in steps], ['0', '11.40'])
        self.assertEqual([s['reserved_usd'] for s in steps], ['11.40', '11.40'])
        self.assertEqual([s['initial_forecast']['projected_usd'] for s in steps], ['10.33', '10.27'])
        self.assertEqual(sum(Decimal(s['reserved_usd']) for s in steps), Decimal('22.80'))
        for step in steps:
            remaining = Decimal('25') - Decimal(step['prior_D_reserved_usd'])
            self.assertLessEqual(Decimal(step['initial_forecast']['projected_usd']), Decimal('.8') * remaining)

    def test_second_entry_retains_first_attempt_reservation(self):
        steps = path.pair_budget(ORIGINAL, [{'logical_id': path.D_JOBS[0]}], '11.40')
        self.assertEqual(len(steps), 1)
        self.assertEqual(steps[0]['logical_id'], path.D_JOBS[1])
        self.assertEqual(steps[0]['prior_D_reserved_usd'], '11.40')

    def test_full_reserve_over_remaining_cap_rejected(self):
        with self.assertRaisesRegex(ValueError, 'remaining D cap'):
            path.pair_budget(ORIGINAL, [{'logical_id': path.D_JOBS[0]}], '14')

    def test_predicted_eighty_percent_still_blocks_when_reserve_fits(self):
        with self.assertRaisesRegex(ValueError, '80-percent D prediction'):
            path.pair_budget(ORIGINAL, [{'logical_id': path.D_JOBS[0]}], '12.20')

    def test_whole_pair_checked_before_first_entry(self):
        candidate = deepcopy(ORIGINAL)
        candidate['jobs'][path.D_JOBS[1]]['limits']['reserved_usd'] = '14.00'
        with self.assertRaisesRegex(ValueError, 'remaining D cap'):
            path.pair_budget(candidate, [], '0')


if __name__ == '__main__':
    unittest.main()

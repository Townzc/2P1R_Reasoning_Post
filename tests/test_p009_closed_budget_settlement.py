"""New pure budget accounting fixtures; no provider calls or prior test rerun."""
import copy
import unittest
from experiments.learning_regime_p009.closed_budget_settlement import build_settlement, app_meter
from experiments.sft_allocation_midpoint.common import digest


class ClosedBudget(unittest.TestCase):
    def setUp(self):
        self.claim = dict(run_id='run', attempt_id='attempt', reserved_cents=252)
        self.closed = [dict(app_id='ap-test', campaign='camp', run_id='run', claim=self.claim,
            terminal=dict(run_id='run', attempt_id='attempt', status='failed',
                finished_epoch=1000, claim_sha256=digest(self.claim)))]
        self.provider = dict(original_app_info=[dict(app_id='ap-test', lifecycle=dict(
            state='stopped', stopped_at='1970-01-01T00:16:50+00:00'))], owned_containers=[])
        self.rows = [dict(object_id='ap-test', environment='main', interval_start='1970-01-01', cost='0.12490961')]
        self.snapshots = [dict(observed_epoch=3000, rows=self.rows)]

    def build(self, **kw):
        args = dict(snapshots=self.snapshots, closed=self.closed, provider=self.provider,
                    now_epoch=3010, pending_reserved_cents=252)
        args.update(kw)
        return build_settlement(**args)

    def test_decimal_rounding_buffer_and_full_new_reserve(self):
        out = self.build()
        self.assertEqual(out['settled_failed_cents'], 63)
        self.assertEqual(out['released_reservation_cents'], 189)
        self.assertEqual(out['stage_remaining_cents'], 685)
        self.assertFalse(out['runtime_admitted'])

    def test_missing_and_duplicate_meter_are_not_free(self):
        for rows in ([], self.rows*2):
            with self.assertRaises(ValueError):
                app_meter(rows, 'ap-test')

    def test_stopped_failed_identity_required(self):
        for field, value in (('status', 'completed'), ('claim_sha256', 'wrong')):
            c = copy.deepcopy(self.closed); c[0]['terminal'][field] = value
            with self.assertRaises(ValueError):
                self.build(closed=c)
        p = copy.deepcopy(self.provider); p['owned_containers'] = [{'app_id': 'ap-test'}]
        with self.assertRaises(ValueError):
            self.build(provider=p)

    def test_stale_future_and_just_stopped_snapshots_refused(self):
        for t in (200, 1900, 4000):
            with self.assertRaises(ValueError):
                self.build(snapshots=[dict(observed_epoch=t, rows=self.rows)])
        with self.assertRaises(ValueError):
            self.build(now_epoch=7000)

    def test_cost_decrease_never_releases_again(self):
        prior = self.build()
        rows = [dict(self.rows[0], cost='0.01')]
        out = self.build(snapshots=[dict(observed_epoch=3010, rows=rows)], previous=prior)
        self.assertEqual(out['settled_failed_cents'], prior['settled_failed_cents'])
        self.assertEqual(out['runs'][0]['meter_floor_usd'], '0.12490961')

    def test_cost_increase_is_not_clipped_to_old_claim(self):
        rows = [dict(self.rows[0], cost='10.01')]
        out = self.build(snapshots=[dict(observed_epoch=3010, rows=rows)])
        self.assertGreater(out['settled_failed_cents'], 252)
        self.assertLess(out['released_reservation_cents'], 0)
        self.assertFalse(out['fits_stage_cap'])

    def test_double_settlement_and_changed_claim_refused(self):
        with self.assertRaises(ValueError):
            self.build(closed=self.closed*2)
        prior = self.build(); c = copy.deepcopy(self.closed)
        c[0]['claim']['reserved_cents'] = 253
        c[0]['terminal']['claim_sha256'] = digest(c[0]['claim'])
        with self.assertRaises(ValueError):
            self.build(closed=c, previous=prior)

    def test_original_claims_unchanged_and_bad_money_refused(self):
        original = copy.deepcopy(self.closed)
        self.build()
        self.assertEqual(self.closed, original)
        for value in ('NaN', '-0.1', 'Infinity', 0.1):
            with self.assertRaises(ValueError):
                app_meter([dict(self.rows[0], cost=value)], 'ap-test')


if __name__ == '__main__':
    unittest.main()

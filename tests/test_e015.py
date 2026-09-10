"""CPU-only launcher, inherited-recipe and whole-rental-window guards."""
from datetime import datetime, timedelta, timezone
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from analyses import e015


class RentalWindowTests(unittest.TestCase):
    def setUp(self):
        self.start = datetime(2026, 9, 10, 8, tzinfo=timezone.utc)

    def test_rate_and_full_export_exit_reservation(self):
        record = e015.rental_window(self.start.isoformat(), 'provider_timestamp', self.start + timedelta(minutes=6))
        self.assertEqual(record['hourly_rate'], 8)
        self.assertEqual(record['overall_ceiling_cny'], 3000)
        self.assertEqual(record['required_job_export_exit_seconds'], 2040)
        self.assertEqual(record['remaining_planned_window_seconds'], 2340)
        self.assertFalse(record['actual_bill_known'])
        self.assertFalse(record['provider_shutdown_confirmed'])

    def test_rejects_enough_time_for_model_but_not_backup(self):
        with self.assertRaisesRegex(ValueError, 'whole-rental'):
            e015.rental_window(self.start.isoformat(), 'provider_timestamp', self.start + timedelta(minutes=12))

    def test_naive_future_and_unknown_time_source_rejected(self):
        with self.assertRaises(ValueError):
            e015.rental_window('2026-09-10T08:00:00', 'provider_timestamp', self.start)
        with self.assertRaises(ValueError):
            e015.rental_window((self.start + timedelta(seconds=1)).isoformat(), 'provider_timestamp', self.start)
        with self.assertRaises(ValueError):
            e015.rental_window(self.start.isoformat(), 'invented', self.start)

    def test_notification_does_not_claim_provider_start_verified(self):
        record = e015.rental_window(self.start.isoformat(), 'owner_start_notification', self.start)
        self.assertFalse(record['provider_start_time_verified'])
        self.assertTrue(record['notification_may_postdate_actual_power_on'])


class LauncherTests(unittest.TestCase):
    def test_inspect_and_unconfirmed_launch_never_touch_server(self):
        cfg = json.loads(e015.CONFIG.read_text())
        planned = {'optimizer_updates': 256, 'supervised_response_tokens': 167232, 'processed_nonpadding_tokens': 229056}
        state = (cfg, {}, [], [], [], planned, [])
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(e015, 'INPUTS', Path(tmp)), patch.object(e015, 'verified_tokenizer', return_value=(object(), {})), \
                 patch.object(e015, 'load_release', return_value=state), patch.object(e015, 'provenance', return_value={'source_commit': 'fixture'}), \
                 patch.object(e015, 'git', return_value=''), patch.object(e015, 'check_ledger', return_value={'remaining_seconds': 733}), \
                 patch.object(e015, 'sha256_file', return_value='fixture'), patch.object(e015, 'server_preflight') as server, \
                 patch.object(e015.subprocess, 'call') as execute, patch('sys.stdout', new_callable=io.StringIO):
                for action in ['inspect', 'launch', 'reclaim']:
                    with patch('sys.argv', ['e015', action, '--tokenizer-dir', tmp]):
                        self.assertEqual(e015.main(), 0)
                server.assert_not_called()
                execute.assert_not_called()

    def test_explicit_launch_requires_power_window_before_server_use(self):
        cfg = json.loads(e015.CONFIG.read_text())
        planned = {'optimizer_updates': 256, 'supervised_response_tokens': 167232, 'processed_nonpadding_tokens': 229056}
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(e015, 'INPUTS', Path(tmp)), patch.object(e015, 'verified_tokenizer', return_value=(object(), {})), \
                 patch.object(e015, 'load_release', return_value=(cfg, {}, [], [], [], planned, [])), \
                 patch.object(e015, 'provenance', return_value={'source_commit': 'fixture'}), patch.object(e015, 'git', return_value=''), \
                 patch.object(e015, 'check_ledger', return_value={}), patch.object(e015, 'sha256_file', return_value='fixture'), \
                 patch.object(e015, 'server_preflight') as server, patch.object(e015.subprocess, 'call') as execute, \
                 patch('sys.argv', ['e015', 'launch', '--execute', '--tokenizer-dir', tmp]):
                with self.assertRaisesRegex(ValueError, 'power-on timestamp'):
                    e015.main()
                server.assert_not_called()
                execute.assert_not_called()

    def test_prepare_refuses_existing_release_without_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / 'inputs'
            folder.mkdir()
            marker = folder / 'original'
            marker.write_bytes(b'preserve')
            with patch.object(e015, 'INPUTS', folder), patch.object(e015, 'provenance') as provenance:
                with self.assertRaises(FileExistsError):
                    e015.prepare(object())
                provenance.assert_not_called()
                self.assertEqual(marker.read_bytes(), b'preserve')


if __name__ == '__main__':
    unittest.main()

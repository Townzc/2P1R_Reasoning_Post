"""Only the new common absolute-closeout boundary, no old tests rerun."""
import unittest
from experiments.p011.c1_execution import CUTOFF_EPOCH
from scripts.p011_c1_io import remaining_io_seconds
from tests.test_p011_c1_execution_draft import spec


class C1IOWindowTests(unittest.TestCase):
    def test_collect_and_audit_share_one_original_deadline(self):
        s = spec(); start = CUTOFF_EPOCH-5000
        receipt = {'worker_start_epoch': start}
        first, limit1 = remaining_io_seconds('collect', s, start+1000, receipt)
        second, limit2 = remaining_io_seconds('audit', s, start+1200, receipt)
        self.assertEqual(limit1, limit2)
        self.assertEqual((first, second), (500, 300))

    def test_expired_or_impossible_start_never_extends_window(self):
        s = spec(); start = CUTOFF_EPOCH-5000
        for now in (start+1500, CUTOFF_EPOCH+1, start-1):
            with self.assertRaises((ValueError, TimeoutError)):
                remaining_io_seconds('audit', s, now, {'worker_start_epoch': start})

    def test_upload_reserves_entire_future_window_and_local_maximum(self):
        s = spec()
        self.assertEqual(remaining_io_seconds('upload', s, CUTOFF_EPOCH-10000)[0], 3600)
        self.assertEqual(remaining_io_seconds('upload', s, CUTOFF_EPOCH-2260)[0], 100)
        with self.assertRaises(TimeoutError):
            remaining_io_seconds('upload', s, CUTOFF_EPOCH-2160)


if __name__ == '__main__': unittest.main()

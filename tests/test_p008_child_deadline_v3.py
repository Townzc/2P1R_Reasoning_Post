import ast
import json
import unittest
from pathlib import Path
from tests.test_p008_continuation_worker import fixture
from experiments.sft_allocation_midpoint.common import digest
from experiments.sft_allocation_p008.continuation_binding import CHILD_DEADLINE, validate_continuation_binding


def rehash(a):
    p,c,r,s=a;s['plan_sha256']=digest(p);s['config_sha256']=digest(c)
    r['spec_sha256']=digest(s);r['gates']['runtime_review']['spec_sha256']=digest(s)


class DeadlineV3Tests(unittest.TestCase):
    def test_new_exact_deadline_and_latest_dispatch(self):
        self.assertEqual(CHILD_DEADLINE,1791925200)
        self.assertEqual(CHILD_DEADLINE-7900,1791917300)
        self.assertTrue(validate_continuation_binding(*fixture()))
    def test_old_or_later_deadline_rejected_even_rehashed(self):
        for t in (1791921600,1791928800):
            a=fixture();a[0]['deadline_epoch']=t;rehash(a)
            with self.assertRaises(ValueError):validate_continuation_binding(*a)
    def test_old_owner_deadline_not_accepted(self):
        a=fixture();a[3]['owner_authorization']['child_deadline_utc']='2026-10-13T20:00:00Z';rehash(a)
        with self.assertRaises(ValueError):validate_continuation_binding(*a)
    def test_old_review_not_transferred(self):
        a=fixture();a[2]['gates']['runtime_review']['spec_sha256']='f'*64
        with self.assertRaises(ValueError):validate_continuation_binding(*a)
    def test_budget_and_worker_cap_still_exact(self):
        for seconds in (7199,7201):
            a=fixture();a[1]['max_seconds']=seconds;rehash(a)
            with self.assertRaises(ValueError):validate_continuation_binding(*a)
        a=fixture();a[3]['stage_reserved_cents']+=1200;rehash(a)
        with self.assertRaises(ValueError):validate_continuation_binding(*a)
    def test_published_amendment_only_changes_authorized_fields(self):
        root=Path('reports/p008_20261013')
        v2=json.loads((root/'d2_continuation_admission_v2/ADMISSION.json').read_text())
        v3=json.loads((root/'d2_continuation_admission_v3/ADMISSION.json').read_text())
        self.assertEqual({k for k in v2 if v2[k]!=v3[k]}, {'owner_authorization','plan_sha256','source_files'})
        self.assertEqual({k for k in v2['source_files'] if v2['source_files'][k]!=v3['source_files'][k]},
                         {'experiments/sft_allocation_p008/continuation_binding.py','experiments/sft_allocation_p008/modal_pool_continuation.py'})


if __name__=='__main__':unittest.main()

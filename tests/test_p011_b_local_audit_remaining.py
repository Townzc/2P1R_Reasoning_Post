"""New boundary checks for the proposed local-only continuation; no old corpus."""
from pathlib import Path
import tempfile
import unittest

from scripts import continue_p011_b_student_local_audit as continuation


class RemainingAuditBoundary(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.failed = dict(type='ModuleNotFoundError', message="No module named 'transformers'",
                           partial_retained=True, whole_helper_retry_allowed=False)
        continuation.create(self.root/'FAILED.json', self.failed)

    def test_exact_environment_failure_only(self):
        self.assertEqual(continuation.failure_gate(self.root), self.failed)
        (self.root/'FAILED.json').unlink()
        continuation.create(self.root/'FAILED.json', {**self.failed, 'message': 'different error'})
        with self.assertRaisesRegex(ValueError, 'exact unexecuted-oracle'):
            continuation.failure_gate(self.root)

    def test_any_partial_tail_output_blocks(self):
        for name in continuation.OUTPUTS:
            with self.subTest(name=name):
                file = self.root/name;file.touch()
                with self.assertRaisesRegex(ValueError, 'partial/completed'):
                    continuation.failure_gate(self.root)
                file.unlink()

    def test_new_fence_is_permanent_and_job_scoped(self):
        continuation.claim(self.root, continuation.JOBS[0], {'test': True})
        with self.assertRaises(FileExistsError):
            continuation.claim(self.root, continuation.JOBS[0], {'test': True})
        with self.assertRaises(ValueError):
            continuation.claim(self.root, 'different_job', {})

    def test_tail_append_preserves_original_failure_and_never_overwrites(self):
        old = (self.root/'FAILED.json').read_bytes()
        continuation.create(self.root/'COMPLETE_PROOF.json', {'synthetic': True})
        self.assertEqual((self.root/'FAILED.json').read_bytes(), old)
        with self.assertRaises(FileExistsError):
            continuation.create(self.root/'COMPLETE_PROOF.json', {'synthetic': False})


if __name__ == '__main__':
    unittest.main()

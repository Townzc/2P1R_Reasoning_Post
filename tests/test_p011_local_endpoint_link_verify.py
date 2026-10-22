import hashlib
from pathlib import Path
import tempfile
import unittest

from experiments.p011.local_endpoint_link_verify import verify_inputs, ENDPOINTS, PASSED_PREFIX


class LocalEndpointLinks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "new"
        self.prior = Path(self.temp.name) / "prior"
        self.root.mkdir()
        self.prior.mkdir()
        self.files = {}
        for name in PASSED_PREFIX + ENDPOINTS:
            content = (name + "\n").encode()
            target = self.prior / name if name in ENDPOINTS else self.root / name
            target.write_bytes(content)
            if name in ENDPOINTS:
                (self.root / name).symlink_to(target)
            self.files[name] = {"bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()}

    def test_only_exact_two_links_and_bound_bytes_pass(self):
        result = verify_inputs(self.root, self.files, self.prior)
        self.assertEqual(result["checked_in_this_continuation"], list(self.files))

    def test_matching_bytes_at_a_foreign_target_are_rejected(self):
        name = ENDPOINTS[0]
        foreign = self.root / "foreign"
        foreign.write_bytes((self.prior / name).read_bytes())
        (self.root / name).unlink()
        (self.root / name).symlink_to(foreign)
        with self.assertRaises(ValueError):
            verify_inputs(self.root, self.files, self.prior)

    def test_endpoint_content_change_is_rejected(self):
        (self.prior / ENDPOINTS[0]).write_bytes(b"changed")
        with self.assertRaises(ValueError):
            verify_inputs(self.root, self.files, self.prior)

    def test_unapproved_link_is_still_rejected(self):
        name = PASSED_PREFIX[0]
        target = self.prior / name
        (self.root / name).rename(target)
        (self.root / name).symlink_to(target)
        with self.assertRaises(ValueError):
            verify_inputs(self.root, self.files, self.prior)

    def test_reuse_is_limited_to_original_ordered_three_file_prefix(self):
        result = verify_inputs(self.root, self.files, self.prior, reuse_passed_prefix=True)
        self.assertEqual(result["checked_in_this_continuation"], list(ENDPOINTS))
        self.assertEqual(result["reused_successful_prefix"], list(PASSED_PREFIX))
        wrong_order = {ENDPOINTS[0]: self.files[ENDPOINTS[0]], **self.files}
        with self.assertRaises(ValueError):
            verify_inputs(self.root, wrong_order, self.prior, reuse_passed_prefix=True)


if __name__ == "__main__":
    unittest.main()

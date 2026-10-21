"""New regression for the independently reported raw/processed gold mismatch."""
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import prepare_p011_b_remaining_student_inputs as driver


class ReachedActualA3(Exception):
    pass


class FrozenGoldLocatorTests(unittest.TestCase):
    def fixture(self, root):
        frozen = '.local/p009_20261014/r1/stage0_inputs_r1/math500.jsonl'
        raw = '.local/p009_20261014/r1/source_assets_r1/math500/test.jsonl'
        for name, data in [(frozen, b'processed fixture\n'), (raw, b'raw decoy\n'),
                           (driver.ENDPOINT, b'endpoint fixture\n')]:
            p = root / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)
        binding = {'student_endpoint_files': {
            name: hashlib.sha256((root / name).read_bytes()).hexdigest()
            for name in (frozen, driver.ENDPOINT)}}
        return frozen, binding

    def test_original_processed_locator_reaches_A3_before_any_fence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            frozen, binding = self.fixture(root)
            self.assertEqual(driver.GOLD, frozen)
            with patch.object(driver.inputs, 'source_authority'), \
                    patch.object(driver.b_student_evidence, 'GOLD_SHA256', binding['student_endpoint_files'][frozen]), \
                    patch.object(driver, 'read', return_value={}), \
                    patch.object(driver, 'actual_generation_A3', side_effect=ReachedActualA3):
                with self.assertRaises(ReachedActualA3):
                    driver.prepare_student(root, binding, {}, {})
            self.assertFalse((root / driver.inputs.LOCAL / 'B_RUNTIME_STUDENT_INPUT_ATTEMPT.json').exists())

    def test_raw_gold_hash_cannot_authorize_the_processed_locator(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            frozen, binding = self.fixture(root)
            raw_hash = hashlib.sha256(b'raw decoy\n').hexdigest()
            with patch.object(driver.inputs, 'source_authority'), \
                    patch.object(driver.b_student_evidence, 'GOLD_SHA256', raw_hash), \
                    patch.object(driver, 'actual_generation_A3') as actual:
                with self.assertRaisesRegex(ValueError, 'Original frozen gold differs'):
                    driver.prepare_student(root, binding, {}, {})
                actual.assert_not_called()
            self.assertFalse((root / driver.inputs.LOCAL / 'B_RUNTIME_STUDENT_INPUT_ATTEMPT.json').exists())


if __name__ == '__main__':
    unittest.main()

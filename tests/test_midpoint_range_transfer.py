import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.midpoint_range_transfer import ranges, assemble


class RangeTransferTests(unittest.TestCase):
    def test_exact_tail_ranges(self):
        self.assertEqual(ranges(11, 4), [(0, 4), (4, 4), (8, 3)])

    def test_invalid_size(self):
        for value in (0, -1, True, 1.5):
            with self.assertRaises(ValueError):
                ranges(value)

    def fixture(self, root, body=b'abcdefghi'):
        parts = root/'parts'; parts.mkdir()
        for start, size in ranges(len(body), 4):
            (parts/f'{start:012d}.bin').write_bytes(body[start:start+size])
        return parts, dict(bytes=len(body), sha256=hashlib.sha256(body).hexdigest())

    def test_verified_copy_preserves_parts(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temp:
            root=Path(temp);parts,spec=self.fixture(root)
            with patch('scripts.midpoint_range_transfer.ranges', lambda size: ranges(size, 4)):
                assemble(parts,root/'state.pt',spec)
            self.assertEqual((root/'state.pt').read_bytes(),b'abcdefghi')
            self.assertEqual((parts/'assembled.pt').read_bytes(),b'abcdefghi')
            self.assertTrue((parts/'000000000000.bin').exists())

    def test_wrong_hash_does_not_publish(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temp:
            root=Path(temp);parts,spec=self.fixture(root);spec['sha256']='0'*64
            with patch('scripts.midpoint_range_transfer.ranges', lambda size: ranges(size, 4)):
                with self.assertRaises(ValueError):assemble(parts,root/'state.pt',spec)
            self.assertFalse((root/'state.pt').exists())
            self.assertTrue((parts/'assembled.pt').exists())

    def test_wrong_range_length_does_not_publish(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temp:
            root=Path(temp);parts,spec=self.fixture(root)
            (parts/'000000000004.bin').write_bytes(b'bad')
            with patch('scripts.midpoint_range_transfer.ranges', lambda size: ranges(size, 4)):
                with self.assertRaises(ValueError):assemble(parts,root/'state.pt',spec)
            self.assertFalse((root/'state.pt').exists())

    def test_existing_state_is_never_replaced(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temp:
            root=Path(temp);parts,spec=self.fixture(root);target=root/'state.pt';target.write_bytes(b'old')
            with self.assertRaises(FileExistsError):assemble(parts,target,spec)
            self.assertEqual(target.read_bytes(),b'old')


if __name__ == '__main__':unittest.main()

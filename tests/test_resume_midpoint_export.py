import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from scripts.resume_midpoint_export import inventory,reusable_ranges


class ExportRecoveryTests(unittest.TestCase):
    def test_existing_good_file_is_reused_and_bad_file_is_preserved(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            r=Path(tmp);(r/'a').write_bytes(b'ok');spec={'bytes':2,'sha256':hashlib.sha256(b'ok').hexdigest()}
            self.assertEqual(inventory(r,{'a':spec,'b':spec}),(['a'],['b']))
            (r/'a').write_bytes(b'xx')
            with self.assertRaises(ValueError):inventory(r,{'a':spec})
            self.assertEqual((r/'a').read_bytes(),b'xx')

    def test_path_escape_is_rejected(self):
        with self.assertRaises(ValueError):inventory('.',{'../x':{}})

    def fixture(self,root):
        (root/'000000000000.bin').write_bytes(b'abcd')
        spec=dict(bytes=8,sha256='unused-by-range-preflight')
        receipt=dict(remote='/f',expected=spec,read_only=True,scientific_calls=0,ranges=[dict(start=0,length=4,status='verified_response',sha256=hashlib.sha256(b'abcd').hexdigest()),dict(start=4,length=4,status='failed_or_interrupted')])
        (root/'transport_receipt.json').write_text(json.dumps(receipt));return spec

    def test_only_proven_ranges_are_reused(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            r=Path(tmp);spec=self.fixture(r)
            with patch('scripts.resume_midpoint_export.ranges',return_value=[(0,4),(4,4)]):
                self.assertEqual(reusable_ranges(r,'/f',spec),[(0,4)])
                (r/'000000000004.bin').write_bytes(b'efgh')
                with self.assertRaises(ValueError):reusable_ranges(r,'/f',spec)

    def test_changed_range_or_identity_is_rejected(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            r=Path(tmp);spec=self.fixture(r)
            with patch('scripts.resume_midpoint_export.ranges',return_value=[(0,4),(4,4)]):
                with self.assertRaises(ValueError):reusable_ranges(r,'/different',spec)
                (r/'000000000000.bin').write_bytes(b'xxxx')
                with self.assertRaises(ValueError):reusable_ranges(r,'/f',spec)


if __name__=='__main__':unittest.main()

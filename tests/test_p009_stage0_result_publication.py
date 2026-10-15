"""New synthetic original-byte archive fixtures; no real outputs or scores."""
from pathlib import Path
import tempfile
import unittest
from scripts.publish_p009_stage0_result import archive_original
from experiments.sft_allocation_midpoint.common import manifest

class OriginalArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)/'source';self.root.mkdir()
        (self.root/'raw.json').write_bytes('{"text":"α\u2028β","ids":[1,2]}\n'.encode())
        (self.root/'environment.json').write_bytes(b'{"synthetic":true}\n')
        self.out=Path(self.temp.name)/'archive.tar.gz'
    def tearDown(self):self.temp.cleanup()
    def test_original_unicode_and_full_member_bytes_survive_readback(self):
        archive_original(self.root,self.out,manifest(self.root))
        self.assertGreater(self.out.stat().st_size,0)
    def test_mismatch_preserves_archive_and_reentry_cannot_overwrite(self):
        expected=manifest(self.root);expected['raw.json']['sha256']='0'*64
        with self.assertRaises(ValueError):archive_original(self.root,self.out,expected)
        original=self.out.read_bytes()
        with self.assertRaises(FileExistsError):archive_original(self.root,self.out,manifest(self.root))
        self.assertEqual(self.out.read_bytes(),original)
    def test_unsafe_member_rejected_before_archive_creation(self):
        with self.assertRaises(ValueError):archive_original(self.root,self.out,{'../raw.json':{}})
        self.assertFalse(self.out.exists())

if __name__=='__main__':unittest.main()

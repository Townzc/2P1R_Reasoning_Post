import tempfile,unittest,json,gzip,tarfile,io
from pathlib import Path
from experiments.sft_allocation_p008.evidence_bundle import pack,unpack,safe_name
from experiments.sft_allocation_midpoint.common import sha

class BundleTest(unittest.TestCase):
 def test_pack_roundtrip_and_state_not_embedded(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp)/'run';root.mkdir();(root/'intents').mkdir();(root/'intents/x.json').write_text('{"a":1}');(root/'state.pt').write_bytes(b'outside')
   r=pack(root);self.assertEqual(r['content_files'],1)
   p=unpack(root/'compact_evidence.tar.gz',root/'compact_manifest.json',root/'bundle_receipt.json',Path(tmp)/'unpacked')
   self.assertEqual(p['files_verified'],1);self.assertEqual((Path(tmp)/'unpacked/intents/x.json').read_bytes(),b'{"a":1}')
   with self.assertRaises(FileExistsError):pack(root)
 def test_unsafe_path_rejected(self):
  for n in ('../x','/x','a/../x','a\\x','./x','a//x',''):
   with self.assertRaises(ValueError):safe_name(n)
 def test_corrupted_archive_rejected_before_unpack(self):
  with tempfile.TemporaryDirectory() as tmp:
   r=Path(tmp);(r/'x').write_text('one');pack(r);(r/'compact_evidence.tar.gz').write_bytes(b'changed')
   with self.assertRaises(ValueError):unpack(r/'compact_evidence.tar.gz',r/'compact_manifest.json',r/'bundle_receipt.json',r/'out')
 def test_symlink_rejected(self):
  with tempfile.TemporaryDirectory() as tmp:
   r=Path(tmp);(r/'x').symlink_to('/tmp')
   with self.assertRaises(ValueError):pack(r)

if __name__=='__main__':unittest.main()

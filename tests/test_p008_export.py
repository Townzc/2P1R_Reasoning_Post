import json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from experiments.sft_allocation_midpoint.common import dump,manifest,digest,sha
from experiments.sft_allocation_p008.evidence_bundle import pack
from scripts.export_p008_bundle import export

class ExportTest(unittest.TestCase):
 def fixture(self,root):
  source=root/'source';source.mkdir();dump(source/'result.json',{'engineering_fixture':True});(source/'checkpoint_0256').mkdir()
  (source/'checkpoint_0256/state.pt').write_bytes(b'not-a-model-transport-fixture')
  dump(source/'checkpoint_0256/manifest.json',{'fixture_only':True});pack(source);files=manifest(source)
  receipt=root/'receipt.json';dump(receipt,dict(artifact_manifest=files,receipt=dict(status='completed',evidence_sha256=digest(files))))
  def read_file(name):yield (source/Path(name).relative_to('/camp/run')).read_bytes()
  fake=SimpleNamespace(Volume=SimpleNamespace(from_name=lambda *a,**k:SimpleNamespace(read_file=read_file)))
  return source,receipt,fake
 def test_bundle_and_state_independently_verify(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);source,receipt,fake=self.fixture(root)
   with patch.dict('sys.modules',{'modal':fake}):
    result=export(SimpleNamespace(out=str(root/'out'),campaign='camp',run='run',volume='fixture',receipt=str(receipt)))
   self.assertTrue(result['passed']);self.assertEqual(sha(source/'checkpoint_0256/state.pt'),sha(root/'out/evidence/checkpoint_0256/state.pt'))
 def test_invalid_remote_identity_before_transfer(self):
  with self.assertRaisesRegex(ValueError,'Unsafe'):export(SimpleNamespace(campaign='../other',run='run'))
 def test_corrupt_bundle_fails_without_overwrite(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);source,receipt,fake=self.fixture(root);(source/'compact_evidence.tar.gz').write_bytes(b'bad')
   with patch.dict('sys.modules',{'modal':fake}),self.assertRaisesRegex(ValueError,'hash differs'):
    export(SimpleNamespace(out=str(root/'out'),campaign='camp',run='run',volume='fixture',receipt=str(receipt)))
if __name__=='__main__':unittest.main()

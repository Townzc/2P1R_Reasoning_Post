import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest

from experiments.public_math_pilot_v1.cache_maintenance import component_paths,evict_clean_cache


class CacheMaintenanceTest(unittest.TestCase):
    def fixture(self,root):
        out=root/'main';volume=root/'volume';arm='TrimSFT';slot='slot_000032_'+'a'*32
        control=out/'checkpoints'/arm;storage=volume/'public_math_pilot_v1'/arm
        (control/'commits').mkdir(parents=True);folder=storage/'slots'/slot;folder.mkdir(parents=True)
        owner=dict(schema=1,phase='public_math_pilot_v1',arm=arm,config_hash='b'*64)
        for path in (control,storage):(path/'checkpoint_owner.json').write_text(json.dumps(owner))
        model=folder/'model.pt';model.write_bytes(b'verified checkpoint bytes')
        record=dict(volume=0,path=str(model.relative_to(volume)),bytes=model.stat().st_size,sha256=hashlib.sha256(model.read_bytes()).hexdigest())
        manifest=dict(identity=owner,checkpoint_id=slot,files=dict(model=record),metadata=dict(parent_checkpoint_id=None))
        raw=json.dumps(manifest).encode();(control/'commits'/(slot+'.json')).write_bytes(raw)
        (control/'latest.json').write_text(json.dumps(dict(checkpoint_id=slot,manifest_sha256=hashlib.sha256(raw).hexdigest())))
        return out,volume,model

    def test_cache_advice_preserves_bytes_and_ignores_uncommitted_files(self):
        with tempfile.TemporaryDirectory() as d:
            out,volume,model=self.fixture(Path(d));before=model.read_bytes()
            (model.parent/'unknown.pt').write_text('untouched');seen=[]
            result=evict_clean_cache(out,volume,lambda fd:seen.append(os.fstat(fd).st_size))
            self.assertEqual(seen,[len(before)]);self.assertEqual(model.read_bytes(),before)
            self.assertEqual(result['files_deleted'],0);self.assertEqual(result['files_modified'],0)

    def test_deleted_superseded_file_does_not_get_recreated(self):
        with tempfile.TemporaryDirectory() as d:
            out,volume,model=self.fixture(Path(d));model.unlink()
            self.assertEqual(component_paths(out,volume),[]);self.assertFalse(model.exists())

    def test_symlink_and_changed_owner_are_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            out,volume,model=self.fixture(Path(d));data=model.read_bytes();model.unlink()
            other=Path(d)/'other';other.write_bytes(data);model.symlink_to(other)
            with self.assertRaises(ValueError):component_paths(out,volume)
            model.unlink();model.write_bytes(data)
            (volume/'public_math_pilot_v1/TrimSFT/checkpoint_owner.json').write_text('{}')
            with self.assertRaises(ValueError):component_paths(out,volume)


if __name__=='__main__':unittest.main()

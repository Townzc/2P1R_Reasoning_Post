"""New integration checks for transport and exact saved admission; no production calls."""
import contextlib
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

from scripts import p011_c1_io as io
from experiments.p011 import c1_outer as o
from experiments.sft_allocation_midpoint.common import dump, read, sha
from tests.test_p011_c1_outer import Fixture


class Volume:
    def __init__(self):
        self.files = {}; self.writes = []
    def read_file(self, path):
        if path not in self.files: raise FileNotFoundError(path)
        yield self.files[path]
    @contextlib.contextmanager
    def batch_upload(self, force):
        assert force is False
        yield self
    def put_file(self, local, remote):
        assert remote not in self.files
        self.files[remote] = Path(local).read_bytes(); self.writes.append(remote)


class C1IOTests(unittest.TestCase):
    def test_exact_input_upload_readback_and_reuse(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); volume = Volume()
            (root/'a.json').write_bytes(b'{"new":1}\n'); (root/'b.json').write_bytes(b'{"old":2}\n')
            spec = {'input_files': {p.name: {'sha256': sha(p), 'bytes': p.stat().st_size}
                for p in root.glob('*.json')}}
            prefix = o.INPUTS.removeprefix('/evidence')+'/'
            volume.files[prefix+'b.json'] = (root/'b.json').read_bytes()
            fake = types.ModuleType('modal.exception'); fake.NotFoundError = FileNotFoundError
            with patch.dict(sys.modules, {'modal.exception': fake}):
                io.transfer(volume, root, root/'evidence', spec)
            self.assertEqual(volume.writes, [prefix+'a.json'])
            self.assertTrue(read(root/'evidence'/'files'/'b.json.json')['reused_identical_remote'])

    def test_mismatching_remote_never_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); volume = Volume(); (root/'a.json').write_bytes(b'{}')
            spec = {'input_files': {'a.json': {'sha256': sha(root/'a.json'), 'bytes': 2}}}
            volume.files[o.INPUTS.removeprefix('/evidence')+'/a.json'] = b'bad'
            fake = types.ModuleType('modal.exception'); fake.NotFoundError = FileNotFoundError
            with patch.dict(sys.modules, {'modal.exception': fake}), self.assertRaises(ValueError):
                io.transfer(volume, root, root/'evidence', spec)
            self.assertFalse(volume.writes)

    def test_missing_readback_blocks_before_dispatch(self):
        with tempfile.TemporaryDirectory() as d:
            f = Fixture(Path(d))
            (f.root/o.LOCAL/'c1_io_r1'/'upload'/'COMPLETED.json').unlink()
            with self.assertRaises(FileNotFoundError): f.submit()
            f.worker.spawn.assert_not_called(); self.assertFalse(f.store)

    def test_budget_original_noncanonical_bytes_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            f = Fixture(Path(d))
            (f.root/'budget.json').write_text(json.dumps(f.budget, ensure_ascii=False))
            original = (f.root/'budget.json').read_bytes()
            f.submit()
            out = f.root/o.LOCAL/'dispatch'/o.LOGICAL
            self.assertEqual((out/'BUDGET_SOURCE.json').read_bytes(), original)
            self.assertEqual(read(out/'INTENT.json')['budget_source_sha256'], sha(out/'BUDGET_SOURCE.json'))

    def test_new_transport_full_closure_with_original_admission_snapshot(self):
        with tempfile.TemporaryDirectory() as d:
            f = Fixture(Path(d)); f.submit(); receipt = f.worker_call()
            run = f.root/o.LOCAL/'dispatch'/o.LOGICAL
            # Fake return was saved by the synthetic submit; use true mocked worker
            # receipt in a separate copied collection, without mutating original return.
            saved = f.root/o.LOCAL/'c1_io_r1'/'collect'; saved.mkdir()
            dump(saved/'ORIGINAL_RESULT.json', receipt)
            dump(saved/'RECORDS.json', dict(f.store))
            dump(saved/'PROVIDER_STOPPED0.json', {'app_id': 'ap-synthetic', 'state': 'stopped',
                'owned_containers': 0, 'observed_epoch': receipt['finished_epoch']+1})
            dump(saved/'COMPLETED.json', {'synthetic': True})
            (saved/'evidence.tar.gz').write_bytes((f.root/'remote'/'payload'/'evidence.tar.gz').read_bytes())
            dest = f.root/o.SPEC; dest.parent.mkdir(parents=True); dest.write_bytes(f.sp.read_bytes())
            out = f.root/'audit'; out.mkdir()
            with patch.object(io, 'load_pack', return_value=(f.tasks, f.members)), \
                    patch.object(o, 'ledger', side_effect=AssertionError('Never use later ledger for earlier admission')):
                io.audit(f.root, out, f.s, read(run/'INTENT.json')['review'])
            proof = read(out/'COMPLETE_READONLY_PROOF.json')
            self.assertTrue(proof['full_outer_bindings_verified'])
            self.assertEqual(proof['model_calls'], 0)
            self.assertFalse(proof['actual_independent_A3_accepted'])

    def test_fixed_modal_decorator_and_missing_actual_spec(self):
        import ast
        module = ast.parse(Path('experiments/p011/modal_c1.py').read_text())
        worker = next(x for x in module.body if isinstance(x, ast.FunctionDef) and x.name == 'worker')
        args = {x.arg: ast.literal_eval(x.value) for x in worker.decorator_list[0].keywords
            if x.arg in ('gpu','retries','max_containers','min_containers','single_use_containers','include_source')}
        self.assertEqual(args, {'gpu': 'H100!', 'retries': 0, 'max_containers': 4,
            'min_containers': 0, 'single_use_containers': True, 'include_source': False})
        self.assertFalse(Path(o.SPEC).exists())


if __name__ == '__main__':
    unittest.main()

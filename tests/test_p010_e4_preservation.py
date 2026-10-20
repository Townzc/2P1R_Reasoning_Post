"""New bounded E4 preservation checks; no Modal or real model state."""
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch

from scripts import p010_preserve_e4_failure as module
from experiments.p010.common import dump, read


class E4Preservation(unittest.TestCase):
    def test_exact_named_keys_include_unattempted_endpoint(self):
        keys = module.named_keys('e4_s17_n400')
        self.assertEqual(len(keys), 144)
        self.assertEqual(len(set(keys)), 144)
        self.assertIn('e4/e4_s17_n400/eval/1280', keys)
        self.assertIn('e4/e4_s17_n400/done/terminal_merge', keys)

    def test_remote_path_forms_and_escape_rejection(self):
        for remote in ('/p010/run/a.json', 'p010/run/a.json'):
            self.assertEqual(module.relative_file(remote, '/p010/run'), Path('a.json'))
        for remote in ('/p010/run2/a.json', '/p010/run/../else.json'):
            with self.assertRaises(ValueError):
                module.relative_file(remote, '/p010/run')

    def test_inventory_bound_and_no_merged_download(self):
        entries = [dict(path='/p/a.json', bytes=10),
                   dict(path='/p/merged/config.json', bytes=10),
                   dict(path='/p/merged/model.safetensors', bytes=10),
                   dict(path='/p/checkpoint_1024/state.pt', bytes=20)]
        self.assertEqual([str(rel) for _, rel in module.select_files(entries, '/p')],
                         ['a.json', 'checkpoint_1024/state.pt'])
        with self.assertRaises(ValueError):
            module.select_files([dict(path='/p/a.json', bytes=256*1024**2+1)], '/p')
        with self.assertRaises(ValueError):
            module.select_files([dict(path='/p/checkpoint_1024/state.pt', bytes=2*1024**3+1)], '/p')

    def exercise(self, folder, fail_state=False):
        receipt = folder/'receipt'; receipt.mkdir()
        dump(receipt/'SUBMITTED.json', dict(n=400, app_id='app-original', call_id='call-original'))
        dump(receipt/'INTENT.json', dict(n=400))
        dump(receipt/'ERROR.json', dict(type='TypeError', error="unhashable type: 'slice'"))
        prefix = 'p010-20261019/e4/e4_s17_n400/'
        files = {prefix+'FAILURE.json': b'{"type":"TypeError"}',
                 prefix+'checkpoint_1024/manifest.json': b'{"state_sha256":"synthetic"}',
                 prefix+'checkpoint_1024/state.pt': b'synthetic-not-a-torch-state'}
        reads = []
        class Volume:
            def iterdir(self, *args, **kwargs):
                return [types.SimpleNamespace(path=k, size=len(v)) for k, v in files.items()]
            def read_file(self, key):
                reads.append(key)
                if fail_state and key.endswith('state.pt'):
                    yield files[key][:4]
                    raise ConnectionError('synthetic interrupted stream')
                yield files[key]
        class Store:
            def get(self, key):
                if key.endswith('/claim'):
                    return dict(run='e4_s17_n400', execution='synthetic')
                if key.endswith('/terminal'):
                    return dict(status='failed', error="unhashable type: 'slice'")
                return None
        fake = types.SimpleNamespace(
            Volume=types.SimpleNamespace(from_name=lambda *a, **k: Volume()),
            Dict=types.SimpleNamespace(from_name=lambda *a, **k: Store()))
        args = types.SimpleNamespace(receipt=str(receipt), out=str(folder/'preserved'))
        with patch.dict('sys.modules', modal=fake), \
                patch.object(module.subprocess, 'check_output', return_value='[]'), \
                patch.object(module, 'read_stopped_apps', return_value=[dict(
                    app_id='app-original', lifecycle=dict(state='stopped', stopped_at='synthetic'))]):
            if fail_state:
                with self.assertRaises(ConnectionError):
                    module.preserve(args)
                self.assertTrue((folder/'preserved/FAILED.json').exists())
                self.assertTrue((folder/'preserved/evidence/FAILURE.json').exists())
                self.assertEqual((folder/'preserved/evidence/checkpoint_1024/state.pt').read_bytes(), b'synt')
            else:
                result = module.preserve(args)
                self.assertTrue(result['complete_checkpoint_file_present'])
                self.assertEqual(result['raw_files'], 0)
                self.assertFalse(result['any_endpoint_intent_or_ack'])
                self.assertTrue(result['failed_parent_remains_failed'])
                self.assertEqual(result['remote_writes'], 0)
                self.assertEqual(len(read(folder/'preserved/LEDGER.json')), 144)
                self.assertEqual((folder/'preserved/evidence/checkpoint_1024/state.pt').read_bytes(), files[prefix+'checkpoint_1024/state.pt'])
            with self.assertRaises(FileExistsError):
                module.preserve(args)
        self.assertEqual(len(reads), len(set(reads)))

    def test_complete_original_bytes_and_replay_blocked(self):
        with tempfile.TemporaryDirectory() as temp:
            self.exercise(Path(temp))

    def test_partial_transfer_retained_and_replay_blocked(self):
        with tempfile.TemporaryDirectory() as temp:
            self.exercise(Path(temp), True)


if __name__ == '__main__':
    unittest.main()

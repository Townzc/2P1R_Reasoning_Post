"""New supervision tests only; tiny OS children, no scorer or scientific data."""
import ast
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from experiments.learning_regime_p009 import stage1_s1_score_process as s

SETUP = '''import pathlib,json,hashlib,sys,os,subprocess,time
r=pathlib.Path(sys.argv[1])
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):
    with p.open('x') as f: json.dump(v,f)
'''
COMPLETE = '''(r/'payload').mkdir()
save(r/'payload/COMPLETED.json',{'synthetic_only':True})
save(r/'CHILD_COMPLETED.json',{'intent_sha256':sha(r/'INTENT.json'),
    'payload_sha256':sha(r/'payload/COMPLETED.json')})
'''


class Supervisor(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)/'job'
        self.rows = [{'synthetic_fixture_only':i} for i in range(500)]
        self.binding = {'synthetic_fixture_only':True}

    def tearDown(self):
        self.tmp.cleanup()

    def run_fixture(self, body, cap=5):
        with patch.object(s, 'command', side_effect=lambda root:
                          [sys.executable, '-c', SETUP+body, str(root)]):
            return s.supervise_endpoint_once(self.root, self.rows, self.binding, cap)

    def test_complete_child_and_replay_refusal_without_scoring(self):
        result = self.run_fixture(COMPLETE)
        self.assertEqual(result['child_exit_code'], 0)
        self.assertFalse(result['scientific_G1_admitted'])
        self.assertFalse(result['full_runtime_lineage_admission_checked'])
        with patch.object(s.subprocess, 'Popen') as spawn:
            with self.assertRaises(FileExistsError):
                s.supervise_endpoint_once(self.root, self.rows, self.binding, 5)
            spawn.assert_not_called()

    def test_timeout_kills_owned_grandchild_and_preserves_partial(self):
        body = '''p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)'])
save(r/'grandchild.json',{'pid':p.pid,'pgid':os.getpgid(p.pid)})
save(r/'preserved.json',{'synthetic_confirmed':True})
time.sleep(60)
'''
        with self.assertRaises(subprocess.TimeoutExpired):
            self.run_fixture(body, cap=1)
        failure = s.read(self.root/'FAILED.json')
        child = s.read(self.root/'CHILD.json')
        grandchild = s.read(self.root/'grandchild.json')
        self.assertEqual(grandchild['pgid'], child['pgid'])
        self.assertTrue(failure['cleanup']['group_signalled'])
        self.assertEqual(failure['cleanup']['child_exit_code'], -9)
        self.assertTrue(s.read(self.root/'preserved.json')['synthetic_confirmed'])
        self.assertFalse((self.root/'COMPLETED.json').exists())
        with patch.object(s.subprocess, 'Popen') as spawn:
            with self.assertRaises(FileExistsError):
                s.supervise_endpoint_once(self.root, self.rows, self.binding, 5)
            spawn.assert_not_called()

    def test_nonzero_child_does_not_turn_into_complete_or_zero_score(self):
        with self.assertRaises(RuntimeError):
            self.run_fixture("save(r/'preserved.json',{'known_pair':True})\nsys.exit(7)\n")
        failure = s.read(self.root/'FAILED.json')
        self.assertEqual(failure['cleanup']['child_exit_code'], 7)
        self.assertTrue(failure['failed_or_unknown_is_not_scored_zero'])
        self.assertFalse((self.root/'COMPLETED.json').exists())

    def test_exit_zero_without_original_child_proof_fails(self):
        with self.assertRaises(FileNotFoundError): self.run_fixture('pass\n')
        self.assertTrue((self.root/'FAILED.json').exists())
        self.assertFalse((self.root/'COMPLETED.json').exists())

    def test_tampered_original_payload_proof_fails(self):
        with self.assertRaises(ValueError):
            self.run_fixture(COMPLETE+"(r/'payload/COMPLETED.json').write_text('{}')\n")
        self.assertFalse((self.root/'COMPLETED.json').exists())

    def test_failed_spawn_is_preserved_and_cannot_be_replayed(self):
        with patch.object(s.subprocess, 'Popen', side_effect=OSError('synthetic spawn failure')):
            with self.assertRaises(OSError):
                s.supervise_endpoint_once(self.root, self.rows, self.binding, 5)
        self.assertIsNone(s.read(self.root/'FAILED.json')['cleanup'])
        with patch.object(s.subprocess, 'Popen') as spawn:
            with self.assertRaises(FileExistsError):
                s.supervise_endpoint_once(self.root, self.rows, self.binding, 5)
            spawn.assert_not_called()

    def test_invalid_window_or_roster_rejected_before_root_or_spawn(self):
        with patch.object(s.subprocess, 'Popen') as spawn:
            for cap in (0, True, 129601, 1.5):
                with self.assertRaises(ValueError):
                    s.supervise_endpoint_once(self.root, self.rows, self.binding, cap)
            with self.assertRaises(ValueError):
                s.supervise_endpoint_once(self.root, self.rows[:-1], self.binding, 5)
            spawn.assert_not_called()
        self.assertFalse(self.root.exists())

    def test_real_child_source_change_rejected_before_scoring_import(self):
        self.root.mkdir()
        s.create(self.root/'ROWS.json', self.rows)
        s.create(self.root/'BINDING.json', self.binding)
        s.create(self.root/'INTENT.json', dict(source_files={},
            rows_sha256=s.sha(self.root/'ROWS.json'), binding_sha256=s.sha(self.root/'BINDING.json')))
        with patch.object(s.os, 'getpid', return_value=77), patch.object(s.os, 'getpgrp', return_value=77):
            with self.assertRaises(ValueError): s.owned_worker(self.root)
        self.assertFalse((self.root/'CHILD_STARTED.json').exists())


if __name__ == '__main__':
    unittest.main()

"""New pure safety fixtures. No Modal imports, model work or old test repetition."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from experiments.sft_allocation_midpoint.common import digest

spec = importlib.util.spec_from_file_location('fast_readonly', 'scripts/p009_p0_fast_readonly.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class ReadonlySafety(unittest.TestCase):
    def test_exact_stopped_subtree_and_bounds(self):
        row = dict(path='/'+m.CAMPAIGN+'/'+m.RUN+'/base_638/raw/0000.json', size=4, mtime=2)
        self.assertEqual(m.bounded_listing([row])['base_638/raw/0000.json']['bytes'], 4)
        for bad in (dict(row, path='/elsewhere/x'), dict(row, path='/'+m.CAMPAIGN+'/'+m.RUN+'/../x'),
                    dict(row, size=m.MAX_FILE_BYTES+1), dict(row, size=-1), dict(row, size=True)):
            with self.assertRaises(ValueError):
                m.bounded_listing([bad])
        with self.assertRaises(ValueError):
            m.bounded_listing([row, row])

    def test_missing_transfer_retained_and_never_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/'raw.json'
            with self.assertRaises(ValueError):
                m.copy_original(p, [b'ab'], 4)
            self.assertEqual(p.read_bytes(), b'ab')
            with self.assertRaises(FileExistsError):
                m.copy_original(p, [b'abcd'], 4)
            self.assertEqual(p.read_bytes(), b'ab')

    def test_complete_copy_and_growing_remote_refused(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/'a'
            result = m.copy_original(p, [b'ab', b'cd'], 4)
            self.assertEqual(result, dict(bytes=4, sha256=m.sha(p)))
            p = Path(d)/'b'
            with self.assertRaises(ValueError):
                m.copy_original(p, [b'ab', b'cde'], 4)
            self.assertEqual(p.read_bytes(), b'ab')

    def test_failed_claim_marker_binding(self):
        claim = dict(run_id=m.RUN, attempt_id='a')
        terminal = dict(run_id=m.RUN, attempt_id='a', status='failed', claim_sha256=digest(claim))
        parent = dict(status='failed')
        s = dict(parent_claim={'p':1}, parent_terminal=parent, owner_plan_A={'owner':True})
        marker = dict(kind='owner_plan_A_fresh_configuration', campaign=m.CAMPAIGN, run_id=m.RUN,
            claim_sha256=digest(claim), owner_plan_A_sha256=digest(s['owner_plan_A']),
            fresh_outputs=2638, inherited_outputs=0, parent_stays_failed=True)
        m.failed_binding(s, claim, terminal, s['parent_claim'], parent, marker)
        m.failed_binding(s, claim, terminal, s['parent_claim'], parent, None)
        for t, mk in ((dict(terminal,status='completed'),marker),
                      (dict(terminal,claim_sha256='0'*64),marker),
                      (terminal,dict(marker,run_id='different'))):
            with self.assertRaises(ValueError):
                m.failed_binding(s, claim, t, s['parent_claim'], parent, mk)


if __name__ == '__main__':
    unittest.main()

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT=Path(__file__).resolve().parents[1]/'scripts/sync_bundle.py'

class BundleSyncTests(unittest.TestCase):
    def scenario(self, mismatch):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); source=root/'source'; target=root/'target'
            def git(where,*args):
                return subprocess.check_output(['git',*args],cwd=where,stderr=subprocess.DEVNULL,text=True).strip()
            source.mkdir();git(source,'init','-b','main')
            git(source,'config','user.name','Test');git(source,'config','user.email','test@example.invalid')
            (source/'code.py').write_text('old\n');(source/'obsolete.py').write_text('old module\n')
            git(source,'add','.');git(source,'commit','-m','initial')
            old=git(source,'rev-parse','HEAD')
            git(root,'clone',str(source),str(target))
            (source/'code.py').write_text('new\n');(source/'run.json').write_text('record\n')
            (source/'obsolete.py').unlink()
            git(source,'add','.');git(source,'commit','-m','records')
            new=git(source,'rev-parse','HEAD');git(source,'bundle','create',str(root/'sync.bundle'),'main')
            (target/'run.json').write_text('different\n' if mismatch else 'record\n')
            (target/'checkpoint.bin').write_bytes(b'preserve model artifact')
            result=subprocess.run([sys.executable,str(SCRIPT),'--bundle',str(root/'sync.bundle'),'--commit',new],cwd=target,capture_output=True,text=True)
            self.assertEqual((target/'checkpoint.bin').read_bytes(),b'preserve model artifact')
            if mismatch:
                self.assertNotEqual(result.returncode,0)
                self.assertIn('Untracked file differs',result.stderr)
                self.assertEqual(git(target,'rev-parse','HEAD'),old)
                self.assertEqual((target/'run.json').read_text(),'different\n')
                self.assertEqual((target/'code.py').read_text(),'old\n')
            else:
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertEqual(git(target,'rev-parse','HEAD'),new)
                self.assertEqual((target/'run.json').read_text(),'record\n')
                self.assertEqual((target/'code.py').read_text(),'new\n')
                self.assertFalse((target/'obsolete.py').exists())
    def test_identical_logs_can_become_tracked_without_losing_checkpoint(self): self.scenario(False)
    def test_differing_untracked_logs_abort_before_updating_checkout(self): self.scenario(True)

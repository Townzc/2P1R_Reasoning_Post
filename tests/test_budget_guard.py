"""Subprocess integration tests for preventing unapproved or unbounded execution."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPT=Path(__file__).resolve().parents[1]/'scripts/run_bounded.py'

@unittest.skipUnless(shutil.which('timeout'),'GNU timeout required; mandatory on GPU server')
class BudgetGuardTests(unittest.TestCase):
    def test_timeout_records_charge_and_prevents_stale_reservation(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            budget={'budget_id':'unit-test','authorized_gpu_seconds':20,'gpus':1}
            (root/'budget.json').write_text(json.dumps(budget))
            command=[sys.executable,str(SCRIPT),'--budget','budget.json','--max-seconds','1','--run-id','timed','--',sys.executable,'-c','import time; time.sleep(30)']
            result=subprocess.run(command,cwd=root,capture_output=True,text=True,timeout=15)
            self.assertEqual(result.returncode,124,result.stderr)
            ledger_path=root/'.local/resource_ledger.json'
            ledger=json.loads(ledger_path.read_text())
            self.assertEqual(ledger['jobs'][0]['status'],'timeout')
            self.assertGreaterEqual(ledger['jobs'][0]['charged_seconds'],1)
            ledger['jobs'][0]['status']='reserved'
            ledger_path.write_text(json.dumps(ledger))
            command[command.index('timed')]='blocked'
            result=subprocess.run(command,cwd=root,capture_output=True,text=True,timeout=5)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('Unresolved reservation',result.stderr)
            self.assertFalse((root/'runs/blocked').exists())

    def test_exhausted_budget_never_launches_child(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'budget.json').write_text(json.dumps({'budget_id':'empty','authorized_gpu_seconds':0,'gpus':1}))
            command=[sys.executable,str(SCRIPT),'--budget','budget.json','--max-seconds','1','--run-id','blocked','--',sys.executable,'-c','from pathlib import Path; Path("executed").touch()']
            result=subprocess.run(command,cwd=root,capture_output=True,text=True,timeout=5)
            self.assertNotEqual(result.returncode,0)
            self.assertFalse((root/'executed').exists())

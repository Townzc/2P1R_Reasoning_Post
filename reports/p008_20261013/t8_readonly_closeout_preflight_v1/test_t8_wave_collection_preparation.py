"""New synthetic local-I/O checks only; every cloud interface is mocked.

These do not test/repeat the already-reviewed scientific cap validator or any
real run. Fixture directories and failure records are deliberately retained.
"""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import contextlib, io, json, runpy, shutil, sys, tempfile, unittest
from experiments.sft_allocation_midpoint.common import dump, read, digest

R=Path(__file__).resolve().parent
FIXTURES=R/'t8_wave_helper_fixtures_r1'

class FakeLedger:
    def __init__(self,values,mutate=False):
        self.values=values;self.scans=0;self.reads={};self.mutate=mutate
    def items(self):
        self.scans+=1
        return iter(self.values.items())
    def get(self,key):
        self.reads[key]=self.reads.get(key,0)+1
        if self.mutate and self.reads[key]>1:return {'changed':True}
        return self.values.get(key)

class FakeVolume:
    def iterdir(self,path):
        return iter([SimpleNamespace(path=path+'/unit.json',mtime=1700000000,size=23)])

class WaveCollectionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        FIXTURES.mkdir(exist_ok=False)
    def fixture(self,mutate=False):
        root=Path(tempfile.mkdtemp(prefix=self._testMethodName+'_',dir=FIXTURES))
        helper=root/'collect_t8_cap_wave.py';shutil.copyfile(R/helper.name,helper)
        runs=read('reports/p008_20261013/student_t8_cap_9600_v1/ADMISSION.json')['runs'][:2]
        plan={'campaign_id':'p008-students-completion-20261013-r1','slots':{run:{} for run in runs}}
        dump(root/'student_completion_r1/plan.json',plan)
        ledger={};infos=[]
        for i,run in enumerate(runs):
            files={'synthetic.json':{'bytes':2,'sha256':'0'*64}}
            terminal={'run_id':run,'status':'completed','evidence_sha256':digest(files)}
            dump(root/'student_completion_r1/runs'/run/'result.json',{'receipt':terminal,'artifact_manifest':files})
            app='synthetic-app-'+str(i)
            dump(root/'student_completion_r1/runs'/run/'dispatch_intent.json',
                 {'run_id':run,'plan':plan,'config':{'training_multiple':8},'provider_app_id':app})
            ledger['midpoint/'+plan['campaign_id']+'/terminal/'+run]=terminal
            infos.append({'app_id':app,'lifecycle':{'state':'stopped','stopped_at':'synthetic'}})
        return root,helper,runs,FakeLedger(ledger,mutate),infos
    def invoke(self,helper,runs,ledger,infos,provider_error=None):
        with patch.object(sys,'argv',[str(helper),*runs]), \
             patch('modal.Dict.from_name',return_value=ledger), \
             patch('modal.Volume.from_name',return_value=FakeVolume()), \
             patch('subprocess.check_output',return_value='[]'), \
             patch('experiments.sft_allocation_p008.provider_release.read_stopped_apps',return_value=infos,side_effect=provider_error), \
             patch('experiments.sft_allocation_p008.student_t8_cap_binding.verify_supplement',return_value={'test_only':'mocked'}), \
             contextlib.redirect_stdout(io.StringIO()):
            runpy.run_path(str(helper),run_name='__main__')
    def test_two_runs_share_one_scan_and_cannot_be_recollected(self):
        root,helper,runs,ledger,infos=self.fixture()
        self.invoke(helper,runs,ledger,infos)
        self.assertEqual(ledger.scans,1)
        paths=[root/'student_completion_r1/closeouts'/run/'ledger.json' for run in runs]
        self.assertTrue(paths[0].samefile(paths[1]))
        for run in runs:
            p=root/'student_completion_r1/closeouts'/run
            self.assertTrue(read(p/'COLLECTION.json')['passed'])
            self.assertEqual(len(read(p/'TIMING_READ_METADATA.json')['files']),2)
        with self.assertRaises(AssertionError):self.invoke(helper,runs,ledger,infos)
        self.assertEqual(ledger.scans,1)
    def test_changed_terminal_preserves_partial_and_failure(self):
        root,helper,runs,ledger,infos=self.fixture(mutate=True)
        with self.assertRaises(AssertionError):self.invoke(helper,runs,ledger,infos)
        wave=root/'student_completion_r1/t8_collection_waves'/digest(runs)
        self.assertTrue((wave/'READ_INTENT.json').exists())
        self.assertTrue((wave/'ERROR.json').exists())
        self.assertTrue((wave/'ledger.json').exists())
        self.assertFalse((wave/'COMPLETED.json').exists())
    def test_active_provider_refused_before_ledger_enumeration(self):
        root,helper,runs,ledger,infos=self.fixture()
        with self.assertRaises(ValueError):self.invoke(helper,runs,ledger,infos,ValueError('active synthetic provider'))
        self.assertEqual(ledger.scans,0)
        wave=root/'student_completion_r1/t8_collection_waves'/digest(runs)
        self.assertTrue((wave/'ERROR.json').exists())
        self.assertFalse((wave/'ledger.json').exists())

if __name__=='__main__':
    unittest.main()

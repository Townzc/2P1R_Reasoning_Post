"""CPU-only failure-path simulation; no Modal, CUDA, old outputs or network."""
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import time
import unittest
from unittest.mock import patch
from experiments.sft_allocation_midpoint.common import dump,read
from experiments.learning_regime_p009 import p0_runtime as runtime


class Store(dict):
    def put(self,key,value,skip_if_exists=False):
        if key in self:return False
        self[key]=value;return True


class FakeEngine:
    def __init__(self,bad=False):self.pending=('ready',{'synthetic':True});self.bad=bad;self.calls=0
    def send(self,command):
        kind,rows=command
        if kind=='generate':
            self.calls+=1
            self.pending=('outputs',[dict(problem_id=r['problem_id'],prompt_token_ids=r['input_ids'],
                token_ids=[12] if self.bad else [12,151643],finish_reason='stop',stop_reason=None) for r in rows])


class P0FlowTests(unittest.TestCase):
    def setUp(self):
        self.fixture_root=Path('.local/p009_20261014/r1/p0_flow_fixtures')
        self.fixture_root.mkdir(parents=True,exist_ok=True)

    def fixture(self,root):
        inputs=root/'inputs';inputs.mkdir()
        rows=[dict(problem_id=f'gsm8k/test/{i:05d}',input_ids=[12]) for i in range(1319)]
        dump(inputs/'qwen_gsm_zero_parity.json',dict(n=1319,eos_token_id=151643,
             max_context=2048,max_new_tokens=512,prompts=rows))
        return dict(remote_inputs=str(inputs),inputs={},remote_base_model=str(root/'base'),
                    base_files={},remote_reference_checkpoint=str(root/'checkpoint'),checkpoint_files={})

    def test_ambiguous_response_preserves_raw_and_attempt_no_done(self):
        with tempfile.TemporaryDirectory(dir=self.fixture_root) as d:
            root=Path(d);spec=self.fixture(root);engine=FakeEngine(bad=True);store=Store()
            guard=SimpleNamespace(prefix='midpoint/test/',check_active=lambda *a,**k:None)
            with patch.object(runtime,'isolated',return_value=(engine,SimpleNamespace(exitcode=0))), \
                 patch.object(runtime,'receive',side_effect=lambda c,p,s:c.pending), \
                 patch.object(runtime,'close_process'), \
                 patch.object(runtime.tempfile,'mkdtemp',return_value=str(root/'scratch')):
                with self.assertRaises(ValueError):
                    runtime.execute(spec,root/'out',store,guard,SimpleNamespace(run_id='pair'),lambda:None,time.time(),time.time()+1200)
            self.assertEqual(engine.calls,1)
            self.assertTrue((root/'out/base_638/raw/0000.json').exists())
            self.assertIn('midpoint/test/pair/unit/base_638_0000',store)
            self.assertNotIn('midpoint/test/pair/done/base_638_0000',store)

    def test_existing_unit_prevents_generation(self):
        with tempfile.TemporaryDirectory(dir=self.fixture_root) as d:
            root=Path(d);spec=self.fixture(root);engine=FakeEngine();store=Store()
            store['midpoint/test/pair/unit/base_638_0000']={'ambiguous_prior_attempt':True}
            guard=SimpleNamespace(prefix='midpoint/test/',check_active=lambda *a,**k:None)
            with patch.object(runtime,'isolated',return_value=(engine,SimpleNamespace(exitcode=0))), \
                 patch.object(runtime,'receive',side_effect=lambda c,p,s:c.pending), \
                 patch.object(runtime,'close_process'), \
                 patch.object(runtime.tempfile,'mkdtemp',return_value=str(root/'scratch')):
                with self.assertRaises(ValueError):
                    runtime.execute(spec,root/'out',store,guard,SimpleNamespace(run_id='pair'),lambda:None,time.time(),time.time()+1200)
            self.assertEqual(engine.calls,0)

    def test_failed_forecast_stops_after_exact_bootstrap_prefix(self):
        with tempfile.TemporaryDirectory(dir=self.fixture_root) as d:
            root=Path(d);spec=self.fixture(root);engine=FakeEngine();store=Store()
            guard=SimpleNamespace(prefix='midpoint/test/',check_active=lambda *a,**k:None)
            with patch.object(runtime,'isolated',return_value=(engine,SimpleNamespace(exitcode=0))), \
                 patch.object(runtime,'receive',side_effect=lambda c,p,s:c.pending), \
                 patch.object(runtime,'close_process'), \
                 patch.object(runtime.tempfile,'mkdtemp',return_value=str(root/'scratch')), \
                 patch.object(runtime,'remaining_forecast',return_value={'admitted':False}):
                with self.assertRaises(TimeoutError):
                    runtime.execute(spec,root/'out',store,guard,SimpleNamespace(run_id='pair'),lambda:None,time.time(),time.time()+1200)
            self.assertEqual(engine.calls,4)
            self.assertEqual(len(list((root/'out/base_638/raw').glob('*.json'))),4)
            self.assertNotIn('midpoint/test/pair/unit/base_638_0128',store)


if __name__=='__main__':unittest.main()

"""New complete-cycle timing fixtures only; old successful tests are not rerun."""
import copy
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from experiments.p011 import c1_execution as c, c1_nll
from experiments.sft_allocation_midpoint.common import dump, read
from tests.test_p011_c1_execution_draft import spec as old_fixture, roster, forward, Store


def spec():
    s=old_fixture();s['timing']['whole_chunk_iteration_timing']=True
    return s


class Clock:
    def __init__(self):self.value=0.;self.commits=0
    def tick(self):self.value+=.01;return self.value
    def commit(self):self.commits+=1;self.value+=2.


class WholeCycleTests(unittest.TestCase):
    def run_new_body(self,root,count=40):
        s=spec();tasks,members=roster(count);store=Store({'x/claim':{'synthetic':True}})
        out=root/'payload';clock=Clock();start=time.time()
        def loader(s,p,deadline):dump(p/'MODEL_LOADED.json',{'synthetic_only':True});return object()
        with patch.object(c.time,'monotonic',side_effect=clock.tick), \
                patch.object(c1_nll,'forward_one',side_effect=forward):
            result=c.run_body(s,tasks,members,out,{'fixture':True},store,'x',store['x/claim'],
                clock.commit,start,start+s['limits']['worker_seconds'],0,loader)
        return s,tasks,members,store,out,result,clock

    def test_all_three_commits_enter_next_forecast_and_readonly_replay(self):
        with tempfile.TemporaryDirectory() as d:
            s,t,m,store,out,result,clock=self.run_new_body(Path(d))
            cycles=read(out/'COMPLETE_ITERATION_TIMES.json')['cycles']
            self.assertEqual(clock.commits,9)  # intent+loader, 2*3 chunks, final summary
            self.assertGreaterEqual(cycles[0]['elapsed_seconds']-cycles[0]['body_ack_elapsed_seconds'],4.)
            self.assertGreaterEqual(cycles[0]['elapsed_seconds'],6.)
            second=read(out/'chunks'/'00001'/'FORECAST.json')
            self.assertEqual(second['max_complete_chunk_seconds'],cycles[0]['elapsed_seconds'])
            self.assertEqual(result['complete_chunk_seconds'],[x['elapsed_seconds'] for x in cycles])
            with patch.object(c1_nll,'forward_one',side_effect=AssertionError('No replay')):
                proof=c.check_body(s,out,t,m,{'fixture':True},store,'x',store['x/claim'])
            self.assertEqual(proof['complete_chunk_seconds'],result['complete_chunk_seconds'])

    def test_old_body_only_basis_cannot_admit_new_path(self):
        with self.assertRaises(ValueError):c.validate_spec(old_fixture())
        s=spec();s['timing']['whole_chunk_iteration_timing']=False
        with self.assertRaises(ValueError):c.validate_spec(s)

    def test_timing_scope_tampering_refused_without_new_forward(self):
        with tempfile.TemporaryDirectory() as d:
            s,t,m,store,out,result,clock=self.run_new_body(Path(d),3)
            path=out/'COMPLETE_ITERATION_TIMES.json';saved=read(path)
            changed=copy.deepcopy(saved);changed['cycles'][0]['volume_commits_included']=1
            with patch.object(c,'read',side_effect=lambda p:changed if Path(p)==path else read(p)), \
                    self.assertRaises(ValueError):
                c.check_body(s,out,t,m,{'fixture':True},store,'x',store['x/claim'])

    def test_confirmed_elapsed_cannot_be_replaced_with_body_ack_duration(self):
        with tempfile.TemporaryDirectory() as d:
            s,t,m,store,out,result,clock=self.run_new_body(Path(d),3)
            path=out/'COMPLETE_ITERATION_TIMES.json';changed=read(path)
            changed['cycles'][0]['elapsed_seconds']=changed['cycles'][0]['body_ack_elapsed_seconds']
            with patch.object(c,'read',side_effect=lambda p:changed if Path(p)==path else read(p)), \
                    self.assertRaises(ValueError):
                c.check_body(s,out,t,m,{'fixture':True},store,'x',store['x/claim'])


if __name__=='__main__':unittest.main()

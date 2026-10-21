"""New owner-exception checks only; fake clocks/models, no old test replay."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from experiments.p011 import c1_execution as c, c1_nll, c1_admission as a
from experiments.sft_allocation_midpoint.common import dump, read, sha
from tests.test_p011_c1_execution_draft import spec as old_spec, roster, forward, Store


def spec():
    s=old_spec();s['limits'].update(worker_seconds=2400,platform_seconds=2460,
        full_result_window_seconds=3660,model_load_deadline_seconds=900,
        measurement_exceptions=1,reserved_usd='3.83')
    owner='reports/p011_20261020/test_owner_placeholder.md'
    s['source_files']={owner:c.SELF_CALIBRATION_OWNER_SHA}
    s['timing'].update(basis_kind=c.SELF_CALIBRATION,complete_chunk_seconds=[],
        measurement_basis_accepted=False,whole_chunk_iteration_timing=True,
        owner_decision_file=owner,owner_decision_sha256=c.SELF_CALIBRATION_OWNER_SHA)
    s['task_inventory']={'journal_chunks':300}
    return s


class Clock:
    def __init__(self,commit_cost=2):self.value=0.;self.cost=commit_cost
    def mono(self):self.value+=.01;return self.value
    def time(self):return 1792556000.+self.value
    def commit(self):self.value+=self.cost


class SelfCalibration(unittest.TestCase):
    def body(self,out,clock,count=48,slow_load=False):
        s=spec();tasks,members=roster(count);store=Store({'x/claim':{'synthetic':True}})
        timer=Mock();factory=Mock(return_value=timer)
        def loader(s,p,deadline):
            dump(p/'MODEL_LOADED.json',{'synthetic':True})
            if slow_load:clock.value+=901
            return object()
        with patch.object(c.time,'time',side_effect=clock.time), \
                patch.object(c.time,'monotonic',side_effect=clock.mono), \
                patch.object(c1_nll,'forward_one',side_effect=forward):
            result=c.run_body(s,tasks,members,out,{'synthetic':True},store,'x',store['x/claim'],
                clock.commit,1792556000.,1792558400.,0,loader,factory)
        return s,tasks,members,store,result,timer,factory

    def test_no_initial_forecast_and_only_in_run_measurements(self):
        s=spec();c.validate_spec(s)
        self.assertFalse(c.initial_admission(s,0,0)['forecast_performed'])
        with self.assertRaisesRegex(ValueError,'first complete'):c.forecast(s,0,300,[],0)
        self.assertEqual(c.forecast(s,10,3,[2,1],0)['max_complete_chunk_seconds'],2)

    def test_owner_bounds_and_historical_proxy_rejected(self):
        for field,value in [('worker_seconds',2401),('platform_seconds',2461),
                            ('startup_seconds',601),('model_load_deadline_seconds',901),
                            ('reserved_usd','4.01'),('measurement_exceptions',0)]:
            s=spec();s['limits'][field]=value
            with self.assertRaises(ValueError):c.validate_spec(s)
        s=spec();s['timing']['complete_chunk_seconds']=[.1]
        with self.assertRaises(ValueError):c.validate_spec(s)
        s=spec();s['timing']['owner_decision_sha256']='0'*64
        with self.assertRaises(ValueError):c.validate_spec(s)

    def test_reserve_80percent_no_release_and_future_cost_guard(self):
        with self.assertRaises(ValueError):c.initial_admission(spec(),0,'8')
        with self.assertRaises(ValueError):c.forecast(spec(),600,299,[10],0)

    def test_complete_body_post_first_and_last_chunk_readonly_replay(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'body';s,t,m,store,result,timer,factory=self.body(out,Clock())
            self.assertFalse(read(out/'INITIAL_FORECAST.json')['forecast_performed'])
            self.assertFalse(read(out/'chunks/00000/FORECAST.json')['forecast_performed'])
            self.assertEqual(read(out/'chunks/00000/POST_FORECAST.json')['actual_observation_count'],1)
            self.assertEqual(read(out/'chunks/00001/POST_FORECAST.json')['remaining_chunks'],0)
            timer.cancel.assert_called_once();self.assertLessEqual(factory.call_args.args[0],900)
            with patch.object(c1_nll,'forward_one',side_effect=AssertionError('No reforward')), \
                    patch.object(c1_nll,'descriptive_summary',side_effect=AssertionError('No recompute')):
                proof=c.check_body(s,out,t,m,{'synthetic':True},store,'x',store['x/claim'])
            self.assertTrue(proof['complete'])

    def test_first_cycle_failure_retains_partial_no_second_attempt(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'body'
            with self.assertRaisesRegex(ValueError,'forecast exceeded'):self.body(out,Clock(300))
            self.assertTrue((out/'chunks/00000/CONFIRMED.json').exists())
            self.assertFalse((out/'chunks/00001').exists())
            self.assertEqual(len(read(out/'FAILED.json')['confirmed_complete_iteration_timings']),1)
            with self.assertRaises(FileExistsError):self.body(out,Clock())

    def test_load900s_bound_fails_before_any_chunk(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'body'
            with self.assertRaisesRegex(TimeoutError,'load deadline'):self.body(out,Clock(),slow_load=True)
            self.assertTrue((out/'FAILED.json').exists());self.assertFalse((out/'chunks').exists())

    def test_post_forecast_tamper_refused_without_forward(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'body';s,t,m,store,_,_,_=self.body(out,Clock())
            path=out/'chunks/00001/POST_FORECAST.json';changed=read(path);changed['remaining_chunks']=1
            with patch.object(c,'read',side_effect=lambda p:changed if Path(p)==path else read(p)), \
                    self.assertRaisesRegex(ValueError,'post-chunk'):
                c.check_body(s,out,t,m,{'synthetic':True},store,'x',store['x/claim'])

    def test_fresh_budget_binds_rate_and_no_initial_prediction(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);dump(root/'meter.json',{'synthetic':True});s=spec()
            b={'observed_epoch':1792556000.,'all_attempted_reservations_usd':{k:'0' for k in a.CAPS},
               'cap_usd':'12','category':'C','overall_cap_usd':'180','protected_usd':'48',
               'reserve_release_used':False,'owner_estimate_used_as_balance':False,
               'availability_basis':'delayed_gross_plus_retained_reserves_conservative_floor',
               'source_evidence_files':{'meter.json':sha(root/'meter.json')},
               'available_after_retained_prior_reserves_usd':'55','observed_gross_resource_usd':'300',
               'usd_per_second':.00125}
            with patch.object(c,'forecast',side_effect=AssertionError('No initial proxy')):
                value=a.fresh_budget(s,b,[],[],{},1792556001.,root)
            self.assertFalse(value['initial_forecast']['forecast_performed'])
            b['usd_per_second']=.001
            with self.assertRaisesRegex(ValueError,'Fresh exact'):a.fresh_budget(s,b,[],[],{},1792556001.,root)


if __name__=='__main__':unittest.main()

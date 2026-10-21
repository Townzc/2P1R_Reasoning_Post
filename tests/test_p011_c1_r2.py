"""New r2-only checks; synthetic inputs/clocks, no old test methods or corpus."""
from copy import deepcopy
from pathlib import Path
import ast
import tempfile
import unittest
from unittest.mock import Mock, patch

from experiments.p011.c1_r2 import execution as c, admission as a, parent, inputs, outer
from experiments.p011 import c1_nll
from experiments.sft_allocation_midpoint.common import dump, read, sha, digest
from tests.test_p011_c1_execution_draft import spec as old_spec, roster, forward, Store
from tests.test_p011_c1_self_calibration import Clock


def spec():
    s=old_spec();owner='reports/p011_20261020/synthetic_owner.md'
    s['limits'].update(worker_seconds=1500,platform_seconds=1560,
        full_result_window_seconds=2760,model_load_deadline_seconds=900,
        measurement_exceptions=1,reserved_usd='2.70')
    s['forward']['journal_chunk_size']=320
    s['source_files']={owner:c.SELF_CALIBRATION_OWNER_SHA}
    s['budget_owner_decision_sha256']=c.BUDGET_OWNER_SHA
    s['timing'].update(basis_kind=c.SELF_CALIBRATION,complete_chunk_seconds=[],
        measurement_basis_accepted=False,whole_chunk_iteration_timing=True,
        owner_decision_file=owner,owner_decision_sha256=c.SELF_CALIBRATION_OWNER_SHA,
        r2_owner_decision_sha256=c.R2_OWNER_SHA,
        target_scope='C1_sequential320_original_token_forwards_including_FP32_loss')
    s['task_inventory']={'unique_sequences':9594,'journal_chunks':30}
    return s


class R2Tests(unittest.TestCase):
    def body(self,out,clock,count=321):
        s=spec();tasks,members=roster(count);store=Store({'r2/claim':{'synthetic':True}})
        timer=Mock();factory=Mock(return_value=timer)
        def loader(spec,path,deadline):
            dump(path/'MODEL_LOADED.json',{'synthetic':True});return object()
        with patch.object(c.time,'time',side_effect=clock.time), \
                patch.object(c.time,'monotonic',side_effect=clock.mono), \
                patch.object(c1_nll,'forward_one',side_effect=forward) as calls:
            result=c.run_body(s,tasks,members,out,{'synthetic':True},store,'r2',store['r2/claim'],
                clock.commit,1792556000.,1792557500.,'3.74',loader,factory)
            self.assertEqual(calls.call_count,count)
        return s,tasks,members,store,result

    def test_authorized_geometry_caps_and_no_initial_proxy(self):
        s=spec();c.validate_spec(s)
        self.assertEqual(c.CHUNK,320)
        self.assertFalse(c.initial_admission(s,0,'3.74')['forecast_performed'])
        with self.assertRaisesRegex(ValueError,'first complete'):c.forecast(s,0,30,[],'3.74')
        self.assertEqual(len(outer.complete_record_keys(s)),63)
        self.assertNotEqual(outer.KEY,parent.KEY)

    def test_r1_or_wrong_owner_settings_rejected(self):
        for field,value in [('worker_seconds',1501),('platform_seconds',1561),
                            ('startup_seconds',601),('reserved_usd','2.71')]:
            s=spec();s['limits'][field]=value
            with self.assertRaises(ValueError):c.validate_spec(s)
        s=spec();s['forward']['journal_chunk_size']=32
        with self.assertRaises(ValueError):c.validate_spec(s)
        for field in ('r2_owner_decision_sha256','owner_decision_sha256'):
            s=spec();s['timing'][field]='0'*64
            with self.assertRaises(ValueError):c.validate_spec(s)
        s=spec();s['budget_owner_decision_sha256']='0'*64
        with self.assertRaises(ValueError):c.validate_spec(s)

    def test_full320_and_tail1_body_and_no_forward_readonly_check(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'body';s,t,m,store,result=self.body(out,Clock())
            self.assertEqual(read(out/'chunks/00000/CONFIRMED.json')['count'],320)
            self.assertEqual(read(out/'chunks/00001/CONFIRMED.json')['count'],1)
            self.assertEqual(read(out/'chunks/00000/POST_FORECAST.json')['remaining_chunks'],1)
            self.assertEqual(read(out/'chunks/00001/POST_FORECAST.json')['remaining_chunks'],0)
            with patch.object(c1_nll,'forward_one',side_effect=AssertionError('No reforward')), \
                    patch.object(c1_nll,'descriptive_summary',side_effect=AssertionError('No restat')):
                self.assertTrue(c.check_body(s,out,t,m,{'synthetic':True},store,'r2',store['r2/claim'])['complete'])
            with self.assertRaises(FileExistsError):self.body(out,Clock())

    def test_failed_whole_cycle_retains320_and_never_starts_tail(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'body'
            with self.assertRaisesRegex(ValueError,'forecast exceeded'):self.body(out,Clock(300))
            self.assertEqual(read(out/'chunks/00000/CONFIRMED.json')['count'],320)
            self.assertFalse((out/'chunks/00001').exists())
            self.assertTrue((out/'FAILED.json').exists())

    def test_readonly_wrong_chunk_geometry_refused(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'body';s,t,m,store,result=self.body(out,Clock(),1)
            value=read(out/'INTENT.json');value['chunk_size']=32
            with patch('experiments.p011.c1_r2.evidence.read',side_effect=lambda p:value if Path(p).name=='INTENT.json' else read(p)):
                with self.assertRaises(ValueError):c.check_body(s,out,t,m,{'synthetic':True},store,'r2',store['r2/claim'])

    def test_original_inventory_adapted_only_in_journal_metadata(self):
        expected={'unique_sequences':9594,'journal_chunks':30,'tasks_sha256':'original'}
        with patch.object(inputs,'original_load_pack',return_value=('tasks','members')) as fn:
            self.assertEqual(inputs.load_pack('root',{'unchanged':True},expected),('tasks','members'))
            self.assertEqual(fn.call_args.args[2],{**expected,'journal_chunks':300})
        self.assertEqual(expected['journal_chunks'],30)
        with self.assertRaises(ValueError):inputs.load_pack('root',{},dict(expected,journal_chunks=300))

    def parent_fixture(self,root):
        intent={'logical_id':parent.R1,'execution':'a'*40,'budget':{'category':'C','new_reserved_usd':'3.74'}}
        sub={'logical_id':parent.R1,'app_id':'ap-original','call_id':'fc-original'}
        failure={'status':'failed','app_id':'ap-original','automatic_retry_allowed':False,'finished_epoch':10}
        review={'decision':'PASS','report_sha256':parent.FAILURE_REPORT_SHA,
                'original_failed_call_integrity_accepted':True,'C1_completed':False}
        objects={'provider':{'app_id':'ap-original','state':'stopped','owned_containers':0,'observed_epoch':11},
                 'failure':failure,'intent':intent,'submitted':sub,'review':review}
        for name,value in [('dispatch',intent),('claim',{'dispatch_sha256':digest(intent)}),('terminal',failure)]:
            objects['named_'+name]={'key':parent.KEY+'/'+name,'value':value}
        files={}
        for name,obj in objects.items():
            dump(root/(name+'.json'),obj);files[name]={'path':name+'.json','sha256':sha(root/(name+'.json'))}
        return {'prior_failed_C1':{'files':files}},objects

    def test_original_failed_reservation_retained_with_saved_provider(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);s,objects=self.parent_fixture(root)
            records=[{**objects['intent'],'app_id':'ap-original'}]
            result=parent.records_with_failed_parent(root,s,records)
            self.assertNotIn('saved_provider',records[0])
            totals,slots=a.accounting(result,[],{'ap-original':'stopped'})
            self.assertEqual(totals['C'],'3.74');self.assertEqual(slots,0)
            store=Store({parent.KEY+'/'+x:objects['named_'+x]['value'] for x in ('dispatch','claim','terminal')})
            parent.remote_fences(root,s,store)
            del store[parent.KEY+'/terminal']
            with self.assertRaises(ValueError):parent.remote_fences(root,s,store)

    def test_corrupt_parent_or_released_reservation_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);s,objects=self.parent_fixture(root)
            records=[{**objects['intent'],'app_id':'ap-original','budget':{'category':'C','new_reserved_usd':'0'}}]
            with self.assertRaises(ValueError):parent.records_with_failed_parent(root,s,records)
            (root/'failure.json').write_text('{}')
            with self.assertRaises(ValueError):parent.preserved(root,s)

    def test_upload_reused_without_source_or_spec_forgery(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);old={'source_files':{'old':'f'*64},'input_files':{'same':{'sha256':'a'*64,'bytes':1}}}
            dump(root/'old.json',old)
            done={**old,'spec_file_sha256':sha(root/'old.json'),'all_remote_file_bytes_read_back':True};dump(root/'done.json',done)
            s={'input_files':old['input_files'],'reused_input_upload':{
                'original_spec_file':{'path':'old.json','sha256':sha(root/'old.json')},
                'completed_file':{'path':'done.json','sha256':sha(root/'done.json')},
                'original_spec_file_sha256':sha(root/'old.json'),'original_source_files':old['source_files']}}
            self.assertEqual(parent.original_upload(root,s),done)
            s['input_files']={}
            with self.assertRaises(ValueError):parent.original_upload(root,s)

    def test_scientific_model_loader_ast_unchanged(self):
        def fn(path,name):
            return ast.dump(next(x for x in ast.parse(Path(path).read_text()).body if isinstance(x,ast.FunctionDef) and x.name==name),include_attributes=False)
        self.assertEqual(fn('experiments/p011/c1_execution.py','load_base'),fn('experiments/p011/c1_r2/execution.py','load_base'))
        self.assertIn('c1_nll.forward_one(model,task)',Path('experiments/p011/c1_r2/execution.py').read_text())
        self.assertNotIn('def upload(',Path('scripts/p011_c1_r2_io.py').read_text())


if __name__=='__main__':unittest.main()

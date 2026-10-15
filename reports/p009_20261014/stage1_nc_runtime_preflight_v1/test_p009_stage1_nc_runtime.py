"""New actual-schema and process-boundary fixtures; no model/remote calls."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch,Mock

from experiments.sft_allocation_midpoint.common import read,digest
from experiments.learning_regime_p009.stage1_nc_binding import validate,require_unused,dispatch_key,logical_key,CAMPAIGN
from experiments.learning_regime_p009 import stage1_nc_runtime as runtime


class NCRuntime(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        p=Path('reports/p009_20261014/stage1_nc_runtime_preflight_v1/ADMISSION.json')
        if p.exists():
            cls.spec=read(p);cls.plan=read(p.parent/'PLAN.json')
        else:
            p=Path('.local/p009_20261014/r1/stage1_nc_runtime_candidate_r1')
            cls.spec=read(p/'ADMISSION_DRAFT.json');cls.plan=read(p/'plan.json')
        r=Path('.local/p009_20261014/r1')
        publics=Path('reports/p009_20261014/review_448e0ac1_accepted_v1')
        cls.release=dict(source_files=cls.spec['source_files'],input_readback=cls.spec['inputs'],review_target='f'*40,
            core_review=read(publics/'STAGE1_SCIENTIFIC_CORE_CODE_ACCEPTED.json'),
            input_review=read(publics/'STAGE1_NC_INPUTS_ACCEPTED.json'),
            G0_review=read('reports/p009_20261014/review_8efc897f_accepted_v1/ACCEPTANCE.json'),
            internal_only_review=read('reports/p009_20261014/review_dec75690_accepted_v1/ACCEPTANCE.json'),
            budget=dict(stage1_prior_reserved_cents=0,new_reserved_cents=1310,stage1_cap_cents=5000,experiment_cap_cents=13000,project_prior_upper_cents=26070))
        # This synthetic review only tests rejection/shape, never written as ACCEPTED.
        cls.release['runtime_review']=dict(scope=cls.spec['scope'],decision='PASS',target_commit='f'*40,report_commit='e'*40,report_sha256='d'*64,
            source_files=cls.spec['source_files'],spec_sha256=digest(cls.spec),timing_sha256=digest(cls.spec['timing']),input_basis_file_sha256=cls.spec['input_basis_file_sha256'],input_archive_file_sha256=cls.spec['input_archive_file_sha256'],all_18_training_hosts_included=True,uncalibrated_timing_proxy_scope_accepted=True,training_process_exit_before_vllm=True,new_reserved_cents=1310,first_paid_measurement_exceptions=0)

    def test_exact_actual_nested_input_schema_reaches_both_NC_recipes(self):
        for run,n in [('nc_s17_n400',400),('nc_s17_n3200',3200)]:
            cap=validate(self.spec,self.plan,run,self.release)
            self.assertEqual((cap['n'],cap['updates'],cap['targets'],cap['worker_seconds']),(n,1024,2097148,4500))
            self.assertEqual(len(self.spec['inputs']),9)

    def test_code_only_or_wrong_timing_is_not_numeric_admission(self):
        for key,v in [('scope','p009-stage1-scientific-training-and-endpoint-core-code'),('timing_sha256','0'*64),('new_reserved_cents',1188),('first_paid_measurement_exceptions',1)]:
            r=deepcopy(self.release);r['runtime_review'][key]=v
            with self.assertRaises(ValueError):validate(self.spec,self.plan,'nc_s17_n400',r)

    def test_old_G0_or_foreign_model_tokenizer_path_rejected(self):
        r=deepcopy(self.release);r['G0_review']['G0']['NC']['passed']=False
        with self.assertRaises(ValueError):validate(self.spec,self.plan,'nc_s17_n400',r)
        spec=deepcopy(self.spec);spec['base']['tokenizer_remote_path']+='/foreign'
        with self.assertRaises(ValueError):validate(spec,self.plan,'nc_s17_n400',self.release)

    def test_any_partial_original_record_blocks_another_dispatch(self):
        pre='midpoint/'+CAMPAIGN+'/'
        for suffix in ['claim/nc_s17_n400','intent/nc_s17_n400','attempt/nc_s17_n400/x','nc_s17_n400/unit/training_block_0001_0016','nc_s17_n400/done/endpoint_00000','dispatch/nc_s17_n400','terminal/nc_s17_n400','unexpected/other']:
            with self.assertRaises(ValueError):require_unused({pre+suffix:{}},'nc_s17_n400',self.plan)
        require_unused({},'nc_s17_n400',self.plan)

    def test_second_slot_requires_first_dispatched_not_failed(self):
        with self.assertRaises(ValueError):require_unused({},'nc_s17_n3200',self.plan)
        records={dispatch_key('nc_s17_n400'):dict(provider_app_id='ap-synthetic')}
        require_unused(records,'nc_s17_n3200',self.plan)
        records['midpoint/'+CAMPAIGN+'/terminal/nc_s17_n400']={'status':'failed'}
        with self.assertRaises(ValueError):require_unused(records,'nc_s17_n3200',self.plan)
        self.assertNotEqual(dispatch_key('nc_s17_n400'),logical_key('nc_s17_n400'))

    def test_training_reply_without_actual_process_exit_does_not_proceed(self):
        connection=Mock();process=Mock();process.is_alive.return_value=True;process.exitcode=None
        with patch.object(runtime,'spawn_process',return_value=(connection,process)),patch.object(runtime,'receive',return_value=('trained',{})),patch.object(runtime,'close_process'):
            with self.assertRaises(RuntimeError):runtime.training_once(None,(),runtime.time.time()+100)

    def test_successful_training_must_join_before_returning_to_endpoint(self):
        connection=Mock();process=Mock();process.is_alive.return_value=False;process.exitcode=0;process.pid=77
        with patch.object(runtime,'spawn_process',return_value=(connection,process)),patch.object(runtime,'receive',return_value=('trained',{'updates':1024})),patch.object(runtime,'close_process'):
            result,proof=runtime.training_once(None,(),runtime.time.time()+100)
        self.assertEqual(result['updates'],1024);process.join.assert_called_once();self.assertTrue(proof['joined_before_endpoint'])

    def test_malformed_returned_raw_is_saved_but_never_acknowledged(self):
        rows=[]
        for i in range(1319):
            row=dict(problem_id=f'gsm8k/test/{i:05d}',input_ids=[10]);rows.append(dict(row,candidate_id='NC::'+row['problem_id'],source_row_sha256=digest(row)))
        class Store(dict):
            def put(self,k,v,skip_if_exists=False):
                if k in self:return False
                self[k]=v;return True
        store=Store();guard=SimpleNamespace(prefix='midpoint/'+CAMPAIGN+'/',check_active=lambda *a,**k:None);claim=SimpleNamespace(run_id='nc_s17_n400');connection=Mock()
        with tempfile.TemporaryDirectory() as tmp,patch.object(runtime,'receive',return_value=('outputs',[{'malformed_original':True}])):
            start=runtime.time.time()
            with self.assertRaises(ValueError):runtime.endpoint_batches(rows,tmp,store,guard,claim,lambda:None,start,start+4500,connection,Mock(),dict(training_block_seconds=[1],endpoint_batch_seconds=[1]),[1]*64,5000)
            self.assertEqual(read(Path(tmp)/'endpoint/raw/00000.json'),[{'malformed_original':True}])
            self.assertFalse(any('/done/' in k for k in store));self.assertEqual(connection.send.call_count,1)


if __name__=='__main__':unittest.main()

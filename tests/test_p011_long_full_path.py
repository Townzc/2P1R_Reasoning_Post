"""New integration boundaries only; no repetition of prior successful suites."""
import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from experiments.p011 import long_path as p,long_transport as transport,long_training as training,long_execution as execution
from scripts import p011_long_io as io
from experiments.sft_allocation_midpoint.common import dump,read,sha,digest


def job(kind='baseline',cell='baseline',arm='S-L15'):
    inp={'ENDPOINT_GPU.json':{'bytes':1,'sha256':'a'*64}}
    return dict(kind=kind,cell=cell,arm=arm,category='D' if cell.startswith('D') else 'A',seed=17,
        U=654 if cell.startswith('A') else 64 if cell.startswith('D') else 0,
        B=41813212 if cell.startswith('A') else 4070922 if cell.startswith('D') else 0,
        input_directory=cell,input_files=inp,local_input_files={**inp,'ENDPOINT_LOCAL.json':{'bytes':1,'sha256':'b'*64}},
        model={**{k:v for k,v in training.ARMS[arm].items() if k in ('model_id','revision')},
            'remote_path':'/evidence/p011-20261020/models/qwen3b_instruct' if arm=='S-L3' else '/evidence/exploratory-20261014-r1/instruct_assets',
            'local_path':'fixture_assets','files':{'config.json':{'bytes':1,'sha256':'c'*64}},'producer_binding_files':{'producer':'d'*64}},
        context=16390,eos_token_ids=[151645,151643],
        timing=dict(source_evidence_files={'fixture':'e'*64},whole_iteration_scope_accepted=True,training_unit_seconds=[.1],endpoint_batch_seconds=[.1],future_allowance_seconds=300),
        limits=dict(worker_seconds=1000,platform_seconds=1060,startup_seconds=600,closeout_seconds=33500,score_seconds=33000,full_result_window_seconds=35160,artifact_max_bytes=100000,hourly_rate_usd='4',reserved_usd='1.85'))

def spec(j):return dict(original_plan_commit=p.shared.PLAN,source_files={'s.py':'0'*64},jobs={p.logical(j):j},measurement_exceptions=0,result_cutoff_epoch=p.CUTOFF)

class Store(dict):
    def put(self,k,v,skip_if_exists=False):
        if skip_if_exists and k in self:return False
        self[k]=v;return True

class WholePath(unittest.TestCase):
    def test_valid_shared_doses_and_original_modes(self):
        for j in (job(),job('baseline',arm='S-L3'),job('student','A7'),job('student','D1','S-F15')):p.validate(spec(j))
        j=job('student','A7');j['B']-=1
        with self.assertRaises(ValueError):p.validate(spec(j))
        j=job('baseline',arm='S-F15')
        with self.assertRaises(ValueError):p.validate(spec(j))
    def test_no_C1_exception_or_missing_proxy_for_long(self):
        s=spec(job());s['measurement_exceptions']=1
        with self.assertRaises(ValueError):p.validate(s)
        j=job();j['timing']['endpoint_batch_seconds']=[]
        with self.assertRaises(ValueError):p.validate(spec(j))
    def test_original_shared_result_window_not_reset(self):
        j=job();start=1792556000;receipt={'worker_start_epoch':start}
        for mode in ('collect','audit','score'):
            _,end=io.window(mode,j,start+1000,receipt);self.assertEqual(end,start+34500)
        with self.assertRaises(TimeoutError):io.window('score',j,start+1600,receipt)
    def test_selection_requires_real_original_smoke_decision(self):
        self.assertIsNone(p.selection(job(),None));self.assertIsNone(p.selection(job('student','A7'),None))
        with self.assertRaises((ValueError,TypeError)):p.selection(job('student','A1'),None)
    def test_transport_keeps_binary_original_once(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'payload';root.mkdir();dump(root/'RESULT.json',{'complete':True});(root/'state.pt').write_bytes(bytes(range(256)))
            proof=transport.pack(root,1000);dest=Path(d)/'unpack';transport.extract(root/'evidence.tar',dest,proof,1000)
            self.assertEqual((dest/'state.pt').read_bytes(),bytes(range(256)))
            with self.assertRaises(ValueError):transport.pack(root,1000)
            with self.assertRaises(FileExistsError):transport.extract(root/'evidence.tar',dest,proof,1000)
    def test_unsafe_member_rejected(self):
        for n in ('../state.pt','/state.pt','a/../state.pt'):
            with self.assertRaises(ValueError):transport.safe(n)
    def test_no_repeated_partial_spawn(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);j=job();s=spec(j);run=root/p.LOCAL/'dispatch'/p.logical(j);run.mkdir(parents=True)
            dump(root/p.LOCAL/'long_io_r1/upload'/p.logical(j)/'COMPLETED.json',{'job_sha256':digest(j),'all_remote_file_bytes_read_back':True})
            report=root/'report.md';report.write_text('PASS');review=root/'review.json';dump(review,{'local_report_path':str(report),'report_sha256':sha(report)})
            budget=root/'budget.json';dump(budget,{})
            worker=unittest.mock.Mock()
            with patch.object(p,'reviewed',return_value={}),patch.object(p,'budget_check',return_value={}),patch.object(p.lifecycle,'ledger',return_value=[]):
                with self.assertRaises(ValueError):p.submit(root,s,p.logical(j),review,budget,None,Store(),worker,'ap-a',publication=lambda *a:'f'*40,observation=lambda *a:{})
            worker.spawn.assert_not_called()
    def test_full_training_cycle_includes_commit_and_remote_overhead(self):
        with tempfile.TemporaryDirectory() as d:
            clock=[1.0];store=Store();encoded=[{'n_supervised':1,'n_processed':2}];plan={'updates':[[0]]};projections=[]
            def commit():clock[0]+=3
            def forecast(*a):projections.append(a);return {'fixture':True}
            with patch.object(execution.time,'monotonic',side_effect=lambda:clock[0]):
                journal=execution.WholeAnswerJournal(d,'k',store,commit,lambda:None,encoded,plan,[.1],forecast)
                record={'step':1,'indices':[0],'lr':.1,'supervised_tokens':1,'processed_tokens':2}
                journal.begin('update_00001',record);commit();clock[0]+=2
                journal.end('update_00001',{**record,'cumulative_supervised':1,'cumulative_processed':2,'loss':1.,'gradient_norm':1.,'seconds':2.})
                commit();journal.finish_update()
                self.assertEqual(journal.times,[8.]);self.assertEqual(journal.cycles[0]['volume_commits_included'],2)
                with self.assertRaises(ValueError):journal.finish_update()
    def test_full_endpoint_cycle_includes_three_commits(self):
        class Answer:
            token_ids=[151645];text='';finish_reason='stop';stop_reason=151645;cumulative_logprob=None
        class Return:
            prompt_token_ids=[1];outputs=[Answer()]
        class LLM:
            def generate(self,*a,**k):clock[0]+=2;return [Return()]
        clock=[1.];row={'id':'math500:0000:greedy:0','mode':'greedy','seed':0,'prompt_token_ids':[1],'request_sha256':'a'*64}
        with tempfile.TemporaryDirectory() as d,patch.object(execution.time,'monotonic',side_effect=lambda:clock[0]):
            def commit():clock[0]+=3
            times=execution.evaluate(LLM(),lambda **kw:kw,[row],[151645],d,'k',Store(),commit,lambda:None,lambda *a:{'fixture':True})
            self.assertEqual(times,[11.]);self.assertEqual(read(Path(d)/'ENDPOINT_COMPLETE_CYCLES.json')[0]['volume_commits_included'],3)
    def test_child_reads_arm_specific_rates_from_new_consumer(self):
        import inspect
        self.assertIn("'rates_'+arm+'.json'",inspect.getsource(execution.child))
        self.assertIn('journal.finish_update()',inspect.getsource(training.train_terminal))
    def test_complete_receipt_cannot_substitute_other_job_or_provider(self):
        j=job();s=spec(j);k=p.key(j);claim={'original':True}
        receipt=dict(status='completed',logical_id=p.logical(j),spec_sha256=digest(s),job_sha256=digest(j),claim=claim,app_id='ap-a',worker_start_epoch=10.,finished_epoch=20.)
        provider=dict(app_id='ap-a',state='stopped',owned_containers=0,observed_epoch=21.);records={k+'/claim':claim,k+'/terminal':receipt}
        io.original(s,j,receipt,provider,records)
        provider['owned_containers']=1
        with self.assertRaises(ValueError):io.original(s,j,receipt,provider,records)
    def test_full_worker_mock_closes_once_without_model(self):
        # All outer worker checks exercised; payload/model supplied as synthetic.
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);j=job();s=spec(j);sf=root/'SPEC.json';dump(sf,s);k=p.key(j);store=Store()
            raw='PASS';intent=dict(job_id=p.logical(j),logical_id=p.logical(j),execution='f'*40,app_id='ap-a',spec_sha256=digest(s),spec_file_sha256=sha(sf),job_sha256=digest(j),dispatch_epoch=1792556000.,budget_observed_epoch=1792556000.,review={'report_sha256':hashlib.sha256(raw.encode()).hexdigest()},budget={'prior_reserved_usd':'0'})
            store[k+'/dispatch']=intent;volume=unittest.mock.Mock();timer=unittest.mock.Mock()
            def body(job,inputs,out,*args):
                value={'synthetic':True};dump(out/'RESULT.json',value);return value
            with patch.object(p.time,'time',return_value=1792556001.),patch.object(p.shared,'exact_source'),patch.object(p,'reviewed'),patch.object(p,'verify'),patch.object(p,'read',side_effect=lambda f:{'eos_token_id':[151645,151643]} if str(f).endswith('generation_config.json') else read(f)),patch.object(p,'BASE',str(root/'runs')),patch.object(p,'INPUTS',str(root/'inputs')):
                result=p.worker_body(s,sf,root,intent,raw,store,volume,lambda _:timer,body)
                self.assertEqual(result['status'],'completed');timer.cancel.assert_called_once();self.assertEqual(store[k+'/terminal'],result)
                with self.assertRaises(ValueError):p.worker_body(s,sf,root,intent,raw,store,volume,lambda _:timer,body)

import hashlib
if __name__=='__main__':unittest.main()

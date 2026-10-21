"""New B full-path integration fixtures; no old corpus/model/scorer execution."""
import copy,hashlib,json,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
from experiments.p011 import b_path as p,b_input_path as inputs
from scripts import p011_b_io as io,analyze_p011_b as analysis
from experiments.sft_allocation_midpoint.common import dump,read,sha,digest
from tests.test_p011_b_input_student import authority
from analyses.p011_b_contrasts import contrast


def job(kind='generation',run='generation'):
    names=['GPU_PACK.json'] if kind=='generation' else ['rows.json','encoded.json','plan.json','config.json','MATH_ENDPOINT.json']
    files={n:{'bytes':1,'sha256':'a'*64} for n in names}
    return dict(kind=kind,run_id=run,category='B',owner_B16_sha256=p.OWNER_SHA,input_directory=run,
        input_files=files,local_input_files={**files,('PACK.json' if kind=='generation' else 'GOLD.jsonl'):{'bytes':1,'sha256':'b'*64}},
        config=None if kind=='generation' else {'run_id':run,'owner_B16_sha256':p.OWNER_SHA},
        model=dict(model_id='Qwen/Qwen2.5-Math-1.5B-Instruct' if kind=='generation' else 'Qwen/Qwen2.5-1.5B',
            revision='aafeb0fc6f22cbf0eaeed126eff8be45b0360a35' if kind=='generation' else '8faed761d45a263340a0528343f099c05c9a4323',
            remote_path='/evidence/mp-teacher-cost-20261012-r1/assets/model' if kind=='generation' else '/evidence/mp-engineering-20261012-r1/assets/model',
            local_path='fixture',files={'config.json':{'bytes':1,'sha256':'c'*64}},producer_binding_files={'writer':'d'*64},remote_path_producer='fixture_writer'),
        timing=dict(source_evidence_files={'fixture':'e'*64},whole_iteration_scope_accepted=True,
            training_cycle_seconds=[] if kind=='generation' else [.1],batch_cycle_seconds=[.1],future_allowance_seconds=600),
        limits=dict(worker_seconds=1000,platform_seconds=1060,startup_seconds=600,closeout_seconds=63000 if kind=='generation' else 26000,
            score_seconds=62000 if kind=='generation' else 25200,full_result_window_seconds=65000 if kind=='generation' else 28000,
            artifact_max_bytes=100000,hourly_rate_usd='4',reserved_usd='1.85'))


def spec(phase='generation'):
    jobs=[job()] if phase=='generation' else [job('student',n) for n in ('B1','B2','B3')]
    return dict(phase=phase,original_plan_commit=p.shared.PLAN,source_files={p.OWNER_PATH:p.OWNER_SHA},
        jobs={p.logical(j):j for j in jobs},measurement_exceptions=0,result_cutoff_epoch=p.CUTOFF)

class Store(dict):
    def put(self,k,v,skip_if_exists=False):
        if skip_if_exists and k in self:return False
        self[k]=v;return True

class NewBWholePath(unittest.TestCase):
    def test_two_immutable_phase_specs_cannot_replace_generation_with_students(self):
        for phase in ('generation','student'):p.validate(spec(phase))
        self.assertNotEqual(p.spec_path(spec()),p.spec_path(spec('student')))
        s=spec('student');s['jobs'].pop('B_B2_s17_r1')
        with self.assertRaises(ValueError):p.validate(s)
        s=spec();s['phase']='student'
        with self.assertRaises(ValueError):p.validate(s)
        with self.assertRaises(ValueError):p.phase_for_job('B4')

    def test_model_asset_writer_and_gold_free_gpu_input_required(self):
        s=spec();j=next(iter(s['jobs'].values()));j['model']['remote_path_producer']=''
        with self.assertRaises(ValueError):p.validate(s)
        s=spec();j=next(iter(s['jobs'].values()));j['input_files']['GOLD.jsonl']={'bytes':1,'sha256':'a'*64}
        with self.assertRaises(ValueError):p.validate(s)

    def test_generation_projection_separates_gold_and_cannot_repeat(self):
        with tempfile.TemporaryDirectory(dir='.local/p011_20261020/r1') as d:
            root=Path(d);binding,review=authority(root);binding['original_input_files']={}
            for n in inputs.ORIGINAL_INPUTS.values():dump(root/n,{'fixture':True});binding['original_input_files'][n]=sha(root/n)
            pack=dict(ordered400=['q'],prompts={'q':[1]},rows=[{'fixture':True}],source={'q':{'problem':'question','solution':'secret'}},gold=[{'gold':'secret'}])
            with patch.object(inputs,'original_inputs',return_value=pack):out=inputs.generate_inputs(root,binding,review)
            self.assertEqual(read(out/'GPU_PACK.json')['source'],{'q':{'problem':'question'}})
            self.assertNotIn('secret',(out/'GPU_PACK.json').read_text())
            self.assertEqual(read(out/'PACK.json'),pack)
            with self.assertRaises(ValueError):inputs.generate_inputs(root,binding,review)

    def test_partial_dispatch_never_spawns_new_function(self):
        with tempfile.TemporaryDirectory(dir='.local/p011_20261020/r1') as d:
            root=Path(d);s=spec();j=job();name=p.logical(j);(root/p.LOCAL/'dispatch'/name).mkdir(parents=True)
            dump(root/p.LOCAL/'b_io_r1/upload'/name/'COMPLETED.json',dict(job_sha256=digest(j),all_remote_file_bytes_read_back=True))
            report=root/'report';report.write_text('fixture');review=root/'review.json';dump(review,dict(local_report_path=str(report),report_sha256=sha(report)))
            budget=root/'budget.json';dump(budget,{})
            worker=Mock()
            with patch.object(p,'reviewed',return_value={}),patch.object(p,'budget_check',return_value={}),patch.object(p.lifecycle,'ledger',return_value=[]):
                with self.assertRaises(ValueError):p.submit(root,s,name,review,budget,Store(),worker,'ap-a',publication=lambda *a:'f'*40,observation=lambda *a:{})
            worker.spawn.assert_not_called()

    def test_shared_pending_unknown_unmatched_slots_block_B_admission(self):
        with tempfile.TemporaryDirectory(dir='.local/p011_20261020/r1') as d:
            root=Path(d);source=root/'budget-source';source.write_text('fixture');now=1792560000.
            totals={k:'0' for k in p.shared.CAPS};totals['C']='1'
            records=[dict(logical_id='C1',app_id=None,budget=dict(category='C',new_reserved_usd='1'))]
            budget=dict(observed_epoch=now,all_attempted_reservations_usd=totals,category='B',cap_usd='20',overall_cap_usd='180',protected_usd='48',reserve_release_used=False,owner_estimate_used_as_balance=False,availability_basis='delayed_gross_plus_retained_reserves_conservative_floor',hourly_rate_usd='4',source_evidence_files={'budget-source':sha(source)},available_after_retained_prior_reserves_usd='60',observed_gross_resource_usd='300')
            obs={'containers':[{'app_id':'ap-unmatched'}]*3,'states':{}}
            with self.assertRaises(ValueError):p.budget_check(root,spec(),job(),budget,records,obs,now)
            obs['containers']=[];self.assertEqual(p.budget_check(root,spec(),job(),budget,records,obs,now)['provider_slots'],1)

    def test_same_original_result_deadline_and_full_score_window(self):
        j=job();start=1792560000.;receipt={'worker_start_epoch':start}
        for mode in ('collect','audit','score'):
            _,end=io.window(mode,j,start+1000,receipt);self.assertEqual(end,start+64000)
        with self.assertRaises(TimeoutError):io.window('score',j,start+2100,receipt)
        self.assertEqual(len(set(io.expected_records(j))),54)
        self.assertEqual(len(set(io.expected_records(job('student','B1')))),153)

    def test_only_true_completed_stopped0_original_job_can_collect(self):
        j=job();s=spec();k=p.key(j);claim={'fixture':True}
        r=dict(status='completed',logical_id=p.logical(j),spec_sha256=digest(s),job_sha256=digest(j),claim=claim,app_id='ap-a',worker_start_epoch=10.,finished_epoch=20.)
        provider=dict(app_id='ap-a',state='stopped',owned_containers=0,observed_epoch=21.);records={k+'/claim':claim,k+'/terminal':r}
        io.original(s,j,r,provider,records)
        provider['state']='unknown'
        with self.assertRaises(ValueError):io.original(s,j,r,provider,records)

    def test_mock_complete_generation_worker_preserves_fence_and_archive(self):
        with tempfile.TemporaryDirectory(dir='.local/p011_20261020/r1') as d:
            root=Path(d);s=spec();j=job();sf=root/'SPEC.json';dump(sf,s);k=p.key(j);store=Store();raw='fixture'
            intent=dict(job_id=p.logical(j),execution='f'*40,app_id='ap-a',spec_sha256=digest(s),spec_file_sha256=sha(sf),job_sha256=digest(j),dispatch_epoch=1792560000.,budget_observed_epoch=1792560000.,review={'report_sha256':hashlib.sha256(raw.encode()).hexdigest()},budget={'prior_reserved_usd':'0'})
            store[k+'/dispatch']=intent;volume=Mock();timer=Mock()
            def body(j,i,out,*args):value={'fixture':True};dump(out/'RESULT.json',value);return value
            with patch.object(p.time,'time',return_value=1792560001.),patch.object(p.shared,'exact_source'),patch.object(p,'reviewed'),patch.object(p,'verify'),patch.object(p,'BASE',str(root/'runs')),patch.object(p,'INPUTS',str(root/'inputs')):
                value=p.worker_body(s,sf,root,intent,raw,store,volume,lambda _:timer,body)
                self.assertEqual(value['status'],'completed');self.assertEqual(store[k+'/terminal'],value)
                with self.assertRaises(ValueError):p.worker_body(s,sf,root,intent,raw,store,volume,lambda _:timer,body)

    def test_new_interaction_uses_same_question_draws_and_rejects_order_changes(self):
        ids=[str(i) for i in range(500)]
        def v(value):return dict(complete=True,technical_unknown=0,question_ids=ids,question_values=[value]*500,metric='greedy')
        vectors={'B1':v(False),'B3':v(True),'T08_K1':v(False),'T08_K8':v(False)}
        result=contrast(vectors,ids,'greedy');self.assertEqual(result['contrasts'][0]['difference_pp'],100.)
        self.assertEqual(result['contrasts'][0]['pointwise95_ci_pp'],[100.,100.])
        vectors['T08_K8']['question_ids']=list(reversed(ids))
        with self.assertRaises(ValueError):contrast(vectors,ids,'greedy')

    def test_analysis_refuses_foreign_job_or_incomplete_saved_scores(self):
        with tempfile.TemporaryDirectory(dir='.local/p011_20261020/r1') as d:
            root=Path(d);s=spec('student');j=s['jobs']['B_B1_s17_r1'];name=p.logical(j)
            folder=root/p.LOCAL/'b_io_r1/score'/name;payload=folder/'owned_score/payload'
            dump(folder/'COMPLETED.json',{'read_only_saved_score_proof':{'passed':True}})
            dump(payload/'COMPLETED.json',{'technical_unknown':0})
            oracle=root/p.LOCAL/'b_io_r1/audit'/name/'COMPLETE_PROOF.json'
            dump(oracle,dict(passed=True,job_sha256='WRONG',source_files=s['source_files']))
            dump(payload/'INTENT.json',dict(binding=dict(job_sha256=digest(j),source_files=s['source_files'],oracle_sha256=sha(oracle))))
            with self.assertRaisesRegex(ValueError,'job/source/oracle'):analysis.new_vectors(root,s,[], 'greedy',{})

if __name__=='__main__':unittest.main()

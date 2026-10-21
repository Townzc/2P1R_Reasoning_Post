"""New preflight-only tests; no old tests, real inputs, model or cloud calls."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import ast,json,tempfile,unittest
from unittest.mock import patch,Mock
from experiments.p011.long_preflight import subset,training,execution,path
from experiments.p011 import long_training
from experiments.sft_allocation_midpoint.common import dump,read,sha,digest,manifest
from scripts import prepare_p011_long_preflight_inputs as prepare
from scripts.p011_long_preflight_io import window


def inputs():
    encoded=[]
    for i,n in enumerate([15000,16384,16000]):
        ids=[10]*n;ids[-1]=151645
        encoded.append({'path_id':str(i),'input_ids':ids,'labels':[-100]*10+ids[10:],
            'assistant_start':10,'assistant_end':n,'n_processed':n,'n_supervised':n-10,
            'eos_token_id':151645,'template_final_newline_supervised':False})
    rows=[];local=[]
    for b,n in subset.BENCHMARK_COUNTS.items():
        for i in range(n):
            for mode,seeds in ([('sample',range(4)),('greedy',[0])] if b=='math500' else [('sample',range(8))]):
                for seed in seeds:
                    tokens=[1]*(2+i%10)
                    x={'id':f'{b}:{i:04d}:{mode}:{seed}','problem_id':f'{b}:{i:04d}',
                       'benchmark':b,'source_row':i,'mode':mode,'seed':seed,'prompt_token_ids':tokens,
                       'prompt_text_sha256':digest('native'),'raw_prompt_text_sha256':digest('native'),
                       'native_NFC_changed':False,'required_context':len(tokens)+16384,'gold':'42'}
                    local.append(x);rows.append({**{k:v for k,v in x.items() if k!='gold'},'request_sha256':digest(x)})
    return encoded,rows,local,16395


def candidate():
    jobs={}
    for arm in long_training.ARMS:
        mem=98304 if arm=='S-F15' else 32768;rate='4.9072' if mem==98304 else '4.3952';reserve='2.13' if mem==98304 else '1.91'
        job={'kind':'engineering_preflight','arm':arm,'category':'A','seed':17,'U':2,'B':100,
             'endpoint_count':32,'input_directory':arm,'input_files':{'encoded.json':{}},
             'local_input_files':{'encoded.json':{},'ENDPOINT_LOCAL.json':{}},'eos_token_ids':[151645,151643],
             'resources':{'cpu':4,'memory_mib':mem},'context':16395,
             'model':{k:long_training.ARMS[arm][k] for k in ('model_id','revision')},
             'resource_rates_usd_per_hour':{'H100':'3.95','cpu_core':'.04730','GiB':'.008'},
             'limits':{'worker_seconds':900,'platform_seconds':960,'startup_seconds':600,'closeout_seconds':7200,
                       'full_result_window_seconds':8760,'artifact_max_bytes':100_000_000_000,
                       'hourly_rate_usd':rate,'reserved_usd':reserve}}
        job['model'].update(remote_path='/evidence/p011-20261020/models/qwen3b_instruct' if arm=='S-L3' else '/evidence/exploratory-20261014-r1/instruct_assets',files={'model':'synthetic'},producer_binding_files={'original':'synthetic'})
        jobs[path.logical(job)]=job
    return {'original_plan_commit':path.shared.PLAN,'source_files':{'synthetic':'a'*64},
            'owner_decision_sha256':subset.OWNER_SHA,'result_cutoff_epoch':path.CUTOFF,
            'engineering_preflight':True,'scientific_cell_result':False,'measurement_exceptions':3,
            'formal_repair_review_sha256':'a'*64,'jobs':jobs}


class PreflightTests(unittest.TestCase):
    def test_longest_two_and_stratified_original_requests_without_encoding(self):
        e,r,l,c=inputs();before=digest([e,r]);a,p,lr,q,proof=subset.select(e,r,c,'S-L15')
        self.assertEqual([x['path_id'] for x in a],['1','2']);self.assertEqual(p['updates'],[[0,1],[0,1]])
        self.assertEqual(len(q),32);self.assertEqual(sum(x['mode']=='greedy' for x in q),1)
        self.assertEqual(digest([e,r]),before);self.assertTrue(proof['formal512_batch_throughput_unmeasured'])
        self.assertTrue(all(x in r for x in q));self.assertTrue(all(x in e for x in a))

    def test_foreign_masks_dose_scope_or_smaller_sequences_rejected(self):
        e,r,l,c=inputs();a,p,lr,q,proof=subset.select(e,r,c,'S-F15')
        for key,value in [('engineering_preflight',False),('scientific_cell_result',True),('optimizer_updates',3),('updates',[[0],[1]])]:
            bad=deepcopy(p);bad[key]=value
            with self.assertRaises(ValueError):subset.validate(a,bad,lr,'S-F15')
        a[0]['labels'][0]=10
        with self.assertRaises(ValueError):subset.validate(a,p,lr,'S-F15')
        e=e[:1]+[deepcopy(e[0])];e[1]['path_id']='unique';e[0]['n_processed']=14999
        with self.assertRaises(ValueError):subset.select(e,r,c,'S-L15')

    def test_gold_extra_sampling_or_incomplete_subset_blocked(self):
        e,r,l,c=inputs();a,p,lr,q,proof=subset.select(e,r,c,'S-L3')
        for change in ('gold','seed','missing'):
            bad=deepcopy(q)
            if change=='missing':bad.pop()
            else:bad[0][change]='42' if change=='gold' else 3
            with self.assertRaises(ValueError):subset.validate_requests(bad,c)

    def test_training_math_and_join_ast_unchanged_after_scope_validator(self):
        def fn(file,name):return next(n for n in ast.parse(Path(file).read_text()).body if isinstance(n,ast.FunctionDef) and n.name==name)
        old=fn('experiments/p011/long_training.py','train_terminal');new=fn('experiments/p011/long_preflight/training.py','train_terminal_subset')
        new.name=old.name
        for n in ast.walk(new):
            if isinstance(n,ast.Name) and n.id=='validate':n.id='validate_plan'
        self.assertEqual(ast.dump(old,include_attributes=False),ast.dump(new,include_attributes=False))
        self.assertEqual(ast.dump(fn('experiments/p011/long_execution.py','joined_training'),include_attributes=False),ast.dump(fn('experiments/p011/long_preflight/execution.py','joined_training'),include_attributes=False))

    def test_three_actual_resource_reserves_and_owner_boundaries(self):
        s=candidate();path.validate(s)
        self.assertEqual(sum(path.Decimal(x['limits']['reserved_usd']) for x in s['jobs'].values()),path.Decimal('5.95'))
        for mutate in ['fourth','worker','owner','fullmemory','formal']:
            bad=deepcopy(s);j=next(iter(bad['jobs'].values()))
            if mutate=='fourth':bad['jobs']['other']=deepcopy(j)
            elif mutate=='worker':j['limits']['worker_seconds']=901
            elif mutate=='owner':bad['owner_decision_sha256']='0'*64
            elif mutate=='fullmemory':bad['jobs']['preflight_S-F15_s17_r1']['resources']['memory_mib']=32768
            else:bad['scientific_cell_result']=True
            with self.assertRaises(ValueError):path.validate(bad)

    def test_budget_retains_failed_calls_and_stale_or_unknown_blocks(self):
        s=candidate();j=s['jobs']['preflight_S-L15_s17_r1'];now=1792567000.
        records=[{'logical_id':'C1_original_token_base_forward_r1','app_id':'ap-old','budget':{'category':'C','new_reserved_usd':'3.74'}}]
        obs={'containers':[],'states':{'ap-old':'stopped'}}
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);dump(root/'e.json',{'fresh':'synthetic'})
            b={'observed_epoch':now,'all_attempted_reservations_usd':{'A':'0','B':'0','C':'3.74','D':'0','emergency':'0'},
                'category':'A','cap_usd':'115','overall_cap_usd':'180','protected_usd':'0','budget_owner_decision_sha256':subset.OWNER_SHA,
                'reserve_release_used':False,'owner_estimate_used_as_balance':False,
                'availability_basis':'owner_current_balance_minus_retained_P011_reserves_and_meter_growth',
                'hourly_rate_usd':'4.3952','source_evidence_files':{'e.json':sha(root/'e.json')},
                'available_after_retained_prior_reserves_usd':'10','observed_gross_resource_usd':'1'}
            x=path.budget_check(root,s,j,b,records,obs,now);self.assertEqual(x['all_attempted_reservations_usd']['C'],'3.74')
            with self.assertRaises(ValueError):path.budget_check(root,s,j,b,records,obs,now+3601)
            with self.assertRaises(ValueError):path.budget_check(root,s,j,b,records,{'containers':[{'app_id':'unknown'}]*4,'states':obs['states']},now)
            b['protected_usd']='48'
            with self.assertRaises(ValueError):path.budget_check(root,s,j,b,records,obs,now)

    def test_closed_engineering_window_never_resets(self):
        j=candidate()['jobs']['preflight_S-F15_s17_r1'];start=1792567000.
        self.assertEqual(window('collect',j,start+900,{'worker_start_epoch':start})[1],start+8100)
        self.assertEqual(window('audit',j,start+8099,{'worker_start_epoch':start})[0],1)
        with self.assertRaises(TimeoutError):window('audit',j,start+8100,{'worker_start_epoch':start})

    def test_input_subset_constructor_once_without_tokenizer_or_generation(self):
        e,r,local,c=inputs()
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source=root/prepare.SOURCE;source.mkdir(parents=True)
            dump(source/'COMPLETED.json',{'synthetic':True});dump(source/'A8/encoded.json',e)
            dump(source/'baseline/ENDPOINT_GPU.json',r);dump(source/'baseline/ENDPOINT_LOCAL.json',local)
            (root/'report.md').write_text('synthetic')
            binding={'source_files':{'synthetic':'a'*64},'input_basis_files':{str(prepare.SOURCE/'COMPLETED.json'):sha(source/'COMPLETED.json')}}
            review={'scope':prepare.SCOPE,**binding,'owner_decision_sha256':subset.OWNER_SHA,'input_preparation_authorized':True,'original_completed_long_inputs_accepted':True,'engineering_subset_only':True}
            with patch.object(prepare.shared,'fixed_report',side_effect=lambda x:x),patch.object(prepare.shared,'exact_source'):
                out=prepare.build(root,binding,review)
                self.assertEqual(read(out/'COMPLETED.json')['tokenizations'],0)
                self.assertEqual(len(read(out/'S-L3/ENDPOINT_GPU.json')),32)
                self.assertTrue((root/prepare.R/'LONG_PREFLIGHT_INPUT_ATTEMPT.json').exists())
                with self.assertRaises(ValueError):prepare.build(root,binding,review)

    def test_measurement_note_never_claims_formal_forecast(self):
        check=Mock();value=execution.hard_measurement_note(check,'training',2,[])
        self.assertFalse(value['forecast_performed']);self.assertTrue(value['not_formal_runtime_admission']);check.assert_called_once()

if __name__=='__main__':unittest.main()

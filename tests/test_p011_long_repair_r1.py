"""New R1/R2/R3 and numeric-gold boundaries; old successful suites not rerun."""
import ast,copy,subprocess,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
from experiments.p011 import long_execution as x,long_evidence as ev,long_path as p
from experiments.p011 import long_protocol as protocol,long_checkpoint,long_gold_input as gold
from experiments.p011 import long_evaluation as evaluation
from experiments.sft_allocation_midpoint.common import read,dump,sha,digest
from scripts import prepare_p011_long_numeric_gold_inputs as inp
from tests.test_p011_long_full_path import job,Store

ROOT=Path(__file__).resolve().parents[1]

def rows():
    return [dict(benchmark=b,source_row=i,problem=f'problem {b} {i}',
        answer=i if b=='aime25' else float(i) if b=='amc23' else ' 2 ')
        for b,n in evaluation.BENCHMARK_COUNTS.items() for i in range(n)]

def spec(arm='S-F15'):
    j=job('student','A7',arm);j['resources']=protocol.resources('student',arm)
    j['resource_rates_usd_per_hour']={'H100':'3.95','cpu_core':'.04730','GiB':'.008'}
    j['limits']['hourly_rate_usd']='4.9072' if arm=='S-F15' else '4.3952'
    j['limits']['reserved_usd']='2.27' if arm=='S-F15' else '2.03'
    source={n:'a'*64 for n in ('src/sft_data.py','src/__init__.py','experiments/p011/long_checkpoint.py','experiments/p011/long_protocol.py')}
    return dict(original_plan_commit=p.shared.PLAN,source_files=source,jobs={p.logical(j):j},measurement_exceptions=0,result_cutoff_epoch=p.CUTOFF)

class Repair(unittest.TestCase):
    def test_full_parameter_requires_96GiB_and_cost_includes_it(self):
        s=spec();p.validate(s);j=next(iter(s['jobs'].values()));j['resources']['memory_mib']=32768
        with self.assertRaisesRegex(ValueError,'resources'):p.validate(s)
    def test_memory_rate_mismatch_and_nonfinite_rejected(self):
        for mutation in ('rate','nan'):
            s=spec();j=next(iter(s['jobs'].values()))
            if mutation=='rate':j['limits']['hourly_rate_usd']='4.3952'
            else:j['resource_rates_usd_per_hour']['GiB']='NaN'
            with self.assertRaises(ValueError):p.validate(s)
    def test_LoRA32GiB_and_source_dependency_mandatory(self):
        for arm in ('S-L15','S-L3'):p.validate(spec(arm))
        s=spec();del s['source_files']['src/sft_data.py']
        with self.assertRaisesRegex(ValueError,'closure'):p.validate(s)
    def test_mmap_writer_saves_small_real_tensors_and_fences_duplicate(self):
        import torch
        state={'schema':'p011_complete_training_state_v1','identity':{'fixture':True},'step':2,
            'supervised_tokens':4,'processed_tokens':8,'adapter':{'w':torch.arange(6,dtype=torch.float32)},
            'optimizer':{'moments':torch.ones(6)},'rng':torch.get_rng_state()}
        calls=[];original=torch.load
        def load(*a,**kw):calls.append(kw.copy());return original(*a,**kw)
        with tempfile.TemporaryDirectory() as d,patch.object(torch,'load',side_effect=load):
            commits=[];rec=long_checkpoint.save(d,state,lambda:commits.append(1))
            self.assertTrue(calls[0]['mmap']);self.assertTrue(calls[0]['weights_only'])
            self.assertEqual(commits,[1]);self.assertEqual(rec['step'],2)
            with self.assertRaises(FileExistsError):long_checkpoint.save(d,state)
    def test_corrupt_mapped_readback_does_not_publish_manifest(self):
        import torch
        state={'step':2,'schema':'fixture','identity':{},'supervised_tokens':1,'processed_tokens':1,'x':torch.ones(1)}
        with tempfile.TemporaryDirectory() as d,patch.object(torch,'load',return_value={}):
            with self.assertRaisesRegex(ValueError,'serialization'):long_checkpoint.save(d,state)
            self.assertTrue((Path(d)/'checkpoint_0002/state.pt').exists())
            self.assertFalse((Path(d)/'checkpoint_0002/manifest.json').exists())
    def test_3300_in_seven_batches_seeds_and_full_commits_preserved(self):
        rows=[{'id':f'synthetic:{i}','mode':'sample','seed':i%8,'prompt_token_ids':[i+1],
               'request_sha256':'a'*64} for i in range(3300)]
        seen=[];clock=[0.];store=Store();commit_count=[];forecasts=[]
        class LLM:
            def generate(self,prompts,params,use_tqdm):
                seen.extend(params);clock[0]+=2
                return [NS(prompt_token_ids=q['prompt_token_ids'],outputs=[NS(token_ids=[151645],text='',finish_reason='stop',stop_reason=151645)]) for q in prompts]
        def commit():clock[0]+=3;commit_count.append(1)
        def forecast(n,t):forecasts.append((n,len(t)));return {'left':n}
        with tempfile.TemporaryDirectory() as d,patch.object(x.time,'monotonic',side_effect=lambda:clock[0]):
            times=x.evaluate(LLM(),lambda **k:k,rows,[151645],d,'k',store,commit,lambda:None,forecast)
            self.assertEqual(times,[11.]*7);self.assertEqual(len(commit_count),21)
            self.assertEqual([r['seed'] for r in seen],[r['seed'] for r in rows])
            self.assertEqual([read(Path(d)/f'completed/eval_{i:04d}.json')['count'] for i in range(7)],[512]*6+[228])
            self.assertEqual(forecasts,[(7-i,i) for i in range(7)])
    def test_new_engine_geometry_and_raw_oracle_unit_count_agree(self):
        settings=x.engine_settings(17000)
        self.assertEqual(settings['max_num_seqs'],256);self.assertEqual(settings['max_num_batched_tokens'],8192)
        self.assertEqual(len(ev.expected_units('baseline',0)),7)
        self.assertEqual(len(ev.expected_units('student',654)),663)
        self.assertEqual(protocol.endpoint_batches(3300),7)
        with self.assertRaises(ValueError):protocol.endpoint_batches(3301)
    def test_old_science_and_input_functions_AST_unchanged(self):
        targets={'experiments/p011/long_training.py':['learning_rates','validate_plan','load_model','accumulate'],
            'experiments/p011/long_execution.py':['validate_endpoint'],
            'experiments/p011/long_evaluation.py':['request_roster','sampling','answer_region','scoring_rows'],
            'scripts/prepare_p011_long_runtime_inputs.py':['source_review','consume','write_endpoint','main']}
        for path,names in targets.items():
            old=subprocess.check_output(['git','show','db1aff076163606ded08776eca637c043d6c916b:'+path],cwd=ROOT).decode()
            def selected(s):return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(s).body if isinstance(n,ast.FunctionDef) and n.name in names}
            self.assertEqual(selected(old),selected((ROOT/path).read_text()),path)
        original=subprocess.check_output(['git','show','db1aff076163606ded08776eca637c043d6c916b:experiments/sft_allocation_midpoint/checkpoint.py'],cwd=ROOT)
        self.assertEqual(original,(ROOT/'experiments/sft_allocation_midpoint/checkpoint.py').read_bytes())
    def test_numeric_gold_is_lossless_and_original_rows_untouched(self):
        data=rows();before=copy.deepcopy(data);out,proof=gold.benchmark_projection(data)
        self.assertEqual(data,before);self.assertEqual(len(out),600);self.assertEqual(len(proof),600)
        self.assertEqual(out[0]['answer'],' 2 ');self.assertEqual(out[530]['answer'],'0');self.assertEqual(out[560]['answer'],'0')
        self.assertEqual(sum(p['original_answer_type']!='str' for p in proof),70)
        self.assertTrue(all(not p['semantic_answer_change'] for p in proof))
    def test_unsafe_gold_and_duplicate_identity_rejected_before_encoding(self):
        for value in (True,float('nan'),float('inf'),2.5,[],{},' '):
            data=rows();data[530]['answer']=value
            with self.assertRaises(ValueError):gold.benchmark_projection(data)
        data=rows();data[531]['source_row']=0
        with self.assertRaisesRegex(ValueError,'identity'):gold.benchmark_projection(data)
    def test_all_gold_validated_then_600_fake_prompts_yield3300_original_requests(self):
        class Tok:
            backend_tokenizer=NS(normalizer=NS(normalize_str=lambda s:s))
            def __init__(self):self.calls=0;self.text=''
            def apply_chat_template(self,messages,**kw):return messages[0]['content']
            def __call__(self,text,**kw):self.calls+=1;self.text=text;return {'input_ids':[1,2]}
            def decode(self,*a,**kw):return self.text
        data=rows();tok=Tok()
        with self.assertRaisesRegex(ValueError,'unsupported gold'):evaluation.request_roster(data,tok)
        self.assertEqual(tok.calls,530)
        normalized,_=gold.benchmark_projection(data);new=Tok();req=evaluation.request_roster(normalized,new)
        self.assertEqual(new.calls,600);self.assertEqual(len(req),3300)
        self.assertEqual([r['seed'] for r in req[-8:]],list(range(8)))
    def test_new_cpu_claim_replay_and_partial_fence_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);dump(root/inp.R/'LONG_RUNTIME_INPUT_ATTEMPT.json',{})
            dump(root/inp.R/'long_inputs_r1/FAILED.json',{});owner=root/'owner.json';dump(owner,{})
            with patch.object(inp.shared,'fixed_report',return_value={'fixture':True}):
                out=inp.claim(root,{'source_files':{'s':'a'*64}},{},owner)
                self.assertTrue(out.exists())
                with self.assertRaises(ValueError):inp.claim(root,{'source_files':{}},{},owner)
                out.rmdir()
                with self.assertRaises(FileExistsError):inp.claim(root,{'source_files':{}},{},owner)
    def test_new_owner_exception_and_exact_CR_required(self):
        with tempfile.TemporaryDirectory() as d:
            ownerpath=Path(d)/'owner.json'
            owner=dict(request_id=inp.OWNER_REQUEST,decision='APPROVED',proposal_sha256='b'*64,original_failure_sha256='c'*64,requires_exact_CR=True,paid_calls_authorized=0,actual_reply='fixture',observed_utc='fixture')
            dump(ownerpath,owner);binding={'source_files':{'s':'a'*64},'input_basis_files':{},'owner_proposal_sha256':'b'*64,'original_failure_sha256':'c'*64}
            review=dict(scope=inp.SCOPE,source_files=binding['source_files'],input_basis_files={},owner_decision_sha256=sha(ownerpath),input_preparation_authorized=True,original_failed_attempt_retained=True,numeric_gold_semantics_unchanged=True,old530_prompts_not_saved_no_false_reuse_claim=True,one_new_cpu_attempt_only=True)
            with patch.object(inp.shared,'fixed_report',return_value={}),patch.object(inp.shared,'exact_source'):
                inp.admission(binding,review,owner,ownerpath)
                for field in ('owner_decision_sha256','one_new_cpu_attempt_only','scope'):
                    bad=copy.deepcopy(review);bad[field]=None
                    with self.assertRaises(ValueError):inp.admission(binding,bad,owner,ownerpath)
                bad=copy.deepcopy(owner);bad['paid_calls_authorized']=1
                with self.assertRaises(ValueError):inp.admission(binding,review,bad,ownerpath)

if __name__=='__main__':unittest.main()

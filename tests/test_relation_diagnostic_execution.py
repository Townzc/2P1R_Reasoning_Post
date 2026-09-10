"""E012 synthetic numerical, raw-output and budget/continuation boundary tests."""
import copy
import hashlib
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from src.relation_transport import make_world
from src.relation_verifier import orbit_key
from src.relation_diagnostics import derive_rows
from src.relation_diagnostic_verifier import token_fields,summarize
from src.relation_diagnostic_execution import (CONFIG,account,reference_record,aggregate_references,
    result_metrics,score_tokens,load_inputs)
from src.relation_diagnostic_training import reference_batch
from src.relation_experiment import profile
from src.sft_data import encode_row,sha256_file
from scripts.run_relation_diagnostics import check_ledger,check_backup,main as launcher
from scripts.audit_relation_diagnostic_outputs import audit,audit_predictions,OUTPUTS


class Tokens:
    eos_token_id = pad_token_id = 2
    def __len__(self): return 512
    def get_vocab(self): return {str(i):i for i in range(512)}
    def __call__(self,text,**kwargs):
        return {'input_ids':[ord(c)+3 for c in text],'offset_mapping':[(i,i+1) for i in range(len(text))]}
    def decode(self,ids,**kwargs): return ''.join(chr(i-3) for i in ids if 3<=i<512)


def fixture():
    cfg = {**json.loads(CONFIG.read_text()),'arm':'single_step','run_id':'synthetic_e012',
        'train_parents':4,'dev_parents':4,'train_worlds':4,'dev_worlds':4,
        'arms':['single_step','given_route','fixed_reference'],'assignment_seed':81401,
        'cycles':1,'steps':4,'profile_warmup':0,'profile_updates':4,'max_length':10000,'max_new_tokens':1000}
    worlds = [make_world(seed,i,split='unit_fixture') for seed in (9917,9987) for i in range(4)]
    for w in worlds: w['audit'] = {'orbit':orbit_key(w['question'])}
    rows,schedule,_ = derive_rows(worlds,cfg); tok = Tokens()
    selected = [r for r in rows if r['arm']=='single_step']
    encoded_map = {}
    for r in selected:
        enc = encode_row(r,tok,10000); r['token_fields'] = token_fields(r,tok,enc)
        r['tokens'] = {k:enc[k] for k in ('n_prompt','n_supervised','n_processed')}
        encoded_map[r['problem_id']] = enc
    train = [r for r in selected if r['split']=='train']; dev = [r for r in selected if r['split']=='engineering_dev']
    enc = [encoded_map[r['problem_id']] for r in train]
    budget = account(train,enc,schedule['single_step'],2)
    data = {'cfg':cfg,'train':train,'dev':dev,'encoded':enc,'schedule':schedule['single_step'],'budget':budget}
    return {'cfg':cfg,'arms':{'single_step':data},'tokenizer':tok,
            'tokenizer_record':{'repo_id':'synthetic_unit_fixture','revision':'unit'},
            'known_token_ids':frozenset(range(512)),'model_vocab_size':514,
            'release':{'source_files_sha256':{}}}


def predictions(rows,tok,known):
    out = []
    for row in rows:
        text = row['response']; ids = tok(text)['input_ids']+[2]
        out.append({**row,'text':text,'generated_ids':ids,'generated_tokens':len(ids),
                    'score':score_tokens(row,text,ids,True,False,known)})
    return out


class ReferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.prepared = fixture()

    def test_shifted_positions_and_padding_match_direct_cross_entropy(self):
        import torch
        import torch.nn.functional as F
        class PositionLogits(torch.nn.Module):
            def forward(self,input_ids,**kwargs):
                vocab = torch.arange(11,dtype=torch.float32)
                pos = torch.arange(input_ids.shape[1],dtype=torch.float32)
                logits = -((vocab[None,None,:]-(pos[None,:,None]%11))**2).expand(input_ids.shape[0],-1,-1)
                return SimpleNamespace(logits=logits)
        enc = [dict(input_ids=[3,4,5,2],labels=[-100,-100,5,2],n_supervised=2,response_hash='a'),
               dict(input_ids=[6,7,8,9,2],labels=[-100,7,8,9,2],n_supervised=4,response_hash='b')]
        rows = [dict(problem_id=str(i),parent_world_id=str(i),arm='fixture',split='train') for i in range(2)]
        result = reference_batch(PositionLogits(),rows,enc,2,device='cpu')
        self.assertEqual(result[0]['target_positions'],[2,3]); self.assertEqual(result[1]['target_positions'],[1,2,3,4])
        for rec in result:
            self.assertEqual(rec['predicted_ids'],[j-1 for j in rec['target_positions']])
            for j,target,loss in zip(rec['target_positions'],rec['target_ids'],rec['token_nll']):
                expected = F.cross_entropy(-((torch.arange(11,dtype=torch.float32)-(j-1))**2)[None,:],torch.tensor([target])).item()
                self.assertAlmostEqual(loss,expected,places=6)

    def test_all_fields_reconciled_and_top_one_consistency_checked(self):
        data = self.prepared['arms']['single_step']; refs = []
        for row,enc in zip(data['train'],data['encoded']):
            ids = [x for x in enc['labels'][1:] if x!=-100]
            refs.append(reference_record(row,enc,ids,[.1]*len(ids)))
        result = aggregate_references(refs,data['train'],data['encoded'],514)
        self.assertEqual(result['reference_count'],16)
        self.assertEqual(result['parent_count'],4)
        self.assertEqual(sum(x['tokens'] for x in result['by_field'].values()),result['all_response']['tokens'])
        self.assertEqual(len(result['after_state_by_original_route_position']),4)
        for key,value in [('predicted_ids',[513]*len(refs[0]['predicted_ids'])),
                          ('target_positions',refs[0]['target_positions'][1:]),('input_ids_sha256','wrong')]:
            bad = copy.deepcopy(refs); bad[0][key] = value
            with self.assertRaises(ValueError): aggregate_references(bad,data['train'],data['encoded'],514)

    def test_unknown_padded_model_tokens_are_retained_as_generation_failure(self):
        row = self.prepared['arms']['single_step']['train'][0]; tok = self.prepared['tokenizer']
        ids = [513]+tok(row['response'])['input_ids']+[2]
        result = score_tokens(row,row['response'],ids,True,False,self.prepared['known_token_ids'])
        self.assertFalse(result['complete_correct']); self.assertEqual(result['unmapped_output_token_positions'],[0])
        self.assertEqual(result['certificate']['reason'],'unmapped_output_token')


class OutputTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name); self.prepared = fixture(); self.data = self.prepared['arms']['single_step']
        self.cfg = self.data['cfg']; self.out = self.root/self.cfg['run_id']; self.out.mkdir()
        self.release = self.root/'release.json'; self.release.write_text('{}\n')
        self.addCleanup(patch.stopall)
        patch('scripts.audit_relation_diagnostic_outputs.RELEASE',self.release).start()
        patch('scripts.audit_relation_diagnostic_outputs.verify_source_hashes').start()
        self.tok = self.prepared['tokenizer']; known = self.prepared['known_token_ids']
        self.history = [{'step':i+1,'row_indices':indices,'seconds':.2,'response_nll':.1,'grad_norm':1.0,
            'peak_allocated_mib':10,'peak_reserved_mib':12,**self.data['budget']['per_update'][i]}
            for i,indices in enumerate(self.data['schedule'])]
        self.baseline = predictions(self.data['dev'],self.tok,known)
        self.training = predictions(self.data['train'],self.tok,known); self.dev = predictions(self.data['dev'],self.tok,known)
        self.refs = []
        for row,enc in zip(self.data['train'],self.data['encoded']):
            ids = [x for x in enc['labels'][1:] if x!=-100]
            self.refs.append(reference_record(row,enc,ids,[.1]*len(ids)))
        self.metrics = result_metrics(self.data,self.history,self.baseline,self.training,self.dev,self.refs,514)
        self.preflight = {'source_commit':'unit_fixture','arm':'single_step','server':{'model':{'all_files_verified':True}}}
        self.write('preflight.json',self.preflight)
        self.manifest = {'status':'completed','steps_completed':4,'config':self.cfg,
            'data_manifest_sha256':self.cfg['data_manifest_sha256'],'execution_release_sha256':sha256_file(self.release),
            'source_files_sha256':{str(self.release):sha256_file(self.release)},'source_commit':'unit_fixture',
            'tokenizer':self.prepared['tokenizer_record'],'model':'synthetic_unit_fixture','model_revision':'unit',
            'weights':'fresh_pinned_base','parameter_dtype':'float32','autocast_dtype':'bfloat16',
            'optimizer':'AdamW_foreach_false','attention':'sdpa','gradient_checkpointing':'nonreentrant',
            'tf32':False,'holdout_access':False,'scientific_treatment_comparison':False,
            'eos_token_id':2,'pad_token_id':2,'model_vocab_size':514,'tokenizer_size':512,
            'preflight_sha256':sha256_file(self.out/'preflight.json'),'server':self.preflight['server']}
        self.write('run_manifest.json',self.manifest)
        for name in ('planned_budget.json','actual_budget.json'): self.write(name,self.data['budget'])
        for name in ('evaluation_metrics.json','metrics.json'): self.write(name,self.metrics)
        self.write('throughput.json',profile(self.history,self.cfg))
        self.write('baseline_metrics.json',summarize(self.data['dev'],[p['score'] for p in self.baseline]))
        self.write('checkpoint_manifest.json',{'kind':'model_weights_only_not_optimizer_or_rng_resume',
            'files':{'synthetic.safetensors':{'sha256':'a'*64,'bytes':100}}})
        self.receipt = {'run_id':self.cfg['run_id'],'status':'completed','exit_code':0,'max_seconds':360,'charged_seconds':2,'elapsed_seconds':1.5}
        self.write('resource_receipt.json',self.receipt); (self.out/'stdout.log').write_text('Synthetic unit fixture, not model execution.\n')
        for name,rows in [('train_history.jsonl',self.history),('base_dev.jsonl',self.baseline),
                         ('final_train.jsonl',self.training),('final_dev.jsonl',self.dev),('train_reference_tokens.jsonl',self.refs)]: self.lines(name,rows)

    def write(self,name,obj): (self.out/name).write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n')
    def lines(self,name,rows): (self.out/name).write_text(''.join(json.dumps(x)+'\n' for x in rows))
    def verify(self): return audit(self.out,self.prepared,'single_step')

    def test_complete_synthetic_outputs_and_stable_reaudit(self):
        result = self.verify(); self.assertTrue(result['engineering_gate']['passed'])
        self.assertEqual(result['predictions_rechecked'],48); self.assertEqual(result['reference_rows_rechecked'],16)
        self.write('outputs_verification.json',result)
        self.assertEqual(result,self.verify())

    def test_bad_raw_tokens_cannot_keep_good_text_scores(self):
        for mutation in ({'text':'Answer : 0'},{'generated_ids':[2]+self.training[0]['generated_ids']},
                         {'generated_tokens':0},{'answer':9},{'parent_world_id':'wrong'}):
            rows = copy.deepcopy(self.training); rows[0].update(mutation); self.lines('final_train.jsonl',rows)
            with self.assertRaises(ValueError): self.verify()

    def test_missing_data_wrong_dose_and_nonfinite_history_fail_audit(self):
        wrong_order=copy.deepcopy(self.history); wrong_order[0]['row_indices'].reverse()
        wrong_tokens=copy.deepcopy(self.history); wrong_tokens[0]['supervised_tokens']+=1
        for rows in (self.history[:-1],wrong_order,wrong_tokens):
            self.lines('train_history.jsonl',rows)
            with self.assertRaises(ValueError): self.verify()
        rows = copy.deepcopy(self.history); rows[0]['grad_norm']=float('nan'); self.lines('train_history.jsonl',rows)
        with self.assertRaises(ValueError): self.verify()

    def test_changed_field_measurement_or_summary_is_rejected(self):
        bad = copy.deepcopy(self.refs); bad[0]['token_nll'][0]=.5; self.lines('train_reference_tokens.jsonl',bad)
        with self.assertRaises(ValueError): self.verify()
        self.lines('train_reference_tokens.jsonl',self.refs)
        bad_metric = copy.deepcopy(self.metrics); bad_metric['teacher_forced_train']['by_field']['after_state']['correct']=0
        self.write('metrics.json',bad_metric)
        with self.assertRaises(ValueError): self.verify()

    def test_wrong_receipt_failed_manifest_source_or_backup_shape_rejected(self):
        variants = [('resource_receipt.json',{**self.receipt,'charged_seconds':1000}),
            ('run_manifest.json',{**self.manifest,'status':'failed'}),
            ('run_manifest.json',{**self.manifest,'weights':'previous_diagnostic'}),
            ('run_manifest.json',{**self.manifest,'source_files_sha256':{}}),
            ('checkpoint_manifest.json',{'kind':'model_weights_only_not_optimizer_or_rng_resume','files':{'../escape.safetensors':{'bytes':100,'sha256':'a'*64}}})]
        for name,value in variants:
            old=(self.out/name).read_text(); self.write(name,value)
            with self.assertRaises(ValueError): self.verify()
            (self.out/name).write_text(old)

    def test_learning_failure_remains_verified_but_does_not_pass_gate(self):
        rows = copy.deepcopy(self.training); first = rows[0]
        text = f"Answer : {first['answer']}"; ids = self.tok(text)['input_ids']+[2]
        first.update(text=text,generated_ids=ids,generated_tokens=len(ids),
                     score=score_tokens(first,text,ids,True,False,self.prepared['known_token_ids']))
        self.lines('final_train.jsonl',rows)
        metrics=result_metrics(self.data,self.history,self.baseline,rows,self.dev,self.refs,514)
        for name in ('metrics.json','evaluation_metrics.json'): self.write(name,metrics)
        result=self.verify(); self.assertTrue(result['verified_compact_outputs']); self.assertFalse(result['engineering_gate']['passed'])


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup); self.root=Path(self.tmp.name)
        self.runs=self.root/'runs'; self.runs.mkdir(); self.ledger_path=self.root/'ledger.json'
        self.cfg=copy.deepcopy(json.loads(CONFIG.read_text())); self.cfg['expected_prior_jobs']=2
        jobs=[{'run_id':'prior_0','status':'completed','charged_seconds':1},
              {'run_id':'prior_1','status':'completed','charged_seconds':5970}]
        anchors=[]
        for job in jobs:
            d=self.runs/job['run_id']; d.mkdir(); p=d/'resource_receipt.json'; p.write_text(json.dumps(job))
            anchors.append({'run_id':job['run_id'],'receipt_sha256':sha256_file(p)})
        self.cfg['base_receipts']=anchors
        self.ledger={'budget_id':'first_session_20260905','authorized_gpu_seconds':7200,'jobs':jobs}
        self.save(); self.cfg['expected_initial_ledger_sha256']=sha256_file(self.ledger_path)

    def save(self): self.ledger_path.write_text(json.dumps(self.ledger,indent=2)+'\n')
    def check(self,arm='single_step',proof=None):
        return check_ledger(self.cfg,self.ledger_path,arm,None,root=self.runs,
            prior_verifier=lambda *args:proof,require_publication=False)

    def add_first(self,status='completed'):
        rid=self.cfg['run_ids']['single_step']; d=self.runs/rid; d.mkdir()
        entry={'run_id':rid,'status':status,'charged_seconds':200,'max_seconds':360,'exit_code':0 if status=='completed' else 1}
        (d/'resource_receipt.json').write_text(json.dumps(entry)); self.ledger['jobs'].append(entry); self.save()

    def test_initial_complete_phase_fits_without_mutation(self):
        before=self.ledger_path.read_bytes(); result=self.check()
        self.assertEqual(result['remaining_ladder_max_reservation_seconds'],1125)
        self.assertEqual(result['remaining_seconds'],1229); self.assertEqual(before,self.ledger_path.read_bytes())

    def test_missing_stale_reserved_duplicate_or_wrong_prefix_rejected(self):
        original=copy.deepcopy(self.ledger)
        variants=[]
        for field,value in [('charged_seconds',5969),('status','reserved'),('run_id','prior_0')]:
            item=copy.deepcopy(original); item['jobs'][1][field]=value; variants.append(item)
        variants.append({**original,'jobs':original['jobs'][:-1]})
        for item in variants:
            self.ledger=item; self.save()
            with self.assertRaises(ValueError): self.check()
        self.ledger_path.unlink()
        with self.assertRaises(ValueError): self.check()

    def test_out_of_order_and_replay_rejected(self):
        with self.assertRaises(ValueError): self.check('given_route')
        (self.runs/self.cfg['run_ids']['single_step']).mkdir()
        with self.assertRaises(FileExistsError): self.check()

    def test_only_verified_passed_stage_can_continue_with_updated_hash(self):
        old_hash=self.cfg['expected_initial_ledger_sha256']; self.add_first()
        failed={'verified_compact_outputs':True,'engineering_gate':{'passed':False}}
        with self.assertRaises(ValueError): self.check('given_route',failed)
        passed={'verified_compact_outputs':True,'engineering_gate':{'passed':True}}
        result=self.check('given_route',passed)
        self.assertEqual(result['remaining_ladder_max_reservation_seconds'],750)
        self.assertEqual(result['remaining_seconds'],1029); self.assertNotEqual(result['ledger_sha256'],old_hash)
        with self.assertRaises(ValueError): self.check('fixed_reference',passed)

    def test_failed_receipt_and_increased_caps_block_continuation(self):
        self.add_first('timeout')
        with self.assertRaises(ValueError): self.check('given_route',{'verified_compact_outputs':True,'engineering_gate':{'passed':True}})

    def test_whole_remaining_phase_must_fit_and_authorization_cannot_expand(self):
        self.cfg['max_seconds']=500
        with self.assertRaisesRegex(ValueError,'remaining conditional caps'): self.check()
        self.cfg['max_seconds']=360; self.cfg['authorized_gpu_seconds']=8000
        with self.assertRaisesRegex(ValueError,'authorization'): self.check()

    def test_passing_metrics_still_require_published_outputs_and_backup(self):
        self.add_first(); proof={'verified_compact_outputs':True,'engineering_gate':{'passed':True},'files_sha256':{'metrics.json':'fixture'}}
        with patch('scripts.run_relation_diagnostics.require_published') as publication,patch('scripts.run_relation_diagnostics.check_backup',side_effect=ValueError('Backup absent')) as backup:
            with self.assertRaisesRegex(ValueError,'Backup absent'):
                check_ledger(self.cfg,self.ledger_path,'given_route',None,root=self.runs,prior_verifier=lambda *args:proof)
            publication.assert_called_once(); backup.assert_called_once()

    def test_backup_manifest_must_match_independent_receipt(self):
        rid='unit_backup'; directory=self.root/rid; directory.mkdir()
        manifest={'files':{'weights.safetensors':{'sha256':'a'*64,'bytes':123}}}
        (directory/'checkpoint_manifest.json').write_text(json.dumps(manifest)); receipt=self.root/'backup.json'
        proof={'run_id':rid,'status':'verified_independent_backup','checkpoint_manifest_sha256':sha256_file(directory/'checkpoint_manifest.json'),
               'files':manifest['files'],'file_count':1,'total_bytes':123}
        receipt.write_text(json.dumps(proof)); check_backup(rid,directory,receipt_path=receipt,require_publication=False)
        proof['total_bytes']=122; receipt.write_text(json.dumps(proof))
        with self.assertRaises(ValueError): check_backup(rid,directory,receipt_path=receipt,require_publication=False)

    def test_watchdog_rechecks_changed_ledger_under_lock_without_child(self):
        from scripts.run_bounded import main
        before=self.ledger_path.read_bytes()
        argv=['run_bounded','--run-id','unit_watchdog','--ledger',str(self.ledger_path),'--max-seconds','360',
              '--expected-ledger-sha256','0'*64,'--require-full-cap','--','unused-child']
        with patch('sys.argv',argv),patch('scripts.run_bounded.shutil.which',return_value='timeout'),patch('scripts.run_bounded.subprocess.Popen') as child:
            with self.assertRaisesRegex(ValueError,'under lock'): main()
            child.assert_not_called()
        self.assertEqual(before,self.ledger_path.read_bytes())


class PreparationTests(unittest.TestCase):
    def test_inspect_default_never_calls_server_or_child(self):
        data=fixture(); data['cfg']['run_ids']['single_step']=data['arms']['single_step']['cfg']['run_id']
        with tempfile.TemporaryDirectory() as temp:
            release=Path(temp)/'release.json'; release.write_text('{}')
            with patch('scripts.run_relation_diagnostics.RELEASE',release),patch('scripts.run_relation_diagnostics.provenance',return_value={'source_commit':'unit'}),patch('scripts.run_relation_diagnostics.load_inputs',return_value=data),patch('scripts.run_relation_diagnostics.check_ledger',return_value={'remaining_seconds':1229}),patch('scripts.run_relation_diagnostics.server_preflight') as server,patch('scripts.run_relation_diagnostics.subprocess.call') as child,patch('sys.argv',['launcher','--tokenizer-dir','unused']),patch('sys.stdout',new_callable=io.StringIO):
                self.assertEqual(launcher(),0); server.assert_not_called(); child.assert_not_called()

    def test_frozen_c016_inputs_and_original_budget_still_verify(self):
        cache=Path('.local/hf-cache/hub/models--Qwen--Qwen2.5-1.5B/snapshots/8faed761d45a263340a0528343f099c05c9a4323')
        if not cache.exists(): self.skipTest('Pinned local tokenizer required before release')
        data=load_inputs(cache,require_release=False)
        self.assertTrue(data['c016_verified']); self.assertEqual(data['model_vocab_size'],151936)
        self.assertLess(len(data['known_token_ids']),data['model_vocab_size'])
        expected={'single_step':(128,29696,169984),'given_route':(32,103424,1252352),'fixed_reference':(32,103424,1164288)}
        for arm,(n,supervised,processed) in expected.items():
            d=data['arms'][arm]; self.assertEqual(len(d['train']),n)
            self.assertEqual(d['budget']['supervised_response_tokens'],supervised)
            self.assertEqual(d['budget']['processed_nonpadding_tokens'],processed)

    def test_execute_requires_explicit_verified_commit_before_server_preflight(self):
        data=fixture()
        with tempfile.TemporaryDirectory() as temp:
            release=Path(temp)/'release.json'; release.write_text('{}')
            with patch('scripts.run_relation_diagnostics.RELEASE',release),patch('scripts.run_relation_diagnostics.provenance',return_value={'source_commit':'unit'}),patch('scripts.run_relation_diagnostics.load_inputs',return_value=data),patch('scripts.run_relation_diagnostics.check_ledger',return_value={}),patch('scripts.run_relation_diagnostics.server_preflight') as server,patch('scripts.run_relation_diagnostics.subprocess.call') as child,patch('sys.argv',['launcher','--tokenizer-dir','unused','--execute']),patch('sys.stdout',new_callable=io.StringIO):
                with self.assertRaisesRegex(ValueError,'published commit'): launcher()
                server.assert_not_called(); child.assert_not_called()


class SummaryTests(unittest.TestCase):
    def test_registry_records_completed_learning_failure_without_invented_accuracy(self):
        from scripts.build_registry import build_registry
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); run=root/'unit_e011'; run.mkdir(); (root/'not_run').mkdir()
            (run/'resource_receipt.json').write_text(json.dumps({'status':'completed','charged_seconds':231}))
            (run/'run_manifest.json').write_text(json.dumps({'phase':'E011','source_commit':'unit_source','config':{}}))
            (run/'metrics.json').write_text(json.dumps({'steps':256,'engineering_gate':{'passed':False},'train':{'n':32,'complete_correct':0}}))
            report=build_registry(root); entry=report['runs'][0]
            self.assertEqual(len(report['runs']),1); self.assertEqual(report['charged_gpu_seconds'],231)
            self.assertEqual(entry['git_commit'],'unit_source'); self.assertFalse(entry['overfit_passed'])
            self.assertIsNone(entry['train_accuracy']); self.assertEqual(entry['relation_diagnostic']['train']['complete_correct'],0)

    def test_public_accounting_preserves_prefix_and_reconciles_all_receipts(self):
        from scripts.update_compute_accounting import reconcile
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            old={'run_id':'old','status':'completed','charged_seconds':5740}
            new={'run_id':'new','status':'completed','charged_seconds':231}
            for job in (old,new):
                run=root/job['run_id']; run.mkdir(); (run/'resource_receipt.json').write_text(json.dumps(job))
            (root/'new/run_manifest.json').write_text(json.dumps({'server':{'gpu':'NVIDIA A800 80GB, 81920, fixture'}}))
            previous={'budget_id':'unit','authorized_gpu_seconds':7200,'charged_gpu_seconds':5740,
                'hardware_charged_seconds':{'A800_80GB':5740},'jobs':[old]}
            ledger={'budget_id':'unit','authorized_gpu_seconds':7200,'jobs':[old,new]}
            result=reconcile(previous,ledger,root)
            self.assertEqual(result['charged_gpu_seconds'],5971); self.assertEqual(result['remaining_gpu_seconds'],1229)
            self.assertEqual(previous['jobs'],[old]); self.assertEqual(result['jobs'],[old,new])
            corrupt=copy.deepcopy(ledger); corrupt['jobs'][0]['charged_seconds']=1
            with self.assertRaises(ValueError): reconcile(previous,corrupt,root)


if __name__=='__main__': unittest.main()

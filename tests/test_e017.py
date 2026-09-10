import copy
from contextlib import nullcontext,redirect_stdout
from datetime import datetime,timedelta,timezone
import json
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import torch
from transformers import PretrainedConfig,PreTrainedModel,GenerationMixin,GenerationConfig,StoppingCriteriaList
from transformers.modeling_outputs import CausalLMOutputWithPast

from analyses import e017
from analyses.completion_contract import first_stop
from analyses.e017_stopping import TaskBoundaryStop,prediction,generate
from analyses.e017_audit import audit_predictions,decisions


class Tokenizer:
    eos_token_id=1000
    all_special_ids=[1000,1001]
    def __len__(self):return 1002
    def __call__(self,text,**kwargs):return {'input_ids':list(text.encode())}
    def decode(self,ids,skip_special_tokens=True,**kwargs):
        return ''.join(chr(x) if x<256 else '' if skip_special_tokens else f'<|special_{x}|>' for x in ids)


class ScriptedLM(PreTrainedModel,GenerationMixin):
    """Parameter-free scripted logits fixture; no pretrained model or learned forward."""
    config_class=PretrainedConfig
    def __init__(self,plans):
        super().__init__(PretrainedConfig(vocab_size=1002,is_decoder=True,num_hidden_layers=1,
                                         eos_token_id=1000,pad_token_id=1000))
        self.register_buffer('device_anchor',torch.zeros(1))
        self.plans=plans;self.calls=0;self.batch_sizes=[]
    @property
    def device(self):return self.device_anchor.device
    @property
    def dtype(self):return self.device_anchor.dtype
    def forward(self,input_ids,attention_mask=None,past_key_values=None,cache_position=None,**kwargs):
        self.batch_sizes.append(input_ids.shape[0])
        logits=torch.full((len(self.plans),1,1002),-1000.,device=input_ids.device)
        for i,plan in enumerate(self.plans):
            logits[i,0,plan[self.calls] if self.calls<len(plan) else 1000]=1000.
        self.calls+=1
        return CausalLMOutputWithPast(logits=logits)


def replay(plans,prompt='Problem: input\nSolution:\n',cap=100):
    tokenizer=Tokenizer();width=len(prompt)
    stopper=TaskBoundaryStop(tokenizer,width,len(plans),cap)
    model=ScriptedLM(plans)
    inputs=torch.tensor([list(prompt.encode())]*len(plans))
    with torch.inference_mode():
        output=model.generate(input_ids=inputs,attention_mask=torch.ones_like(inputs),
            generation_config=GenerationConfig(do_sample=False,num_beams=1,max_new_tokens=cap,
                    eos_token_id=1000,pad_token_id=1000,use_cache=True),
            stopping_criteria=StoppingCriteriaList([stopper]))
    return tokenizer,model,stopper,output[:,width:].tolist(),width


class RuntimeTests(unittest.TestCase):
    def test_production_writer_with_real_generation_loop_and_mixed_left_padding(self):
        tok=Tokenizer();plans=[list(b'Answer: 4\nQuestion: tail'),list(b'Answer: 7')+[1000]]
        rows=[{'problem_id':'a','prompt':'input','answer':'4'},
              {'problem_id':'b','prompt':'longer input','answer':'7'}]
        cfg={'max_new_tokens':100,'max_length':256,'eval_batch_size':2}
        original_tensor=torch.tensor
        def cpu_tensor(*args,**kwargs):
            if kwargs.get('device')=='cuda':kwargs['device']='cpu'
            return original_tensor(*args,**kwargs)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'raw.jsonl'
            with patch('torch.tensor',side_effect=cpu_tensor),patch('torch.autocast',return_value=nullcontext()),patch('torch.cuda.synchronize'):
                records=generate(ScriptedLM(plans),tok,rows,cfg,path)
                with self.assertRaises(FileExistsError):generate(ScriptedLM(plans),tok,rows,cfg,path)
            self.assertEqual(audit_predictions(path,rows,tok,cfg),records)
            self.assertEqual(records[0]['stop']['stop_reason'],'new_problem_boundary')
            self.assertEqual(records[1]['stop']['stop_reason'],'native_eos')

    def test_default_inspection_and_unarmed_launch_never_contact_server(self):
        cfg=json.loads(e017.CONFIG.read_text())
        for argv in (['e017','--tokenizer-dir','fixture'],['e017','launch','--tokenizer-dir','fixture']):
            with patch('sys.argv',argv),patch.object(e017,'verified_tokenizer',return_value=(Tokenizer(),{})),patch.object(e017,'load_release',return_value=(cfg,[])),patch.object(e017,'provenance',return_value={'source_commit':'fixture'}),patch.object(e017,'sha256_file',return_value='fixture'),patch.object(e017,'check_ledger',return_value={}),patch.object(e017,'server_preflight') as server,patch.object(e017.subprocess,'call') as launch,redirect_stdout(io.StringIO()):
                self.assertEqual(e017.main(),0)
                server.assert_not_called();launch.assert_not_called()

    def test_actual_generation_loop_keeps_mixed_batch_and_distinguishes_padding(self):
        plans=[list(b'Answer: 4\nProblem: should never run'),list(b'Answer: 7 and more words')+[1000]]
        tok,model,stopper,output,width=replay(plans)
        first=stopper.events[0]
        self.assertEqual(first['stop_reason'],'new_problem_boundary')
        self.assertFalse(first['actual_eos_at_stop'])
        self.assertEqual(first['retained_tokens'],len(b'Answer: 4\nProblem:'))
        self.assertEqual(first['answer_segment'],'Answer: 4\n')
        self.assertTrue(all(t==1000 for t in output[0][first['retained_tokens']:]))
        self.assertEqual(set(model.batch_sizes),{2})
        self.assertEqual(model.calls,max(e['retained_tokens'] for e in stopper.events))
        for ids,event in zip(output,stopper.events):
            self.assertEqual(first_stop(ids,lambda x:tok.decode(x),1000,100,tok.all_special_ids),event)

    def test_prompt_boundary_excluded_and_first_answer_not_a_stop(self):
        tok,_,stopper,_,_=replay([list(b'Answer: 4\nAnswer: 5')+[1000]])
        self.assertEqual(stopper.events[0]['stop_reason'],'native_eos')
        self.assertEqual(stopper.events[0]['answer_segment'],'Answer: 4\nAnswer: 5')

    def test_native_eos_before_other_rows_boundary(self):
        _,_,stopper,output,_=replay([[1000],list(b'Question: new')])
        self.assertEqual(stopper.events[0]['retained_tokens'],1)
        self.assertEqual(stopper.events[1]['stop_reason'],'new_problem_boundary')
        self.assertTrue(all(t==1000 for t in output[0]))

    def test_special_invalid_and_cap_do_not_become_success(self):
        tok=Tokenizer()
        for tokens,reason in [([65,1001],'invalid_special_token'),([65,1200],'invalid_special_token'),([65,66],'length_cap')]:
            stopper=TaskBoundaryStop(tok,1,1,2)
            for i in range(1,3):stopper(torch.tensor([[1]+tokens[:i]]),None)
            self.assertEqual(stopper.events[0]['stop_reason'],reason)
            row=prediction({'answer':'1'},tok,tokens,stopper.events[0],.1,0,1)
            self.assertFalse(row['task_score']['task_answer_correct'])

    def test_nonsequential_batch_and_wrong_padding_rejected(self):
        tok=Tokenizer();stopper=TaskBoundaryStop(tok,1,1,5)
        with self.assertRaises(ValueError):stopper(torch.tensor([[1,2,3]]),None)
        stopper=TaskBoundaryStop(tok,1,1,5);stopper(torch.tensor([[1,1000]]),None)
        with self.assertRaises(ValueError):stopper(torch.tensor([[1,1000,65]]),None)

    def test_registered_rental_admission_boundary(self):
        start=datetime(2026,9,10,tzinfo=timezone.utc)
        self.assertEqual(e017.rental_window(start.isoformat(),start+timedelta(seconds=345))['remaining_seconds'],555)
        for age in [-1,346,900]:
            with self.assertRaises(ValueError):e017.rental_window(start.isoformat(),start+timedelta(seconds=age))
        with self.assertRaises(ValueError):e017.rental_window('2026-09-10T00:00:00')


class AuditTests(unittest.TestCase):
    def fixtures(self):
        plans=[list(b'Answer: 4\nProblem: later'),list(b'Answer: 7')+[1000]]
        tok,_,stopper,outputs,width=replay(plans)
        rows=[{'problem_id':str(i),'prompt':'input','answer':str(v)} for i,v in enumerate([4,7])]
        records=[prediction(r,tok,ids,e,.1,0,width) for r,ids,e in zip(rows,outputs,stopper.events)]
        cfg={'eval_batch_size':2,'max_new_tokens':100,'max_length':256}
        return tok,rows,records,cfg

    def test_independent_audit_accepts_valid_mixed_outputs(self):
        tok,rows,records,cfg=self.fixtures()
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'records.jsonl';p.write_text(''.join(json.dumps(r)+'\n' for r in records))
            self.assertEqual(audit_predictions(p,rows,tok,cfg),records)
        self.assertFalse(records[0]['legacy_marked_prefix_score']['clean_correct'])
        self.assertTrue(records[0]['task_score']['task_answer_correct'])

    def test_tampered_stop_gold_tokens_padding_and_scores_rejected(self):
        tok,rows,original,cfg=self.fixtures()
        mutations=[lambda r:r[0]['stop'].update(actual_eos_at_stop=True),
          lambda r:r[0]['stop'].update(retained_tokens=1),lambda r:r[0].update(answer='99'),
          lambda r:r[0]['task_score'].update(task_answer_correct=False),
          lambda r:r[1]['batch_output_ids'].__setitem__(-1,65),
          lambda r:r[0].update(generated_tokens=1),lambda r:r[0].update(raw_text='different'),
          lambda r:r.pop()]
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'records.jsonl'
            for mutate in mutations:
                records=copy.deepcopy(original);mutate(records)
                p.write_text(''.join(json.dumps(r)+'\n' for r in records))
                with self.assertRaises(ValueError):audit_predictions(p,rows,tok,cfg)

    def test_full_run_audit_and_sidecar_tampering(self):
        tok,rows,records,cfg=self.fixtures()
        # Keep the registered denominator while reusing deterministic fixtures.
        rows=[{**rows[i%2],'problem_id':str(i)} for i in range(64)]
        records=[{**copy.deepcopy(records[i%2]),**row,'batch_index':i//2} for i,row in enumerate(rows)]
        cfg.update(run_id='fixture',usability_screen={'n':64,'minimum_parsed':48,'minimum_task_answer_correct':8,'maximum_actual_length_cap_stops':8})
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);release=root/'release';release.write_text('{}')
            inputs=root/'inputs';inputs.mkdir();(inputs/'manifest.json').write_text(json.dumps({'source_files_sha256':{}}))
            def put(name,obj):(root/name).write_text(json.dumps(obj))
            (root/'base.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in records))
            put('metrics.json',decisions(records,cfg))
            put('run_manifest.json',{'status':'completed','config':cfg,'release_sha256':e017.sha256_file(release),'source_files_sha256':{},'source_commit':'fixture',
                'phase':'E017','optimizer_updates':0,'checkpoint_write':False,'parameter_dtype':'float32',
                'autocast_dtype':'bfloat16','attention':'sdpa','tf32':False,'official_test_evaluation':False,
                'row_compaction':False,'boundary_is_native_eos':False})
            put('base_profile.json',{'n':64,'output_tokens':sum(r['generated_tokens'] for r in records),'padded_output_tokens':sum(r['batch_generated_steps'] for r in records),'generation_seconds':4,'peak_allocated_mib':1,'peak_reserved_mib':2})
            put('base_generation_config.json',{})
            put('phase_timings.json',{'completed_phases_seconds':{'base_generation':4}})
            put('resource_receipt.json',{'run_id':'fixture','status':'completed','exit_code':0,'charged_seconds':10})
            with patch.object(e017,'RELEASE',release),patch.object(e017,'INPUTS',inputs),patch.object(e017,'load_release',return_value=(cfg,rows)),patch.object(e017,'check_generation_settings'):
                self.assertEqual(e017.audit_run(tok,root,root/'audit.json')['raw_streams_checked'],64)
                put('metrics.json',{'passed':True})
                with self.assertRaises(ValueError):e017.audit_run(tok,root,root/'bad.json')

    def test_gate_requires_cap_format_and_full_denominator(self):
        _,_,records,_=self.fixtures();cfg=json.loads(e017.CONFIG.read_text())
        good=[copy.deepcopy(records[i%2]) for i in range(64)]
        self.assertTrue(decisions(good,cfg)['operational_usability_passed'])
        for r in good[:9]:r['stop']['stop_reason']='length_cap';r['stop']['actual_eos_at_stop']=False
        self.assertFalse(decisions(good,cfg)['operational_usability_passed'])
        with self.assertRaises(ValueError):decisions(good[:-1],cfg)


if __name__=='__main__':unittest.main()

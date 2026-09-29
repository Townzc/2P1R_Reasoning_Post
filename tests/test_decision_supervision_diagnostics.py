"""CPU-only durable forward and actual greedy-hook regression tests."""
import copy
import json
from pathlib import Path
import random
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
import torch
from transformers import GenerationConfig, Qwen2Config, Qwen2ForCausalLM, StoppingCriteriaList

from experiments.post_e039_decision_supervision import diagnostics as d
from experiments.post_e039_decision_supervision.decision_spans import annotate
from experiments.post_e037_goal_training.generation import capture_rng
from experiments.thursday_probe.lora import attach
from src.sft_data import encode_row, read_jsonl
from tests.test_decision_spans import CharacterTokenizer
from tests.test_thursday_v2_resumable_generation import Budget


class Tokenizer(CharacterTokenizer):
    eos_token_id=255


class PositionModel(torch.nn.Module):
    def __init__(self):
        super().__init__();self.dummy=torch.nn.Parameter(torch.zeros(1));self.calls=0
    def forward(self,input_ids,attention_mask,use_cache=False):
        self.calls+=1
        random.random();np.random.random();torch.rand(1)
        batch,width=input_ids.shape
        logits=torch.arange(256,dtype=torch.float32).view(1,1,256).repeat(batch,width,1)*.003
        for j in range(width):logits[:,j,(j*3+1)%256]+=1.
        return SimpleNamespace(logits=logits)


class RowStop:
    def __init__(self,batch,width,limit=3):self.events=[None]*batch;self.width=width;self.limit=limit
    def __call__(self,ids,scores,**kwargs):
        for i in range(len(ids)):
            if self.events[i] is None and (int(ids[i,-1])==9 or ids.shape[1]-self.width>=self.limit):
                self.events[i]={'step':ids.shape[1]-self.width}
        return torch.tensor([e is not None for e in self.events])


class ActualLoopModel(torch.nn.Module):
    """Exercise a real forward hook, ties, a processor and post-stop padding."""
    def __init__(self,bad=False):
        super().__init__();self.p=torch.nn.Parameter(torch.zeros(1));self.bad=bad;self.calls=0
    def forward(self,input_ids,attention_mask,use_cache=True,**kwargs):
        self.calls+=1;b,t=input_ids.shape;logits=torch.zeros(b,t,16)
        logits[:,-1,3:5]=2.
        if self.calls==1:logits[0,-1,9]=4.
        return SimpleNamespace(logits=logits)
    def generate(self,*,input_ids,attention_mask,generation_config,stopping_criteria,logits_processor=None):
        from transformers import LogitsProcessorList
        processors=LogitsProcessorList(logits_processor or []);output=input_ids.clone();stopper=stopping_criteria[0]
        for step in range(generation_config.max_new_tokens):
            scores=processors(output,self(input_ids=output,attention_mask=attention_mask,use_cache=True).logits[:,-1].float())
            next_tokens=scores.argmax(-1)
            for i,event in enumerate(stopper.events):
                if event is not None:next_tokens[i]=generation_config.pad_token_id
            if self.bad and step==0:next_tokens[0]=0
            output=torch.cat((output,next_tokens[:,None]),1)
            if bool(stopper(output,scores).all()):break
        return output


class FavorFour:
    def __call__(self,input_ids,scores):
        changed=scores.clone();changed[:,4]+=.5;return changed


class DiagnosticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)
        cls.tokenizer=Tokenizer()
        cls.row=read_jsonl('experiments/post_e037_goal_training/release_v1/single.jsonl')[0]
        cls.span=annotate(cls.row,cls.tokenizer)

    def test_full_token_causal_nll_masks_and_one_shared_candidate_forward(self):
        model=PositionModel()
        record=d.decomposition_record(model,self.tokenizer,self.row,self.span,'cpu')
        encoded=encode_row(self.row,self.tokenizer,1024)
        for index,value in zip(record['response_token_positions'],record['response_log_probabilities']):
            vector=torch.arange(256,dtype=torch.float32)*.003;vector[((index-1)*3+1)%256]+=1.
            self.assertEqual(value,vector.log_softmax(-1)[encoded['input_ids'][index]].item())
        self.assertEqual(record['causal_logit_positions'],[x-1 for x in record['response_token_positions']])
        self.assertEqual(record['response_ids'][-1],255)
        self.assertFalse(record['response_masks']['decision_mask'][-1])
        self.assertEqual(record['partitions']['decision_mask']['tokens'],1)
        self.assertAlmostEqual(record['partitions']['full']['nll_sum'],
            record['partitions']['decision_mask']['nll_sum']+record['partitions']['rest']['nll_sum'])
        context=dict(self.span,problem_id=self.row['problem_id'])
        result=d.candidate_record(model,context,'cpu')
        self.assertEqual((result['forward_calls'],result['sequence_equivalents']),(1,1))
        self.assertEqual(model.calls,2)
        self.assertAlmostEqual(sum(r['normalized_probability'] for r in result['candidates']),1.)
        multi=dict(context,candidates={op:{'token_ids':[ord(op),1]} for op in '+-*/'})
        self.assertEqual(d.candidate_record(model,multi,'cpu')['forward_calls'],4)
        multi['candidates']['-']['token_ids']=[ord('+'),1,2]
        with self.assertRaisesRegex(ValueError,'prefix-free'):d.candidate_record(model,multi,'cpu')

    def test_durable_forward_identity_resume_rng_protection_and_ambiguous_intent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);path=root/'forward.json';budget=Budget(root/'budget.json');model=PositionModel()
            random.seed(91);np.random.seed(19);torch.manual_seed(919);before=capture_rng()
            args=(model,self.tokenizer,[self.row],[self.span],path)
            kw=dict(identity={'adapter':'fixture'},forward_budget=budget,deadline=time.time()+300,device='cpu')
            first=d.run_decomposition(*args,**kw)
            self.assertEqual(first['status'],'completed');self.assertTrue(model.training)
            self.assertEqual(capture_rng(),before);self.assertEqual(model.calls,1)
            second=d.run_decomposition(*args,**kw)
            self.assertEqual(second,first);self.assertEqual((model.calls,budget.reserve_calls),(1,1))
            pending=root/'pending.json';old=d._atomic
            kw=dict(kw,identity={'adapter':'independent_fixture'})
            def fail_after_charge(p,value,**kwargs):
                if Path(p).name=='000000.json':raise RuntimeError('interrupted after forward')
                return old(p,value,**kwargs)
            with patch.object(d,'_atomic',side_effect=fail_after_charge),self.assertRaisesRegex(RuntimeError,'interrupted'):
                d.run_decomposition(model,self.tokenizer,[self.row],[self.span],pending,**kw)
            calls=model.calls;charged=budget.record()['used']
            with self.assertRaisesRegex(d.DiagnosticConsistencyError,'Ambiguous'):
                d.run_decomposition(model,self.tokenizer,[self.row],[self.span],pending,**kw)
            self.assertEqual((model.calls,budget.record()['used']),(calls,charged))

    def cases(self):
        return [dict(problem_id='a',source_row_sha256='a'*64,prompt_ids=[1,2],
                     reference_response_ids=[9],decision_response_positions=[0]),
                dict(problem_id='b',source_row_sha256='b'*64,prompt_ids=[3],
                     reference_response_ids=[4,4,4],decision_response_positions=[1])]

    def generate(self,model,processors=None):
        inputs=torch.tensor([[1,2],[0,3]]);masks=torch.tensor([[1,1],[0,1]])
        config=GenerationConfig(do_sample=False,num_beams=1,max_new_tokens=3,pad_token_id=9,eos_token_id=9,use_cache=True)
        return model.generate(input_ids=inputs,attention_mask=masks,generation_config=config,
            stopping_criteria=StoppingCriteriaList([RowStop(2,2)]),logits_processor=processors)

    def test_passive_observer_exact_greedy_processor_ties_and_finished_padding(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'alignment/nested/result.json';cases=self.cases();model=ActualLoopModel().eval()
            expected=self.generate(ActualLoopModel().eval(),[FavorFour()])
            with d.observe_greedy_alignment(model,None,cases,path,identity={'model':'fixture'}):
                actual=self.generate(model,[FavorFour()])
            self.assertTrue(torch.equal(actual,expected));self.assertEqual(model.calls,3)
            summary=json.loads(path.read_text());self.assertEqual(summary['status'],'passed')
            self.assertEqual(summary['genuine_mismatches'],0)
            self.assertEqual(summary['extra_forward_calls'],0)
            raw=json.loads(next(path.with_suffix('.observations').glob('*.json')).read_text())
            # Row0 finished afterEOS, while its later raw argmax differs from padding9.
            self.assertEqual([r['step'] for r in raw['selection_checks'] if r['batch_row']==0],[0])
            r=next(r for r in raw['observations'] if r['batch_row']==1)
            self.assertEqual(r['raw_argmax_tokens'],[3,4]);self.assertEqual(r['effective_argmax'],4)
            bits=torch.tensor(r['effective_logits_fp32_bits'],dtype=torch.int32).view(torch.float32)
            self.assertEqual(int(bits.argmax()),r['generated_token'])
            with d.observe_greedy_alignment(model,None,cases,path,identity={'model':'fixture'}):pass
            self.assertEqual(json.loads(path.read_text())['status'],'passed');self.assertEqual(model.calls,3)
            with self.assertRaisesRegex(d.DiagnosticConsistencyError,'identity changed'):
                with d.observe_greedy_alignment(model,None,cases,path,identity={'model':'other'}):pass

    def test_genuine_effective_argmax_mismatch_is_durable_hard_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'alignment.json';model=ActualLoopModel(bad=True).eval()
            with self.assertRaisesRegex(d.DiagnosticConsistencyError,'training must stop'):
                with d.observe_greedy_alignment(model,None,self.cases(),path,identity={'model':'fixture'}):self.generate(model)
            saved=json.loads(path.read_text());self.assertEqual(saved['status'],'hard_failure')
            self.assertGreater(saved['genuine_mismatches'],0)
            self.assertEqual(len(list(path.with_suffix('.observations').glob('*.json'))),1)

    def test_partial_alignment_coverage_resume_and_exact_reference_end_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'alignment.json';cases=self.cases()
            cases[0]['decision_response_positions']=[]  # Exact F-like reference9 has no literal deviation.
            model=ActualLoopModel().eval()
            def one(prompt):
                inputs=torch.tensor([prompt]);width=len(prompt)
                return model.generate(input_ids=inputs,attention_mask=torch.ones_like(inputs),
                    generation_config=GenerationConfig(do_sample=False,num_beams=1,max_new_tokens=3,
                        pad_token_id=9,eos_token_id=9,use_cache=True),
                    stopping_criteria=StoppingCriteriaList([RowStop(1,width)]))
            with d.observe_greedy_alignment(model,None,cases,path,identity={'model':'fixture'}):one([1,2])
            self.assertEqual(json.loads(path.read_text())['status'],'incomplete')
            record=json.loads(next(path.with_suffix('.observations').glob('*.json')).read_text())
            self.assertEqual(len(record['observations']),1)
            self.assertTrue(record['observations'][0]['fully_matched_reference_end'])
            with d.observe_greedy_alignment(model,None,cases,path,identity={'model':'fixture'}):one([3])
            summary=json.loads(path.read_text());self.assertEqual(summary['status'],'passed')
            self.assertEqual(summary['batches'],2)

    def test_real_tiny_peft_generate_hook_uses_actual_underlying_emitter(self):
        torch.manual_seed(71)
        model=attach(Qwen2ForCausalLM(Qwen2Config(vocab_size=16,hidden_size=16,intermediate_size=32,
            num_hidden_layers=1,num_attention_heads=2,num_key_value_heads=1,
            max_position_embeddings=32,attention_dropout=0))).eval()
        # No pretrained model, logits, or actual task inference is loaded.
        expected=self.generate(copy.deepcopy(model))
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'align.json';before=capture_rng()
            with d.observe_greedy_alignment(model,None,self.cases(),path,identity={'model':'tiny_random'}):
                actual=self.generate(model)
            self.assertTrue(torch.equal(actual,expected));self.assertEqual(capture_rng(),before)
            summary=json.loads(path.read_text());self.assertEqual(summary['status'],'passed')
            raw=json.loads(next(path.with_suffix('.observations').glob('*.json')).read_text())
            self.assertTrue(raw['observations']);self.assertTrue(all(r['forward']['use_cache'] for r in raw['observations']))


if __name__=='__main__':unittest.main()

"""CPU causal-token, gradient, optimizer and exact-recovery contracts."""
import copy
import json
from pathlib import Path
import random
import tempfile
import time
import unittest
from unittest.mock import patch

import numpy as np
import torch

from experiments.post_e039_decision_supervision import runtime as rt
from experiments.post_e039_decision_supervision.decision_spans import annotate
from experiments.post_e037_goal_training import training as prior
from src.sft_data import collate, shifted_loss_sum, read_jsonl
import tests.test_thursday_v2_resumable_training as training_fixture
from tests.test_decision_spans import CharacterTokenizer


class DecisionRuntimeTests(unittest.TestCase):
    def setUp(self):
        fixture=training_fixture.ResumableTrainingTests();fixture.setUp()
        for name in ('model','rows','schedule','lrs','tokenizer','identity'):
            setattr(self,name,getattr(fixture,name))
        self.rows[0].update(interface='H',decision_mask=[False,False,True,False,False])
        self.rows[1].update(interface='F',decision_mask=[False]*4)

    def run_segment(self,model,path,objective='D',end=4):
        return rt.train_segment(model,self.rows,self.schedule,self.lrs,self.tokenizer,path,
            identity=self.identity,objective=objective,end_step=end,deadline=time.time()+300,device='cpu')

    def state(self,path):
        pointer=json.loads((path/'recovery/latest.json').read_text())
        return torch.load(path/'recovery'/pointer['file'],map_location='cpu',weights_only=True)

    def test_actual_serialization_mask_and_per_row_mass(self):
        tokenizer=CharacterTokenizer()
        original=read_jsonl('experiments/post_e037_goal_training/release_v1/single.jsonl')
        rows=[original[0],original[512]];spans=[annotate(r,tokenizer) for r in rows]
        encoded=rt.prepare_encoded(rows,spans,tokenizer)
        for row in encoded:
            for objective in ('U','D'):
                weights=rt.row_weights(row,objective)
                self.assertAlmostEqual(sum(weights),row['n_supervised'],places=10)
                self.assertTrue(all(w==0 for w in weights[:row['n_prompt']]))
                self.assertFalse(row['decision_mask'][-1])
                self.assertGreater(weights[-1],0)  # EOS remains supervised.
                if row['interface']=='F' or objective=='U':
                    self.assertTrue(all(w==1 for w in weights[row['n_prompt']:]))
                else:
                    selected=next(i for i,m in enumerate(row['decision_mask']) if m)
                    self.assertAlmostEqual(weights[selected]/weights[-1],5.)
        broken=copy.deepcopy(spans);broken[0]['causal_logit_indices']=broken[0]['decision_token_indices']
        with self.assertRaises(ValueError):rt.prepare_encoded(rows,broken,tokenizer)
        broken=copy.deepcopy(spans);broken[0]['decision_mask'][-1]=True
        with self.assertRaises(ValueError):rt.prepare_encoded(rows,broken,tokenizer)

    def test_real_causal_shift_no_prompt_or_padding_loss_and_lambda_one_equivalence(self):
        batch=collate(self.rows,0)
        logits=torch.randn(2,5,32,requires_grad=True)
        weights=torch.tensor([rt.row_weights(r,'D')+[0.]*(5-len(r['labels'])) for r in self.rows])
        loss,raw=rt.loss_sums(logits,batch['labels'],weights)
        expected=0.
        for i,row in enumerate(self.rows):
            for j,label in enumerate(row['labels']):
                if j>0 and label!=-100:
                    expected=expected-logits[i,j-1].float().log_softmax(-1)[label]*weights[i,j]
        self.assertTrue(torch.allclose(loss,expected,atol=3e-6,rtol=0))
        self.assertTrue(torch.equal(raw,shifted_loss_sum(logits,batch['labels'])))
        loss.backward();grad=logits.grad
        self.assertTrue(torch.equal(grad[:,0],torch.zeros_like(grad[:,0])))
        self.assertTrue(torch.equal(grad[0,4],torch.zeros_like(grad[0,4])))
        self.assertTrue(torch.equal(grad[1,3:],torch.zeros_like(grad[1,3:])))
        self.assertGreater(float(grad[0,1].abs().sum()),0.)  # predicts selected token at index2
        unit=torch.tensor([rt.row_weights(r,'U')+[0.]*(5-len(r['labels'])) for r in self.rows])
        weighted,unweighted=rt.loss_sums(logits,batch['labels'],unit)
        self.assertIs(weighted,unweighted)
        self.assertTrue(torch.equal(weighted,shifted_loss_sum(logits,batch['labels'])))

    def test_microbatch_denominator_matches_whole_batch_gradients(self):
        a=copy.deepcopy(self.model);b=copy.deepcopy(self.model);a.eval();b.eval()
        metrics=rt.accumulate_gradients(a,self.rows,0,1,'cpu',objective='D')
        batch=collate(self.rows,0)
        weights=torch.tensor([rt.row_weights(r,'D')+[0.]*(5-len(r['labels'])) for r in self.rows])
        loss,raw=rt.loss_sums(b(**batch_without_labels(batch),use_cache=False).logits,batch['labels'],weights)
        (loss/5).backward()
        self.assertEqual(metrics['raw_supervised_denominator'],5)
        self.assertAlmostEqual(metrics['objective_loss'],float(loss.detach())/5,places=6)
        for pa,pb in zip(a.parameters(),b.parameters()):
            if pa.requires_grad:self.assertTrue(torch.allclose(pa.grad,pb.grad,atol=2e-7,rtol=2e-5))

    def test_U_is_previous_ordinary_ce_update_and_D_exact_recovery(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);a=copy.deepcopy(self.model);b=copy.deepcopy(self.model)
            ordinary=self.run_segment(a,root/'U','U')
            old=prior.train_segment(b,self.rows,self.schedule,self.lrs,self.tokenizer,root/'old',
                identity=self.identity,end_step=4,deadline=time.time()+300,device='cpu')
            self.assertEqual(ordinary['final_adapter'],old['final_adapter'])
            self.assertTrue(prior._same_tree(self.state(root/'U')['optimizer'],self.state(root/'old')['optimizer']))
            expected=self.run_segment(copy.deepcopy(self.model),root/'D')
            self.run_segment(copy.deepcopy(self.model),root/'split',end=2)
            random.seed(94);np.random.seed(57);torch.manual_seed(991)
            actual=self.run_segment(copy.deepcopy(self.model),root/'split')
            self.assertEqual(expected['final_adapter'],actual['final_adapter'])
            for key in ('adapter','optimizer','rng'):
                self.assertTrue(prior._same_tree(self.state(root/'D')[key],self.state(root/'split')[key]))
            # U and D consume identical dropout/random schedules, not identical gradients.
            self.assertTrue(prior._same_tree(self.state(root/'U')['rng'],self.state(root/'D')['rng']))
            self.assertNotEqual(ordinary['final_adapter'],expected['final_adapter'])
            self.run_segment(copy.deepcopy(self.model),root/'new_arm',end=1)
            self.assertTrue(all(float(v['step'])==1 for v in self.state(root/'new_arm')['optimizer']['state'].values()))
            again=self.run_segment(copy.deepcopy(self.model),root/'split')
            self.assertEqual(again['segment_updates'],0)
            with self.assertRaisesRegex(ValueError,'identity changed'):
                self.run_segment(copy.deepcopy(self.model),root/'split','U')

    def test_crash_preserves_uncommitted_dose_without_silent_resume_recount(self):
        calls=0;original=rt.accumulate_gradients
        def fail(*args,**kw):
            nonlocal calls
            calls+=1
            if calls==2:raise RuntimeError('injected second update')
            return original(*args,**kw)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            with patch.object(rt,'accumulate_gradients',side_effect=fail),self.assertRaisesRegex(RuntimeError,'injected'):
                self.run_segment(copy.deepcopy(self.model),root/'failed')
            self.assertEqual(self.state(root/'failed')['step'],0)
            actual=self.run_segment(copy.deepcopy(self.model),root/'failed')
            expected=self.run_segment(copy.deepcopy(self.model),root/'full')
            self.assertEqual(actual['final_adapter'],expected['final_adapter'])
            self.assertEqual([r['step'] for r in actual['discarded_uncommitted_history']],[1])
            self.assertEqual(sum(r['supervised_tokens'] for r in actual['cumulative_history']),20)


def batch_without_labels(batch):return {k:v for k,v in batch.items() if k!='labels'}


if __name__=='__main__':unittest.main()

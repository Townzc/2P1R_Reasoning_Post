import copy
import json
from pathlib import Path
import random
import tempfile
import types
import unittest
import numpy as np
import torch
from experiments.sft_allocation_midpoint import checkpoint as ck
from experiments.sft_allocation_midpoint.runtime import gradients,lrs
from src.sft_data import collate,shifted_loss_sum


class CompleteStateTests(unittest.TestCase):
    def setUp(self):
        torch.manual_seed(3);random.seed(3);np.random.seed(3)
        self.model=torch.nn.Linear(3,2)
        self.opt=torch.optim.AdamW(self.model.parameters(),lr=.01)
    def update(self):
        self.opt.zero_grad(set_to_none=True)
        loss=self.model(torch.randn(4,3)).square().mean();loss.backward();self.opt.step()
        random.random();np.random.random()
        return loss.item()
    def test_complete_roundtrip_and_next_update(self):
        self.update();state=ck.snapshot(self.model,self.opt,{'run':'test'},1,10,20,[.01,.01],[[0],[1]])
        with tempfile.TemporaryDirectory() as tmp:
            ck.save(tmp,state);saved=ck.load(Path(tmp)/'checkpoint_0001',{'run':'test'})
            expected_loss=self.update();expected=ck.snapshot(self.model,self.opt,{'run':'test'},2,20,40,[.01,.01],[[0],[1]])
            other=torch.nn.Linear(3,2);otheropt=torch.optim.AdamW(other.parameters(),lr=.5)
            ck.restore(other,otheropt,saved);self.model=other;self.opt=otheropt
            actual_loss=self.update();actual=ck.snapshot(other,otheropt,{'run':'test'},2,20,40,[.01,.01],[[0],[1]])
            self.assertEqual(actual_loss,expected_loss);self.assertTrue(ck.same(actual,expected))
    def test_no_overwrite_and_corruption_refused(self):
        state=ck.snapshot(self.model,self.opt,{'run':'test'},0,0,0,[.1],[[0]])
        with tempfile.TemporaryDirectory() as tmp:
            ck.save(tmp,state)
            with self.assertRaises(FileExistsError):ck.save(tmp,state)
            with self.assertRaises(ValueError):ck.load(Path(tmp)/'checkpoint_0000',{'run':'foreign'})
            with (Path(tmp)/'checkpoint_0000/state.pt').open('ab') as f:f.write(b'corruption')
            with self.assertRaises(ValueError):ck.load(Path(tmp)/'checkpoint_0000')
    def test_restore_rejects_parameter_schema(self):
        state=ck.snapshot(self.model,self.opt,{},0,0,0,[.1],[[0]])
        state['trainable_names'].reverse()
        with self.assertRaises(ValueError):ck.restore(self.model,self.opt,state)


class LossTests(unittest.TestCase):
    def test_whole_update_token_normalization(self):
        class Tiny(torch.nn.Module):
            def __init__(self):
                super().__init__();self.e=torch.nn.Embedding(12,4);self.l=torch.nn.Linear(4,12)
            def forward(self,input_ids,attention_mask,use_cache=False):return types.SimpleNamespace(logits=self.l(self.e(input_ids)))
        torch.manual_seed(1);a=Tiny();b=copy.deepcopy(a)
        rows=[dict(input_ids=[1,2,3],labels=[-100,-100,3],n_supervised=1),
              dict(input_ids=[4,5,6,7],labels=[-100,5,6,7],n_supervised=3)]
        value=gradients(a,rows,types.SimpleNamespace(pad_token_id=0),'cpu')
        batch=collate(rows,0);ref=shifted_loss_sum(b(**{k:v for k,v in batch.items() if k!='labels'}).logits,batch['labels'])/4
        ref.backward();self.assertAlmostEqual(value,ref.item(),places=6)
        for x,y in zip(a.parameters(),b.parameters()):self.assertTrue(torch.allclose(x.grad,y.grad,atol=1e-7,rtol=1e-6))
    def test_frozen_lr_endpoints(self):
        vector=lrs();self.assertEqual(len(vector),256);self.assertAlmostEqual(vector[15],1e-4)
        self.assertAlmostEqual(vector[-1],1e-5);self.assertTrue(all(v>0 for v in vector))


if __name__=='__main__':unittest.main()

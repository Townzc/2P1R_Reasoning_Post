"""New scoring integration and candidate-token accounting under CPU-only models."""
from contextlib import ExitStack, nullcontext
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace
import torch

from experiments.post_e036_goal_probe import generation as rg
from experiments.post_e036_goal_probe.operator_forward import score_candidates, probabilities
from experiments.post_e036_goal_probe.launcher import GenerationBudget
from tests.test_thursday_v2_resumable_generation import Tokenizer, Model


class RuntimeTests(unittest.TestCase):
    def cpu(self):
        stack=ExitStack();tensor=torch.tensor
        def cpu_tensor(*a,**kw):
            if kw.get('device')=='cuda':kw['device']='cpu'
            return tensor(*a,**kw)
        stack.enter_context(patch.object(torch,'tensor',cpu_tensor))
        stack.enter_context(patch.object(torch,'autocast',lambda *a,**kw:nullcontext()))
        for name in ('synchronize','reset_peak_memory_stats'):
            stack.enter_context(patch.object(torch.cuda,name,lambda:None))
        for name in ('max_memory_allocated','max_memory_reserved'):
            stack.enter_context(patch.object(torch.cuda,name,lambda:0))
        stack.enter_context(patch.object(torch.cuda,'is_available',return_value=False))
        return stack

    def test_interrupted_stream_replays_identically_without_recharging(self):
        rows=[dict(problem_id=f'q{i}',prompt='Compute 1+1.',task='compute',answer='2',
                   numbers=[1,1],target=2,interface='C',group_id=f'g{i}',target_index=0) for i in range(5)]
        event=dict(name='C-S_C_sampled_fixture',questions=5,samples=4,sampling=True,generations=20)
        identity=dict(model_hash='a'*64,split_hash='b'*64,batch_time_reserve_seconds=120.)
        with tempfile.TemporaryDirectory() as tmp,self.cpu():
            root=Path(tmp);a=root/'a';b=root/'b';a.mkdir();b.mkdir()
            first=GenerationBudget(a/'budget.json');full=GenerationBudget(b/'budget.json')
            import random,numpy as np
            random.seed(7);np.random.seed(7);torch.manual_seed(7)
            initial=rg.capture_rng()
            expected=rg.run_batches(Model(),Tokenizer(),rows,b/'rows.jsonl',event,identity,99,full,float('1e20'))
            rg.restore_rng(initial)
            part=rg.run_batches(Model(),Tokenizer(),rows,a/'rows.jsonl',event,identity,1,first,float('1e20'))
            self.assertEqual(part['completed_records'],8)
            m=Model()
            final=rg.run_batches(m,Tokenizer(),rows,a/'rows.jsonl',event,identity,99,first,float('1e20'))
            for x,y in zip(expected['records'],final['records']):
                x.pop('batch_seconds');y.pop('batch_seconds');self.assertEqual(x,y)
            self.assertEqual((m.calls,first.used),(2,20))
            self.assertTrue(all(r['interface']=='C' for r in final['records']))

    def test_candidate_chain_includes_only_operator_tokens(self):
        class Fixed:
            def __init__(self):self.inputs=[]
            def __call__(self,input_ids,**kw):
                self.inputs.append(input_ids.tolist()[0])
                return SimpleNamespace(logits=torch.arange(7,dtype=torch.float32).repeat(1,input_ids.shape[1],1))
        with self.cpu():
            context=[1,2,3];single={o:[i] for i,o in enumerate('+-*/')};m=Fixed()
            r=score_candidates(m,context,single)
            self.assertEqual((r['forward_calls'],r['input_tokens']), (1,3))
            lp=torch.arange(7,dtype=torch.float32).log_softmax(0)
            self.assertEqual(r['log_probabilities'],[lp[i].item() for i in range(4)])
            chain={'+':[0,4],'-':[1],'*':[2],'/':[3]};m=Fixed();r=score_candidates(m,context,chain)
            self.assertEqual(m.inputs,[[1,2,3,0],[1,2,3],[1,2,3],[1,2,3]])
            self.assertEqual(r['log_probabilities'][0],lp[0].item()+lp[4].item())
            self.assertEqual((r['forward_calls'],r['input_tokens'],r['candidate_tokens']),(4,13,5))
            mass,norm=probabilities(r['log_probabilities'])
            self.assertAlmostEqual(sum(norm),1);self.assertAlmostEqual(mass,sum(math.exp(x) for x in r['log_probabilities']))

if __name__=='__main__':unittest.main()

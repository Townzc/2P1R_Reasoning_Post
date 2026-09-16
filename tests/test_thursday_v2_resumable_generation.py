"""CPU fake sampling, durable interruption and real Python/NumPy/torch RNG checks."""
from contextlib import ExitStack, nullcontext
import itertools
import json
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import torch

from experiments.thursday_probe_v2.generation import generate as uninterrupted_generate
from experiments.thursday_probe_v2 import resumable_generation as rg


class Tokenizer:
    eos_token_id=0
    all_special_ids=[0,9]
    def __len__(self):return 10
    def encode(self,text,add_special_tokens=False):return [5]*(1+len(text)%3)
    def decode(self,ids,**kwargs):
        return ''.join({1:'Answer: 2',2:'Answer: 3',3:'\nProblem:',4:'z',5:'p'}.get(t,'') for t in ids)


class Model:
    def __init__(self):self.training=True;self.calls=0
    def train(self,mode=True):self.training=mode;return self
    def eval(self):return self.train(False)
    def generate(self,input_ids,attention_mask,generation_config,stopping_criteria):
        self.calls+=1
        # Exercise all three CPU RNG domains; no model parameters are involved.
        offset=random.randrange(1000)+int(np.random.randint(1000))
        choices=(torch.randint(0,6,(len(input_ids),))+offset)%6
        streams=([1,0],[2,0],[1,9],[1,10],[1,3],[4]*generation_config.max_new_tokens)
        selected=[streams[int(choice)] for choice in choices];stopper=stopping_criteria[0]
        output=input_ids.clone()
        for step in range(generation_config.max_new_tokens):
            tokens=[0 if stopper.events[i] is not None else stream[step] for i,stream in enumerate(selected)]
            output=torch.cat((output,torch.tensor(tokens).unsqueeze(1)),dim=1)
            if bool(stopper(output,None).all()):break
        return output


class Budget:
    def __init__(self,path):
        self.path=Path(path);self.reserve_calls=0
        if not self.path.exists():self.path.write_text(json.dumps({'used':592,'events':[]}))
    def record(self):return json.loads(self.path.read_text())
    def reserve(self,name,n):
        self.reserve_calls+=1;record=self.record()
        if any(e['name']==name for e in record['events']):raise ValueError('Duplicate reserve')
        if record['used']+n>4864:raise ValueError('Cap exceeded')
        record['used']+=n;record['events'].append({'name':name,'reserved':n,'at_utc':'fixture'})
        self.path.write_text(json.dumps(record))


class ResumableGenerationTests(unittest.TestCase):
    def setUp(self):
        self.rows=[dict(problem_id=f'q{i}',prompt='Compute 1+1.'+' '*i,
            task='compute',category='atomic',numbers=[1,1],answer='2') for i in range(5)]
        self.event=dict(name='C_probes',state='C',view='probes',questions=5,samples=4,sampling=True,generations=20)
        self.identity=dict(model_hash='a'*64,split_hash='b'*64,batch_time_reserve_seconds=120.,exit_reserve_seconds=30.)

    def cpu(self):
        context=ExitStack();tensor=torch.tensor
        def cpu_tensor(*args,**kwargs):
            if kwargs.get('device')=='cuda':kwargs['device']='cpu'
            return tensor(*args,**kwargs)
        context.enter_context(patch.object(torch,'tensor',cpu_tensor))
        context.enter_context(patch.object(torch,'autocast',lambda *a,**kw:nullcontext()))
        context.enter_context(patch.object(torch.cuda,'synchronize',lambda:None))
        context.enter_context(patch.object(torch.cuda,'is_available',return_value=False))
        context.enter_context(patch.object(torch.cuda,'manual_seed_all',lambda seed:None))
        context.enter_context(patch('time.monotonic',side_effect=itertools.count().__next__))
        context.enter_context(patch('time.time',return_value=1000.))
        return context

    def seed(self,n=400):
        random.seed(n+1);np.random.seed(n+2);torch.manual_seed(n+3)

    def run_eval(self,model,path,budget,limit=99,deadline=2000.,identity=None):
        return rg.run_batches(model,Tokenizer(),self.rows,path,self.event,
            identity or self.identity,limit,budget,deadline)

    def test_uninterrupted_and_new_process_resume_match_frozen_records(self):
        with tempfile.TemporaryDirectory() as directory,self.cpu():
            root=Path(directory);old=root/'old';full=root/'full';split=root/'split'
            for folder in (old,full,split):folder.mkdir()
            self.seed();old_model=Model()
            reference=uninterrupted_generate(old_model,Tokenizer(),self.rows,old/'predictions.jsonl',Budget(old/'ledger.json'),samples=4,sampling=True)
            self.seed();full_model=Model();full_budget=Budget(full/'ledger.json');training_rng=rg.capture_rng()
            complete=self.run_eval(full_model,full/'predictions.jsonl',full_budget)
            self.assertEqual(reference,complete['records']);self.assertEqual(complete['status'],'completed')
            self.assertEqual(rg.capture_rng(),training_rng);self.assertTrue(full_model.training)
            self.seed();first_model=Model();first_budget=Budget(split/'ledger.json');training_rng=rg.capture_rng()
            first=self.run_eval(first_model,split/'predictions.jsonl',first_budget,limit=1)
            self.assertEqual((first['status'],first['new_batches'],len(first['records'])),('partial',1,8))
            self.assertEqual(rg.capture_rng(),training_rng);self.assertTrue(first_model.training)
            # Simulate unrelated training plus a new process/model/budget object.
            self.seed(900);second_model=Model();second_budget=Budget(split/'ledger.json');training_rng=rg.capture_rng()
            resumed=self.run_eval(second_model,split/'predictions.jsonl',second_budget)
            self.assertEqual(resumed['records'],reference)
            self.assertEqual(resumed['request_ids'],complete['request_ids'])
            self.assertEqual((first_model.calls,second_model.calls),(1,2))
            self.assertEqual((len(second_budget.record()['events']),second_budget.record()['used']),(3,612))
            self.assertEqual(second_budget.reserve_calls,2)
            self.assertEqual(rg.capture_rng(),training_rng);self.assertTrue(second_model.training)
            again=self.run_eval(second_model,split/'predictions.jsonl',second_budget,limit=0)
            self.assertEqual(again['records'],reference);self.assertEqual(again['new_batches'],0)
            self.assertEqual(second_budget.reserve_calls,2)
            for timing in resumed['batch_timings']:
                self.assertIsNone(timing['prefill_seconds']);self.assertTrue(timing['generation_seconds_includes_prefill'])
                self.assertGreater(timing['input_nonpadding_tokens'],0)
                self.assertGreaterEqual(timing['generated_tokens_with_padding'],timing['retained_generated_tokens'])

    def test_crash_immediately_after_raw_commit_replays_score_without_generation(self):
        with tempfile.TemporaryDirectory() as directory,self.cpu():
            root=Path(directory);path=root/'predictions.jsonl';budget=Budget(root/'ledger.json')
            self.seed();model=Model();training_rng=rg.capture_rng();atomic=rg._atomic
            def fail_after_raw(p,*args,**kwargs):
                atomic(p,*args,**kwargs)
                if str(p).endswith('.raw.json'):raise RuntimeError('injected crash after durable raw')
            with patch.object(rg,'_atomic',side_effect=fail_after_raw),self.assertRaisesRegex(RuntimeError,'injected'):
                self.run_eval(model,path,budget)
            self.assertEqual(model.calls,1);self.assertEqual(rg.capture_rng(),training_rng);self.assertTrue(model.training)
            raw=rg._read(path.with_suffix('.resume')/'batches/000000.raw.json')
            self.assertIn('rng_before',raw);self.assertIn('rng_after',raw)
            self.seed(700);resumed_model=Model();resumed_budget=Budget(root/'ledger.json')
            replayed=self.run_eval(resumed_model,path,resumed_budget,limit=0)
            self.assertEqual((resumed_model.calls,resumed_budget.reserve_calls),(0,0))
            self.assertEqual((len(replayed['records']),replayed['replayed_scoring_batches']),(8,1))
            self.assertIsNone(replayed['batch_timings'][0]['raw_save_seconds'])
            result=self.run_eval(resumed_model,path,resumed_budget)
            other=root/'reference';other.mkdir();self.seed()
            reference=uninterrupted_generate(Model(),Tokenizer(),self.rows,other/'predictions.jsonl',Budget(other/'ledger.json'),samples=4,sampling=True)
            self.assertEqual(result['records'],reference)
            self.assertEqual((len(resumed_budget.record()['events']),resumed_budget.record()['used']),(3,612))

    def test_committed_reservation_without_raw_is_not_regenerated(self):
        with tempfile.TemporaryDirectory() as directory,self.cpu():
            root=Path(directory);path=root/'predictions.jsonl';budget=Budget(root/'ledger.json');reserve=budget.reserve
            def charge_then_crash(name,n):reserve(name,n);raise RuntimeError('after budget commit')
            with patch.object(budget,'reserve',side_effect=charge_then_crash),self.assertRaisesRegex(RuntimeError,'after budget'):
                self.run_eval(Model(),path,budget)
            resumed=Budget(root/'ledger.json');model=Model()
            with self.assertRaisesRegex(RuntimeError,'Ambiguous interrupted batch'):self.run_eval(model,path,resumed)
            self.assertEqual((model.calls,resumed.reserve_calls),(0,0))
            self.assertTrue((path.with_suffix('.resume')/'batches/000000.reserved.json').exists())
            self.assertEqual(resumed.record()['used'],600)

    def test_unit_time_admission_and_changed_identity_do_not_generate(self):
        with tempfile.TemporaryDirectory() as directory,self.cpu():
            root=Path(directory);path=root/'predictions.jsonl';budget=Budget(root/'ledger.json');model=Model()
            training_rng=rg.capture_rng();result=self.run_eval(model,path,budget,deadline=1149.)
            self.assertEqual(result['reason'],'insufficient_time_for_next_batch_and_exit')
            self.assertEqual((model.calls,budget.reserve_calls),(0,0));self.assertEqual(rg.capture_rng(),training_rng)
            with self.assertRaisesRegex(ValueError,'identity or decoding contract changed'):
                self.run_eval(model,path,budget,identity={**self.identity,'model_hash':'c'*64})
            self.assertEqual((model.calls,budget.reserve_calls),(0,0))

    def test_corrupted_committed_score_fails_without_regeneration(self):
        with tempfile.TemporaryDirectory() as directory,self.cpu():
            root=Path(directory);path=root/'predictions.jsonl';budget=Budget(root/'ledger.json')
            self.run_eval(Model(),path,budget,limit=1)
            scored_path=path.with_suffix('.resume')/'batches/000000.scored.json';record=rg._read(scored_path)
            record['records'][0]['score']['correct']=not record['records'][0]['score']['correct']
            scored_path.write_text(json.dumps(record));model=Model();resume_budget=Budget(root/'ledger.json')
            with self.assertRaisesRegex(ValueError,'score identity/hash changed'):self.run_eval(model,path,resume_budget)
            self.assertEqual((model.calls,resume_budget.reserve_calls),(0,0))


if __name__=='__main__':unittest.main()

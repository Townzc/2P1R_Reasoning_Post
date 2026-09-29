"""CPU fixtures for new paired substreams, unchanged loss, and exact recovery."""
import copy
import json
from pathlib import Path
import random
import tempfile
import time
from unittest.mock import patch
import unittest

import numpy as np
import torch
from experiments.post_e037_goal_training import generation as gen
from experiments.post_e037_goal_training import training as training
from experiments.post_e037_goal_training.queue import evaluation_queue, ensure_parent_reference, reference_progress
from experiments.thursday_probe.lora import parameter_digest, save_adapter
from src.relation_experiment import accumulate_gradients
from src.sft_data import collate, shifted_loss_sum, sha256_file
import tests.test_goal_probe_runtime as probe_fixture
from tests.test_thursday_v2_resumable_generation import Model, Tokenizer, Budget
import tests.test_thursday_v2_resumable_training as training_fixture


class PairedGenerationTests(unittest.TestCase):
    def fixture(self):
        rows=[dict(problem_id=f'q{g}t{t}',group_id=f'g{g}',target_index=t,interface='C',
            task='compute',prompt=f'Compute1+1 for fixture{g}.',answer='2',target=2,numbers=[1,1])
            for g in range(3) for t in (0,1)]
        event=dict(name='E031_F_sampled_fixture',questions=6,samples=4,sampling=True,generations=24)
        identity=dict(model_hash='a'*64,split_hash='b'*64,batch_time_reserve_seconds=120.)
        return rows,event,identity

    def run_eval(self,model,path,budget,limit=99):
        rows,event,identity=self.fixture()
        return gen.run_event(model,Tokenizer(),rows,path,event,identity,limit,budget,1e20)

    def normalized(self,records):
        return [{k:v for k,v in r.items() if k!='batch_seconds'} for r in records]

    def test_two_independent_target_seeds_resume_equal_and_caller_rng_protected(self):
        with tempfile.TemporaryDirectory() as tmp,probe_fixture.RuntimeTests().cpu():
            root=Path(tmp);full=root/'full';split=root/'split';full.mkdir();split.mkdir()
            random.seed(5);np.random.seed(6);torch.manual_seed(7);caller=gen.capture_rng()
            expected=self.run_eval(Model(),full/'out.jsonl',Budget(full/'ledger.json'))
            self.assertEqual(gen.capture_rng(),caller)
            model=Model();budget=Budget(split/'ledger.json')
            first=self.run_eval(model,split/'out.jsonl',budget,1)
            self.assertEqual(first['completed_records'],8);self.assertEqual(model.calls,1)
            random.seed(42);np.random.seed(12);torch.manual_seed(66);newcaller=gen.capture_rng()
            resumed=Model();result=self.run_eval(resumed,split/'out.jsonl',Budget(split/'ledger.json'))
            self.assertEqual(result['status'],'completed')
            self.assertEqual(self.normalized(result['records']),self.normalized(expected['records']))
            self.assertEqual(gen.capture_rng(),newcaller)
            self.assertEqual(resumed.calls,3)
            self.assertEqual(len(set(result['request_ids'])),24)
            self.assertNotEqual(gen.target_seed(0),gen.target_seed(1))
            self.assertNotIn(2026091708,[gen.target_seed(i) for i in (0,1)])
            self.assertEqual([r['problem_id'] for r in result['records']],
                [r['problem_id'] for r in self.fixture()[0] for _ in range(4)])
            self.assertFalse((split/'out.raw_batches.jsonl').exists())
            for item in result['substreams']:
                self.assertEqual(item['predictions_sha256'],sha256_file(split/item['path']))
            again=self.run_eval(resumed,split/'out.jsonl',Budget(split/'ledger.json'),0)
            self.assertEqual(again['new_batches'],0);self.assertEqual(resumed.calls,3)

    def test_crash_after_raw_replays_without_charge_and_ambiguous_reserve_stops(self):
        with tempfile.TemporaryDirectory() as tmp,probe_fixture.RuntimeTests().cpu():
            root=Path(tmp);path=root/'out.jsonl';budget=Budget(root/'ledger.json');atomic=gen._atomic
            def crash(p,*args,**kw):
                atomic(p,*args,**kw)
                if str(p).endswith('.raw.json'):raise RuntimeError('after_raw')
            with patch.object(gen,'_atomic',side_effect=crash),self.assertRaisesRegex(RuntimeError,'after_raw'):
                self.run_eval(Model(),path,budget)
            model=Model();replayed=self.run_eval(model,path,Budget(root/'ledger.json'),0)
            self.assertEqual((model.calls,replayed['completed_records']),(0,8))
            self.assertEqual(Budget(root/'ledger.json').record()['used'],600)
        with tempfile.TemporaryDirectory() as tmp,probe_fixture.RuntimeTests().cpu():
            root=Path(tmp);budget=Budget(root/'ledger.json');reserve=budget.reserve
            def charge(name,n):reserve(name,n);raise RuntimeError('charged')
            with patch.object(budget,'reserve',side_effect=charge),self.assertRaisesRegex(RuntimeError,'charged'):
                self.run_eval(Model(),root/'out.jsonl',budget)
            model=Model()
            with self.assertRaisesRegex(RuntimeError,'Ambiguous'):
                self.run_eval(model,root/'out.jsonl',Budget(root/'ledger.json'))
            self.assertEqual(model.calls,0)

    def test_fixed_queue_dose_and_priorities(self):
        events=evaluation_queue()
        self.assertEqual(len(events),21);self.assertEqual(sum(e['generations'] for e in events),3344)
        self.assertEqual(sum(e['generations'] for e in events if e['view']=='midpoint12'),48)
        self.assertEqual(sum(e['generations'] for e in events if e['view']=='train16'),128)
        self.assertTrue(all(e['state']=='E031' for e in events[:5]))
        self.assertEqual({e['checkpoint_step'] for e in events if e['view']=='midpoint12'},{128})
        self.assertEqual(sum(e['generations'] for e in events if e['decoding']=='sampled'),2304)

    def test_reference_accounting_excludes_intents_and_reports_unfinished_work(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);out=root/'arm';out.mkdir()
            (out/'reference_H_before.intent.json').write_text(json.dumps({'planned_forward_calls':512}))
            (out/'reference_F_before.intent.json').write_text(json.dumps({'planned_forward_calls':512}))
            (out/'reference_H_before.json').write_text(json.dumps(dict(forward_calls=512,forward_seconds=2.,input_tokens=1200)))
            actual=reference_progress(root,[{'run_id':'arm'}])
            self.assertEqual(actual['reference_forward_calls'],512)
            self.assertEqual(actual['reference_forward_input_tokens'],1200)
            self.assertEqual(actual['reference_incomplete_intents'],['arm/reference_F_before.intent.json'])


class TrainingContractTests(unittest.TestCase):
    def setUp(self):
        fixture=training_fixture.ResumableTrainingTests();fixture.setUp()
        for name in ('model','rows','schedule','lrs','tokenizer','identity'):setattr(self,name,getattr(fixture,name))

    def train(self,model,path,end=4):
        return training.train_segment(model,self.rows,self.schedule,self.lrs,self.tokenizer,path,
            identity=self.identity,end_step=end,deadline=time.time()+300,device='cpu')

    def state(self,path):
        pointer=json.loads((path/'recovery/latest.json').read_text())
        return torch.load(path/'recovery'/pointer['file'],map_location='cpu',weights_only=True)

    def test_optimizer_rng_resume_matches_uninterrupted_and_new_arm_resets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);a=copy.deepcopy(self.model);b=copy.deepcopy(self.model)
            expected=self.train(a,root/'full');self.train(b,root/'split',2)
            random.seed(731);np.random.seed(31);torch.manual_seed(91)
            resumed=self.train(copy.deepcopy(self.model),root/'split')
            self.assertEqual(expected['final_adapter'],resumed['final_adapter'])
            for field in ('adapter','optimizer','rng'):
                self.assertTrue(training._same_tree(self.state(root/'full')[field],self.state(root/'split')[field]))
            self.train(copy.deepcopy(self.model),root/'other_arm',1)
            steps=[float(v['step']) for v in self.state(root/'other_arm')['optimizer']['state'].values()]
            self.assertTrue(steps and all(s==1 for s in steps))
            self.assertEqual(sum(r['supervised_tokens'] for r in resumed['cumulative_history']),20)

    def test_crash_preserves_physical_work_without_double_counting(self):
        original=training.accumulate_gradients;calls=0
        def fail(*args,**kw):
            nonlocal calls
            calls+=1
            if calls==2:raise RuntimeError('after_update1')
            return original(*args,**kw)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            with patch.object(training,'accumulate_gradients',side_effect=fail),self.assertRaisesRegex(RuntimeError,'after_update1'):
                self.train(copy.deepcopy(self.model),root/'split')
            self.assertEqual(self.state(root/'split')['step'],0)
            resumed=self.train(copy.deepcopy(self.model),root/'split')
            reference=self.train(copy.deepcopy(self.model),root/'full')
            self.assertEqual(resumed['final_adapter'],reference['final_adapter'])
            self.assertEqual([r['step'] for r in resumed['discarded_uncommitted_history']],[1])

    def test_checkpoint_zero_reference_and_prune_requires_independent_backup(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);parent=root/'E031';save_adapter(self.model,parent)
            ensure_parent_reference(root/'child',parent)
            self.assertTrue((root/'child/checkpoint_0').is_symlink())
            self.train(copy.deepcopy(self.model),root/'child',2)
            self.assertEqual(json.loads((root/'child/checkpoint_0/checkpoint_identity.json').read_text()),json.loads((parent/'checkpoint_identity.json').read_text()))
            folder=root/'child/recovery';pointer=json.loads((folder/'latest.json').read_text());keep=pointer['file']
            old=[p for p in folder.glob('rolling_step_*.pt') if p.name!=keep]
            self.assertEqual(len(old),1)
            training._prune_recoveries(folder,keep);self.assertTrue(old[0].exists())
            (folder/'backup_confirmed.json').write_text(json.dumps({'files':{old[0].name:{'sha256':sha256_file(old[0])}}}))
            training._prune_recoveries(folder,keep);self.assertTrue(old[0].exists())
            (folder/'backup_confirmed.json').write_text(json.dumps({'files':{keep:{'sha256':sha256_file(folder/keep),'step':2}}}))
            # Matching glob alone never authorizes deleting unknown or foreign state.
            unrelated=folder/'rolling_step_000001_user.pt';unrelated.write_bytes(b'private unrelated bytes')
            foreign=folder/('rolling_step_000001_'+'a'*32+'.pt')
            foreign_state=copy.deepcopy(self.state(root/'child'));foreign_state['step']=1;foreign_state['fingerprint']='f'*64
            torch.save(foreign_state,foreign)
            training._prune_recoveries(folder,keep);self.assertFalse(old[0].exists());self.assertTrue((folder/keep).exists())
            self.assertEqual(unrelated.read_bytes(),b'private unrelated bytes');self.assertTrue(foreign.exists())
            future=folder/('rolling_step_000003_'+'b'*32+'.pt');future.write_bytes((folder/keep).read_bytes())
            (folder/'backup_confirmed.json').write_text(json.dumps({'files':{future.name:{'sha256':sha256_file(future),'step':3}}}))
            with self.assertRaisesRegex(ValueError,'step/fingerprint'):
                training._prune_recoveries(folder,keep)
            self.assertTrue(foreign.exists());self.assertTrue((folder/keep).exists())
            from experiments.thursday_probe_v2.config import learning_rates
            result=training.train_segment(copy.deepcopy(self.model),self.rows,[[0,1]]*256,learning_rates(256),self.tokenizer,root/'policy',
                identity=self.identity,end_step=0,deadline=time.time()+30,device='cpu')
            protocol=json.loads((root/'policy/training_identity.json').read_text())['protocol']
            self.assertEqual(protocol['checkpoint_steps'],[0,128,256])

    def test_active_target_token_loss_matches_full_batch_gradient_no_padding_loss(self):
        a=copy.deepcopy(self.model);b=copy.deepcopy(self.model)
        actual=accumulate_gradients(a,self.rows,0,1,'cpu')
        batch=collate(self.rows,0)
        self.assertTrue(torch.all(batch['labels'][batch['attention_mask']==0]==-100))
        denominator=sum(r['n_supervised'] for r in self.rows)
        direct=shifted_loss_sum(b(input_ids=batch['input_ids'],attention_mask=batch['attention_mask'],use_cache=False).logits,batch['labels'])/denominator
        direct.backward();self.assertAlmostEqual(actual,direct.item(),places=6)
        for (na,pa),(nb,pb) in zip(a.named_parameters(),b.named_parameters()):
            self.assertEqual(na,nb)
            if pa.requires_grad:self.assertTrue(torch.allclose(pa.grad,pb.grad,atol=2e-7,rtol=2e-5))


if __name__=='__main__':unittest.main()

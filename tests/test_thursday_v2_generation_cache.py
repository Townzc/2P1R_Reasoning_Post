"""CPU-only fake decoding; no pretrained model or scientific result is generated."""
from contextlib import ExitStack, nullcontext
import itertools
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import torch

from analyses.completion_contract import first_stop
from experiments.thursday_probe.arithmetic_eval import generate as original_generate
from experiments.thursday_probe_v2 import generation


class Tokenizer:
    eos_token_id=0

    def __init__(self):
        self.vocab_queries=0
        self.special_queries=0

    def __len__(self):
        self.vocab_queries+=1
        return 10

    @property
    def all_special_ids(self):
        self.special_queries+=1
        return [0,9]

    def encode(self,text,add_special_tokens=False):
        return [5]*(1+len(text)%3)

    def decode(self,ids,**kwargs):
        return ''.join({1:'Answer: 2',2:'\nProblem:',3:'x',5:'p'}.get(t,'') for t in ids)


class Budget:
    def __init__(self):self.reservations=[]
    def reserve(self,name,n):self.reservations.append((name,n))


class Model:
    # Native EOS, in-vocabulary special, out-of-vocabulary, cap and boundary.
    streams=([1,0],[1,9],[1,10],[1,3,3,3],[1,2],[0])

    def __init__(self):self.seen=0;self.configs=[]
    def eval(self):return self

    def generate(self,input_ids,attention_mask,generation_config,stopping_criteria):
        self.configs.append(generation_config.to_dict())
        stopper=stopping_criteria[0]
        streams=[self.streams[(self.seen+i)%len(self.streams)] for i in range(len(input_ids))]
        self.seen+=len(input_ids)
        output=input_ids.clone()
        for step in range(generation_config.max_new_tokens):
            tokens=[0 if stopper.events[i] is not None else stream[step] for i,stream in enumerate(streams)]
            output=torch.cat((output,torch.tensor(tokens).unsqueeze(1)),dim=1)
            if bool(stopper(output,None).all()):break
        return output


class GenerationCacheTests(unittest.TestCase):
    def cpu_only(self):
        context=ExitStack()
        tensor=torch.tensor
        def cpu_tensor(*args,**kwargs):
            if kwargs.get('device')=='cuda':kwargs['device']='cpu'
            return tensor(*args,**kwargs)
        context.enter_context(patch.object(torch,'tensor',cpu_tensor))
        context.enter_context(patch.object(torch,'autocast',lambda *a,**kw:nullcontext()))
        context.enter_context(patch.object(torch.cuda,'synchronize',lambda:None))
        # Keep timing fields identical while comparing the complete record schema.
        context.enter_context(patch('time.monotonic',side_effect=itertools.count().__next__))
        return context

    def rows(self):
        return [dict(problem_id=f'q{i}',prompt='Compute 1+1.'+' '*i,
                     task='compute',category='atomic',numbers=[1,1],answer='2') for i in range(10)]

    def test_identical_records_and_bounded_metadata_queries(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);outputs=[];models=[];tokenizers=[];budgets=[]
            for name,generate in (('old',original_generate),('cached',generation.generate)):
                folder=root/name;folder.mkdir();tokenizer=Tokenizer();model=Model();budget=Budget()
                with self.cpu_only():
                    records=generate(model,tokenizer,self.rows(),folder/'predictions.jsonl',budget,
                        samples=2,sampling=True,max_new_tokens=4,forced={'q0':'Prefix\n'})
                outputs.append(records);models.append(model);tokenizers.append(tokenizer);budgets.append(budget)
            self.assertEqual(outputs[0],outputs[1])
            self.assertEqual(models[0].configs,models[1].configs)
            self.assertEqual(budgets[0].reservations,budgets[1].reservations)
            self.assertEqual((tokenizers[1].vocab_queries,tokenizers[1].special_queries),(1,1))
            self.assertGreater(tokenizers[0].vocab_queries,20)
            self.assertEqual({r['stop']['stop_reason'] for r in outputs[1]},
                {'native_eos','invalid_special_token','length_cap','new_problem_boundary'})
            batches=[json.loads(s) for s in (root/'cached/predictions.raw_batches.jsonl').read_text().splitlines()]
            self.assertEqual([len(b['output_ids']) for b in batches],[8,8,4])
            for b in batches:
                for index,full_ids in enumerate(b['output_ids']):
                    ids=full_ids[b['padded_prompt_width']:]
                    oracle=first_stop(ids,tokenizers[1].decode,0,4,{0,9}|{t for t in ids if t>=10})
                    self.assertEqual(oracle,b['stop_events'][index])

    def test_raw_batch_is_fsynced_before_score_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'predictions.jsonl'
            real_fsync=generation.os.fsync
            with self.cpu_only(),patch.object(generation.os,'fsync',wraps=real_fsync) as fsync:
                def fail_score(*args):
                    self.assertEqual(fsync.call_count,1)
                    raise RuntimeError('simulated score interruption')
                with patch.object(generation,'score',side_effect=fail_score),self.assertRaisesRegex(RuntimeError,'simulated'):
                    generation.generate(Model(),Tokenizer(),self.rows(),path,Budget(),max_new_tokens=4)
            self.assertEqual(path.read_text(),'')
            batches=[json.loads(s) for s in path.with_suffix('.raw_batches.jsonl').read_text().splitlines()]
            self.assertEqual(len(batches),1)
            self.assertEqual(len(batches[0]['output_ids']),8)
            self.assertEqual(len(batches[0]['stop_events']),8)


if __name__=='__main__':unittest.main()

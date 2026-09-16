"""Finite generation reservations and outcome-independent execution safeguards."""
import json
from pathlib import Path
import time

from experiments.thursday_probe.common import dump, stamp
from experiments.thursday_probe_v2.generation import generate as frozen_generate
from experiments.thursday_probe_v2.config import LIMITS
from experiments.thursday_probe_v2.training import atomic_json


class GenerationBudget:
    def __init__(self,path,cap=LIMITS['generation_cap'],fault_generations=0):
        if type(cap) is not int or cap<=0 or type(fault_generations) is not int or not 0<=fault_generations<=cap:
            raise ValueError('Invalid generation cap or carryover fault charge')
        self.path=Path(path); self.cap=cap; self.used=fault_generations
        dump(self.path,dict(cap=cap,used=fault_generations,events=[],fault_generations=fault_generations,accounting='Same v2 phase across attempts; completed reused outputs count once, interrupted attempts remain charged; E018 is historical.'))

    def reserve(self,name,n):
        record=json.loads(self.path.read_text())
        if type(n) is not int or n<=0 or self.used+n>self.cap:
            raise ValueError('Generation cap exceeded')
        if record['used']!=self.used or name in {e['name'] for e in record['events']}:
            raise ValueError('Concurrent writer or duplicate/reserved evaluation')
        self.used+=n;record['used']=self.used
        record['events'].append(dict(name=name,reserved=n,at_utc=stamp()))
        atomic_json(self.path,record)


def generation_contract(records, expected):
    if len(records)!=expected:
        raise ValueError('Incomplete generation stream')
    keys=[(r['problem_id'],r['sample_index']) for r in records]
    if len(set(keys))!=len(keys):
        raise ValueError('Duplicated question/sample identity')
    # Length-capped unsuccessful answers remain in the denominator. Even a high
    # cap fraction is not itself a reason to select cells. A scoring/length hard
    # error is established if valid supplied references cannot fit (CPU audit),
    # or if token streams/stop detection violate the uniform 512-token contract.
    for r in records:
        if not 1<=len(r['generated_ids'])<=512:
            raise ValueError('Invalid retained generation length')
        if r['stop']['stop_reason']=='length_cap' and len(r['generated_ids'])!=512:
            raise ValueError('Incorrect cap termination')


def evaluate(model,tokenizer,rows,path,budget,event,deadline):
    if len(rows)!=event['questions']:
        raise ValueError('Evaluation selection differs from frozen queue')
    if time.time()>=deadline:
        raise TimeoutError('Phase deadline reached')
    records=frozen_generate(model,tokenizer,rows,path,budget,samples=event['samples'],
        sampling=event['sampling'],max_new_tokens=512,seed=2026091603)
    generation_contract(records,event['generations'])
    return records


def projected_remainder(calibration_history, measured_evaluations, remaining_updates,
                        remaining_processed_tokens, remaining_generations):
    """Conservative planning from this window, never an accuracy/significance gate."""
    h=calibration_history[2:]
    train_seconds=sum(r['seconds'] for r in h)
    processed=sum(r['processed_tokens'] for r in h)
    if not h or processed<=0:
        raise ValueError('Measured training profile required')
    rates=[]
    for records in measured_evaluations:
        batches={r['batch_index']:r['batch_seconds'] for r in records}
        rates.append(sum(batches.values())/len(records))
    if not rates or max(rates)<=0:
        raise ValueError('Measured generation profile required')
    training=remaining_processed_tokens*train_seconds/processed
    generation=remaining_generations*max(rates)
    total=1.5*(training+generation)+420
    return dict(method='1.5 * (measured processed-token training projection + slowest measured generation seconds/output) + 420s checkpoint/load allowance',
        calibration_profile_updates=len(h),remaining_updates=remaining_updates,
        training_seconds=training,generation_seconds=generation,projected_process_seconds=total,
        caveat='Planning estimate only; absolute process and whole-window timeouts remain authoritative.')

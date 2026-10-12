"""Recompute endpoint metrics from public per-question records; no private data."""
import argparse
from collections import defaultdict, Counter
from pathlib import Path
import json
import numpy as np
from experiments.sft_allocation_midpoint.common import read, verify


def verify_packet(folder):
    root=Path(folder);manifest=read(root/'manifest.json');verify(root,manifest['files'])
    runs=read(root/'runs.json');rows=defaultdict(dict)
    for line in (root/'question_outcomes.jsonl').open():
        row=json.loads(line);run=row['run_id'];qid=row['question_id']
        if qid in rows[run] or type(row['correct']) is not bool:
            raise ValueError('Duplicated or unknown endpoint')
        rows[run][qid]=row
    if set(rows)!=set(runs) or len(rows)!=9:
        raise ValueError('Wrong run roster')
    ids=sorted(rows['base']);table={}
    for run, data in rows.items():
        if sorted(data)!=ids or len(data)!=431:raise ValueError('Question roster differs')
        recorded=runs[run]
        for value,want in [
            (sum(x['correct'] for x in data.values()), recorded['correct']),
            (sum(x['parse_status']=='parsed' for x in data.values()),recorded['parsed']),
            (dict(Counter(x['stop_reason'] for x in data.values())),recorded['stop_counts']),
            (sum(x['generated_tokens'] for x in data.values()),recorded['generated_tokens'])]:
            if value!=want:raise ValueError('Aggregated metric differs')
        table[run]=dict(correct=recorded['correct'],n=431,accuracy=recorded['correct']/431)
    indices=np.random.default_rng(20261013).integers(0,431,size=(10000,431))
    contrasts=[]
    for high,low in [('solutions','repeat'),('breadth','solutions')]:
        differences=[];per_seed={}
        for seed in (17,23):
            a=np.array([rows[f'{high}_{seed}'][q]['correct'] for q in ids],dtype=float)
            b=np.array([rows[f'{low}_{seed}'][q]['correct'] for q in ids],dtype=float)
            d=a-b;differences.append(d)
            per_seed[str(seed)]=dict(difference_pp=float(d.mean()*100),gained=int((d==1).sum()),lost=int((d==-1).sum()),
                question_bootstrap_interval_pp=np.quantile(d[indices].mean(axis=1)*100,[.025,.975]).tolist())
        mean=np.mean(differences,axis=0)
        contrasts.append(dict(contrast=high+' minus '+low,per_seed=per_seed,mean_difference_pp=float(mean.mean()*100),
            conditional_question_interval_pp=np.quantile(mean[indices].mean(axis=1)*100,[.025,.975]).tolist()))
    return dict(status='local_metric_recomputation_passed_not_external_verdict',table=table,
        primary_contrasts=contrasts,rows=sum(len(x) for x in rows.values()),
        interpretation='Intervals condition on these models and this one procurement draw. No equivalence or dollar-optimality claim.')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--packet',required=True)
    a=p.parse_args();print(json.dumps(verify_packet(a.packet),indent=2))

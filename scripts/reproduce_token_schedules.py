"""Rebuild frozen whole-answer plans from public ordered length/hash metadata.

No teacher/student execution. Lengths are independently tokenizer-audited at
preparation; reproducing this packet does not independently re-tokenize text.
"""
import argparse
import json
from pathlib import Path
from collections import Counter
from experiments.sft_allocation_midpoint.common import read,dump,digest,manifest,verify
from scripts.plan_real_math_scale import whole_response_schedule
from src.sft_data import budget_report


def reproduce(packet,out):
    packet=Path(packet);out=Path(out);verify(packet,read(packet/'manifest.json')['files'])
    meta=read(packet/'training_lengths.json');reach={}
    for cell,rows in meta['cells'].items():
        bits=1;lengths=[x['n_supervised'] for x in rows]
        for n in lengths:bits|=bits<<n
        reach[cell]=(bits,sum(lengths),lengths)
    feasible=[b for b in range(524288,int(524288*.99)-1,-1)
              if all(b>=total and (bits>>(b%total))&1 for bits,total,_ in reach.values())]
    if not feasible or feasible[0]!=meta['chosen_targets']:
        raise ValueError('Common length-only target selection differs')
    target=feasible[0];out.mkdir(parents=True,exist_ok=False);report={}
    for cell,rows in meta['cells'].items():
        for seed in (17,23):
            schedule=whole_response_schedule(reach[cell][2],target,256,seed)
            budget=budget_report(rows,schedule,1)
            # Admission hashes the serialized JSON, whose exposure-map keys are
            # strings. Normalize before hashing, retaining every value.
            plan=json.loads(json.dumps(dict(seed=seed,updates=schedule,budget=budget)))
            if digest(plan)!=meta['plan_digests'][f'{cell}_s{seed}']:
                raise ValueError('Reconstructed plan differs from admitted bytes')
            counts=Counter(i for batch in schedule for i in batch)
            report[f'{cell}_s{seed}']=dict(rows=len(rows),presentations=sum(counts.values()),
                min_exposures=min(counts.values()),max_exposures=max(counts.values()),
                mean_exposures=sum(counts.values())/len(rows),
                one_pass_targets=reach[cell][1],token_weighted_exposures=target/reach[cell][1],
                targets=budget['supervised_response_tokens'],updates=len(schedule))
            dump(out/f'{cell}_seed{seed}.json',plan)
    dump(out/'REPORT.json',dict(chosen_targets=target,all_eight_match=True,exposures=report,new_model_calls=0))
    dump(out/'manifest.json',manifest(out));return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--packet',required=True);p.add_argument('--out',required=True)
    a=p.parse_args();print(__import__('json').dumps(reproduce(a.packet,a.out),indent=2))

"""Local paired development analysis from immutable returned results, no model calls."""
import argparse
from pathlib import Path
import json
from experiments.sft_allocation_midpoint.common import dump,sha


def analyze(folder):
    import numpy as np
    folder=Path(folder);runs={};source={};ids=None
    for arm in ('repeat','solutions','breadth','mixed'):
        for seed in (17,23):
            file=folder/f'{arm}_{seed}_result.json';raw=json.loads(file.read_text());r=raw['result']
            if (r['status']!='completed' or r['arm']!=arm or r['seed']!=seed or r['committed_updates']!=256
                or r['supervised_tokens']!=524288 or r['endpoint']['n']!=431):
                raise ValueError('Incomplete or mismatched scientific dose')
            current=sorted(r['endpoint']['question_correct'])
            if ids is None:ids=current
            if current!=ids or len(current)!=431:raise ValueError('Evaluation roster differs')
            values=[r['endpoint']['question_correct'][i] for i in ids]
            if any(type(v) is not bool for v in values):raise ValueError('Missing/unknown outcome must not become a score')
            if sum(values)!=r['endpoint']['correct']:raise ValueError('Score total differs')
            runs[(arm,seed)]=r;source[file.name]=sha(file)
    table=[]
    for arm in ('repeat','solutions','mixed','breadth'):
        row={'arm':arm,'seeds':{}}
        for seed in (17,23):
            r=runs[(arm,seed)];row['seeds'][str(seed)]=dict(correct=r['endpoint']['correct'],n=431,
                accuracy=r['endpoint']['correct']/431,parsed=r['endpoint']['parsed'],
                stop_reasons=r['endpoint']['stop_reasons'],train_seconds=r['train_seconds'],
                wall_seconds=r['wall_seconds'],runtime_rate_estimate_usd=r['runtime_rate_estimate_usd'])
        row['mean_accuracy']=sum(x['accuracy'] for x in row['seeds'].values())/2
        table.append(row)
    rng=np.random.default_rng(20261013);indices=rng.integers(0,431,size=(10000,431))
    contrasts=[]
    for high,low in [('solutions','repeat'),('breadth','solutions')]:
        differences=[];per_seed={}
        for seed in (17,23):
            a=np.array([runs[(high,seed)]['endpoint']['question_correct'][i] for i in ids],dtype=float)
            b=np.array([runs[(low,seed)]['endpoint']['question_correct'][i] for i in ids],dtype=float)
            d=a-b;differences.append(d)
            per_seed[str(seed)]=dict(difference_pp=float(d.mean()*100),gained=int((d==1).sum()),lost=int((d==-1).sum()),
                question_bootstrap_interval_pp=np.quantile(d[indices].mean(axis=1)*100,[.025,.975]).tolist())
        mean=np.mean(differences,axis=0)
        contrasts.append(dict(contrast=high+' minus '+low,per_seed=per_seed,mean_difference_pp=float(mean.mean()*100),
            conditional_question_interval_pp=np.quantile(mean[indices].mean(axis=1)*100,[.025,.975]).tolist()))
    return dict(schema='midpoint_development_grid_v1',source_files=source,table=table,primary_contrasts=contrasts,
        committed_updates=2048,supervised_tokens=4194304,procurement_draws=1,training_seeds=[17,23],
        bootstrap=dict(replicates=10000,seed=20261013,unit='paired question; same resample across seeds',
          interpretation='Conditional on these trained models and the one procurement draw; not training-seed or procurement uncertainty.'),
        limitations=['Development, not pretraining-clean or fresh confirmation.',
          'Uncertainty spanning zero is not equivalence.','Distinct answer text does not certify different reasoning strategies.',
          'Historical bank acquisition prices are unknown; no dollar-optimal policy follows from this table.'])


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--receipts',required=True);p.add_argument('--out',required=True)
    a=p.parse_args();dump(a.out,analyze(a.receipts))

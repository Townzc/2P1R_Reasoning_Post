"""Independent local record audit and paired observed-development E018 report."""
import argparse
import csv
import json
from pathlib import Path
import random

from analyses.e017_audit import audit_predictions,decisions
from experiments.thursday_probe.common import dump,jsonl,stamp,verify_manifest
from experiments.thursday_probe.e018_prepare import OUT as INPUTS
from scripts.audit_family_matching import verified_tokenizer
from src.sft_data import read_jsonl,sha256_file


def analyze(run,out,tokenizer_dir,checkpoint):
    run=Path(run);out=Path(out);verify_manifest(INPUTS)
    if out.exists():raise FileExistsError('No audit overwrite')
    tokenizer,_=verified_tokenizer(Path(tokenizer_dir))
    cfg=json.loads(Path('configs/real_math_e017/stopping.json').read_text())
    dev=read_jsonl(INPUTS/'dev.jsonl');train=read_jsonl(INPUTS/'train.jsonl')
    proposal=json.loads(Path('configs/diagnostics/real_math_p006_proposal.json').read_text())
    ti=proposal['training']['final_train_decode_sample']['problem_ids']
    tr=[next(r for r in train if r['problem_id']==p) for p in ti]
    b=audit_predictions(run/'base.jsonl',dev,tokenizer,cfg)
    f=audit_predictions(run/'final.jsonl',dev,tokenizer,cfg)
    t=audit_predictions(run/'final_train.jsonl',tr,tokenizer,cfg)
    metrics=json.loads((run/'metrics.json').read_text())
    if decisions(b,cfg)!=metrics['base'] or decisions(f,cfg)!=metrics['final']:
        raise ValueError('Server/local score discrepancy')
    history=read_jsonl(run/'train_history.jsonl')
    schedule=json.loads((INPUTS/'schedule.json').read_text());lr=json.loads((INPUTS/'learning_rates.json').read_text())
    if len(history)!=64 or any(h['step']!=i+1 or h['row_indices']!=schedule[i] or h['learning_rate']!=lr[i] for i,h in enumerate(history)):
        raise ValueError('Actual schedule/LR differs')
    if sum(h['supervised_tokens'] for h in history)!=77192:raise ValueError('Actual supervised budget differs')
    bm=json.loads((run/'base_reference_nll.json').read_text());fm=json.loads((run/'final_reference_nll.json').read_text())
    if any(n['reference_count']!=253 or n['supervised_tokens']!=38596 for n in (bm,fm)):
        raise ValueError('NLL reference denominator differs')
    if metrics['reference_nll_reduction_fraction'] != 1-fm['nll']/bm['nll']:raise ValueError('NLL reduction differs')
    ck=Path(checkpoint);ci=json.loads((ck/'checkpoint_identity.json').read_text())
    if ci!=metrics['checkpoint'] or any(sha256_file(ck/n)!=h for n,h in ci['files_sha256'].items()):
        raise ValueError('Independent complete adapter copy differs')
    receipt=json.loads((run/'resource_receipt.json').read_text())
    if receipt['exit_code']!=0 or not 0<receipt['charged_seconds']<=915 or not receipt['old_ledger_unchanged']:
        raise ValueError('Bounded completed receipt differs')
    pairs=[]
    for x,y in zip(b,f):
        bc=x['task_score']['task_answer_correct'];fc=y['task_score']['task_answer_correct']
        pairs.append({'problem_id':x['problem_id'],'base_correct':bc,'adapter_correct':fc,
            'change':int(fc)-int(bc),'category':'both_correct' if bc and fc else 'gained' if fc else 'lost' if bc else 'both_wrong',
            'base_stop':x['stop']['stop_reason'],'adapter_stop':y['stop']['stop_reason'],
            'base_parse':x['task_score']['marked']['status'],'adapter_parse':y['task_score']['marked']['status'],
            'evaluation_scope':'already_observed_GSM8K_development_E018_not_arithmetic_discovery'})
    both=sum(p['category']=='both_correct' for p in pairs);nb=sum(p['base_correct'] for p in pairs);nf=sum(p['adapter_correct'] for p in pairs)
    checks={**metrics['checks'],'retention':10*both>=9*nb,'net_loss':nb-nf<=4,
        'nll_reduction':1-fm['nll']/bm['nll']>=.1,'base_unchanged':metrics['initial_base']==metrics['final_base'],
        'adapter_changed':metrics['initial_adapter']!=metrics['final_adapter']}
    if checks!=metrics['checks'] or all(checks.values())!=metrics['passed']:raise ValueError('Decision discrepancy')
    rng=random.Random(17020);diff=[];ret=[];undefined=0
    for _ in range(10000):
        draw=[pairs[rng.randrange(64)] for _ in range(64)]
        diff.append(sum(p['change'] for p in draw)/64)
        den=sum(p['base_correct'] for p in draw)
        if den:ret.append(sum(p['base_correct'] and p['adapter_correct'] for p in draw)/den)
        else:undefined+=1
    def interval(xs):
        xs=sorted(xs);return [xs[int(.025*(len(xs)-1))],xs[int(.975*(len(xs)-1))]]
    old=read_jsonl('runs/gsm8k_stop_e017_r1/base.jsonl')
    summary={'phase':'E018','checked_at_utc':stamp(),'raw_streams_independently_audited':len(b)+len(f)+len(t),
        'base_correct':nb,'adapter_correct':nf,'both_correct':both,'lost':nb-both,'gained':nf-both,
        'paired_accuracy_difference':(nf-nb)/64,'paired_accuracy_difference_CI95':interval(diff),
        'retained_fraction':both/nb if nb else None,'retained_fraction_CI95':interval(ret),
        'undefined_zero_baseline_bootstraps':undefined,'bootstrap_samples':10000,'bootstrap_seed':17020,
        'before_nll':bm['nll'],'after_nll':fm['nll'],'nll_reduction_fraction':1-fm['nll']/bm['nll'],
        'base_tokens_identical_to_E017':sum(x['generated_ids']==y['generated_ids'] for x,y in zip(old,b)),
        'checks':checks,'passed':all(checks.values()),'adapter_backup_complete':True,
        'checkpoint_bytes':ci['bytes'],'receipt':receipt,
        'train_decode_correct':sum(r['task_score']['task_answer_correct'] for r in t),
        'interpretation':'Descriptive observed-development calibration with one known erroneous training reference; no fresh confirmation, general capability retention or treatment effect.'}
    out.mkdir();dump(out/'independent_audit.json',summary);jsonl(out/'per_problem.jsonl',pairs)
    with (out/'failure_breakdown.csv').open('x',newline='') as file:
        w=csv.DictWriter(file,fieldnames=['endpoint','kind','value','count']);w.writeheader()
        for endpoint,results in [('base',metrics['base']),('adapter',metrics['final'])]:
            for kind in ('parse_status','stop_reasons'):
                for key,count in results[kind].items():w.writerow({'endpoint':endpoint,'kind':kind,'value':key,'count':count})
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',required=True);p.add_argument('--out',required=True)
    p.add_argument('--tokenizer-dir',required=True);p.add_argument('--checkpoint',required=True)
    a=p.parse_args();print(json.dumps(analyze(a.run,a.out,a.tokenizer_dir,a.checkpoint),indent=2))

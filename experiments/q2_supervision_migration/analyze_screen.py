"""Local, model-free reconciliation and descriptive analysis of the frozen screen."""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path
import random

from . import screen_plan as spec
from .contracts import ContractError, identity_hash, read_records
from .gpu_profile import durable_json


def percentile(xs,q):
    ordered=sorted(xs);i=(len(ordered)-1)*q;lo=math.floor(i);hi=math.ceil(i)
    return ordered[lo]*(hi-i)+ordered[hi]*(i-lo) if hi!=lo else ordered[lo]


def paired_question_interval(left,right, *, resamples=5000,seed=730):
    if not left or set(left)!=set(right): raise ContractError('paired evaluation IDs differ')
    differences=[left[t]-right[t] for t in sorted(left)];n=len(differences)
    rng=random.Random(seed)
    draws=[sum(differences[rng.randrange(n)] for _ in range(n))/n for _ in range(resamples)]
    return {'difference_pp':100*sum(differences)/n,
            'conditional_question_bootstrap_95pp':[100*percentile(draws,.025),100*percentile(draws,.975)],
            'question_count':n,'resamples':resamples,
            'scope':'conditional on these trained models; not uncertainty across training seeds'}


def score_maps(samples,expected_ids):
    grouped=defaultdict(list)
    for r in samples:
        if r['task_id'] not in expected_ids: raise ContractError('evaluation task outside frozen roster')
        if r['base']['status'] not in ['pass','fail'] or r['extra']['status'] not in ['pass','fail']:
            raise ContractError('unresolved evaluation cannot become zero')
        grouped[r['task_id']].append(r)
    if set(grouped)!=set(expected_ids) or any(len(rs)!=spec.EVAL_SAMPLES for rs in grouped.values()):
        raise ContractError('missing or duplicated evaluation completions')
    maps={k:{} for k in ['base','extra','union','pass_at_8']}
    for t,rs in grouped.items():
        bs=[r['base']['status']=='pass' for r in rs];es=[r['extra']['status']=='pass' for r in rs]
        us=[b and e for b,e in zip(bs,es)]
        for k,vs in [('base',bs),('extra',es),('union',us)]:maps[k][t]=sum(vs)/len(vs)
        maps['pass_at_8'][t]=float(any(us))
    return maps


def descriptive_decision(contrasts):
    wr=contrasts['W_future_minus_R_future']['difference_pp']
    wc=contrasts['W_future_minus_C_future']['difference_pp']
    cr=contrasts['C_future_minus_R_future']['difference_pp']
    pattern=wr<=-3.0 and wc<=-3.0 and cr>=-1.0
    return {'candidate_pattern':pattern,
            'project_decision':('candidate_for_replication_and_teacher_discussion' if pattern else
                                'no_clear_target_pattern_in_this_screen; discuss_or_deprioritize_without_claiming_falsification'),
            'scientific_confirmation':False,'new_compute_automatically_authorized':False}


def inspect_phase(root,plan,name,evaluation=False):
    p=Path(root)/name
    expected=([ [t for t in plan['eval_ids'][i:i+4] for _ in range(8)] for i in range(0,128,4)] if evaluation else
              plan['schedules'][next(x['schedule'] for x in plan['training_phases'] if x['name']==name)])
    phasesamples=[];indices=set();completed_indices=set();sealed=0;returned=0;backend_returned=0;reserved=0;complete=0
    statuses=Counter();lengths=[];group_types=Counter();reward_flips=0
    inp=json.loads((p/'input_receipt.json').read_text()) if (p/'input_receipt.json').exists() else None
    for d in sorted((p/'batches').glob('*')):
        if not d.is_dir(): raise ContractError('unexpected batch file')
        if not (d/'intent.jsonl').exists():
            # A crash may leave just the reserved directory. It must not be replayed.
            raise ContractError('ambiguous empty batch reservation; inspect failure evidence')
        intent,=read_records(d/'intent.jsonl');i=intent['batch_index']
        if intent['kind']!='batch_intent' or intent['schema']!=1:
            raise ContractError('unexpected intent schema')
        if i in indices or i not in range(len(expected)) or intent['tasks']!=expected[i]:
            raise ContractError('batch index/task order differs from plan')
        if intent['phase_id']!=name or intent['run_id']!=plan['run_id']:
            raise ContractError('batch phase/run identity differs')
        if d.name!=identity_hash({k:intent[k] for k in ['run_id','phase_id','batch_index']}):
            raise ContractError('batch directory identity differs')
        if inp is None: raise ContractError('batch lacks phase input provenance')
        expected_config=identity_hash(plan['evaluation']) if evaluation else inp['config_identity']
        expected_policy=inp['source_identity'] if evaluation else identity_hash({'source':inp['source_identity'],'phase':name,'committed_updates':i})
        if intent['config_sha256']!=expected_config or intent['policy_sha256']!=expected_policy:
            raise ContractError('batch config/policy lineage differs')
        indices.add(i);reserved+=len(expected[i]);samples=[]
        for f in sorted(d.glob('sample_*.jsonl')):
            r,=read_records(f);j=r['sample_index']
            if r['kind']!='sample' or r['schema']!=1:
                raise ContractError('unexpected sample schema')
            if j!=len(samples) or r['task_id']!=expected[i][j] or f.name!=f'sample_{j:08d}.jsonl':
                raise ContractError('sample order/identity differs')
            if r['intent_sha256']!=intent['record_sha256'] or r['policy_sha256']!=expected_policy or r['sample_id']!=identity_hash({'intent':intent['record_sha256'],'sample_index':j}):
                raise ContractError('sample provenance differs')
            samples.append(r);statuses[r['base']['status']+'/'+r['extra']['status']]+=1
            reward_flips+=r['base']['status']=='pass' and r['extra']['status']=='fail'
            lengths.append(len(r['completion_token_ids']))
        backend_path=d/('backend_return.json' if evaluation else 'generation_return.json')
        backend_texts=backend_ids=None
        if backend_path.exists():
            backend=json.loads(backend_path.read_text())
            if evaluation:
                if len(backend)!=spec.EVAL_TASKS_PER_BATCH or any(
                    sorted(x['index'] for x in request['outputs'])!=list(range(spec.EVAL_SAMPLES))
                    for request in backend):
                    raise ContractError('evaluation backend request/sample counts differ')
                outputs=[x for request in backend for x in sorted(request['outputs'],key=lambda x:x['index'])]
                backend_texts=[x['text'] for x in outputs];backend_ids=[x['token_ids'] for x in outputs]
            else:
                backend_texts=backend['decoded_text'];backend_ids=backend['completion_ids']
                if len(backend['prompt_ids'])!=len(expected[i]):
                    raise ContractError('training backend prompt count differs')
            if len(backend_texts)!=len(expected[i]) or len(backend_ids)!=len(expected[i]):
                raise ContractError('backend completion count differs')
            backend_returned+=len(backend_texts)
        raw_path=d/'raw_generations.json'
        if raw_path.exists():
            raw=json.loads(raw_path.read_text());returned+=len(raw['texts'])
            if raw['task_id']!=expected[i] or len(raw['texts'])!=len(expected[i]) or len(raw['completion_ids'])!=len(expected[i]):
                raise ContractError('raw generation counts/tasks differ')
            if raw['texts']!=backend_texts or raw['completion_ids']!=backend_ids:
                raise ContractError('raw scoring input differs from original backend return')
            for r in samples:
                j=r['sample_index']
                if raw['texts'][j]!=r['completion_text'] or raw['completion_ids'][j]!=r['completion_token_ids']:
                    raise ContractError('saved sample differs from raw output')
        if (d/'batch.jsonl').exists():
            if len(samples)!=len(expected[i]) or read_records(d/'batch.jsonl')!=[intent,*samples]:
                raise ContractError('sealed batch is incomplete or modified')
            sealed+=1
            for start in range(0,len(samples),8):
                group=samples[start:start+8]
                if all(r['base']['status'] in ['pass','fail'] and r['extra']['status'] in ['pass','fail'] for r in group):
                    for rule in ['base','union']:
                        wins=sum(r['base']['status']=='pass' and (rule=='base' or r['extra']['status']=='pass') for r in group)
                        group_types[rule+':'+('all_fail' if wins==0 else 'all_pass' if wins==8 else 'mixed')]+=1
        if (d/'generation_complete.json').exists():
            if not (d/'batch.jsonl').exists() or not raw_path.exists(): raise ContractError('completion without sealed outputs')
            done=json.loads((d/'generation_complete.json').read_text())
            if not evaluation and not done['global_step']==done['last_loaded_step']==i:
                raise ContractError('rollout source step not synchronized')
            complete+=1
            completed_indices.add(i)
        phasesamples.extend(samples)
    pre_updates=[]
    for f in sorted(p.glob('pre_update_*.json')):
        pre=json.loads(f.read_text());step=pre['step']
        if evaluation or step!=len(pre_updates)+1 or step-1 not in completed_indices:
            raise ContractError('unexpected pre-update dose/order')
        if not pre['all_finite'] or pre['gradient_tensors']<=0:
            raise ContractError('invalid pre-step check')
        pre_updates.append(step)
    updates=[]
    for f in sorted(p.glob('update_*.json')):
        u=json.loads(f.read_text());step=u['committed_update']
        if evaluation or step!=len(updates)+1 or step-1 not in completed_indices:
            raise ContractError('unexpected optimizer dose/order')
        pre=json.loads((p/f'pre_update_{step:04d}.json').read_text())
        if pre['step']!=step or not pre['all_finite'] or pre['gradient_tensors']<=0:
            raise ContractError('committed update lacks valid pre-step check')
        updates.append(step)
    ambiguous_updates=sorted(set(pre_updates)-set(updates))
    if ambiguous_updates not in [[],[len(updates)+1]]:
        raise ContractError('multiple unresolved optimizer attempts in serial worker')
    marker=p/('evaluation_complete.json' if evaluation else 'phase_complete.json')
    finished=marker.exists()
    if finished:
        receipt=json.loads(marker.read_text())
        if receipt['plan_sha256']!=identity_hash(plan): raise ContractError('phase plan identity differs')
        if indices!=set(range(len(expected))) or sealed!=len(expected) or complete!=len(expected):
            raise ContractError('completed phase lacks exact batches')
        if returned!=sum(map(len,expected)) or len(phasesamples)!=returned:
            raise ContractError('completed phase lacks exact returned/scored samples')
        if any(k not in ['pass/pass','pass/fail','fail/pass','fail/fail'] for k in statuses):
            raise ContractError('completed phase contains unresolved scoring')
        if not evaluation:
            if ambiguous_updates or len(updates)!=spec.PREFIX_UPDATES or receipt['training_completions']!=returned or receipt['committed_updates']!=len(updates):
                raise ContractError('completed phase optimizer count differs')
        elif receipt['completions']!=returned: raise ContractError('completed evaluation count differs')
    return {'phase':name,'finished':finished,'reserved_completions':reserved,'saved_raw_completions':returned,
            'saved_backend_completions':backend_returned,'reserved_without_backend_return':reserved-backend_returned,
            'signed_samples':len(phasesamples),'sealed_batches':sealed,'completed_generation_batches':complete,
            'committed_updates':len(updates),'pre_update_receipts':len(pre_updates),
            'optimizer_steps_with_uncertain_commit':ambiguous_updates,'base_extra_counts':dict(statuses),
            'base_pass_extra_fail':reward_flips,'group_types':dict(group_types),
            'completion_tokens_total':sum(lengths),'completion_tokens_max':max(lengths,default=0),
            'completion_at_cap':sum(x==640 for x in lengths)},phasesamples


def analyze(root):
    root=Path(root);intent=json.loads((root/'screen_intent.json').read_text());plan=intent['plan']
    spec.validate_plan(plan,{'train_ids':plan['train_ids'],'eval_ids':plan['eval_ids']})
    if intent['plan_sha256']!=identity_hash(plan): raise ContractError('study plan changed')
    summaries=[];maps={};initial_identity=intent['initial_model_identity']
    for phase in plan['training_phases']:
        name=phase['name'];summary,_=inspect_phase(root,plan,name);summaries.append(summary)
        if not summary['finished']: continue
        inp=json.loads((root/name/'input_receipt.json').read_text())
        if phase['source_state']=='R':
            if inp['source_identity']!=initial_identity: raise ContractError('initial model identity differs across arms')
        else:
            origin=json.loads((root/phase['source_state']/'checkpoint_manifest.json').read_text())
            if inp['source_identity']!=identity_hash(origin): raise ContractError('continuation source checkpoint differs')
            if not json.loads((root/name/'source_reload_check.json').read_text())['passed']:
                raise ContractError('continuation source reload not verified')
        fresh=json.loads((root/name/'fresh_optimizer.json').read_text())
        if fresh['class']!='Adafactor' or fresh['state_entries']!=0 or fresh['initial_global_step']!=0:
            raise ContractError('optimizer was not fresh')
        checkpoint=json.loads((root/name/'checkpoint_manifest.json').read_text())
        if checkpoint['state']!=name or checkpoint['updates']!=128 or checkpoint['plan_sha256']!=identity_hash(plan):
            raise ContractError('checkpoint dose/identity differs')
    for state in plan['evaluation']['states']:
        name='eval_'+state;summary,samples=inspect_phase(root,plan,name,evaluation=True);summaries.append(summary)
        if summary['finished']:
            inp=json.loads((root/name/'input_receipt.json').read_text())
            expected_identity=initial_identity if state=='R' else identity_hash(json.loads((root/state/'checkpoint_manifest.json').read_text()))
            if inp['source_identity']!=expected_identity: raise ContractError('evaluation source state differs')
            maps[state]=score_maps(samples,plan['eval_ids'])
    result={'plan_sha256':identity_hash(plan),'source_commit':intent['source_commit'],'phases':summaries,
            'training_updates_committed':sum(x['committed_updates'] for x in summaries),
            'new_completions_saved':sum(x['saved_backend_completions'] for x in summaries),
            'optimizer_steps_with_uncertain_commit':{x['phase']:x['optimizer_steps_with_uncertain_commit'] for x in summaries if x['optimizer_steps_with_uncertain_commit']},
            'reserved_completions':sum(x['reserved_completions'] for x in summaries),
            'complete':all(x['finished'] for x in summaries),'training_replicates':1,
            'checkpoint_bytes_must_be_independently_verified_on_server':True,
            'limitations':['exploratory observed benchmark; not contamination-free confirmation',
                           'one training replicate; question intervals do not measure training randomness',
                           'official test union is not semantic truth','EvalPlus inner FAIL attribution remains limited']}
    if result['complete']:
        if result['training_updates_committed']!=640 or result['new_completions_saved']!=16384:
            raise ContractError('total frozen dose differs')
        if not (root/'screen_complete.json').exists(): raise ContractError('parent closeout absent')
        result['scores_percent']={s:{k:100*sum(v.values())/len(v) for k,v in ms.items()} for s,ms in maps.items()}
        result['contrasts']={a+'_minus_'+b:paired_question_interval(maps[a]['union'],maps[b]['union']) for a,b in
            [('W_future','R_future'),('W_future','C_future'),('C_future','R_future'),('W_prefix','R'),('C_prefix','R')]}
        result['decision']=descriptive_decision(result['contrasts'])
    else:
        result['decision']={'scientific_contrasts':'withheld_incomplete','automatic_retry':False,'scientific_failure_established':False}
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();durable_json(a.out,analyze(a.root))

if __name__=='__main__': main()

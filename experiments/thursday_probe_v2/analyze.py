"""Independently replay saved tokens; paired discovery estimates, never invented scores."""
import argparse
from collections import Counter,defaultdict
import csv
import json
from pathlib import Path

import numpy as np

from analyses.completion_contract import first_stop
from experiments.thursday_probe.common import dump,jsonl,SEEDS
from experiments.thursday_probe.arithmetic_eval import score
from experiments.thursday_probe_v2.config import ROOT,DATA,RELEASE,OUT,STATES,LIMITS
from experiments.thursday_probe_v2.queue import load_inputs
from experiments.thursday_probe_v2.training import atomic_json
from scripts.audit_family_matching import verified_tokenizer
from src.countdown_smoke import canonical,safe_parse
from src.sft_data import prefix,read_jsonl,sha256_file
from src.trace_audit import audit_trace

N_BOOTSTRAP=10000


def csv_write(path,rows):
    if not rows:raise ValueError('Do not create an empty result table')
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with Path(path).open('x',newline='') as f:
        w=csv.DictWriter(f,keys);w.writeheader();w.writerows(rows)


def paired_interval(values,clusters):
    values=np.asarray(values,dtype=float)
    if not len(values):return dict(mean=None,questions=0,clusters=0,question_ci=None,cluster_ci=None)
    rng=np.random.default_rng(SEEDS['bootstrap'])
    samples=rng.integers(0,len(values),(N_BOOTSTRAP,len(values)))
    qmeans=values[samples].mean(axis=1)
    groups=defaultdict(list)
    for i,c in enumerate(clusters):groups[c].append(i)
    ckeys=sorted(groups)
    if len(ckeys)>1:
        sums=np.array([values[groups[c]].sum() for c in ckeys]);sizes=np.array([len(groups[c]) for c in ckeys])
        draws=rng.integers(0,len(ckeys),(N_BOOTSTRAP,len(ckeys)))
        cmeans=sums[draws].sum(axis=1)/sizes[draws].sum(axis=1)
        cci=np.quantile(cmeans,[.025,.975]).tolist()
    else:cci=None
    return dict(mean=float(values.mean()),questions=len(values),clusters=len(ckeys),
                question_ci=np.quantile(qmeans,[.025,.975]).tolist(),cluster_ci=cci)


def audit_records(path,rows,tokenizer):
    by={r['problem_id']:r for r in rows};records=read_jsonl(path);audited=[]
    decode=lambda ids:tokenizer.decode(ids,skip_special_tokens=True,clean_up_tokenization_spaces=False)
    for r in records:
        problem=by[r['problem_id']];ids=r['batch_output_ids'];forced=r['forced_prefix']
        stop=first_stop(ids,decode,tokenizer.eos_token_id,512,set(tokenizer.all_special_ids)|{t for t in ids if t>=len(tokenizer)})
        if (stop!=r['stop'] or r['generated_ids']!=ids[:stop['retained_tokens']]
            or any(t!=tokenizer.eos_token_id for t in ids[stop['retained_tokens']:])
            or r['prompt_ids']!=tokenizer.encode(prefix(problem['prompt'])+forced,add_special_tokens=False)
            or score(problem,stop,forced)!=r['score']):
            raise ValueError('Independent token/stop/prompt/score mismatch: '+path.name)
        family='unknown'
        if problem['task']=='construct' and r['score']['correct']:
            key=canonical(safe_parse(r['score']['expression']))
            family=next((f for f,p in problem.get('paths',{}).items() if p['path_id']==key),'unknown')
        trace=r['score']['trace_status']
        if problem['task']=='compute':
            text=forced+stop['answer_segment']
            # Numeric tasks require a numeric answer, not an input-use expression.
            # Audit displayed steps against the supplied input expression separately.
            lines=text.splitlines()
            answer_lines=[i for i,s in enumerate(lines) if s.strip().startswith('Answer:')]
            if len(answer_lines)==1:
                lines[answer_lines[0]]='Answer: '+problem['expression']
                trace=audit_trace('\n'.join(lines),problem['numbers'],
                                  __import__('fractions').Fraction(problem['answer']))['complete_trace_status']
                if not r['score']['answer_correct_ignoring_stop'] and r['score']['parsed']:
                    trace='inconsistent'
            else:trace='unverifiable'
        audited.append(dict(**r,reference_program_class=family,independent_trace_status=trace))
    if len({(r['problem_id'],r['sample_index']) for r in audited})!=len(audited):
        raise ValueError('Duplicate predictions')
    return audited


def per_question(records):
    groups=defaultdict(list)
    for r in records:groups[r['problem_id']].append(r)
    result={}
    for pid,rs in groups.items():
        n=len(rs);k=sum(r['score']['correct'] for r in rs)
        result[pid]=dict(n=n,correct_samples=k,pass_at_1=k/n,
            pass_at_4=(1.0 if k else 0.0) if n==4 else None,
            parse_fraction=sum(r['score']['parsed'] for r in rs)/n,
            complete_fraction=sum(r['score']['completed'] for r in rs)/n,
            verified_trace_fraction=sum(r['independent_trace_status']=='verified' and r['score']['completed'] for r in rs)/n,
            stop_reasons=dict(Counter(r['stop']['stop_reason'] for r in rs)),
            failures=dict(Counter(r['score']['failure'] for r in rs)),
            program_class=dict(Counter(r['reference_program_class'] for r in rs)))
    return result


def analyze(snapshot,out=OUT):
    out=Path(out);manifest=json.loads((out/'run_manifest_final.json').read_text())
    if manifest['status']!='completed':
        raise ValueError('Use a separately labeled partial audit for an incomplete queue; no fake four-cell table')
    inputs,_,_,_,_=load_inputs();tokenizer,_=verified_tokenizer(Path(snapshot))
    audit_dir=out/'independent_audit';audit_dir.mkdir()
    all_records={};hashes={};failures=[];perq=[]
    for event in manifest['evaluations']:
        name=event['name'];key='discovery_problems' if event['view'].startswith('discovery_') else event['view']
        path=out/(name+'.jsonl')
        if sha256_file(path)!=event['predictions_sha256']:raise ValueError('Prediction bytes changed')
        rs=audit_records(path,inputs[key],tokenizer)
        if len(rs)!=event['generations']:raise ValueError('Wrong generation denominator')
        all_records[name]=rs;hashes[name]=sha256_file(path)
        qs=per_question(rs)
        if len(qs)!=event['questions'] or any(x['n']!=event['samples'] for x in qs.values()):
            raise ValueError('Missing per-question sample')
        perq.extend(dict(state=event['state'],view=event['view'],problem_id=pid,**r) for pid,r in qs.items())
        failures.append(dict(state=event['state'],view=event['view'],generations=len(rs),
            questions=len(qs),failures=dict(Counter(r['score']['failure'] for r in rs)),
            stops=dict(Counter(r['stop']['stop_reason'] for r in rs)),
            traces=dict(Counter(r['independent_trace_status'] for r in rs)),
            reference_program_class=dict(Counter(r['reference_program_class'] for r in rs)),
            retained_length_quantiles=np.quantile([len(r['generated_ids']) for r in rs],[0,.25,.5,.75,.95,1]).tolist()))
    if sum(len(r) for r in all_records.values())!=LIMITS['planned_generations']:
        raise ValueError('Overall generation total differs')
    jsonl(audit_dir/'per_question.jsonl',perq);dump(audit_dir/'failure_breakdown.json',failures)
    data_audit=json.loads((RELEASE/'DATA_AUDIT_v2.json').read_text())
    groups=data_audit['reference_subgroups']['discovery']['groups']
    problems={p['problem_id']:p for p in inputs['discovery_problems']}
    table=[];contrasts={};gains=[]
    for group,ids in groups.items():
        ids=sorted(ids);clusters=[problems[pid]['paths']['B']['structure_id'] for pid in ids]
        for view,metric in (('discovery_sampled','pass_at_1'),('discovery_sampled','pass_at_4'),('discovery_greedy','pass_at_1')):
            arrays={s:np.array([per_question(all_records[s+'_'+view])[pid][metric] for pid in ids]) for s in STATES}
            vectors=dict(arrays,delta_C=arrays['C-P']-arrays['C-S'],delta_B=arrays['B-P']-arrays['B-S'],
                         interaction=(arrays['B-P']-arrays['B-S'])-(arrays['C-P']-arrays['C-S']))
            for state,values in vectors.items():
                stat=paired_interval(values,clusters)
                row=dict(subgroup=group,state_or_contrast=state,view=view,metric=metric,
                    estimate=stat['mean'],questions=stat['questions'],template_clusters=stat['clusters'],
                    question_ci_low=stat['question_ci'][0] if stat['question_ci'] else None,
                    question_ci_high=stat['question_ci'][1] if stat['question_ci'] else None,
                    cluster_ci_low=stat['cluster_ci'][0] if stat['cluster_ci'] else None,
                    cluster_ci_high=stat['cluster_ci'][1] if stat['cluster_ci'] else None)
                table.append(row)
                if state not in STATES:contrasts[group+'/'+view+'/'+metric+'/'+state]=stat
            for a,b in (('C-S','C-P'),('B-S','B-P'),('C','B'),('C','C-S'),('C','C-P'),('B','B-S'),('B','B-P')):
                gains.extend(dict(subgroup=group,view=view,metric=metric,problem_id=pid,
                    from_state=a,to_state=b,before=float(x),after=float(y),difference=float(y-x),
                    direction='gain' if y>x else 'loss' if y<x else 'tie') for pid,x,y in zip(ids,arrays[a],arrays[b]))
    csv_write(ROOT/'FOUR_CELL_RESULTS.csv',table)
    jsonl(audit_dir/'paired_gain_loss.jsonl',gains)
    dump(audit_dir/'paired_intervals.json',dict(estimates=contrasts,bootstrap_replicates=N_BOOTSTRAP,
        seed=SEEDS['bootstrap'],cluster_definition='Reference B canonical structure ID, fixed before model outputs.',
        limits='Question/template resampling only; excludes all training/prep/assignment seed variability. Single-template strata have no cluster interval.'))
    prep=[]
    base_means={}
    for state in ('C0','C','B'):
        for cat in ('atomic','target','control'):
            rows=[r for r in all_records[state+'_probes'] if r['category']==cat]
            qs=per_question(rows);values=[x['pass_at_1'] for x in qs.values()]
            stat=paired_interval(values,[cat]*len(values))
            if state=='C0':base_means[cat]=stat['mean']
            prep.append(dict(state=state,category=cat,questions=len(qs),samples_per_question=4,
                pass_at_1=stat['mean'],change_from_C0=stat['mean']-base_means[cat],
                question_ci_low=stat['question_ci'][0],question_ci_high=stat['question_ci'][1],
                parse_fraction=sum(r['score']['parsed'] for r in rows)/len(rows),
                completed_fraction=sum(r['score']['completed'] for r in rows)/len(rows),
                length_caps=sum(r['stop']['stop_reason']=='length_cap' for r in rows)))
    csv_write(ROOT/'PREP_MANIPULATION_CHECK.csv',prep)
    pm={(r['state'],r['category']):r['pass_at_1'] for r in prep}
    manipulation=dict(delta_target=pm['B','target']-pm['C','target'],delta_control=pm['B','control']-pm['C','control'])
    manipulation['D']=manipulation['delta_target']-manipulation['delta_control']
    manipulation['descriptive_only_not_a_training_gate']=True
    rng=np.random.default_rng(SEEDS['bootstrap'])
    draws={}
    for cat in ('target','control'):
        c=per_question([r for r in all_records['C_probes'] if r['category']==cat])
        b=per_question([r for r in all_records['B_probes'] if r['category']==cat])
        ids=sorted(c);diff=np.array([b[pid]['pass_at_1']-c[pid]['pass_at_1'] for pid in ids])
        draws[cat]=diff[rng.integers(0,len(diff),(N_BOOTSTRAP,len(diff)))].mean(axis=1)
        manipulation['delta_'+cat+'_paired_question_ci']=np.quantile(draws[cat],[.025,.975]).tolist()
    manipulation['D_stratified_paired_question_ci']=np.quantile(draws['target']-draws['control'],[.025,.975]).tolist()
    manipulation['cluster_interval']=None
    manipulation['cluster_limitation']='Each compute category has one canonical template; no across-template population interval can be estimated.'
    dump(audit_dir/'manipulation_contrasts.json',manipulation)
    sentinel_ids={r['problem_id'] for r in inputs['sentinel']};sentinel=[]
    for state in ('C0',)+STATES:
        rs=([r for r in all_records[state+'_probes'] if r['problem_id'] in sentinel_ids and r['sample_index']<2]
            if state in ('C0','C','B') else all_records[state+'_sentinel'])
        for category in ('atomic','target','control'):
            sub=[r for r in rs if r['category']==category];qs=per_question(sub)
            sentinel.append(dict(state=state,category=category,questions=len(qs),samples_per_question=2,
                pass_at_1=sum(x['pass_at_1'] for x in qs.values())/len(qs),
                parse_fraction=sum(r['score']['parsed'] for r in sub)/len(sub),
                completed_fraction=sum(r['score']['completed'] for r in sub)/len(sub),
                source='first_two_parent_samples' if state in ('C0','C','B') else 'new_endpoint_sampling'))
    csv_write(ROOT/'POST_MAIN_SENTINEL.csv',sentinel)
    cal=json.loads((out/'ARITH_CALIBRATION_RESULTS.json').read_text())
    dump(ROOT/'ARITH_CALIBRATION_RESULTS.json',cal)
    atomic_json(ROOT/'RUN_MANIFEST_v2.json',manifest)
    dump(audit_dir/'summary.json',dict(status='all_raw_streams_independently_verified',generations=4704,
        files_sha256=hashes,reference_subgroups=groups,manipulation=manipulation,
        reserved_test_contents_read=False))
    return dict(table=table,prep=prep,sentinel=sentinel,calibration=cal,manipulation=manipulation)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--tokenizer-dir',required=True);p.add_argument('--run-dir',default=str(OUT))
    a=p.parse_args();result=analyze(a.tokenizer_dir,a.run_dir)
    print(json.dumps(dict(manipulation=result['manipulation'],four_cell_rows=len(result['table'])),indent=2))

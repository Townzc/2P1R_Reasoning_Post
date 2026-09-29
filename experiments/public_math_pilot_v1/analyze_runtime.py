"""CPU-only scoring and paired question inference; never imports the GPU runtime."""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import re
import threading
import time
import uuid

import numpy as np

from .scoring import MathScorer, environment_identity

ARMS=('SFT','DFT','TrimSFT','QDW_v0')
RELEASE_SHA='f7c67a1c523c3ec5dfbd1ae63506a9ce91dd03683643dcf3b7a72c70b16fa370'
_LOCAL=threading.local()
_SCORERS=[]
_LOCK=threading.Lock()


def read(path):return json.loads(Path(path).read_text())


def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),
        ensure_ascii=False,allow_nan=False).encode()).hexdigest()


def publish(path,value,replace=False):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists() and not replace:
        if read(path)!=value:raise ValueError('Existing analysis record differs')
        return
    tmp=path.with_name(path.name+'.pending_'+uuid.uuid4().hex)
    with tmp.open('x') as f:
        json.dump(value,f,sort_keys=True,indent=2,ensure_ascii=False,allow_nan=False)
        f.write('\n');f.flush();os.fsync(f.fileno())
    os.replace(tmp,path)
    fd=os.open(path.parent,os.O_RDONLY)
    try:os.fsync(fd)
    finally:os.close(fd)


def load_references(release):
    release=Path(release)
    if sha(release/'manifest.json')!=RELEASE_SHA:raise ValueError('Frozen release differs')
    manifest=read(release/'manifest.json');result={}
    for name in ('dev','math500','gsm8k'):
        filename=name+'.jsonl'
        if sha(release/filename)!=manifest['files_sha256'][filename]:raise ValueError('Frozen reference SHA differs')
        result[name]=[json.loads(s) for s in (release/filename).read_text().splitlines()]
    return result


def run_catalog():
    jobs=[dict(name='Base-dev',dataset='dev',arm='Base',step=0,draw=None)]
    for arm in ('Base',*ARMS):
        jobs.append(dict(name=arm+'-GSM8K',dataset='gsm8k',arm=arm,step=0 if arm=='Base' else 128,draw=None))
        for j in range(8):jobs.append(dict(name=f'{arm}-MATH500-draw{j}',dataset='math500',arm=arm,
            step=0 if arm=='Base' else 128,draw=j))
    for arm in ARMS:
        for step in (64,128):jobs.append(dict(name=f'{arm}-step{step}-dev',dataset='dev',arm=arm,step=step,draw=None))
    return jobs


def load_complete_run(out,preflight,job,reference_rows):
    folder=Path(out)/'generation'/job['name'];meta=read(folder/'identity.json')
    expected_ids=[r['problem_id'] for r in reference_rows]
    if meta['logical_name']!=job['name'] or meta['all_ids']!=expected_ids:
        raise ValueError('Generation roster differs from the full frozen dataset')
    results={}
    for path in sorted(folder.glob('batch_*.json')):
        if not re.fullmatch(r'batch_[0-9]{5}\.json',path.name):continue
        value=read(path);request=value['request'];records=value['records']
        if (request['logical_name']!=job['name'] or request['model']!=meta['model']
                or request['decoding']!=meta['decoding'] or digest(records)!=value['records_sha256']
                or [r['id'] for r in records]!=request['row_ids']
                or [r['prompt_sha256'] for r in records]!=request['prompt_sha256']):
            raise ValueError('Raw generation batch identity/SHA differs')
        for record in records:
            if record['id'] in results:raise ValueError('Duplicate generated row')
            results[record['id']]=record
    if meta['reused_ids']:
        if job['name']!='Base-dev' or len(meta['reused_ids'])!=32:
            raise ValueError('Unexpected preflight reuse')
        reuse=read(Path(out)/'preflight_reuse.json')
        if sha(Path(preflight)/'PREFLIGHT_RECEIPT.json')!=reuse['preflight_receipt_sha256']:
            raise ValueError('Preflight receipt changed')
        imported={}
        for path in sorted((Path(preflight)/'base_dev32').glob('*.outputs.json')):
            for record in read(path)['records']:
                if record['id'] in imported:raise ValueError('Duplicate preflight row')
                old=dict(record['identity']);old.pop('source_commit')
                if old!=meta['model']:raise ValueError('Reused Base identity differs')
                imported[record['id']]=record
        if set(imported)!=set(meta['reused_ids']) or set(imported).intersection(results):
            raise ValueError('Preflight reuse coverage differs')
        results.update(imported)
    if set(results)!=set(expected_ids):raise ValueError('Incomplete official denominator')
    ordered=[results[pid] for pid in expected_ids]
    if digest(ordered)!=read(folder/'COMPLETE.json')['records_sha256']:
        raise ValueError('Completed run SHA differs')
    return ordered,meta


def _init_scorer():
    judge=MathScorer(timeout_seconds=3.0);judge._start();_LOCAL.judge=judge
    with _LOCK:_SCORERS.append(judge)


def score_one(item):
    record,reference,dataset,path,scorer_hash=item
    identity=dict(raw_record_sha256=digest(record),reference_sha256=digest(reference),
        scorer_identity_sha256=scorer_hash,dataset=dataset,problem_id=record['id'])
    if Path(path).exists():
        old=read(path)
        if old['identity']!=identity:raise ValueError('Existing score identity differs')
        return old
    judge=_LOCAL.judge;attempts=[judge.score(record['raw_text'],reference,dataset)]
    if attempts[-1].get('reason') in ('judge_timeout','judge_unavailable','judge_process_failure'):
        # One logged CPU infrastructure retry, never a new model completion.
        attempts.append(judge.score(record['raw_text'],reference,dataset,timeout_seconds=15.0))
    result=dict(identity=identity,attempts=attempts,judgment=attempts[-1],
        raw_record=dict(id=record['id'],output_tokens=record['output_tokens'],stop_reason=record['stop_reason']),
        model_generations_added=0)
    publish(path,result);return result


def outcome_bounds(scores,draws):
    """rows are questions, columns are dependent repeated completions."""
    values=np.asarray(scores,dtype=object)
    if values.ndim!=2 or values.shape[1]!=draws or values.shape[0]==0:
        raise ValueError('Complete per-question draw matrix required')
    for value in values.flat:
        if value is not None and type(value) is not bool:raise ValueError('Invalid correctness value')
    lower=np.asarray([[float(v is True) for v in r] for r in values],dtype=np.float64)
    upper=np.asarray([[float(v is not False) for v in r] for r in values],dtype=np.float64)
    return dict(questions=len(values),draws=draws,expected_outputs=values.size,
        correct=sum(v is True for v in values.flat),wrong=sum(v is False for v in values.flat),
        unresolved=sum(v is None for v in values.flat),
        average_lower=float(lower.mean()),average_upper=float(upper.mean()),
        pass_at_draws_lower=float(lower.max(axis=1).mean()),pass_at_draws_upper=float(upper.max(axis=1).mean()),
        per_question_lower=lower.mean(axis=1).tolist(),per_question_upper=upper.mean(axis=1).tolist(),
        point_estimate=float(lower.mean()) if all(v is not None for v in values.flat) else None)


def paired_bounds(treatment,control,confidence,replicates=10000):
    lo=np.asarray(treatment['per_question_lower'])-np.asarray(control['per_question_upper'])
    hi=np.asarray(treatment['per_question_upper'])-np.asarray(control['per_question_lower'])
    if len(lo)!=treatment['questions'] or treatment['questions']!=control['questions']:
        raise ValueError('Paired question counts differ')
    rng=np.random.default_rng(2026091814);boot_lo=[];boot_hi=[]
    for start in range(0,replicates,250):
        idx=rng.integers(0,len(lo),size=(min(250,replicates-start),len(lo)))
        boot_lo.extend(lo[idx].mean(axis=1).tolist());boot_hi.extend(hi[idx].mean(axis=1).tolist())
    alpha=(1-confidence)/2
    return dict(question_count=len(lo),replicates=replicates,seed=2026091814,confidence=confidence,
        mean_difference_lower=float(lo.mean()),mean_difference_upper=float(hi.mean()),
        paired_bootstrap_interval=[float(np.quantile(boot_lo,alpha)),float(np.quantile(boot_hi,1-alpha))],
        unresolved_scores_bounded_not_dropped=bool(treatment['unresolved'] or control['unresolved']),
        resampling_unit='whole_question_including_all_draws',training_seed_uncertainty_included=False)


def aggregate(scored,references):
    results={};dev={};comparisons={}
    for arm in ('Base',*ARMS):
        methods={}
        for dataset,draws in (('gsm8k',1),('math500',8)):
            names=[arm+'-GSM8K'] if draws==1 else [f'{arm}-MATH500-draw{j}' for j in range(8)]
            ready=[n for n in names if n in scored]
            if len(ready)!=len(names):
                methods[dataset]=dict(status='incomplete',completed_runs=len(ready),required_runs=len(names),
                    official_questions=len(references[dataset]));continue
            question_ids=[r['problem_id'] for r in references[dataset]]
            indexed=[{s['identity']['problem_id']:s for s in scored[n]} for n in names]
            if any(set(d)!=set(question_ids) for d in indexed):raise ValueError('Score question coverage differs')
            matrix=[[d[pid]['judgment']['correct'] for d in indexed] for pid in question_ids]
            bounds=outcome_bounds(matrix,draws)
            all_rows=[s for n in names for s in scored[n]]
            methods[dataset]=dict(status='scored',**bounds,
                mean_output_tokens=sum(s['raw_record']['output_tokens'] for s in all_rows)/len(all_rows),
                length_cap_fraction=sum(s['raw_record']['stop_reason']=='length_cap' for s in all_rows)/len(all_rows),
                unresolved_reasons=dict(Counter(s['judgment'].get('reason','unspecified') for s in all_rows if s['judgment']['correct'] is None)),
                parse_failures=sum(s['judgment'].get('parseable') is False for s in all_rows))
        results[arm]=methods
    for name,rows in scored.items():
        if name.endswith('-dev'):
            dev[name]=outcome_bounds([[s['judgment']['correct']] for s in rows],1)
    for dataset in ('math500','gsm8k'):
        if any(results[a][dataset]['status']!='scored' for a in ARMS):continue
        comparisons[dataset]={}
        for control in ('DFT','TrimSFT','SFT'):
            confidence=.95 if control=='SFT' else .975
            comparisons[dataset]['QDW_v0-minus-'+control]=paired_bounds(results['QDW_v0'][dataset],results[control][dataset],confidence)
    return dict(schema=1,methods=results,dev=dev,paired_comparisons=comparisons,
        primary_comparisons='MATH avg@8: QDW-DFT and QDW-TrimSFT, each97.5% two-sided; Bonferroni family95%',
        gsm_intervals='secondary descriptive; same97.5% widths, not an additional confirmatory family',
        training_seed=17,training_seeds=1,completed_scored_runs=sorted(scored),
        known_reference_boundary='Official math500-test-0097 normalizes to empty; all its outputs remain unresolved. Bounds retain all500 questions.',
        accuracy_gate_used=False,optional_experiments_run=False)


def write_tables(out,report):
    out=Path(out);rows=[]
    for arm,metrics in report['methods'].items():
        for dataset,record in metrics.items():
            rows.append(dict(method=arm,dataset=dataset,status=record['status'],
                questions=record.get('questions',record.get('official_questions')),
                avg_lower=record.get('average_lower'),avg_upper=record.get('average_upper'),
                point_estimate=record.get('point_estimate'),unresolved=record.get('unresolved'),
                pass_at_k_lower=record.get('pass_at_draws_lower'),pass_at_k_upper=record.get('pass_at_draws_upper'),
                mean_output_tokens=record.get('mean_output_tokens'),length_cap_fraction=record.get('length_cap_fraction')))
    text=io.StringIO();writer=csv.DictWriter(text,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    tmp=out/'PUBLIC_RESULTS.csv.pending';tmp.write_text(text.getvalue());os.replace(tmp,out/'PUBLIC_RESULTS.csv')
    lines=['# Public-math pilot results','',
        'All completed estimates retain official denominators. Unresolved judgments are bounded, never counted as wrong or removed. One training seed does not measure training-seed variability.','',
        '| Method | MATH avg@8 | GSM8K greedy |','|---|---:|---:|']
    def fmt(m):
        if m['status']!='scored':return 'Pending'
        a,b=m['average_lower']*100,m['average_upper']*100
        return f'{a:.2f}%' if a==b else f'[{a:.2f}, {b:.2f}]%'
    for arm,metrics in report['methods'].items():lines.append(f"| {arm} | {fmt(metrics['math500'])} | {fmt(metrics['gsm8k'])} |")
    lines.extend(['','MATH reports average@8; pass@8 is secondary in the JSON/CSV. Ranges are unresolved-score bounds, not confidence intervals. Paired bootstrap intervals are in PAIRED_COMPARISONS.json.','',report['known_reference_boundary'],''])
    tmp=out/'RESULTS.md.pending';tmp.write_text('\n'.join(lines));os.replace(tmp,out/'RESULTS.md')


def run(args):
    out=Path(args.output);analysis=out/'analysis';analysis.mkdir(parents=True,exist_ok=True)
    refs=load_references(args.release);env=environment_identity()
    identity=dict(environment=env,scoring_source_sha256=sha(Path(__file__).with_name('scoring.py')),
        first_timeout_seconds=3.,infrastructure_retry_timeout_seconds=15.,max_infrastructure_retries=1,
        generated_math_errors_resampled=False,empty_reference_policy='unresolved_full_denominator')
    publish(analysis/'SCORER_IDENTITY.json',identity);scorer_hash=digest(identity)
    jobs=run_catalog();scored={}
    try:
        with ThreadPoolExecutor(max_workers=4,initializer=_init_scorer) as pool:
            while time.time()+30<args.deadline_unix:
                changed=False
                for job in jobs:
                    if job['name'] in scored or not (out/'generation'/job['name']/'COMPLETE.json').exists():continue
                    records,meta=load_complete_run(out,args.preflight,job,refs[job['dataset']])
                    lookup={r['problem_id']:r['reference'] for r in refs[job['dataset']]}
                    items=[(r,lookup[r['id']],job['dataset'],analysis/'scores'/job['name']/(r['id']+'.json'),scorer_hash) for r in records]
                    values=list(pool.map(score_one,items));scored[job['name']]=values;changed=True
                    publish(analysis/'runs'/(job['name']+'.json'),dict(job=job,model=meta['model'],
                        outputs=len(values),score_sha256=digest(values),raw_complete_sha256=sha(out/'generation'/job['name']/'COMPLETE.json')))
                    print(json.dumps(dict(event='run_scored',run=job['name'],outputs=len(values),
                        correct=sum(s['judgment']['correct'] is True for s in values),
                        unresolved=sum(s['judgment']['correct'] is None for s in values))),flush=True)
                if changed or not (analysis/'PUBLIC_RESULTS.json').exists():
                    report=aggregate(scored,refs)
                    publish(analysis/'snapshots'/f'snapshot_{len(scored):03d}.json',report)
                    publish(analysis/'PUBLIC_RESULTS.json',report,replace=True)
                    publish(analysis/'PAIRED_COMPARISONS.json',report['paired_comparisons'],replace=True)
                    write_tables(analysis,report)
                if len(scored)==len(jobs):
                    publish(analysis/'SCORING_COMPLETE.json',dict(scored_runs=len(jobs),scored_outputs=31203,
                        scorer_identity_sha256=scorer_hash,report_sha256=sha(analysis/'PUBLIC_RESULTS.json'),
                        grading_fully_resolved=all(s['judgment']['correct'] is not None for vv in scored.values() for s in vv),
                        raw_outputs_preserved=True,no_new_model_calls=True))
                    return dict(status='scoring_complete',runs=len(jobs))
                if not args.watch:return dict(status='current_available_runs_scored',runs=len(scored))
                time.sleep(10)
    finally:
        for scorer in _SCORERS:scorer.close()
    return dict(status='paused_at_daytime_boundary',runs=len(scored))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('release','output','preflight'):p.add_argument('--'+name,required=True)
    p.add_argument('--deadline-unix',type=float,required=True);p.add_argument('--watch',action='store_true')
    print(json.dumps(run(p.parse_args()),sort_keys=True),flush=True)

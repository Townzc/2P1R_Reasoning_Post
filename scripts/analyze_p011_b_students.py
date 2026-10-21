"""Once-only B interactions of new saved labels and original frozen T0.8 labels."""
import argparse
from pathlib import Path
import os
import threading
import time
from experiments.p011 import b_students_path as b_path
from experiments.sft_allocation_midpoint.common import read,dump,sha,manifest,digest
from analyses.p011_b_contrasts import contrast

ROOT=Path(__file__).resolve().parents[1]
OLD='reports/p010_20261019/c9_complete_students_v1'


def old_vectors(root,metric,binding):
    label='MATH_GREEDY' if metric=='greedy' else 'MATH_SAMPLED'
    folder=root/OLD;p=folder/(label+'_VECTORS.json');meta=read(folder/'MANIFEST.json')[p.name]
    if sha(p)!=meta['sha256'] or p.stat().st_size!=meta['bytes']:raise ValueError('Original fixed T08 vector bytes differ')
    binding[str(p.relative_to(root))]=meta
    values=read(p)
    return {'T08_K1':values['t15_n400_k1'],'T08_K8':values['t15_n400_k8']}


def new_vectors(root,spec,ids,metric,binding):
    vectors={}
    for run in ('B1','B3'):
        job=spec['jobs']['B_'+run+'_s17_r1'];folder=root/b_path.LOCAL/'b_io_r1/score'/b_path.logical(job)
        closed=read(folder/'COMPLETED.json');payload=folder/'owned_score/payload';proof=read(payload/'COMPLETED.json')
        oracle=root/b_path.LOCAL/'b_io_r1/audit'/b_path.logical(job)/'COMPLETE_PROOF.json'
        exact=read(oracle);saved=read(payload/'INTENT.json')['binding']
        if (exact.get('passed') is not True or exact['job_sha256']!=digest(job)
                or exact['source_files']!=spec['source_files']
                or saved['job_sha256']!=digest(job) or saved['source_files']!=spec['source_files']
                or saved['oracle_sha256']!=sha(oracle)):
            raise ValueError('Actual complete B job/source/oracle binding differs')
        if closed['read_only_saved_score_proof']['passed'] is not True or proof['technical_unknown']!=0:
            raise ValueError('Only complete original frozen B labels may enter analysis')
        p=payload/'ALL_SCORED_ROWS.json'
        if sha(p)!=proof['scored_rows_sha256']:raise ValueError('New frozen labels changed')
        binding[str(p.relative_to(root))]=dict(sha256=sha(p),bytes=p.stat().st_size)
        table={}
        for r in read(p):
            label,pid=r['id'].split('::',1)
            if (label,pid) in table or type(r['score']['correct']) is not bool:raise ValueError('Duplicate/unknown score')
            table[label,pid]=r['score']['correct']
        expected={(label,pid) for label in ('greedy','sample0','sample1','sample2','sample3') for pid in ids}
        if set(table)!=expected:raise ValueError('All original five500-question endpoints required')
        values=([table['greedy',pid] for pid in ids] if metric=='greedy' else
                [sum(table['sample'+str(i),pid] for i in range(4))/4 for pid in ids])
        vectors[run]=dict(complete=True,technical_unknown=0,question_ids=ids,question_values=values,metric=metric)
        if metric!='greedy':vectors[run]['samples_per_question']=4
    return vectors


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--review',required=True);args=p.parse_args()
    specfile=ROOT/b_path.SPEC_FILES['student']
    spec=b_path.validate(read(specfile));review=b_path.reviewed(spec,specfile,read(args.review));b_path.published(ROOT,spec)
    if time.time()>=b_path.CUTOFF:raise TimeoutError('Original result cutoff')
    out=ROOT/b_path.LOCAL/'b_analysis_r1';out.mkdir(exist_ok=False)
    dump(out/'INTENT.json',dict(review=review,source_files=spec['source_files'],new_model_calls=0,new_scores=0))
    timer=threading.Timer(min(300,b_path.CUTOFF-time.time()),lambda:os._exit(124));timer.daemon=True;timer.start()
    try:
        bindings={}
        for metric in ('greedy','sampled_mean_pass_at_1'):
            old=old_vectors(ROOT,metric,bindings);ids=old['T08_K1']['question_ids']
            values={**old,**new_vectors(ROOT,spec,ids,metric,bindings)}
            dump(out/(metric+'_VECTORS.json'),values)
            dump(out/(metric+'_CONTRASTS.json'),contrast(values,ids,metric))
        if time.time()>=b_path.CUTOFF:raise TimeoutError('Original result cutoff')
        dump(out/'COMPLETED.json',dict(input_files=bindings,actual_A3_pending=True,
            old_bootstrap_or_scoring_repeated=False,new_contrasts_only=True))
        dump(out/'MANIFEST.json',manifest(out))
    except BaseException as exc:
        dump(out/'FAILED.json',dict(type=type(exc).__name__,error=str(exc),automatic_retry=False));raise
    finally:timer.cancel()


if __name__=='__main__':main()

"""Once-only C2 interactions of new saved labels and original frozen T0.8 labels."""
import argparse
from pathlib import Path
import os
import threading
import time
from experiments.p011 import c2_path
from experiments.sft_allocation_midpoint.common import read,dump,sha,manifest,digest
from analyses.p011_c2_contrast import contrast

ROOT=Path(__file__).resolve().parents[1]



def endpoint_ids(rows):
    from experiments.p011.c2_student_execution import endpoint_rows
    return [r['problem_id'] for r in endpoint_rows(rows)]


def new_vectors(root,spec,ids,metric,binding):
    vectors={}
    for run in ('C2a','C2b'):
        job=spec['jobs']['C2_'+run+'_s17_r1'];folder=root/c2_path.LOCAL/'c2_io_r1/score'/c2_path.logical(job)
        closed=read(folder/'COMPLETED.json');payload=folder/'owned_score/payload';proof=read(payload/'COMPLETED.json')
        oracle=root/c2_path.LOCAL/'c2_io_r1/audit'/c2_path.logical(job)/'COMPLETE_PROOF.json'
        exact=read(oracle);saved=read(payload/'INTENT.json')['binding']
        if (exact.get('passed') is not True or exact['job_sha256']!=digest(job)
                or exact['source_files']!=spec['source_files']
                or saved['job_sha256']!=digest(job) or saved['source_files']!=spec['source_files']
                or saved['oracle_sha256']!=sha(oracle)):
            raise ValueError('Actual complete C2 job/source/oracle binding differs')
        if closed['read_only_saved_score_proof']['passed'] is not True or proof['technical_unknown']!=0:
            raise ValueError('Only complete original frozen C2 labels may enter analysis')
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
    specfile=ROOT/c2_path.SPEC_FILES['student']
    spec=c2_path.validate(read(specfile));review=c2_path.reviewed(spec,specfile,read(args.review));c2_path.published(ROOT,spec)
    if time.time()>=c2_path.CUTOFF:raise TimeoutError('Original result cutoff')
    out=ROOT/c2_path.LOCAL/'c2_analysis_r1';out.mkdir(exist_ok=False)
    dump(out/'INTENT.json',dict(review=review,source_files=spec['source_files'],new_model_calls=0,new_scores=0))
    timer=threading.Timer(min(300,c2_path.CUTOFF-time.time()),lambda:os._exit(124));timer.daemon=True;timer.start()
    try:
        bindings={}
        for metric in ('greedy','sampled_mean_pass_at_1'):
            endpoint=read(c2_path.local_inputs(ROOT,spec['jobs']['C2_C2a_s17_r1'])/'MATH_ENDPOINT.json')
            ids=endpoint_ids(endpoint)
            values=new_vectors(ROOT,spec,ids,metric,bindings)
            dump(out/(metric+'_VECTORS.json'),values)
            dump(out/(metric+'_CONTRASTS.json'),contrast(values,ids,metric))
        if time.time()>=c2_path.CUTOFF:raise TimeoutError('Original result cutoff')
        dump(out/'COMPLETED.json',dict(input_files=bindings,actual_A3_pending=True,
            old_bootstrap_or_scoring_repeated=False,new_contrasts_only=True))
        dump(out/'MANIFEST.json',manifest(out))
    except BaseException as exc:
        dump(out/'FAILED.json',dict(type=type(exc).__name__,error=str(exc),automatic_retry=False));raise
    finally:timer.cancel()


if __name__=='__main__':main()

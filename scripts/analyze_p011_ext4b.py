"""New nested-pool contrast only; saved A7 is descriptive and never rescored."""
import argparse
import time
from pathlib import Path
from experiments.p011.ext4b_runtime_contract import LOCAL,SPEC,review,JOBS
from experiments.p011.ext4b_path import ACTUAL
from experiments.p011.owner_0205_common import read,sha,digest,create,utc
from experiments.p011 import long_evaluation
from experiments.p011.long_d2_scope import greedy_interval
from scripts.p011_ext4b_io import remaining_window


def main():
    p=argparse.ArgumentParser();p.add_argument('--source-review',required=True);p.add_argument('--actual-review',required=True);p.add_argument('--small-attempt',required=True);p.add_argument('--large-attempt',required=True);a=p.parse_args()
    review(SPEC,a.source_review,a.actual_review);actual=read(ACTUAL);saved=[];bindings={};deadline=float('inf')
    for job,name in ((JOBS[1],a.small_attempt),(JOBS[0],a.large_attempt)):
        dispatch=LOCAL/'dispatch'/name;intent=read(dispatch/'INTENT.json')
        if intent['job']!=job or intent['job_spec']!=actual['jobs'][job]:raise ValueError('Only exact LARGE-minus-SMALL matched-dose contrast')
        deadline=min(deadline,time.time()+remaining_window(dispatch,60))
        sf=LOCAL/'score'/name/'COMPLETED.json';of=LOCAL/'audit'/name/'COMPLETE_PROOF.json';s=read(sf)['saved_score_proof'];o=read(of)
        if not s['passed'] or not o['passed'] or s['outputs'] not in (500,1000,1500,2000,2500) or o['job_sha256']!=digest(intent['job_spec']):raise ValueError('Both original training and complete scoped-endpoint score proofs required')
        saved.append(s);bindings[job]={'attempt':name,'score_sha256':sha(sf),'oracle_sha256':sha(of)}
    out=LOCAL/'analysis';out.mkdir(parents=True,exist_ok=False);create(out/'ATTEMPT.json',{'utc':utc(),'bindings':bindings,'retries':0,'absolute_deadline_epoch':deadline})
    try:
        sample=long_evaluation.paired_question_interval(*[s['endpoints']['math500_sample']['question_correct'] for s in saved]) if all('math500_sample' in s['endpoints'] for s in saved) else {'status':'unavailable','reason':'Four complete sample endpoints required in both cells; missing not zero'}
        greedy=greedy_interval(*[s['endpoints']['math500_greedy']['question_correct'] for s in saved]) if all('math500_greedy' in s['endpoints'] for s in saved) else {'status':'unavailable','reason':'Complete greedy endpoint required in both cells; missing not zero'}
        descriptive={label:{'small':saved[0]['endpoints'][label],'large':saved[1]['endpoints'].get(label,{'status':'unavailable'}),'descriptive_only':True} for label in saved[0]['endpoints'] if label not in ('math500_sample','math500_greedy')}
        if time.time()>=deadline:raise TimeoutError('Original extension result window elapsed')
        create(out/'COMPLETED.json',{'utc':utc(),'contrast':'LARGE_minus_SMALL','sample':sample,'greedy':greedy,'descriptive_endpoints':descriptive,'bindings':bindings,
            'bootstrap_draws':10000,'bootstrap_seed':20261021,'single_training_seed':17,'question_not_training_seed_population':True,
            'greedy_repeated_saved_bit_only_for_original_four_bit_interface':True,'A7_different_pool_descriptive_only_no_recomputed_contrast':True,'AIME_AMC':'NOT_RUN_BY_OWNER_OPTION2_SCOPE','endpoint_scope_selected_by_completion_not_outcome':True,'actual_A3_accepted':False,'interpretation_written':False})
    except BaseException as exc:create(out/'FAILED.json',{'utc':utc(),'type':type(exc).__name__,'message':str(exc),'automatic_retry':False});raise


if __name__=='__main__':main()

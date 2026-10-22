"""Only newly requested contrasts; original natural interval reversed algebraically."""
import argparse
from copy import deepcopy
from collections import Counter
from experiments.p011.owner_0205_common import create,read,sha,utc
from experiments.p011.forced_answer_ext3b import SPEC,SCOPE,LOCAL,INPUTS,CELLS,admit
from experiments.p011.forced_answer import joined_labels,question_vectors
from experiments.p011.long_evaluation import paired_question_interval
from scripts.analyze_p011_forced_answer_retry import rates


def reverse_interval(value):
    v=deepcopy(value);v['difference_pp']=-v['difference_pp']
    lo,hi=v['ci95_pp'];v['ci95_pp']=[-hi,-lo]
    v['derived_by_sign_reversal_of_saved_LARGE_minus_SMALL']=True
    v['bootstrap_reexecuted']=False
    return v


def a6_a7(spec,out):
    labels={}
    for cell,binding in spec['saved_A6_A7_labels'].items():
        if sha(binding['path'])!=binding['sha256']:raise ValueError('Saved forced labels changed')
        labels[cell]=read(binding['path'])
    result={m:paired_question_interval(question_vectors(labels['A7'],m),question_vectors(labels['A6'],m)) for m in ('sample','greedy')}
    create(out/'RESULTS.json',{'contrast':'A6_minus_A7','forced':result,'source_bindings':spec['saved_A6_A7_labels'],
        'posthoc_diagnostic':True,'new_generation_or_scoring':False})


def extension(spec,out):
    statuses=read(LOCAL/'collect/COMPLETED.json')['cell_statuses'];cells={};labels={}
    manifest=read(INPUTS/'INPUT_MANIFEST.json')
    for cell in CELLS:
        folder=LOCAL/'score'/cell
        if statuses[cell]!='completed' or not (folder/'COMPLETED.json').exists():
            cells[cell]={'status':'unavailable','generation_status':statuses[cell],'missing_not_zero':True};continue
        scored=read(folder/'payload/ALL_SCORED_ROWS.json')
        old=read(INPUTS/cell/'ORIGINAL_LABELS_AND_GOLD.json');original=old['labels']
        selected=set(old['truncation_diagnostics']);new={r['id']:r['score']['correct'] for r in scored}
        full=joined_labels(original,new,selected);labels[cell]=full
        decoded=read(LOCAL/'audit'/cell/'DECODED.json')
        closed={r['id']:r['forced_box_completion_category'] for r in decoded}
        modes={}
        for mode in ('sample','greedy'):
            ids=[k for k in original if k.split(':')[2]==mode];capped=[k for k in ids if k in selected]
            closure=Counter(closed[k] for k in capped)
            modes[mode]={'n_rows':len(ids),'n_capped':len(capped),'n_continuations':len(capped),
                'unclosed_boxes':closure['forced_box_unclosed'],'box_completion_categories':dict(closure),
                'natural_accuracy':sum(original[k] for k in ids)/len(ids),'forced_accuracy':sum(full[k] for k in ids)/len(ids),
                'all_rows':rates(ids,original,full),'capped_rows':rates(capped,original,full),
                'capped_looping':rates([k for k in capped if old['truncation_diagnostics'][k]['loop']],original,full),
                'capped_nonlooping':rates([k for k in capped if not old['truncation_diagnostics'][k]['loop']],original,full)}
        cells[cell]={'status':'complete','modes':modes,'native_scores_reused':2500-len(selected),
            'backend_length_native_exclusions':manifest['cells'][cell]['backend_length_native_exclusions'],
            'new_score_binding':sha(folder/'COMPLETED.json'),'input_binding':sha(INPUTS/cell/'ORIGINAL_LABELS_AND_GOLD.json')}
        create(out/(cell+'_FORCED_LABELS.json'),full)
    b=spec['saved_extension_natural_summary']
    if sha(b['path'])!=b['sha256']:raise ValueError('Saved natural summary changed')
    saved=read(b['path'])['analysis']
    contrasts={'SMALL_minus_LARGE':{'natural':{m:reverse_interval(saved[m]) for m in ('sample','greedy')}}}
    if all(c in labels for c in CELLS):
        contrasts['SMALL_minus_LARGE']['forced']={m:paired_question_interval(question_vectors(labels[CELLS[1]],m),question_vectors(labels[CELLS[0]],m)) for m in ('sample','greedy')}
    else:contrasts['SMALL_minus_LARGE']['forced']={'status':'unavailable','missing_not_zero':True}
    contrasts['A6_minus_A7']=read(LOCAL/'a6_a7/RESULTS.json')
    result={'cells':cells,'contrasts':contrasts,'posthoc_diagnostic':True,'primary_results_replaced':False,
        'single_training_seed':17,'unique_causal_mechanism_claim':False,
        'bootstrap':{'resamples':10000,'seed':20261021,'quantile_method':'linear','sample_unit':'question mean of four',
        'greedy_note':'One saved Boolean repeated four times only at the unchanged interface; no extra observations.'},
        'loop_note':'zlib compressed UTF8 bytes / original UTF8 bytes for last 6000 original answer characters < .12; descriptive, capped rows only.',
        'scoring_note':'Unchanged frozen P1; first balanced forced box only, unclosed incorrect; actual native stop retained separately.',
        'original_16384_streams_redecoded':0,'natural_scores_recomputed':0,'actual_A3_accepted':False}
    create(out/'RESULTS.json',result)


def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['a6_a7','analysis']);p.add_argument('--review',required=True);a=p.parse_args()
    spec=admit(SPEC,a.review,SCOPE);out=LOCAL/a.mode;out.mkdir(parents=True,exist_ok=False)
    create(out/'ATTEMPT.json',{'utc':utc(),'source_review_sha256':sha(a.review),'automatic_retry':False})
    try:
        (a6_a7 if a.mode=='a6_a7' else extension)(spec,out)
        create(out/'COMPLETED.json',{'utc':utc(),'results_sha256':sha(out/'RESULTS.json')})
    except BaseException as exc:
        create(out/'FAILED.json',{'utc':utc(),'type':type(exc).__name__,'message':str(exc),'automatic_retry':False});raise

if __name__=='__main__':main()

"""New fixed posthoc labels and contrasts; no original scoring/bootstrap repeated."""
import argparse
from pathlib import Path
from experiments.p011.owner_0205_common import admit, create, read, sha, utc
from experiments.p011.forced_answer import CELLS, CONTRASTS, joined_labels, question_vectors
from experiments.p011.long_evaluation import paired_question_interval

SPEC='reports/p011_20261020/forced_answer_preflight_v2/SPEC.json'


def rates(ids,original,forced):
    n=len(ids)
    return {'n':n,'original_correct':sum(original[k] for k in ids),'forced_correct':sum(forced[k] for k in ids),
        'original_accuracy':sum(original[k] for k in ids)/n if n else None,
        'forced_accuracy':sum(forced[k] for k in ids)/n if n else None,
        'recovered_originally_incorrect':sum(not original[k] and forced[k] for k in ids),
        'recovery_fraction_among_originally_incorrect':sum(not original[k] and forced[k] for k in ids)/sum(not original[k] for k in ids) if any(not original[k] for k in ids) else None}


def main():
    p=argparse.ArgumentParser();p.add_argument('--review',required=True);a=p.parse_args()
    spec=admit(SPEC,a.review,'p011-forced-answer-complete-path-CR');root=Path(spec['local_root'])
    read(root/'collect/COMPLETED.json');out=root/'analysis';out.mkdir(exist_ok=False)
    create(out/'ATTEMPT.json',{'utc':utc(),'source_CR_sha256':sha(a.review),'bootstrap_retries':0})
    try:
        cells={};joined={};bindings={}
        statuses=read(root/'collect/COMPLETED.json')['cell_statuses']
        for cell in CELLS:
            folder=root/'score'/cell
            if statuses[cell]!='completed' or not (folder/'COMPLETED.json').exists():
                cells[cell]={'status':'unavailable','generation_status':statuses[cell],'missing_not_zero':True};continue
            read(folder/'COMPLETED.json')
            old=read(Path(spec['input_output'])/cell/'ORIGINAL_LABELS_AND_GOLD.json')
            scored=read(folder/'payload/ALL_SCORED_ROWS.json');forced={r['id']:r['score']['correct'] for r in scored}
            selected=set(old['truncation_diagnostics']);original=old['labels'];full=joined_labels(original,forced,selected);joined[cell]=full
            bindings[cell]={'score_sha256':sha(folder/'COMPLETED.json'),'labels_sha256':sha(Path(spec['input_output'])/cell/'ORIGINAL_LABELS_AND_GOLD.json')}
            modes={}
            for mode in ('sample','greedy'):
                ids=[k for k in original if k.split(':')[2]==mode];truncated=[k for k in ids if k in selected]
                modes[mode]={'all_rows':rates(ids,original,full),'truncated_rows':rates(truncated,original,full),
                    'truncated_looping':rates([k for k in truncated if old['truncation_diagnostics'][k]['loop']],original,full),
                    'truncated_nonlooping':rates([k for k in truncated if not old['truncation_diagnostics'][k]['loop']],original,full)}
            cells[cell]={'status':'complete','modes':modes,'natural_rows_reused':2500-len(selected)}
            create(out/(cell+'_FORCED_LABELS.json'),full)
        contrasts={}
        for left,right in CONTRASTS:
            name=right+'_minus_'+left
            if left not in joined or right not in joined:
                contrasts[name]={'status':'unavailable','missing_not_zero':True};continue
            contrasts[name]={'status':'complete','sample':paired_question_interval(question_vectors(joined[left],'sample'),question_vectors(joined[right],'sample')),
                'greedy':paired_question_interval(question_vectors(joined[left],'greedy'),question_vectors(joined[right],'greedy')),
                'greedy_interface_note':'One saved greedy Boolean repeated four times only to preserve the original paired-question function; no extra independent observations.'}
        create(out/'RESULTS.json',{'cells':cells,'contrasts':contrasts,'bindings':bindings,
            'posthoc_diagnostic':True,'primary_results_replaced':False,'one_fixed_suffix_not_tuned':True,
            'training_seed_population_or_unique_causal_mechanism_claim':False,
            'scorer_note':'Frozen P1 scalar/pool; a continuation still hitting64 tokens retains length_cap and is incorrect under that frozen policy.',
            'loop_note':'zlib compressed UTF8 bytes of last6000 original answer characters / original UTF8 byte length < .12; descriptive heuristic.'})
        create(out/'COMPLETED.json',{'utc':utc(),'results_sha256':sha(out/'RESULTS.json'),'actual_A3_accepted':False})
    except BaseException as exc:
        create(out/'FAILED.json',{'utc':utc(),'type':type(exc).__name__,'message':str(exc),'automatic_retry':False});raise


if __name__=='__main__':main()

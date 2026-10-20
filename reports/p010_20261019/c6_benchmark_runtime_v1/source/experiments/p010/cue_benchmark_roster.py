"""P010 original C6 benchmark roster; private preparation, no dispatch."""
from math import ceil, isfinite
from experiments.p010.common import digest

RUNS=('base_math','base_gsm','s1_n400_math','t72_n400_math')
SAMPLES=tuple(range(4))


def checked_selection(selection):
    if (not isinstance(selection,dict) or selection.get('gold_used') is not False
            or selection.get('correctness_used') is not False
            or selection.get('test_data_used') is not False
            or selection.get('tie_rule')!='no-cue then frozen beam rank'):
        raise ValueError('Original complete label-free selection proof required')
    candidates=selection.get('candidates');winner=selection.get('selected_candidate')
    if (not isinstance(candidates,list) or len(candidates)!=21
            or type(winner) is not int or not 0<=winner<21
            or candidates[winner].get('candidate')!=winner
            or candidates[winner].get('eligible') is not True
            or candidates[winner].get('token_ids')!=selection.get('selected_token_ids')):
        raise ValueError('Actual selected candidate must bind full original selection')
    cue=selection['selected_token_ids']
    if (not isinstance(cue,list) or not 0<=len(cue)<=2
            or (winner==0)!=(cue==[])
            or any(type(t) is not int or not 0<=t<151643 for t in cue)):
        raise ValueError('Original no-cue or one/two mapped non-special tokens only')
    return list(cue)


def parameters(task,evaluation):
    if task not in ('math','gsm') or evaluation not in ('greedy',)+tuple('sample'+str(i) for i in SAMPLES):
        raise ValueError('Only original primary and four sampled endpoints')
    greedy=evaluation=='greedy'
    return dict(n=1,temperature=0 if greedy else .6,top_p=1 if greedy else .95,
        top_k=-1,repetition_penalty=1,max_tokens=1024 if task=='math' else 512,
        seed=17 if greedy else int(evaluation[-1]),stop=None,stop_token_ids=[151643],
        ignore_eos=False,detokenize=True,skip_special_tokens=False,include_stop_str_in_output=True)


def roster(run,endpoint,selection,existing):
    """Reuse each exact already completed condition; never regenerate old greedy.

    Existing proofs must already bind an original verified Boolean/raw endpoint.
    This function accepts no gold or correctness fields. A selected empty cue
    aliases the identical no-cue condition, including its four same-seed draws.
    No second copy of the same prompts/parameters is generated or scored.
    """
    if run not in RUNS:raise ValueError('Only original C6 four model/task cells')
    task='gsm' if run=='base_gsm' else 'math';count=1319 if task=='gsm' else 500
    cue=checked_selection(selection)
    if (not isinstance(endpoint,list) or len(endpoint)!=count
            or len({r.get('problem_id') for r in endpoint})!=count
            or any(set(r)-{'problem_id','candidate_id','input_ids','source_row_sha256'} for r in endpoint)):
        raise ValueError('Exact gold-free original benchmark roster required')
    for row in endpoint:
        ids=row.get('input_ids')
        if (not isinstance(row.get('problem_id'),str) or not isinstance(ids,list) or not ids
                or any(type(t) is not int or not 0<=t<151936 for t in ids)
                or len(ids)+len(cue)+parameters(task,'greedy')['max_tokens']>2048):
            raise ValueError('Full prompt plus forced cue must fit; no truncation')
    evaluations=['greedy']+['sample'+str(i) for i in SAMPLES]
    required_existing=['greedy'] if run.startswith('base_') else evaluations
    if set(existing)!=set(required_existing):
        raise ValueError('Original required reusable endpoint proofs are incomplete')
    ids=[row['problem_id'] for row in endpoint]
    for evaluation,proof in existing.items():
        if (set(proof)!={'problem_ids','parameters','cue_token_ids','raw_proof_sha256','score_proof_sha256','complete','technical_unknown'}
                or proof['problem_ids']!=ids or proof['parameters']!=parameters(task,evaluation)
                or proof['cue_token_ids']!=[] or proof['complete'] is not True or proof['technical_unknown']!=0
                or any(not isinstance(proof[k],str) or len(proof[k])!=64 for k in ('raw_proof_sha256','score_proof_sha256'))):
            raise ValueError('Only exact complete original no-cue proofs may be reused')
    rows=[];reused=[];aliases=[]
    for condition,tokens in [('no_cue',[]),('cue',cue)]:
        for evaluation in evaluations:
            if condition=='cue' and not cue:
                aliases.append(dict(condition=condition,evaluation=evaluation,target_condition='no_cue',
                    target_evaluation=evaluation,reason='Actual selected opening is empty; identical original condition'))
                continue
            if condition=='no_cue' and evaluation in existing:
                reused.append(dict(condition=condition,evaluation=evaluation,proof=existing[evaluation]))
                continue
            for i,row in enumerate(endpoint):
                rows.append(dict(candidate_id=f'{condition}/{evaluation}/{task}/{i:04d}',
                    problem_id=row['problem_id'],source_row_sha256=digest(row),
                    input_ids=row['input_ids']+tokens,original_input_ids=row['input_ids'],
                    cue_token_ids=tokens,condition=condition,evaluation=evaluation,task=task,
                    sampling=parameters(task,evaluation)))
    return dict(run=run,task=task,problem_ids=ids,selected_cue=cue,rows=rows,reused=reused,aliases=aliases,
        new_outputs=len(rows),new_batches=ceil(len(rows)/256),greedy_regeneration=False,
        new_training_updates=0,selection_changed=False,test_correctness_used_in_selection=False)


def observed_scenario(elapsed,completed,times,observed,full_batches,hard_seconds,allowance=600):
    """Prospective arithmetic only; exact budget/caps belong to final candidate."""
    if (type(full_batches) is not int or full_batches<=0 or type(completed) is not int
            or not 0<=completed<full_batches or len(times)!=completed or not observed
            or not isfinite(elapsed) or elapsed<0 or hard_seconds<=30
            or any(not isfinite(x) or x<=0 for x in list(times)+list(observed))):
        raise ValueError('Complete actual timing observations and an explicit candidate cap required')
    maximum=max(list(times)+list(observed));remaining=1.2*(maximum*(full_batches-completed)+allowance)
    if elapsed+remaining>hard_seconds-30:raise TimeoutError('Remainder exceeds exact proposed worker window')
    return dict(elapsed_seconds=elapsed,remaining_seconds=remaining,total_seconds=elapsed+remaining,
        maximum_completed_batch_seconds=maximum,full_batches=full_batches,completed=completed,
        uncalibrated_setup_allowance_seconds=allowance,margin=1.2,calibrated_bound=False,
        first_paid_measurement_exceptions=0)

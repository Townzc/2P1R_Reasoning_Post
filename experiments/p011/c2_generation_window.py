"""Prepared C2 finite batching over immutable E1d order and saved verdicts.

Not an entry or admission: future shared C2 CR/A1/A2 must bind full original
raw/score provenance, concrete window, numerical budget and all runtime sources.
No original corpus is read here, and no scorer, model or tokenizer is imported.
"""
from experiments.p011.short_generation import c2_prefix, confirmed_first_four, request
from experiments.p010.dataset_selection import inventory
from experiments.sft_allocation_midpoint.common import digest


def plan_window(ordered_e1d, t72_records, t15_records, prompts, s1_ids, window_size):
    """Choose at most a fixed700 unresolved eligible parents; never skip unknowns.

    The reviewer suggested finite batched missing-attempt generation.700 is an
    upper candidate width, not an approved number of new outputs or a cost claim.
    Extra outputs beyond the final400 selected parents remain saved and billed.
    Already usable/exhausted T15 parents need no new attempt. Every requested
    parent uses only missing attempts1..4 at original temperature.8 and seeds.
    """
    if type(window_size) is not int or not 1 <= window_size <= 700:
        raise ValueError('Fixed bounded C2 window width required')
    if len(ordered_e1d) != len(set(ordered_e1d)) or not ordered_e1d:
        raise ValueError('Immutable unique E1d order required')
    for rows in (t72_records, t15_records):
        inventory(rows)
        if any(type(r.get('score',{}).get('score',{}).get('correct')) is not bool for r in rows.values()):
            raise ValueError('Missing Boolean verdict is unknown, not an unusable answer')
        if not {r['problem_id'] for r in rows.values()} <= set(ordered_e1d):
            raise ValueError('Reuse must be an explicit original E1d projection')
    initial=c2_prefix(ordered_e1d,t72_records,t15_records,s1_ids)
    if initial.get('complete') or initial.get('blocked_missing_old_T72') or initial.get('insufficient_common_support') is not None:
        return {'initial_prefix':initial,'window_parents':[],'new_requests':[],
                'new_T72_generation_allowed':False,'training_admitted':False}
    window=[];rows=[];old_missing=None
    for pid in ordered_e1d:
        right=confirmed_first_four(pid,t72_records)
        if right['state']=='missing':
            old_missing=pid;break
        if right['state']=='exhausted':continue
        left=confirmed_first_four(pid,t15_records)
        if left['state']!='missing':continue
        ids=prompts.get(pid)
        if (not isinstance(ids,list) or not ids or len(ids)+1024>2048
                or any(type(i) is not int or not 0<=i<151936 for i in ids)):
            raise ValueError('Original native prompt tokens required')
        window.append(pid)
        for attempt in range(1,5):
            cid=f'{pid}::attempt{attempt:02d}'
            if cid not in t15_records:rows.append(request(pid,attempt,ids,.8))
        if len(window)==window_size:break
    if old_missing is not None:
        # A full input review must resolve this original missing record first.
        return {'initial_prefix':initial,'window_parents':[], 'new_requests':[],
                'blocked_missing_old_T72':old_missing,
                'new_T72_generation_allowed':False,'training_admitted':False}
    return {'initial_prefix':initial,'window_parents':window,'new_requests':rows,
            'window_size':window_size,'immutable_order_sha256':digest(ordered_e1d),
            'old_T72_verdicts_sha256':digest(t72_records),
            'old_T15_verdicts_sha256':digest(t15_records),
            'new_T72_generation_allowed':False,'training_admitted':False,
            'extra_generated_attempts_must_be_saved_and_charged':True}


def after_window(plan, ordered_e1d, t72_records, old_t15_records, new_records, s1_ids):
    """Consume complete saved Boolean rows only; no old/new symbolic rescoring."""
    if (plan.get('immutable_order_sha256')!=digest(ordered_e1d)
            or plan.get('old_T72_verdicts_sha256')!=digest(t72_records)
            or plan.get('old_T15_verdicts_sha256')!=digest(old_t15_records)):
        raise ValueError('Original selection basis changed')
    expected={x['request']['candidate_id'] for x in plan['new_requests']}
    if not expected or set(new_records)!=expected or set(new_records)&set(old_t15_records):
        raise ValueError('Complete exact new-only window verdicts required')
    inventory(new_records)
    if any(type(r.get('score',{}).get('score',{}).get('correct')) is not bool for r in new_records.values()):
        raise ValueError('Every new attempt requires a saved Boolean verdict')
    result=c2_prefix(ordered_e1d,t72_records,{**old_t15_records,**new_records},s1_ids)
    result['all_window_outputs_retained']=True
    result['new_window_output_count']=len(new_records)
    result['training_admitted']=False
    return result

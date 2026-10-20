# C6 adapter: only sampled-vector cardinality expands from MATH500 to
# GSM1319. The paired_summary AST is identical to the original P010 primitive.
# No original analysis source is edited; no old analysis is rerun.
"""Deterministic P010 paired question bootstrap; no scoring or report prose."""
import numpy as np

DRAWS=10000
SEED=20261019


def checked_vector(value, expected_ids, metric):
    if (not isinstance(value,dict) or value.get('technical_unknown')!=0
            or value.get('complete') is not True or value.get('question_ids')!=expected_ids
            or len(set(expected_ids))!=len(expected_ids) or len(expected_ids) not in (500,1319)
            or value.get('metric')!=metric):
        raise ValueError('Complete original question order, zero unknown and exact metric required')
    data=value.get('question_values')
    if not isinstance(data,list) or len(data)!=len(expected_ids):raise ValueError('All question values required')
    if metric=='greedy':
        if any(type(x) is not bool for x in data):raise ValueError('Frozen Boolean greedy values required')
    elif metric=='sampled_mean_pass_at_1':
        if len(expected_ids) not in (500,1319) or value.get('samples_per_question')!=4:
            raise ValueError('Original four samples per 500 or 1319 questions required')
        if any(type(x) not in (int,float) or x not in (0,.25,.5,.75,1) for x in data):
            raise ValueError('Question mean must include all four original Boolean samples')
    else:raise ValueError('Unapproved metric')
    return np.asarray(data,dtype=np.float64)


def paired_summary(vectors,contrasts,question_ids,metric):
    """One shared question-resampling matrix; every named contrast is returned.

    Conditional pointwise intervals, not a training-seed population statement,
    familywise guarantee, equivalence test or any scientific stopping rule.
    Caller supplies only already verified frozen primary labels/sample means.
    """
    if not isinstance(vectors,dict) or not vectors or not isinstance(contrasts,list) or not contrasts:
        raise ValueError('Explicit complete vector set and fixed contrast roster required')
    names=[c.get('name') for c in contrasts]
    if any(not isinstance(x,str) or not x for x in names) or len(set(names))!=len(names):
        raise ValueError('Unique fixed contrast identities required')
    arrays={name:checked_vector(v,question_ids,metric) for name,v in vectors.items()}
    for c in contrasts:
        if set(c)!={'name','left','right'} or c['left'] not in arrays or c['right'] not in arrays:
            raise ValueError('Missing/cancelled comparison cannot be invented or scored zero')
    rng=np.random.default_rng(SEED)
    # A single fixed shared matrix makes the result invariant to contrast order.
    sample=rng.integers(0,len(question_ids),size=(DRAWS,len(question_ids)))
    result=[]
    for c in contrasts:
        difference=arrays[c['left']]-arrays[c['right']]
        draws=difference[sample].mean(axis=1)*100
        lower,upper=np.quantile(draws,[.025,.975],method='linear')
        point=float(difference.mean()*100)
        item=dict(**c,left_mean=float(arrays[c['left']].mean()),right_mean=float(arrays[c['right']].mean()),
            difference_pp=point,pointwise_95_ci_pp=[float(lower),float(upper)],questions=len(question_ids),
            meets_frozen_3pp_and_positive_lower=bool(point>=3 and lower>0),
            interval_scope='conditional_on_observed_models_and_question_resampling',
            training_seed_population=False,familywise_interval=False,equivalence_test=False)
        if metric=='greedy':
            item['net_correct_count']=int(difference.sum());item['discordant_questions']=int(np.count_nonzero(difference))
        result.append(item)
    return dict(metric=metric,draws=DRAWS,seed=SEED,numpy_version=np.__version__,
        percentile_method='linear',shared_question_draws=True,contrasts=result,
        primary_labels_changed=False,model_calls=0,parser_calls=0,automatic_next_stage_admission=False)

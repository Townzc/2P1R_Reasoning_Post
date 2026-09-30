"""Descriptive available-state summaries; unknown bounds are not confidence intervals."""
from collections import Counter, defaultdict

from .contracts import ContractError
from .screen_plan import EVAL_SAMPLES


def empirical_bounds(samples, expected_ids):
    """Retain the complete planned denominator, including any unobserved slots."""
    expected_ids=list(expected_ids)
    if not expected_ids or len(set(expected_ids))!=len(expected_ids):
        raise ContractError('invalid expected task roster')
    grouped=defaultdict(list)
    identities=set()
    for row in samples:
        task=row['task_id'];identity=row['sample_id']
        if task not in expected_ids or identity in identities:
            raise ContractError('unexpected task or duplicate sample')
        identities.add(identity);grouped[task].append(row)
    if any(len(rows)>EVAL_SAMPLES for rows in grouped.values()):
        raise ContractError('too many completions for a task')
    totals={key:Counter() for key in ['base','extra','union']}
    coverage=Counter();dual_unknown=0
    for task in expected_ids:
        union=[]
        for row in grouped[task]:
            verdicts={key:row[key]['status'] for key in ['base','extra']}
            values={key:True if value=='pass' else False if value=='fail' else None
                    for key,value in verdicts.items()}
            dual_unknown+=any(value is None for value in values.values())
            # A known failing suite rules out union success even if the other is unknown.
            values['union']=(False if False in values.values() else
                             True if all(value is True for value in values.values()) else None)
            union.append(values['union'])
            for key,value in values.items():
                totals[key]['pass' if value is True else 'fail' if value is False else 'unknown']+=1
        missing=EVAL_SAMPLES-len(grouped[task])
        union.extend([None]*missing)
        for key in totals:totals[key]['unobserved']+=missing
        coverage['pass' if True in union else 'unknown' if None in union else 'fail']+=1
    denominator=len(expected_ids)*EVAL_SAMPLES
    metrics={}
    for key,count in totals.items():
        lower=count['pass'];upper=lower+count['unknown']+count['unobserved']
        metrics[key]={'denominator':denominator,'counts':dict(count),
                      'percent_bounds':[100*lower/denominator,100*upper/denominator]}
    metrics['pass_at_8']={'denominator':len(expected_ids),'counts':dict(coverage),
        'percent_bounds':[100*coverage['pass']/len(expected_ids),
                          100*(coverage['pass']+coverage['unknown'])/len(expected_ids)]}
    return {'planned_completions':denominator,'recorded_completions':len(samples),
            'recorded_dual_unknown':dual_unknown,'metrics':metrics,
            'bound_scope':'logical empirical bounds from unknown/unobserved slots; not a confidence interval',
            'training_replicates':1,'scientific_confirmation':False}


def descriptive_difference(left,right,metric='union'):
    if left['planned_completions']!=right['planned_completions']:
        raise ContractError('planned denominators differ')
    lo,hi=left['metrics'][metric]['percent_bounds']
    rlo,rhi=right['metrics'][metric]['percent_bounds']
    return {'difference_pp_bounds':[lo-rhi,hi-rlo],
            'scope':'descriptive available-state difference; not the missing matched-future contrast',
            'confidence_interval':False}

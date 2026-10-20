"""Whole-answer exact target schedule; acquired answers may have zero exposure.

Unlike historical P007's all-answers-once requirement, P008's high-B/low-T
bridge can have q=0. Every acquired row remains in the inventory/denominators.
The seeded subset-sum residue uses lengths, not scores; report that limitation.
"""
from bisect import bisect_left
from collections import Counter
import random
from scripts.plan_real_math_scale import exact_remainder


def schedule(lengths,budget,updates,seed=17):
    if (not lengths or any(type(x) is not int or x<=0 for x in lengths)
        or type(budget) is not int or budget<=0 or type(updates) is not int or updates<=0):
        raise ValueError('Positive integer lengths/dose/updates required')
    q,remainder=divmod(budget,sum(lengths))
    extra=exact_remainder(lengths,remainder,seed)
    stream=list(range(len(lengths)))*q+extra
    if len(stream)<updates:raise ValueError('Insufficient complete presentations for nonempty updates')
    random.Random(seed+1).shuffle(stream)
    prefix=[0]
    for i in stream:prefix.append(prefix[-1]+lengths[i])
    if prefix[-1]!=budget:raise AssertionError('Dose differs')
    cuts=[0]
    for step in range(1,updates):
        index=bisect_left(prefix,step*budget/updates)
        index=min((index-1,index),key=lambda k:abs(prefix[k]-step*budget/updates))
        cuts.append(max(cuts[-1]+1,min(index,len(stream)-(updates-step))))
    cuts.append(len(stream))
    rows=[stream[a:b] for a,b in zip(cuts,cuts[1:])]
    counts=Counter(stream);all_counts=[counts[i] for i in range(len(lengths))]
    return dict(updates=rows,acquired_answers=len(lengths),exposed_answers=sum(x>0 for x in all_counts),
       zero_exposure_answers=sum(x==0 for x in all_counts),row_exposures=all_counts,
       supervised_targets=budget,q=q,subset_selection_depends_on_lengths=True)

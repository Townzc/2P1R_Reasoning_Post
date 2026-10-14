"""Validate exact preregistered LR bytes without host-libm recomputation.

The vectors remain the original published plans; even a one-ULP change to a
planned LR is rejected. No tolerance or regenerated replacement is used.
"""
from collections import Counter
import math
from experiments.sft_allocation_midpoint.common import digest
from src.sft_data import budget_report
from .contract import BASE_UPDATES, BASE_TARGETS
from .student_runtime import EVAL

FROZEN_VECTOR_FILE_SHA256 = 'cb9c2e046e588dcdede0770f497f32550b797f0a7d7feacde343936a486cabe2'
FROZEN_LR_SHA256 = {1024: '14ac59d273e901d23524a077fd6b89c393f698f07fb0da0bc71a1c8d46f08a73', 2048: '8f0a7733e950d2f297e39222bba1829b3fffa7a1a2154d77b44a3d0f06afd8be', 256: '181a27e1b8344ba9bc7651185b28e4cbb01bc818a7abd2b6fd8033f8fa60d597'}

def validate_frozen_lrs(values, updates):
    if (type(updates) is not int or updates not in FROZEN_LR_SHA256
            or type(values) is not list or len(values) != updates
            or any(type(x) is not float or not math.isfinite(x) or x <= 0 for x in values)):
        raise ValueError('Invalid frozen learning-rate vector')
    if digest(values) != FROZEN_LR_SHA256[updates]:
        raise ValueError('Learning-rate vector differs from preregistered bytes')
    return list(values)


def validate_plan(rows,encoded,plan,config):
    u=config['updates'];multiple=config['training_multiple'];targets=config['targets']
    if u!=BASE_UPDATES*multiple or multiple not in (1,4,8):raise ValueError('Unregistered training horizon')
    nominal=BASE_TARGETS*multiple
    if not nominal-nominal//1000<=targets<=nominal:raise ValueError('Target tolerance differs')
    if config['seed']!=17 or len(plan['updates'])!=u:
        raise ValueError('Fixed seed or update count differs')
    validate_frozen_lrs(plan['lrs'],u)
    if plan['row_path_ids']!=[r['path_id'] for r in rows] or len(set(plan['row_path_ids']))!=len(rows):
        raise ValueError('Whole inventory/order differs')
    if any(not b or any(type(i)is not int or not 0<=i<len(rows) for i in b) for b in plan['updates']):
        raise ValueError('Empty/foreign row in update')
    count=Counter(i for b in plan['updates'] for i in b);all_counts=[count[i] for i in range(len(rows))]
    if (max(all_counts)-min(all_counts)>1 or plan['row_exposures']!=all_counts
         or plan['zero_exposure_answers']!=sum(n==0 for n in all_counts)):
        raise ValueError('Balanced complete-answer exposure differs')
    budget=budget_report(encoded,plan['updates'],1)
    if budget['supervised_response_tokens']!=targets or budget['optimizer_updates']!=u or budget['padding_tokens']!=0:
        raise ValueError('Full-answer dose differs')
    if plan['supervised_targets']!=targets or not plan['targets_are_frozen_before_student_scores']:
        raise ValueError('Plan is not bound to pre-outcome common target')
    return budget

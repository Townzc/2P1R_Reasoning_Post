"""Frozen, CPU-only plan for one exploratory W/C/R supervision-history screen."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

from .contracts import ContractError, identity_hash
from .gpu_profile import PROFILE, durable_json

PREFIX_UPDATES = 128
FUTURE_UPDATES = 128
TRAIN_IDS = 250
EVAL_IDS = 128
GROUP_SIZE = 8
COMPLETIONS_PER_UPDATE = 16
EVAL_SAMPLES = 8
EVAL_TASKS_PER_BATCH = 4
WORKER_CAP_SECONDS = 13200
POWERED_CAP_SECONDS = 14400
SCORER_TIMEOUT_SECONDS = 120
INSTRUCTION = ('Write a complete Python function that solves the task below. '
               'Return the full function definition in a single ```python code block.\n\n')
TRAINING = {**PROFILE, 'max_steps': PREFIX_UPDATES, 'steps_per_generation': 4}
PHASES = (
    ('W_prefix', 'R', 'base', 'prefix', 0),
    ('C_prefix', 'R', 'union', 'prefix', 0),
    ('W_future', 'W_prefix', 'union', 'future', 1),
    ('C_future', 'C_prefix', 'union', 'future', 1),
    ('R_future', 'R', 'union', 'future', 1),
)
EVAL_STATES = ('R', 'W_prefix', 'C_prefix', 'W_future', 'C_future', 'R_future')


def validate_split(split):
    tr, ev = split.get('train_ids'), split.get('eval_ids')
    if split.get('PROVISIONAL_smoke_only') or not isinstance(tr, list) or not isinstance(ev, list):
        raise ContractError('frozen split required')
    if len(tr) != TRAIN_IDS or len(ev) != EVAL_IDS:
        raise ContractError('expected the original 250/128 split')
    if len(set(tr)) != len(tr) or len(set(ev)) != len(ev) or set(tr) & set(ev):
        raise ContractError('duplicate IDs or train/evaluation overlap')
    if any(not isinstance(x, str) or not x.startswith('Mbpp/') or not x[5:].isdigit() for x in tr+ev):
        raise ContractError('invalid MBPP ID')
    return sorted(tr), sorted(ev)


def prompt_schedule(ids, stage, updates=PREFIX_UPDATES):
    """Outcome-independent hash permutations; every task appears once per epoch."""
    if stage not in {'prefix', 'future'} or not ids or len(set(ids)) != len(ids):
        raise ContractError('invalid prompt schedule inputs')
    if type(updates) is not int or not 1 <= updates <= PREFIX_UPDATES:
        raise ContractError('invalid finite dose')
    order, epoch = [], 0
    while len(order) < 2 * updates:
        order.extend(sorted(ids, key=lambda task: identity_hash(
            {'replicate': 0, 'stage': stage, 'epoch': epoch, 'task_id': task})))
        epoch += 1
    return [[order[2*i]] * GROUP_SIZE + [order[2*i+1]] * GROUP_SIZE for i in range(updates)]


def sampler_indices(ids, schedule):
    """TRL 1.7 consumes a generation batch four times per optimizer update."""
    index = {task: i for i, task in enumerate(ids)}
    result = []
    for batch in schedule:
        if len(batch) != COMPLETIONS_PER_UPDATE or any(t not in index for t in batch):
            raise ContractError('schedule task/batch mismatch')
        for _ in range(4):
            result.extend(index[t] for t in batch)
    return result


def make_plan(split):
    train, evaluation = validate_split(split)
    schedules = {stage: prompt_schedule(train, stage) for stage in ['prefix', 'future']}
    plan = {
        'schema': 1, 'run_id': 'q2_screen_20260930_r0_t128_k128',
        'kind': 'exploratory_single_paired_training_replicate',
        'replicate': 0, 'train_ids': train, 'eval_ids': evaluation,
        'training_config': TRAINING, 'schedules': schedules,
        'schedule_sha256': {k: identity_hash(v) for k,v in schedules.items()},
        'training_phases': [{'name': n, 'source_state': s, 'reward': r,
                            'schedule': d, 'trainer_seed': seed,
                            'vllm_engine_seed': 0, 'updates': PREFIX_UPDATES}
                           for n,s,r,d,seed in PHASES],
        'evaluation': {'states': list(EVAL_STATES), 'samples_per_task': EVAL_SAMPLES,
                       'tasks_per_batch': EVAL_TASKS_PER_BATCH, 'temperature': 1.0,
                       'top_p': 1.0, 'top_k': -1, 'max_tokens': 640,
                       'request_seed_rule': 'sha256(eval-v1/task_id) first 8 hex modulo 2^31',
                       'primary': 'task_macro_mean_union_sampled_pass_at_1',
                       'secondary': ['base', 'extra', 'observed_pass_at_8'],
                       'development_only': True},
        'dose': {'optimizer_updates': len(PHASES)*PREFIX_UPDATES,
                 'training_completions': len(PHASES)*PREFIX_UPDATES*COMPLETIONS_PER_UPDATE,
                 'evaluation_completions': len(EVAL_STATES)*EVAL_IDS*EVAL_SAMPLES,
                 'canonical_reference_tasks': TRAIN_IDS+EVAL_IDS,
                 'final_checkpoints': len(PHASES)},
        'limits': {'worker_seconds': WORKER_CAP_SECONDS, 'powered_seconds': POWERED_CAP_SECONDS,
                   'reference_phase_seconds': 600, 'training_phase_seconds': 2700,
                   'evaluation_phase_seconds': 1800,
                   'scorer_timeout_seconds': SCORER_TIMEOUT_SECONDS,
                   'data_min_free_gib': 40, 'runtime_min_free_data_gib': 10,
                   'runtime_min_free_system_gib': 3, 'automatic_retry': False},
        'decisions': {
            'meaningful_pilot_gap_pp': 3.0,
            'descriptive_candidate_pattern': 'W_future-R_future <= -3pp; W_future-C_future <= -3pp; C_future-R_future >= -1pp',
            'does_not_establish': ['training-seed robustness', 'noninferiority', 'irreversibility', 'unique mechanism'],
            'null_rule': 'No automatic dose/seed extension; weak or imprecise signal remains unresolved and may be deprioritized for Thursday.',
            'missing_or_failed_rule': 'No imputation/replay. Preserve all attempts; incomplete comparisons cannot decide scientific failure.'},
        'reference_semantics': 'EvalPlus0.3.1 MBPP+v0.2.0; empty extra suite passes vacuously; union means base AND extra',
        'original_profile_weights_used': False,
    }
    return plan


def validate_plan(plan, split):
    if plan != make_plan(split):
        raise ContractError('plan differs from frozen screen; no adaptive arm/dose/task changes')
    return plan


def eval_seed(task):
    return int(hashlib.sha256(('eval-v1/'+task).encode()).hexdigest()[:8],16) % (2**31)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--split',type=Path,default=Path(__file__).parent/'assets/split.json')
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();a.out.parent.mkdir(parents=True,exist_ok=True)
    durable_json(a.out,make_plan(json.loads(a.split.read_text())))

if __name__=='__main__': main()

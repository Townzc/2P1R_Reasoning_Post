"""P009 CPU-only whole-answer planning; never trains or admits a runtime.

Reuse the existing P008 scheduling algorithm, but require every selected answer
at least once and exactly 2,097,148 targets. Neither P008's q=0 allowance nor its
optional target reduction applies to this new experiment.
"""
from collections import Counter
import math

from experiments.sft_allocation_midpoint.common import digest, read, sha
from experiments.sft_allocation_p008.schedule import schedule
from src.sft_data import budget_report

UPDATES = 1024
TARGETS = 2097148
SEEDS = (17, 29)
LR_FILE = 'reports/p008_20261013/LR_VECTORS.json'
LR_FILE_SHA256 = 'cb9c2e046e588dcdede0770f497f32550b797f0a7d7feacde343936a486cabe2'
LR_VECTOR_SHA256 = '14ac59d273e901d23524a077fd6b89c393f698f07fb0da0bc71a1c8d46f08a73'


def frozen_lrs(path=LR_FILE):
    if sha(path) != LR_FILE_SHA256:
        raise ValueError('Original frozen LR file differs; do not regenerate')
    values = read(path)['1024']
    validate_lrs(values)
    return values


def validate_lrs(values):
    if (type(values) is not list or len(values) != UPDATES
            or any(type(x) is not float or not math.isfinite(x) or x <= 0 for x in values)
            or digest(values) != LR_VECTOR_SHA256):
        raise ValueError('Exact pre-existing 1024-step LR bytes required')


def checked_rows(rows, eos_token_id):
    if not rows or type(eos_token_id) is not int or eos_token_id < 0:
        raise ValueError('Nonempty encoded inventory and explicit EOS required')
    for field in ('problem_id', 'path_id'):
        values = [r[field] for r in rows]
        if any(type(v) is not str or not v for v in values) or len(set(values)) != len(rows):
            raise ValueError('Exactly one unique answer per unique question required')
    for row in rows:
        ids, labels, first = row['input_ids'], row['labels'], row['n_prompt']
        if (type(ids) is not list or type(labels) is not list
                or any(type(x) is not int or x < 0 for x in ids)
                or any(type(x) is not int for x in labels)
                or type(first) is not int or not 0 < first < len(ids) - 1
                or not 2 < len(ids) <= 2048 or len(labels) != len(ids)
                or ids[-1] != eos_token_id or eos_token_id in ids[:-1]
                or labels[:first] != [-100] * first or labels[first:] != ids[first:]
                or type(row['n_supervised']) is not int or type(row['n_processed']) is not int
                or row['n_supervised'] != len(ids) - first
                or row['n_processed'] != len(ids)):
            raise ValueError('Full answer/mask/EOS/context differs; no truncation or packing')
    return [r['n_supervised'] for r in rows]


def make_plan(rows, seed, eos_token_id, lr_file=LR_FILE):
    if type(seed) is not int or seed not in SEEDS:
        raise ValueError('Only the two authorized training seeds')
    lengths = checked_rows(rows, eos_token_id)
    if sum(lengths) > TARGETS:
        raise ValueError('Fixed dose cannot expose all selected answers; no q=0')
    planned = schedule(lengths, TARGETS, UPDATES, seed)
    planned.update(schema='p009_whole_answer_plan_v1', seed=seed,
                   eos_token_id=eos_token_id, encoded_rows_sha256=digest(rows),
                   row_path_ids=[r['path_id'] for r in rows], lrs=frozen_lrs(lr_file),
                   lr_vector_sha256=LR_VECTOR_SHA256, fixed_before_student_outcomes=True,
                   runtime_admitted=False)
    validate_plan(rows, planned, seed, eos_token_id)
    return planned


def validate_plan(rows, plan, seed, eos_token_id):
    if type(seed) is not int or seed not in SEEDS:
        raise ValueError('Unregistered seed')
    lengths = checked_rows(rows, eos_token_id)
    if (plan['schema'] != 'p009_whole_answer_plan_v1' or plan['seed'] != seed
            or type(plan['seed']) is not int or type(plan['eos_token_id']) is not int
            or plan['eos_token_id'] != eos_token_id
            or plan['encoded_rows_sha256'] != digest(rows)
            or plan['row_path_ids'] != [r['path_id'] for r in rows]
            or plan['supervised_targets'] != TARGETS
            or plan['lr_vector_sha256'] != LR_VECTOR_SHA256
            or plan['fixed_before_student_outcomes'] is not True):
        raise ValueError('Frozen plan identity/dose differs')
    validate_lrs(plan['lrs'])
    batches = plan['updates']
    if (type(batches) is not list or len(batches) != UPDATES
            or any(not b or type(b) is not list for b in batches)
            or any(type(i) is not int or not 0 <= i < len(rows) for b in batches for i in b)):
        raise ValueError('Exactly 1024 nonempty whole-answer updates required')
    counts = Counter(i for b in batches for i in b)
    exposures = [counts[i] for i in range(len(rows))]
    q = TARGETS // sum(lengths)
    if (q < 1 or type(plan['q']) is not int or type(plan['row_exposures']) is not list
            or any(type(n) is not int for n in plan['row_exposures'])
            or any(n not in (q, q + 1) for n in exposures)
            or exposures != plan['row_exposures'] or plan['q'] != q
            or plan['zero_exposure_answers'] != 0
            or plan['exposed_answers'] != len(rows) or plan['acquired_answers'] != len(rows)):
        raise ValueError('Every selected answer must have balanced positive exposure')
    budget = budget_report(rows, batches, 1)
    if (budget['supervised_response_tokens'] != TARGETS
            or budget['optimizer_updates'] != UPDATES or budget['padding_tokens'] != 0):
        raise ValueError('Exact target-normalized whole-answer dose differs')
    return budget

"""Original exact scheduler and mask validator, with multiple paths per question.

No old plan is changed. A repeated question is allowed; a repeated path is not.
"""
from collections import Counter
from experiments.p010.common import digest
from experiments.learning_regime_p009.training_plan import (
    checked_rows as check_single, frozen_lrs, validate_lrs, TARGETS, UPDATES,
    LR_VECTOR_SHA256, LR_FILE)
from experiments.sft_allocation_p008.schedule import schedule
from src.sft_data import budget_report


def checked_rows(rows, eos_token_id):
    if not rows or len({r['path_id'] for r in rows}) != len(rows):
        raise ValueError('Nonempty inventory of distinct answer identities required')
    lengths = []
    for row in rows:
        lengths.extend(check_single([row], eos_token_id))
    return lengths


def make_plan(rows, seed, eos_token_id, lr_file=LR_FILE):
    if type(seed) is not int or seed not in (17, 29):
        raise ValueError('P010 original training seed only')
    lengths = checked_rows(rows, eos_token_id)
    if sum(lengths) > TARGETS:
        raise ValueError('Whole-answer coverage exceeds original dose; report without shrinking')
    plan = schedule(lengths, TARGETS, UPDATES, seed)
    plan.update(schema='p010_whole_multi_answer_plan_v1', seed=seed,
        eos_token_id=eos_token_id, encoded_rows_sha256=digest(rows),
        row_path_ids=[r['path_id'] for r in rows], lrs=frozen_lrs(lr_file),
        lr_vector_sha256=LR_VECTOR_SHA256, runtime_admitted=False)
    validate_plan(rows, plan, seed, eos_token_id)
    return plan


def validate_plan(rows, plan, seed, eos_token_id):
    lengths = checked_rows(rows, eos_token_id)
    if (type(seed) is not int or seed not in (17, 29)
            or plan['schema'] != 'p010_whole_multi_answer_plan_v1'
            or type(plan['seed']) is not int or plan['seed'] != seed
            or type(plan['eos_token_id']) is not int or plan['eos_token_id'] != eos_token_id
            or plan['encoded_rows_sha256'] != digest(rows)
            or plan['row_path_ids'] != [r['path_id'] for r in rows]
            or plan['supervised_targets'] != TARGETS
            or plan['lr_vector_sha256'] != LR_VECTOR_SHA256):
        raise ValueError('Original answer inventory, seed, EOS or dose differs')
    validate_lrs(plan['lrs'])
    batches = plan['updates']
    if (type(batches) is not list or len(batches) != UPDATES
            or any(type(b) is not list or not b for b in batches)
            or any(type(i) is not int or not 0 <= i < len(rows) for b in batches for i in b)):
        raise ValueError('Exactly1024 nonempty updates over whole answers required')
    counts = Counter(i for b in batches for i in b)
    exposures = [counts[i] for i in range(len(rows))]
    q = TARGETS // sum(lengths)
    if (q < 1 or type(plan['q']) is not int or plan['q'] != q
            or exposures != plan['row_exposures']
            or any(type(x) is not int or x not in (q, q+1) for x in plan['row_exposures'])
            or plan['zero_exposure_answers'] != 0
            or plan['exposed_answers'] != len(rows) or plan['acquired_answers'] != len(rows)):
        raise ValueError('All answers need balanced positive exposure')
    budget = budget_report(rows, batches, 1)
    if (budget['supervised_response_tokens'] != TARGETS
            or budget['optimizer_updates'] != UPDATES or budget['padding_tokens'] != 0):
        raise ValueError('Original exact target-normalized dose differs')
    return budget

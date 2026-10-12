"""Prepared policy-to-SFT conversion. No cloud calls or outcome-based selection.

The caller must independently audit acquisition records first. Every retained
usable answer is exposed; an untrainable pool rejects admission instead of
silently dropping answers or changing only one condition's training budget.
"""
from collections import Counter
import hashlib

from .contract import REVISION
from scripts.plan_real_math_scale import whole_response_schedule
from src.sft_data import encode_row, budget_report

TARGETS = 524288
UPDATES = 256
SEEDS = (17, 23)


def training_rows(parents, acquired_ids, records):
    lookup = {p['id']: p for p in parents}
    if len(lookup) != len(parents) or len(set(acquired_ids)) != len(acquired_ids):
        raise ValueError('Parent identity is not unique')
    if not acquired_ids or not set(acquired_ids) <= lookup.keys():
        raise ValueError('Missing or foreign acquired parents')
    positions = {pid: i for i, pid in enumerate(acquired_ids)}
    seen = set()
    attempted = Counter()
    rows = []
    for record in records:
        pid, cid = record['problem_id'], record['candidate_id']
        if pid not in positions or cid in seen:
            raise ValueError('Foreign or repeated physical candidate')
        seen.add(cid)
        attempted[pid] += 1
        if record['attempt'] != attempted[pid] or attempted[pid] > 8:
            raise ValueError('Attempt gap, reordering or cap violation')
        if type(record['usable']) is not bool:
            raise ValueError('Unknown usability cannot be silently filtered')
        if not record['usable']:
            continue
        if (not record['score']['clean_correct'] or
                record['usable_duplicate_of'] is not None or
                not record['stop']['eos'] or record['stop']['truncated'] or
                not isinstance(record['text'], str) or not record['text'].strip()):
            raise ValueError('Accepted answer violates the acquisition contract')
        parent = lookup[pid]
        # Preserve the entire teacher text. Reference is metadata, never a target.
        rows.append(dict(problem_id=pid, group_id=parent['group_id'],
            path_id=cid, prompt=parent['problem'], response=record['text'],
            answer=parent['answer'], source=dict(candidate_id=cid,
                teacher_revision=REVISION, attempt=record['attempt'],
                response_sha256=hashlib.sha256(record['text'].encode()).hexdigest())))
    if not rows:
        raise ValueError('No usable data; no student run is admitted')
    rows.sort(key=lambda r: (positions[r['problem_id']], r['source']['attempt']))
    return rows


def exact_plans(rows, tokenizer):
    encoded = [encode_row(row, tokenizer, 2048) for row in rows]
    lengths = [r['n_supervised'] for r in encoded]
    for row, value in zip(rows, encoded):
        row['source'].update({k: value[k] for k in
                            ('n_prompt', 'n_processed', 'n_supervised')})
    plans = {}
    for seed in SEEDS:
        schedule = whole_response_schedule(lengths, TARGETS, UPDATES, seed)
        budget = budget_report(encoded, schedule, 1)
        exposures = Counter(i for update in schedule for i in update)
        if (set(exposures) != set(range(len(rows))) or
                max(exposures.values()) - min(exposures.values()) > 1 or
                budget['supervised_response_tokens'] != TARGETS or
                budget['optimizer_updates'] != UPDATES or budget['padding_tokens'] != 0):
            raise ValueError('Complete-answer exposure contract differs')
        plans[str(seed)] = dict(seed=seed, updates=schedule, budget=budget)
    return plans

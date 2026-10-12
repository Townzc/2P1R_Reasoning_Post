"""Frozen acquisition accounting; no model, cloud, or external calls."""
from collections import Counter
import hashlib
from analyses.gsm8k_answer_audit import score
from src.real_math_audit import normalized

TEACHER = 'Qwen/Qwen2.5-Math-1.5B-Instruct'
REVISION = 'aafeb0fc6f22cbf0eaeed126eff8be45b0360a35'
SYSTEM = r'Please reason step by step, and put your final answer within \boxed{}.'
SAMPLING = dict(do_sample=True, temperature=0.8, top_p=0.95, top_k=0,
                max_new_tokens=1024, num_return_sequences=1, repetition_penalty=1.0,
                eos_token_id=[151645, 151643], pad_token_id=151643)
SEED = 2026101201


def messages(parent):
    return [dict(role="system",content=SYSTEM),dict(role="user",content=parent["problem"])]


def roster(parents):
    if len(parents) != 128 or len({r['id'] for r in parents}) != 128:
        raise ValueError('Exactly 128 unique frozen parents required')
    if [r['rank'] for r in parents] != list(range(1, 129)):
        raise ValueError('Parent order changed')
    # Startup parents count within the same 1,024 attempts. No adaptive resizing.
    blocks = [(0, 16), (16, 48), (48, 80), (80, 112), (112, 128)]
    batches = []
    for lo, hi in blocks:
        for attempt in range(1, 9):
            items = [dict(problem_id=r['id'], attempt=attempt,
                          candidate_id=f"{r['id']}::attempt{attempt:02d}") for r in parents[lo:hi]]
            batches.append(dict(batch_id=f'batch_{len(batches):04d}', seed=SEED+len(batches), items=items))
    return batches


def completion(ids):
    """Identify the first native EOS; never treat padded suffix as generated text."""
    if not ids or len(ids) > 1024 or any(type(x) is not int or x < 0 for x in ids):
        raise ValueError('Invalid returned continuation')
    pos = next((i for i, x in enumerate(ids) if x in SAMPLING['eos_token_id']), None)
    if pos is None:
        if len(ids) != 1024:
            raise ValueError('Unknown early stopping')
        return dict(token_ids=ids, text_token_ids=ids, eos=False, truncated=True, token_count=len(ids))
    if any(x != SAMPLING['pad_token_id'] for x in ids[pos+1:]):
        raise ValueError('Nonpadding tokens after first EOS')
    return dict(token_ids=ids[:pos+1], text_token_ids=ids[:pos], eos=True,
                truncated=False, token_count=pos+1)


def assess(parent, text, stop, seen, usable_seen):
    verdict = score(parent, text, stop['eos'], stop['truncated'])
    key = hashlib.sha256(normalized(text).encode()).hexdigest()
    duplicate = seen.get(key)
    usable_duplicate = usable_seen.get(key)
    usable = bool(verdict['clean_correct'] and usable_duplicate is None)
    # All normalized text duplicates are linked, even unsuccessful ones.
    return dict(score=verdict, normalized_text_sha256=key, duplicate_of=duplicate,
                usable_duplicate_of=usable_duplicate,
                usable=usable, duplicate_definition='NFC_whitespace_exact_within_parent',
                distinct_reasoning_strategy_certified=False)


def summarize(parents, records):
    groups = {p['id']: [] for p in parents}
    identities = set()
    for row in records:
        cid = row['candidate_id']
        if cid in identities or row['problem_id'] not in groups:
            raise ValueError('Duplicate or foreign candidate record')
        identities.add(cid);groups[row['problem_id']].append(row)
    supply = []
    for pid, rows in groups.items():
        rows.sort(key=lambda r:r['attempt'])
        if [r['attempt'] for r in rows] != list(range(1, len(rows)+1)):
            raise ValueError('Attempt accounting has a gap')
        usable = [r for r in rows if r['usable']]
        supply.append(dict(problem_id=pid, attempted=len(rows), usable=len(usable),
            attempts_to_k={str(k):usable[k-1]['attempt'] if len(usable)>=k else None for k in (1,2,4)},
            right_censored_k=[k for k in (1,2,4) if len(usable)<k]))
    return dict(parents=len(parents), recorded_outputs=len(records), usable=sum(r['usable'] for r in records),
        duplicates=sum(r['duplicate_of'] is not None for r in records),
        wrong_or_unusable=sum(not r['score']['clean_correct'] for r in records),
        rejected_valid_duplicates=sum(r['score']['clean_correct'] and r['usable_duplicate_of'] is not None for r in records),
        duplicate_any_text_count_overlaps_invalid_count=True,
        stop_counts=dict(Counter('eos' if r['stop']['eos'] else 'length' for r in records)),
        parse_counts=dict(Counter(r['score']['status'] for r in records)), supply=supply,
        reasoning_validated=False, historical_bank_cost_known=False,
        attempts_to_k_is_logged_tape_statistic_not_counterfactual_runtime=True)

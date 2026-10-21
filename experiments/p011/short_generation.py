"""Prepared P011 B/C2 pure request and saved-verdict rules; not a cloud entry.

No model/scorer calls. The future IO path must verify complete original receipts
and raw/score bindings before passing any reused records to these functions.
"""
from experiments.p010.teacher_contract import canonical_request, sampling
from experiments.p010.dataset_selection import usable, text_key, inventory


def request(pid, attempt, prompt_ids, temperature):
    if temperature not in (0.6, 0.8, 1.0):
        raise ValueError('Only original B/C2 temperatures allowed')
    row = canonical_request(pid, attempt, 't15', prompt_ids)
    params = sampling(row)
    params['temperature'] = temperature
    return {'request': row, 'sampling': params}


def b_requests(ordered400, prompt_ids, temperature=1.0):
    if len(ordered400) != 400 or len(set(ordered400)) != 400 or temperature not in (.6, 1.):
        raise ValueError('Original ordered400 and B T1.0 / optional T0.6 required')
    return [request(pid, attempt, prompt_ids[pid], temperature)
            for pid in ordered400 for attempt in range(1, 17)]


def b_selection(ordered400, records):
    """Owner B-only amendment: first usable of16, else attempt01 unverified.

    Recorded by Claude at d3f66ec3, before B generation. The full B path must
    bind that original owner-decision record in its actual CR/A1/A2-lite.
    C2 and every original P010 result retain their original four-attempt rule.
    """
    if len(ordered400) != 400 or len(set(ordered400)) != 400:
        raise ValueError('Original ordered400 required')
    groups = inventory(records)
    if set(groups) != set(ordered400):
        raise ValueError('Unexpected or missing parent in B complete record roster')
    selected = {1: [], 4: [], 8: []}
    fallback, conflicts, short = [], [], {4: [], 8: []}
    for pid in ordered400:
        attempts = groups[pid]
        if set(attempts) != set(range(1, 17)):
            raise ValueError('All16 original attempts required; no assumed failure')
        first = next((attempts[a] for a in range(1, 17) if usable(attempts[a])), attempts[1])
        selected[1].append(first['candidate_id'])
        if not usable(first):
            fallback.append(pid)
        seen, candidates = set(), []
        for a in range(1, 17):
            row = attempts[a]
            key = text_key(row['answer_text'])
            if usable(row) and key not in seen:
                seen.add(key)
                candidates.append(row['candidate_id'])
        if not candidates or candidates[0] != first['candidate_id']:
            conflicts.append(pid)
        for k in (4, 8):
            selected[k].extend(candidates[:k])
            if len(candidates) < k:
                short[k].append(pid)
    if conflicts != fallback:
        raise ValueError('Only all16-unusable parents may break B nesting')
    return {'selected_ids': {str(k): v for k, v in selected.items()},
            'unverified_fallback_questions': fallback, 'nesting_conflicts': conflicts,
            'underfilled_questions': {str(k): v for k, v in short.items()},
            'requires_owner_disposition': len(fallback) / 400 > .10,
            'report_fallback_above_10pct': len(fallback) / 400 > .10,
            'K1_attempt_window': 16, 'all16_unusable_exception_reported': True,
            'report_underfill_above_10pct': {str(k): len(v) / 400 > .10 for k, v in short.items()},
            'training_admitted': False}


def confirmed_first_four(pid, records):
    """A missing earlier attempt is unknown, never a failed or zero-scored attempt."""
    for attempt in range(1, 5):
        cid = f'{pid}::attempt{attempt:02d}'
        if cid not in records:
            return {'state': 'missing', 'next_attempt': attempt}
        row = records[cid]
        if (row['candidate_id'] != cid or row['problem_id'] != pid or row['attempt'] != attempt
                or row['usable'] is not usable(row)):
            raise ValueError('Original confirmed request/verdict identity differs')
        if usable(row):
            return {'state': 'usable', 'selected_id': cid}
    return {'state': 'exhausted'}


def c2_prefix(ordered_e1d, t72_records, t15_records, s1_ids):
    """Prefix stops on a genuinely missing request or after400 common usable IDs.

    Every examined parent is evaluated in the original E1d order. A T72 missing
    prefix blocks reuse and never authorizes T72 generation. T15 may request only
    the next missing attempt, preserving all already confirmed outputs. No later
    parent can replace an unconfirmed earlier one. S1 overlap is counted, allowed.
    """
    if len(set(ordered_e1d)) != len(ordered_e1d):
        raise ValueError('Original E1d order must contain unique parents')
    chosen, examined, skipped = [], [], []
    for pid in ordered_e1d:
        right = confirmed_first_four(pid, t72_records)
        if right['state'] == 'missing':
            return {'complete': False, 'blocked_missing_old_T72': pid,
                    'new_T72_generation_allowed': False, 'selected': chosen, 'examined': examined}
        if right['state'] == 'exhausted':
            # A known unusable T72 parent cannot enter the common support set.
            # No T15 output is needed to establish that deterministic exclusion.
            examined.append(pid)
            skipped.append(pid)
            continue
        left = confirmed_first_four(pid, t15_records)
        if left['state'] == 'missing':
            return {'complete': False, 'next_T15_request': {'problem_id': pid,
                    'attempt': left['next_attempt']}, 'selected': chosen, 'examined': examined}
        examined.append(pid)
        if right['state'] == left['state'] == 'usable':
            chosen.append({'problem_id': pid, 't15': left['selected_id'], 't72': right['selected_id']})
        if len(chosen) == 400:
            return {'complete': True, 'selected': chosen, 'examined': examined,
                    'T72_exhausted_skipped_without_new_T15': skipped,
                    'S1_overlap': sum(x['problem_id'] in s1_ids for x in chosen),
                    'training_admitted': False}
    return {'complete': False, 'insufficient_common_support': len(chosen),
            'T72_exhausted_skipped_without_new_T15': skipped,
            'selected': chosen, 'examined': examined, 'requires_owner_disposition': True}

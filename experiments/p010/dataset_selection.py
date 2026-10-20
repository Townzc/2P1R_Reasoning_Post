"""P010 frozen selection over saved verdicts, with no scorer or model import.

Selection never silently repairs contradictory fallback/nesting requirements.
Short cells retain their original question roster and report actual coverage.
"""
from collections import Counter
import hashlib

from experiments.p010.common import digest
from src.real_math_audit import normalized


def usable(row):
    verdict = (row.get('score') or {}).get('score', {})
    return bool(row.get('gold_supported', True)
                and row['stop']['stop_reason'] == 'native_eos'
                and verdict.get('box_extracted') is True
                and verdict.get('parsed') is True
                and verdict.get('correct') is True)


def text_key(text):
    return hashlib.sha256(normalized(text).encode()).hexdigest()


def inventory(records):
    groups = {}
    for cid, row in records.items():
        pid, attempt = row['problem_id'], row['attempt']
        if (type(attempt) is not int or not 1 <= attempt <= 16
                or cid != f'{pid}::attempt{attempt:02d}'
                or row['candidate_id'] != cid
                or type(row['answer_text']) is not str
                or row['usable'] is not usable(row)):
            raise ValueError('Saved identity/usable verdict differs from frozen definition')
        groups.setdefault(pid, {})[attempt] = row
    return groups


def select_grid(model, records, roster, original_s1=None):
    """Build requested selections only; no data-dependent replacement questions."""
    if model not in ('t15', 't7', 't72'):
        raise ValueError('Teacher outside P010')
    ids400, ids3200 = roster['400'], roster['3200']
    if (len(ids400) != 400 or len(ids3200) != 3200
            or ids3200[:400] != ids400 or len(set(ids3200)) != 3200):
        raise ValueError('Exact original nested S1 question roster required')
    groups = inventory(records)
    cells, k1 = {}, {}
    if model == 't15':
        if not original_s1:
            raise ValueError('T1.5 K1 requires immutable S1 answers')
        for n, ids in ((400, ids400), (3200, ids3200)):
            rows = original_s1[str(n)]
            if ([r['problem_id'] for r in rows] != ids
                    or any(r['attempt'] != 1 for r in rows)):
                raise ValueError('Original S1 answer identity changed')
            cells[f'n{n}_k1'] = dict(reuse_original_S1=True,
                original_rows_sha256=digest(rows), question_ids=ids,
                selected_ids=[r['path_id'] for r in rows], N=n, P_cov=n,
                retried_questions=0, unverified_questions=[], underfilled_questions=[])
        for r in original_s1['400']:
            old = groups.get(r['problem_id'], {}).get(1)
            if (old is None or not usable(old) or old['answer_text'] != r['response']
                    or old['candidate_id'] != r['path_id']):
                raise ValueError('T1.5 first answer differs from original S1 bytes')
            k1[r['problem_id']] = old
    else:
        for pid in ids3200:
            attempts = groups.get(pid, {})
            found = next((attempts[a] for a in range(1, 5)
                          if a in attempts and usable(attempts[a])), None)
            # A missing earlier request is not a recorded unsuccessful attempt.
            required = range(1, found['attempt'] + 1) if found else range(1, 5)
            if any(a not in attempts for a in required):
                raise ValueError('K1 attempt prefix incomplete; no assumed failure')
            k1[pid] = found or attempts[1]
        for n, ids in ((400, ids400), (3200, ids3200)):
            unverified = [pid for pid in ids if not usable(k1[pid])]
            retried = sum(k1[pid]['attempt'] > 1 for pid in ids)
            cells[f'n{n}_k1'] = dict(reuse_original_S1=False, question_ids=ids,
                selected_ids=[k1[pid]['candidate_id'] for pid in ids], N=n, P_cov=n,
                retried_questions=retried, retry_fraction=retried/n,
                unverified_questions=unverified, unverified_fraction=len(unverified)/n,
                report_before_training=len(unverified)/n > .03, underfilled_questions=[])
    for k in (4, 8):
        selected, counts, duplicates, conflicts = [], {}, [], []
        for pid in ids400:
            attempts = groups.get(pid, {})
            if set(attempts) != set(range(1, 17)):
                raise ValueError('Every original question needs all16 recorded attempts')
            seen, candidates = {}, []
            for attempt in range(1, 17):
                row = attempts[attempt]
                if not usable(row):
                    continue
                key = text_key(row['answer_text'])
                if key in seen:
                    duplicates.append(dict(candidate_id=row['candidate_id'], duplicate_of=seen[key]))
                else:
                    seen[key] = row['candidate_id']; candidates.append(row)
            chosen = candidates[:k]
            if not chosen or chosen[0]['candidate_id'] != k1[pid]['candidate_id']:
                conflicts.append(pid)
            selected.extend(r['candidate_id'] for r in chosen); counts[pid] = len(chosen)
        short = [pid for pid in ids400 if counts[pid] < k]
        cells[f'n400_k{k}'] = dict(reuse_original_S1=False, question_ids=ids400,
            selected_ids=selected, N=len(selected), P_cov=sum(n > 0 for n in counts.values()),
            per_question_counts=counts, underfilled_questions=short,
            underfilled_fraction=len(short)/400, report_before_training=len(short)/400 > .10,
            normalized_duplicates=duplicates, nesting_conflicts=conflicts,
            selection_conflict_requires_owner_resolution=bool(conflicts),
            deduplication='P008 NFC_whitespace_exact_within_parent')
    if not set(cells['n400_k4']['selected_ids']) <= set(cells['n400_k8']['selected_ids']):
        raise AssertionError('K4 must be nested in K8')
    return dict(model=model, cells=cells, records_sha256=digest(records),
                training_admitted=False, new_generations=0, new_symbolic_scores=0)


def select_e1d(records, ordered_ids, accepted_proof):
    groups = inventory(records)
    selected, examined = [], []
    for pid in ordered_ids:
        attempts = groups.get(pid, {})
        found = next((attempts[a] for a in range(1, 5)
                      if a in attempts and usable(attempts[a])), None)
        required = range(1, found['attempt']+1) if found else range(1, 5)
        if any(a not in attempts for a in required):
            raise ValueError('E1d selection cannot skip an unconfirmed request')
        examined.append(pid)
        if found:
            selected.append(found['candidate_id'])
        if len(selected) == 3200:
            break
    accepted = [records[cid]['problem_id'] for cid in selected]
    if (len(selected) != 3200 or accepted != accepted_proof['problem_ids']
            or len(examined) != accepted_proof['examined_prefix_count']
            or digest(ordered_ids) != accepted_proof['source_order_sha256']):
        raise ValueError('Actual E1d proof differs from ordered first3200 rule')
    return dict(selected_ids=selected, question_ids=accepted, N=3200, P_cov=3200,
                examined_prefix=examined, no_T15_correctness_filter=True,
                training_admitted=False)

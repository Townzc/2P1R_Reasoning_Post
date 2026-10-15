"""Prepared read-only S1 scoring proof; no scorer, decoding or admission.

The future complete outer oracle must supply the original verified 500 rows,
source/runtime binding and admitted local window. This module only checks the
stored journal and summarizes its existing Boolean verdicts. It does not load
model state, call math-verify, re-extract boxes or adjudicate disagreements.
"""
import hashlib
import json
import math
from pathlib import Path


def digest(value):
    data = json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode()
    return hashlib.sha256(data).hexdigest()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def require(condition, message):
    if not condition:
        raise ValueError(message)


def duration(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def verify_samples(saved, rows, scored, pairs):
    require(saved['sample_domain'] == 'p009-p1-fixed-audit-sample-v1'
            and saved['independent_adjudication_complete'] is False
            and saved['eligibility_admitted'] is False
            and saved['primary_labels_changed'] is False
            and saved['structurally_unsupported_gold_rows'] == 0
            and saved['unsupported_gold_is_not_scored_zero'] is True,
            'Original sample scope cannot imply adjudication or scientific admission')
    originals = {row['id']:row for row in rows}
    disagree = [r for r in scored if r['score'].get('string_symbolic_disagreement')]
    fallback = [r for r in scored if r['score']['fallback_used']]
    boxed = saved['boxed_rows']
    require(type(boxed) is int and 0 <= boxed <= 500
            and type(saved['unbraced_boxed_rows']) is int
            and 0 <= saved['unbraced_boxed_rows'] <= 500
            and saved['disagreement_count'] == len(disagree)
            and saved['fallback_rows'] == len(fallback), 'Original sample counts differ')
    high = bool(boxed and 100*len(fallback) > 2*boxed)
    require(saved['fallback_over_two_percent'] is high, 'Original fallback threshold differs')
    order = lambda r:(digest([saved['sample_domain'], r['id']]), r['id'])
    for key, chosen in [('disagreement_sample', sorted(disagree, key=order)[:50]),
                        ('fallback_sample', sorted(fallback, key=order)[:25] if high else [])]:
        require(saved[key] == [dict(original=originals[r['id']], scored=r, adjudication=None)
                               for r in chosen], 'Fixed sample changed or adjudication was invented')
    outer = sum(p['observation']['symbolic']['status'] == 'outer_timeout' for p in pairs.values())
    require(saved['unique_pairs'] == len(pairs) and saved['outer_timeout_unique_pairs'] == outer
            and saved['outer_timeout_over_half_percent'] is bool(pairs and 200*outer > len(pairs)),
            'Original unique-pair timeout denominator differs')


def verify_score_payload(root, rows, binding, local_seconds):
    """Validate one complete original journal; no filesystem writes or scoring."""
    root = Path(root)
    require(len(rows) == 500 and len({r['id'] for r in rows}) == 500
            and len({r['problem_id'] for r in rows}) == 500
            and all(r['id'] == 'S1::'+r['problem_id'] for r in rows)
            and isinstance(binding, dict) and bool(binding)
            and type(local_seconds) is int and 0 < local_seconds <= 129600,
            'Exact original500 rows, explicit binding and bounded local window required')
    expected = {'INTENT.json', 'ROWS.json', 'pairs', 'chunks', 'ALL_SCORED_ROWS.json',
                'AUDIT_SAMPLES.json', 'COMPLETED.json'}
    require({p.name for p in root.iterdir()} == expected,
            'Partial, failed or unknown journal is not a complete endpoint')
    require(read(root/'ROWS.json') == rows, 'The original decoded rows changed')
    intent = read(root/'INTENT.json')
    require(intent['ordered_rows_sha256'] == digest(rows) and intent['row_count'] == 500
            and intent['binding'] == binding and intent['local_seconds'] == local_seconds
            and intent['automatic_retry'] is False and intent['payload_only'] is True
            and intent['outer_hard_process_cap_required'] is True,
            'Original scoring intent/source/window differs')
    pairs = {}
    for path in sorted((root/'pairs').iterdir()):
        require(path.is_file() and path.suffix == '.json', 'Unknown pair artifact')
        value = read(path); pair = value['pair']; obs = value['observation']
        require(isinstance(pair, list) and len(pair) == 2
                and all(isinstance(x, str) and x.strip() for x in pair), 'Original pair is invalid')
        key = hashlib.sha256(json.dumps(pair, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()
        require(path.stem == key == obs['pair_id'] and key not in pairs
                and type(obs['attempt_index']) is int and duration(obs['elapsed_seconds']),
                'Original pair identity/timing differs')
        symbolic = obs['symbolic']
        require((symbolic['status'] == 'compared' and type(symbolic['equivalent']) is bool)
                or (symbolic['status'] in ('parse_failure', 'symbolic_timeout', 'tool_error', 'outer_timeout')
                    and symbolic['equivalent'] is None), 'Unknown symbolic result is not a scored zero')
        pairs[key] = value
    require(sorted(v['observation']['attempt_index'] for v in pairs.values()) == list(range(len(pairs))),
            'Missing or duplicate original symbolic attempt')
    folders = sorted((root/'chunks').iterdir())
    require([p.name for p in folders] == [f'{i:05d}' for i in range(5)], 'Exactly five original chunks required')
    seen = set(); merged = []
    for i, folder in enumerate(folders):
        require(folder.is_dir() and {p.name for p in folder.iterdir()} ==
                {'INTENT.json', 'RESULT.json', 'COMPLETED.json', 'TIMING.json'},
                'Failed or partial original chunk cannot become complete')
        source = rows[i*100:(i+1)*100]
        ci, result, done, timing = [read(folder/n) for n in
                                   ('INTENT.json', 'RESULT.json', 'COMPLETED.json', 'TIMING.json')]
        require(ci['start'] == i*100 and ci['end'] == (i+1)*100
                and ci['rows_sha256'] == digest(source) and ci['row_ids'] == [r['id'] for r in source]
                and [r['id'] for r in result['rows']] == ci['row_ids']
                and ci['cached_pairs_before'] == len(seen)
                and done['intent_sha256'] == sha(folder/'INTENT.json')
                and done['result_sha256'] == sha(folder/'RESULT.json')
                and done['confirmed_rows'] == 100 and done['technical_unknown'] == 0
                and duration(timing['elapsed_through_completed_proof_seconds'])
                and timing['final_timing_record_write_excluded'] is True,
                'Original committed chunk identity/hash/counter/timing differs')
        referenced = set()
        for original, row in zip(source, result['rows']):
            score = row['score']; key = row['pair_id']; obs = row['symbolic_attempt']
            require(all(type(score.get(k)) is bool for k in ('correct', 'parsed', 'fallback_used',
                    'teacher_label_eligible', 'reasoning_validated')) and score['reasoning_validated'] is False,
                    'Complete frozen Boolean verdict required')
            if key is None:
                require(obs is None and score['correct'] is False and score['parsed'] is False,
                        'An unattempted answer cannot acquire a positive verdict')
            else:
                require(key in pairs and obs == pairs[key]['observation']
                        and pairs[key]['pair'] == [original['gold'], score['extracted_answer']]
                        and score['symbolic'] == obs['symbolic']
                        and original['stop_reason'] in ('native_eos', 'new_problem_boundary'),
                        'A row references a different original pair')
                referenced.add(key)
            if original['stop_reason'] in ('length_cap', 'invalid_special_token'):
                require(key is None and score['status'] == original['stop_reason'],
                        'Original logical cap/special failure must remain a failure')
        new = referenced-seen
        require(ci['new_pair_intents'] == {p:pairs[p]['pair'] for p in new}
                and result['new_symbolic_attempts'] == len(new)
                and {pairs[p]['observation']['attempt_index'] for p in new} ==
                    set(range(len(seen), len(seen)+len(new))), 'Original pair intent/cache history differs')
        seen |= referenced
        require(result['unique_pairs_in_session'] == len(seen)
                and result['rows_in_session'] == (i+1)*100, 'Original session counters differ')
        merged.extend(result['rows'])
    require(seen == set(pairs) and read(root/'ALL_SCORED_ROWS.json') == merged,
            'All original pairs and complete ordered rows are required')
    saved = read(root/'AUDIT_SAMPLES.json'); verify_samples(saved, rows, merged, pairs)
    scores = {r['problem_id']:out['score']['correct'] for r,out in zip(rows, merged)}
    result = read(root/'COMPLETED.json')
    require(result['row_count'] == 500 and result['question_correct'] == scores
            and result['correct'] == sum(scores.values()) and result['unique_symbolic_pairs'] == len(pairs)
            and result['technical_unknown'] == 0 and result['original_rows_sha256'] == sha(root/'ROWS.json')
            and result['scored_rows_sha256'] == sha(root/'ALL_SCORED_ROWS.json')
            and result['audit_samples_sha256'] == sha(root/'AUDIT_SAMPLES.json')
            and duration(result['elapsed_before_final_proof_seconds'])
            and result['elapsed_before_final_proof_seconds'] < local_seconds
            and result['payload_only'] is True and result['full_runtime_lineage_admission_checked'] is False
            and result['external_outcome_review_pending'] is True and result['scientific_G1_admitted'] is False
            and result['original_parser_unchanged'] is True and result['automatic_retry'] is False
            and result['new_model_calls'] == 0, 'Original complete proof or its scope differs')
    return dict(passed=True, complete_rows=500, correct=sum(scores.values()), question_correct=scores,
        unique_symbolic_pairs=len(pairs), technical_unknown=0, chunks=5,
        scoring_completed_file_sha256=sha(root/'COMPLETED.json'), symbolic_calls=0,
        raw_decode_calls=0, model_state_loads=0, boxed_denominator_recomputed=False,
        boxed_denominator_source='Original AUDIT_SAMPLES.json; no new extraction',
        payload_only=True, full_runtime_lineage_admission_checked=False,
        scientific_G1_admitted=False, independent_adjudication_complete=False)

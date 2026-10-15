"""Read-only P1 closeout candidate. Never import or call a symbolic scorer.

This validates the committed journal and summarizes existing Boolean verdicts.
It does not adjudicate disagreements, change labels, or admit eligibility/G0.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import tarfile

SCOPE = 'p009-math-p1-complete-readonly-publication-code'
DATASETS = ('math_procurement', 'teacher_math_zero', 'qwen_math_zero', 'qwen_math_four')
DRIVER_SCOPE = 'p009-math-p1-extended-local-window-and-first100'
TIMING_SCOPE = 'p009-math-p1-first100-throughput'


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def create(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(canonical(value) + b'\n')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def finite_duration(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def review_file(path, scope):
    value = read(path)
    require(value.get('scope') == scope and value.get('decision') in ('PASS', 'PASS-WITH-NOTES')
            and len(value.get('report_commit', '')) == 40
            and file_sha(value['local_report_path']) == value['report_sha256'],
            'A real fixed report with the exact scope is required')
    return value


def verify_journal(root, rows, binding, timing_review):
    """Verify hashes, exact order and cached observations without executing code."""
    root = Path(root)
    require(rows and len({r['id'] for r in rows}) == len(rows), 'Unique complete input rows required')
    basis = read(root/'journal/BASIS.json')
    require(basis['ordered_rows_sha256'] == digest(rows) and basis['row_count'] == len(rows)
            and basis['binding'] == binding, 'Original journal basis changed')
    require(timing_review['basis_sha256'] == digest(basis), 'Numeric basis differs')
    pairs = {}
    for path in sorted((root/'journal/pairs').glob('*.json')):
        record = read(path)
        pair = record['pair']
        obs = record['observation']
        pair_id = hashlib.sha256(json.dumps(pair, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()
        require(isinstance(pair, list) and len(pair) == 2 and all(isinstance(x, str) for x in pair)
                and path.stem == pair_id == obs['pair_id'] and pair_id not in pairs,
                'Original unique pair identity differs')
        require(type(obs['attempt_index']) is int and finite_duration(obs['elapsed_seconds']),
                'Invalid original pair timing/index')
        pairs[pair_id] = record
    require(sorted(p['observation']['attempt_index'] for p in pairs.values()) == list(range(len(pairs))),
            'Unconfirmed or duplicated symbolic attempt')
    position = 0
    merged = []
    seen = set()
    folders = sorted((root/'journal/chunks').iterdir())
    require(bool(folders), 'No committed chunks')
    for i, folder in enumerate(folders):
        require(folder.name == f'{i:05d}' and folder.is_dir()
                and {p.name for p in folder.iterdir()} == {'INTENT.json', 'RESULT.json', 'COMPLETED.json', 'TIMING.json'},
                'Partial, failed or unknown chunk must be preserved, never published complete')
        intent, result, proof, timing = [read(folder/n) for n in
                                        ('INTENT.json', 'RESULT.json', 'COMPLETED.json', 'TIMING.json')]
        start, end = intent['start'], intent['end']
        require(type(start) is int and type(end) is int and start == position
                and 1 <= end-start <= 100 and end <= len(rows)
                and (i != 0 or end == min(100, len(rows))), 'Original chunk boundary/order differs')
        original = rows[start:end]
        require(intent['rows_sha256'] == digest(original)
                and intent['row_ids'] == [r['id'] for r in original]
                and [r['id'] for r in result['rows']] == intent['row_ids']
                and proof['intent_sha256'] == file_sha(folder/'INTENT.json')
                and proof['result_sha256'] == file_sha(folder/'RESULT.json')
                and proof['confirmed_rows'] == len(original) and proof['technical_unknown'] == 0
                and intent['automatic_retry'] is False,
                'Committed original proof or row identity differs')
        require(finite_duration(timing['elapsed_through_completed_proof_seconds'])
                and timing['final_timing_record_write_excluded'] is True, 'Original chunk timing invalid')
        require(intent['timing_review'] == (None if i == 0 else timing_review),
                'Chunk was not bound to the accepted measured timing review')
        referenced = set()
        for original_row, row in zip(original, result['rows']):
            score = row['score']
            require(all(type(score.get(k)) is bool for k in
                        ('correct', 'parsed', 'fallback_used', 'teacher_label_eligible', 'reasoning_validated'))
                    and score['reasoning_validated'] is False, 'Complete frozen Boolean verdict required')
            pair_id, obs = row['pair_id'], row['symbolic_attempt']
            if pair_id is None:
                require(obs is None and score['correct'] is False and score['parsed'] is False,
                        'Unattempted answer cannot acquire a positive verdict')
            else:
                require(pair_id in pairs and obs == pairs[pair_id]['observation']
                        and pairs[pair_id]['pair'] == [original_row['gold'], score['extracted_answer']]
                        and original_row['stop_reason'] in ('native_eos', 'new_problem_boundary')
                        and score['symbolic'] == obs['symbolic'], 'Row references a different cached pair')
                referenced.add(pair_id)
            if original_row['stop_reason'] in ('length_cap', 'invalid_special_token'):
                require(pair_id is None and score['status'] == original_row['stop_reason'],
                        'A logical stop failure cannot become an ordinary answer')
        new = referenced-seen
        require(intent['new_pair_intents'] == {p:pairs[p]['pair'] for p in new}
                and result['new_symbolic_attempts'] == len(new)
                and {pairs[p]['observation']['attempt_index'] for p in new}
                    == set(range(len(seen), len(seen)+len(new))), 'Original pair reservation/cache history differs')
        seen |= referenced
        require(result['unique_pairs_in_session'] == len(seen) and result['rows_in_session'] == end,
                'Original complete session counters differ')
        merged.extend(result['rows'])
        position = end
    require(position == len(rows) and seen == set(pairs), 'Complete roster and all original attempts required')
    require(merged == read(root/'ALL_SCORED_ROWS.json'), 'Final rows differ from original committed chunks')
    return merged, pairs, len(folders)


def verify_samples(samples, rows, scored):
    """Check saved fixed samples without calling extraction or adjudication."""
    require(set(samples) == set(DATASETS), 'Every original pool must appear')
    originals = {r['id']:r for r in rows}
    outcomes = {r['id']:r for r in scored}
    for name in DATASETS:
        pool = [outcomes[r['id']] for r in rows if r['dataset'] == name]
        saved = samples[name]
        require(saved['independent_adjudication_complete'] is False
                and saved['eligibility_admitted'] is False and saved['primary_labels_changed'] is False,
                'Publication cannot invent adjudication or eligibility')
        disagree = [r for r in pool if r['score'].get('string_symbolic_disagreement')]
        fallback = [r for r in pool if r['score']['fallback_used']]
        domain = saved['sample_domain']
        require(domain == 'p009-p1-fixed-audit-sample-v1', 'Fixed sample domain differs')
        order = lambda r:(digest([domain, r['id']]), r['id'])
        require(saved['disagreement_count'] == len(disagree) and saved['fallback_rows'] == len(fallback)
                and type(saved['boxed_rows']) is int and 0 <= saved['boxed_rows'] <= len(pool),
                'Saved complete sample counts differ')
        high = bool(saved['boxed_rows'] and 100*len(fallback) > 2*saved['boxed_rows'])
        require(saved['fallback_over_two_percent'] is high, 'Original fallback threshold differs')
        for key, expected in [('disagreement_sample', sorted(disagree, key=order)[:50]),
                              ('fallback_sample', sorted(fallback, key=order)[:25] if high else [])]:
            require(saved[key] == [dict(original=originals[r['id']], scored=r, adjudication=None)
                                   for r in expected], 'Fixed sample changed or adjudication was invented')
        pairs = {r['pair_id']:r['symbolic_attempt'] for r in pool if r['pair_id'] is not None}
        outer = sum(p['symbolic']['status'] == 'outer_timeout' for p in pairs.values())
        require(saved['unique_pairs'] == len(pairs) and saved['outer_timeout_unique_pairs'] == outer
                and saved['outer_timeout_over_half_percent'] is bool(pairs and 200*outer > len(pairs)),
                'Unique-pair timeout denominator or flag differs')


def checked_completion(root, driver, timing):
    root = Path(root)
    require(not (root/'FIRST100_FAILURE.json').exists() and not (root/'REMAINDER_FAILURE.json').exists(),
            'Failed or partial scoring is not a complete result')
    frozen, binding, rows = [read(root/n) for n in ('FROZEN.json', 'INPUT_BINDING.json', 'ROWS.json')]
    for field, name in [('rows_sha256', 'ROWS.json'), ('binding_sha256', 'INPUT_BINDING.json'),
                        ('exclusions_sha256', 'UNSUPPORTED_GOLD.json')]:
        require(frozen[field] == file_sha(root/name), 'Original frozen file changed')
    require(binding['source_files'] == driver['source_files'] == timing['driver_source_files']
            and len(driver['source_files']) == 12, 'Exact accepted12-source scoring lineage required')
    for name, h in driver['source_files'].items():
        require(file_sha(name) == h, 'Accepted scoring code changed')
    proposal = read(root/'FIRST100_PROPOSAL.json')
    require(timing['proposal_sha256'] == file_sha(root/'FIRST100_PROPOSAL.json')
            and timing['first100_result_sha256'] == file_sha(root/'journal/chunks/00000/RESULT.json')
            and timing['local_window_amendment_sha256'] == binding['local_window_amendment_sha256']
            and type(timing['approved_total_wall_seconds']) is int
            and proposal['serial_time_scenario_seconds'] <= timing['approved_total_wall_seconds'] <= 129600,
            'Actual accepted timing/owner binding differs')
    first, started, done = [read(root/n) for n in
                           ('FIRST100_COMPLETED.json', 'REMAINDER_STARTED.json', 'REMAINDER_COMPLETED.json')]
    require(finite_duration(first['total_command_seconds']) and 0 < first['total_command_seconds'] <= 1200
            and started['wall_seconds'] == timing['approved_total_wall_seconds']-first['total_command_seconds']
            and started['rows_sha256'] == frozen['rows_sha256'] and started['no_retry'] is True
            and finite_duration(done['total_command_seconds'])
            and done['total_command_seconds'] <= started['wall_seconds']
            and all(x['model_calls'] == 0 for x in (first, started, done)), 'Actual one-pass command proof differs')
    status = read(root/'ALL_ROWS_SCORED.json')
    require(status['rows'] == len(rows) and status['technical_unknown'] == 0 and status['model_calls'] == 0
            and all(status[k] is False for k in ('independent_adjudication_complete', 'eligibility_admitted',
                                                 'G0_admitted', 'primary_labels_changed', 'raw_decode_repeated')),
            'Scoring completion must not claim scientific admission')
    scored, pairs, chunks = verify_journal(root, rows, binding, timing)
    samples = read(root/'FIXED_AUDIT_SAMPLES.json')
    verify_samples(samples, rows, scored)
    excluded = read(root/'UNSUPPORTED_GOLD.json')
    summary = read(root/'INPUT_SUMMARY.json')
    require(len(excluded) == summary['structurally_unsupported_gold_rows']
            and len(rows) == summary['scorable_total']
            and len(rows)+len(excluded) == summary['generated_total'], 'Original gold exclusions differ')
    outcomes = {r['id']:r for r in scored}
    counts = {}
    for name in DATASETS:
        selected = [r for r in rows if r['dataset'] == name]
        omitted = [r for r in excluded if r['dataset'] == name]
        expected = summary['counts'][name]
        require(len(selected) == expected['scorable'] and len(omitted) == expected['unsupported_gold']
                and len(selected)+len(omitted) == expected['generated']
                and samples[name]['unsupported_gold_exclusions'] == omitted
                and samples[name]['structurally_unsupported_gold_rows'] == len(omitted),
                'Every generated row must have a score or explicit unsupported gold record')
        if name != 'math_procurement':
            require(len(selected) == 500 and not omitted and len({r['problem_id'] for r in selected}) == 500,
                    'All original500 endpoint gold rows are required')
        counts[name] = dict(generated=expected['generated'], scorable=len(selected),
            unsupported_gold=len(omitted), correct=sum(outcomes[r['id']]['score']['correct'] for r in selected),
            logical_caps=sum(r['stop_reason'] == 'length_cap' for r in selected),
            status_counts=dict(Counter(outcomes[r['id']]['score']['status'] for r in selected)),
            unique_pairs=samples[name]['unique_pairs'],
            outer_timeout_unique_pairs=samples[name]['outer_timeout_unique_pairs'],
            outer_timeout_over_half_percent=samples[name]['outer_timeout_over_half_percent'],
            fallback_rows=samples[name]['fallback_rows'], boxed_rows=samples[name]['boxed_rows'],
            fallback_over_two_percent=samples[name]['fallback_over_two_percent'],
            disagreement_count=samples[name]['disagreement_count'])
    return dict(counts=counts, chunks=chunks, unique_pairs=len(pairs), complete_rows=len(rows),
                total_first_command_seconds=first['total_command_seconds'],
                total_remaining_command_seconds=done['total_command_seconds'],
                technical_unknown=0, model_calls=0, symbolic_calls=0, raw_decoding_repeated=False,
                primary_labels_changed=False, independent_adjudication_complete=False,
                eligibility_admitted=False, G0_admitted=False,
                boxed_denominator_source='Original FIXED_AUDIT_SAMPLES; no new last-box extraction here')


def project_intent(value, timing):
    projected = json.loads(canonical(value))
    private_locator = projected['timing_review'].pop('local_report_path', None)
    require(private_locator == timing['local_report_path'], 'Only the known host locator may be projected')
    return projected


def publish(args):
    root, out = Path(args.root), Path(args.out)
    require(not out.exists(), 'Original or partial publication exists; preserve and reconcile, never rebuild')
    code = review_file(args.code_review, SCOPE)
    source_name = str(Path(__file__).resolve().relative_to(Path.cwd()))
    require(code.get('source_files') == {source_name:file_sha(__file__)}, 'Exact read-only publisher source required')
    driver = review_file(args.driver_review, DRIVER_SCOPE)
    timing = review_file(args.timing_review, TIMING_SCOPE)
    summary = checked_completion(root, driver, timing)
    # No scorer/pool instance is constructed; verification is only on saved data.
    files = [root/n for n in ('ROWS.json', 'UNSUPPORTED_GOLD.json', 'INPUT_BINDING.json', 'INPUT_SUMMARY.json',
        'FROZEN.json', 'FIRST100_STARTED.json', 'FIRST100_COMPLETED.json', 'FIRST100_PROPOSAL.json',
        'REMAINDER_STARTED.json', 'REMAINDER_COMPLETED.json', 'ALL_SCORED_ROWS.json', 'FIXED_AUDIT_SAMPLES.json',
        'ALL_ROWS_SCORED.json', 'journal/BASIS.json')]
    files += sorted((root/'journal/chunks').glob('*/*.json')) + sorted((root/'journal/pairs').glob('*.json'))
    require(all(p.is_file() and not p.is_symlink() for p in files), 'Original regular evidence files required')
    original = {str(p.relative_to(root)):dict(bytes=p.stat().st_size, sha256=file_sha(p)) for p in files}
    out.mkdir(parents=True, exist_ok=False)
    create(out/'PUBLICATION_INTENT.json', dict(utc=datetime.now(timezone.utc).isoformat(),
        complete_original_files=original, publisher_source_sha256=file_sha(__file__), no_retry=True))
    projected = {}
    with tarfile.open(out/'evidence.tar.gz', 'x:gz') as archive:
        for path in files:
            rel = str(path.relative_to(root))
            if path.name == 'INTENT.json' and '/chunks/' in '/'+rel:
                value = read(path)
                if value.get('timing_review') is not None:
                    value = project_intent(value, timing)
                    target = out/'projections'/rel
                    create(target, value)
                    member = 'projected/'+rel
                    archive.add(target, arcname=member, recursive=False)
                    projected[rel] = dict(archive_member=member, original_sha256=original[rel]['sha256'],
                        projection_sha256=file_sha(target), removed_fields=['timing_review.local_report_path'])
                    continue
            archive.add(path, arcname='original/'+rel, recursive=False)
    expected = {v['archive_member'] if rel in projected else 'original/'+rel:
                (v['projection_sha256'] if rel in projected else original[rel]['sha256'])
                for rel in original for v in [projected.get(rel, {})]}
    with tarfile.open(out/'evidence.tar.gz', 'r:gz') as archive:
        require(len(archive.getmembers()) == len(expected) and set(archive.getnames()) == set(expected),
                'Evidence archive member set differs')
        for member in archive:
            require(member.isfile(), 'Only regular evidence members allowed')
            with archive.extractfile(member) as stream:
                h = hashlib.sha256()
                while block := stream.read(1024*1024):
                    h.update(block)
            require(h.hexdigest() == expected[member.name], 'Archive readback differs')
    create(out/'SUMMARY.json', summary)
    create(out/'COLLECTION.json', dict(original_files=original, projected_intents=projected,
        archive_sha256=file_sha(out/'evidence.tar.gz'), archive_bytes=(out/'evidence.tar.gz').stat().st_size,
        original_intent_hashes_not_recomputable_from_projection=True,
        complete_originals_retained_privately=True, copied_symbolic_cache_not_new_scoring=True))
    for name, value in [('DRIVER_REVIEW.json', driver), ('TIMING_REVIEW.json', timing), ('PUBLICATION_CODE_REVIEW.json', code)]:
        projected_review = {k:v for k,v in value.items() if k != 'local_report_path'}
        create(out/name, projected_review)
    for name in sorted(set(driver['source_files']) | {source_name}):
        require(not Path(name).is_absolute() and '..' not in Path(name).parts,
                'Only repository-relative reviewed source names may be copied')
        target = out/'source'/name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream:
            stream.write(Path(name).read_bytes())
    create(out/'SOURCE_BINDING.json', dict(driver_source_files=driver['source_files'],
        publisher_source_files=code['source_files'], public_host_locator_projection=True))
    (out/'REVIEW_REQUEST.md').write_text('''# Actual complete P1 scoring and fixed-sample adjudication

Request p009-math-p1-complete-scoring-A2-r1.
Scope p009-math-p1-complete-scoring-and-independent-adjudication-A2.

Inspect the complete frozen rows, original committed pair observations/chunks,
all saved verdicts, complete denominator/exclusions, timeout/fallback flags and
all fixed samples in the archive. Independently adjudicate every registered
disagreement and required fallback sample against its full original question,
reference and answer; publish explicit findings and uncertainty. No invented
adjudication or silent label repair is permitted. The copied samples have null
adjudications deliberately. Any unresolved issue remains visible before labels
or G0 are used. No symbolic/raw rescore occurred in this publisher.

The full scoring run retains original pair failures/timeouts in its exact cache;
first100 was not rerun. All generated unsupported-gold rows are explicit and
not scored zero. The original seven long-context exclusions were never generated.
Inspect >0.5% unique-pair outer timeouts and >2% fallback denominators per pool.
The boxed denominator is copied from the original scorer's sample record, not
independently reparsed by this publisher. Do not treat code PASS as outcome A2.

Only the known host-local report locator in each remaining chunk intent is
projected out for public access. COLLECTION retains each original SHA and names
every projection; original completion proofs still refer to original private
intent bytes. A projection is not an original hash preimage or full independent
read of the private original. The source, review, complete output rows and all
other original evidence remain available here. No model/checkpoint is reloaded.

No eligibility, G0 or student admission is asserted by publication. P009 uses
its common reviewed vLLM evaluation settings and post-P0 internal-only scope;
HF638/969 historical references never enter new scientific effects.
''')
    create(out/'MANIFEST.json', {str(p.relative_to(out)):dict(bytes=p.stat().st_size, sha256=file_sha(p))
        for p in sorted(out.rglob('*')) if p.is_file()})
    print(out)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ('root', 'out', 'code-review', 'driver-review', 'timing-review'):
        parser.add_argument('--'+name, required=True)
    publish(parser.parse_args())

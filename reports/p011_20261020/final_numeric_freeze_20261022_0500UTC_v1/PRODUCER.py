"""One new copy-only P011 final freeze, never before the real 05:00 UTC cutoff.

This producer copies already saved numeric and review artifacts. It never imports
scientific code, reads old raw archives, or recomputes any result. A fresh honest
status snapshot must be supplied at the actual freeze, including any separately
authorized diagnostic that remains active or pending.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

R = Path('.local/p011_20261020/r1')
P = Path('reports/p011_20261020')
OUT = P / 'final_numeric_freeze_20261022_0500UTC_v1'
FENCE = R / 'final_numeric_freeze_20261022_r1'
CUTOFF = datetime(2026, 10, 22, 5, tzinfo=timezone.utc)
TECH = P / 'technical_numeric_handoff_v1'
TECH_TARGET = 'da4c00a60814a8692b7c098c7840201dd584876a'
TECH_FILES = (
    'MANIFEST.json', 'MISSING_AND_FAILED_CELLS.json', 'README.md',
    'REVIEW_AND_USE_LIMITS.json', 'SAVED_POSTHOC_SMOKE.json',
    'SOURCE_BINDINGS.json', 'T5_A_D_saved_endpoint_scores.csv',
    'T5_A_saved_endpoint_stops.csv', 'T5_A_saved_paired_contrasts.csv',
    'T5_D1_D2_saved_MATH_contrasts.json', 'T6_B_and_clean_saved_scores.csv',
    'T6_B_saved_paired_contrasts.csv', 'T6_C1_saved_descriptive_NLL.csv',
    'T6_clean_saved_paired_contrasts.csv',
)


def now():
    return datetime.now(timezone.utc).isoformat()


def dump(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write('\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--status-json', required=True)
    args = parser.parse_args()
    observed = datetime.now(timezone.utc)
    if observed < CUTOFF:
        raise ValueError('Formal P011 freeze is not authorized before real05UTC')
    status_path = Path(args.status_json)
    status_path.resolve().relative_to(R.resolve())
    status_bytes = status_path.read_bytes()
    status = json.loads(status_bytes)
    stamp = datetime.fromisoformat(status['snapshot_utc'].replace('Z', '+00:00'))
    if not CUTOFF <= stamp <= observed or (observed-stamp).total_seconds() > 600:
        raise ValueError('A new honest after-cutoff status snapshot is required')
    for key in ('original_science_complete', 'original_owner_A3_closed',
                'D2_all_disclosures_closed', 'P010_final_A5_closed',
                'new_diagnostics_separate_from_original_freeze',
                'course_interpretation_by_owner'):
        if status.get(key) is not True:
            raise ValueError('Missing original-scope closure/status fact: '+key)
    if not all(k in status for k in ('census_actual_A3_status',
                                     'forced_diagnostic_status',
                                     'active_work_and_CLI_receipts')):
        raise ValueError('New diagnostics may not silently disappear at freeze')

    sources = [(TECH/name, 'technical/'+name, TECH_TARGET) for name in TECH_FILES]
    selected = {
        'review_7873c88d_owner_actual_A3_accepted_v1': (
            'ACCEPTED.json', 'REPORT_OWNER150_COMPLETE_ACTUAL_A3.md',
            'FROZEN_SCORER_SENSITIVITY_NOTE.json', 'READ_SCOPE_NOTE.json'),
        'review_8ec1cf65_D2_disclosure_closed_v1': (
            'ACCEPTED.json', 'CLARIFICATION_D2_DISCLOSURE_FLAGS.md'),
        'review_10c0885f_forced_actual_A2_accepted_v1': (
            'ACCEPTED.json', 'A2_FORCED_ANSWER_ACTUAL_INPUTS_2921c7b9_PASS.md',
            'REVIEW_EVENTS.json', 'FRESH_BUDGET_PUBLIC_PROJECTION.json'),
        'ot3_full_math_census_actual_results_v1': (
            'COUNTS.json', 'ACTUAL_RESULT_BINDING.json', 'MANIFEST.json'),
        'owner_0205_new_analyses_authorization_v1': (
            'AUTHORIZATION_AND_RECEIPTS.json',
            'OWNER_DECISION_FORCED_ANSWER_AND_OT3_COUNT.md'),
    }
    for folder, names in selected.items():
        for name in names:
            sources.append((P/folder/name, 'later_records/'+folder+'/'+name,
                            'Exact saved later record; see its own immutable binding'))
    for name in status.get('additional_public_records', []):
        path = Path(name)
        rel = path.resolve().relative_to(P.resolve())
        if path.suffix not in ('.json', '.md', '.csv') or 'Z1' in str(rel).upper():
            raise ValueError('Only explicit small non-Z1 public metadata may be added')
        sources.append((path, 'cutoff_records/'+str(rel),
                        'Exact new review/status record selected at actual cutoff'))
    if len({dest for _, dest, _ in sources}) != len(sources):
        raise ValueError('Duplicate copy destination')
    for src, _, _ in sources:
        if not src.is_file() or src.stat().st_size > 2*1024*1024:
            raise ValueError('Missing/oversized metadata source; do not use science archives')
    if OUT.exists() or FENCE.exists():
        raise ValueError('P011 final copy freeze was already attempted; never rebuild it')
    FENCE.mkdir()
    dump(FENCE/'ATTEMPT.json', {'utc':now(), 'scheduled_cutoff_utc':CUTOFF.isoformat(),
                              'status_source':str(status_path), 'automatic_retry':False})
    try:
        OUT.mkdir()
        start = now()
        inventory = {}
        copied = []

        def write_bytes(dest, data):
            target = OUT/dest
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('xb') as stream:
                stream.write(data)
            record = {'bytes':len(data), 'sha256':hashlib.sha256(data).hexdigest()}
            inventory[dest] = record
            return record

        for src, dest, target in sources:
            # Read each selected old artifact only as the source of this new copy.
            data = src.read_bytes()
            record = write_bytes(dest, data)
            copied.append({'source_path':str(src), 'frozen_path':dest,
                           'source_target_reference':target, **record,
                           'byte_copy_only':True})
        write_bytes('STATUS_AT_ACTUAL_FREEZE.json', status_bytes)
        binding = {
            'scheduled_cutoff_utc':CUTOFF.isoformat(), 'actual_copy_start_utc':start,
            'actual_copy_end_utc':now(), 'copies':copied,
            'technical_source_target':TECH_TARGET,
            'technical_manifest_sha256':'f9297eeeef3d3b521ca6d74d67c8295fab94165e77bce55f046807c086f1f1d5',
            'numeric_source_binding_sha256':'2268af77436a9f78d9cdb349ad9e5cdbdf08480bc96833ad623da67248c4dac7',
            'old_science_recomputed':False, 'old_archives_rebuilt_or_reread':False,
            'Z1_original_read':False, 'historical_exposure_fact_retained':True,
            'pending_diagnostics_not_claimed_closed':True,
            'independent_private_binary_access_not_claimed':True,
            'final_A5_status':'PENDING_NOT_A_FORMER_SOURCE_OR_EARLY_CHECK',
        }
        write_bytes('COPY_BINDING.json', (json.dumps(binding, indent=2)+'\n').encode())
        write_bytes('PRODUCER.py', Path(__file__).read_bytes())
        readme = (
            '# P011 final numeric freeze\n\n'
            'Scheduled cutoff: 2026-10-22 05:00 UTC. This is one new copy-only '
            'technical freeze; actual copy timestamps are preserved separately. '
            'T5/T6 are unchanged bytes, with original per-row pointers and hashes. '
            'Large scientific archives are referenced by the copied bindings, not rebuilt.\n\n'
            'Original failures, NOT_RUN cells, A7 posthoc-smoke FAIL, frozen-scorer '
            'sensitivities, single-training-seed limits, private-state access limits '
            'and non-final-invoice accounting remain in force. New owner-authorized '
            'census/forced diagnostics have their exact status in STATUS_AT_ACTUAL_FREEZE; '
            'pending or active work is not represented as completed. The original '
            'freeze does not overwrite later separate diagnostic evidence.\n\n'
            'A true fixed final A5 numeric-provenance review is required after this '
            'freeze. P010 final A5 and prior P011 source/result reviews do not replace it. '
            'Course interpretation belongs to the owner.\n')
        write_bytes('README.md', readme.encode())
        dump(OUT/'MANIFEST.json', {'created_utc':now(), 'files':inventory,
                                  'science_recomputed':False, 'copy_binding':'COPY_BINDING.json'})
        end = now()
        result = {'scheduled_cutoff_utc':CUTOFF.isoformat(),
                  'actual_public_write_start_utc':start, 'actual_public_write_end_utc':end,
                  'packet':str(OUT), 'copied_original_files':len(copied),
                  'packet_file_count':len(inventory)+1,
                  'copy_binding_sha256':inventory['COPY_BINDING.json']['sha256'],
                  'manifest_sha256':hashlib.sha256((OUT/'MANIFEST.json').read_bytes()).hexdigest(),
                  'new_scientific_computation':False, 'final_A5_pending':True}
        dump(FENCE/'COMPLETED.json', result)
        dump(R/'P011_FINAL_FREEZE_20261022_COMPLETED.json', result)
        print(json.dumps(result, indent=2))
    except BaseException as exc:
        dump(FENCE/'FAILED.json', {'utc':now(), 'type':type(exc).__name__,
                                 'message':str(exc), 'automatic_retry':False})
        raise


if __name__ == '__main__':
    main()

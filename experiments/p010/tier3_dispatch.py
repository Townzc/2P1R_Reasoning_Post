"""Original Tier3 admission: exact inputs, independent A2, and an issued A4 report.

A4 is the owner's requested signal report, not an additional approval round.
All past attempted category reservations remain until a separate real settlement.
"""
from pathlib import Path
from decimal import Decimal
from collections import Counter
from experiments.p010.common import read, sha, CAPS

SEED29_RUNS = {f'{teacher}_s29_n{n}_k1' for teacher in ('t15', 't72') for n in (400, 3200)}


def attempted_records(root):
    root = Path(root)
    candidates = set(root.glob('*/INTENT.json')) | set(root.glob('*_runs/*/INTENT.json'))
    records = []
    for path in sorted(candidates):
        value = read(path)
        if isinstance(value.get('budget'), dict) and 'new_reserved_usd' in value['budget']:
            records.append(path)
    return records


def totals_and_slots(records, containers, app_states):
    totals = {k: Decimal('0') for k in CAPS}
    apps = []; pending = 0
    for path in records:
        b = read(path)['budget']; category = b['category']; amount = Decimal(b['new_reserved_usd'])
        if category not in totals or not amount.is_finite() or amount < 0:
            raise ValueError('Invalid original attempted reservation')
        totals[category] += amount
        submitted = path.parent/'SUBMITTED.json'
        if submitted.exists(): apps.append(read(submitted)['app_id'])
        else: pending += 1
    if len(apps) != len(set(apps)):
        raise ValueError('Ambiguous original app ownership')
    if any(totals[k] > CAPS[k] for k in totals) or sum(totals.values()) > Decimal('240'):
        raise ValueError('Original category or overall hard cap exceeded')
    counts = Counter(x.get('app_id') for x in containers)
    slots = pending
    for app in apps:
        count = counts.pop(app, 0)
        slots += count if str(app_states.get(app, 'unknown')).lower() == 'stopped' else max(1, count)
    slots += sum(counts.values())
    return totals, slots


def fixed_review(value):
    if (value.get('decision') not in ('PASS', 'PASS-WITH-NOTES')
            or sha(value['local_report_file']) != value['report_sha256']
            or len(value.get('target_commit', '')) != 40):
        raise ValueError('Actual complete fixed independent report required')
    return {k: v for k, v in value.items() if k != 'local_report_file'}


def validate_seed29_data(spec, run, review):
    expected = spec['data_binding']
    if (run not in SEED29_RUNS or run not in spec['configs']
            or review.get('scope') != 'p010-Tier3-seed29-exact-input-and-plan-A1'
            or review.get('target_commit') != expected['target_commit']
            or review.get('basis_sha256') != expected['basis_sha256']
            or review.get('input_archive_sha256') != expected['input_archive_sha256']
            or review.get('source_files') != expected['source_files']
            or set(review.get('accepted_cells', [])) != SEED29_RUNS):
        raise ValueError('Exact same-data four-cell seed29 A1 binding required')
    return True


def validate_a4(report, results_review):
    """An issued report with true actual-A3 evidence; no new audit permission."""
    if (report.get('scope') != 'p010-A4-scientific-signal-report'
            or report.get('issued') is not True
            or report.get('original_plan_commit') != '4287537f7733f5c3568ddb11695d47b566ef75fa'
            or report.get('actual_A3_report_sha256') != results_review.get('report_sha256')
            or results_review.get('scope') != 'p010-K1-E1d-existing-samples-and-C9-complete-A3'
            or results_review.get('decision') not in ('PASS', 'PASS-WITH-NOTES')
            or results_review.get('target_commit') != 'a8fb5c78190b5cd5f75cdcafd269af81cf717ff8'
            or report.get('results_target_commit') != results_review['target_commit']
            or report.get('automatic_Tier3_under_original_plan') is not True):
        raise ValueError('Actual A3 and issued original A4 signal report required')
    return True

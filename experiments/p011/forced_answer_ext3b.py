"""Isolated owner-authorized two-cell diagnostic; accepted scientific functions reused."""
from decimal import Decimal, ROUND_FLOOR
from pathlib import Path
from experiments.p011.owner_0205_common import read, sha

SPEC = 'reports/p011_20261020/forced_answer_ext3b_preflight_v2/SPEC.json'
SCOPE = 'p011-forced-answer-ext3b-complete-path-CR'
A2_SCOPE = 'p011-forced-answer-ext3b-actual-input-A2-lite'
LOCAL = Path('.local/p011_20261020/r1/forced_answer_ext3b_r1')
INPUTS = LOCAL/'inputs'
STORE = 'p011-forced-answer-ext3b-20261022-v1'
REMOTE = '/evidence/p011-forced-answer-ext3b-20261022-v1'
CELLS = ('long_R3024xE3_S-F15_s17', 'long_R9072x1_S-F15_s17')


def entry_slots(apps, containers, current_app):
    from experiments.p011.provider_slots import shared_slots
    slots = shared_slots(apps, containers)
    # A just-created app can be absent from an eventually consistent listing.
    if current_app not in {r.get('app_id', r.get('App ID')) for r in apps}:
        slots += 1
    if slots > 8: raise ValueError('Shared eight-slot ceiling including this pending app')
    return slots


def admit(spec_path, review_path, scope=SCOPE):
    spec, cr = read(spec_path), read(review_path)
    if (str(spec_path) != SPEC or scope != SCOPE or cr.get('scope') != SCOPE
            or cr.get('decision') not in ('PASS', 'PASS-WITH-NOTES')
            or cr.get('spec_sha256') != sha(spec_path)
            or cr.get('source_files') != spec['source_files']
            or sha(cr['local_report_path']) != cr['report_sha256']
            or any(cr.get(k) is not True for k in spec['required_source_review_flags'])):
        raise ValueError('Exact new two-cell source review required')
    for name, wanted in spec['source_files'].items():
        if sha(name) != wanted: raise ValueError('Reviewed source changed: '+name)
    for item in spec['authority_and_prior_reviews']:
        if sha(item['path']) != item['sha256']: raise ValueError('Authority/protocol binding changed')
    if tuple(spec['cells']) != CELLS or spec['total_cap_usd'] != '20':
        raise ValueError('Exact two-cell owner scope/cap required')
    return spec


def actual(spec):
    cr = read(spec['actual_review_path'])
    if (cr.get('scope') != A2_SCOPE or cr.get('decision') not in ('PASS', 'PASS-WITH-NOTES')
            or cr.get('spec_sha256') != sha(SPEC)
            or cr.get('input_manifest_sha256') != sha(INPUTS/'INPUT_MANIFEST.json')
            or sha(cr['local_report_path']) != cr['report_sha256']
            or any(cr.get(k) is not True for k in spec['required_A2_flags'])):
        raise ValueError('Exact actual two-cell input A2 required')
    return cr


def checked_budget(budget, now):
    rate = Decimal(budget['hourly_rate_usd'])
    retained = Decimal(budget['noncompute_allowance_usd'])
    predicted = Decimal(str(budget['throughput_prediction_seconds']))
    if (not all(x.is_finite() for x in (rate, retained, predicted)) or rate <= 0
            or retained != Decimal('1.50') or predicted <= 0
            or not 0 <= now-budget['observed_epoch'] <= 3600
            or budget['total_cap_usd'] != '20'
            or type(budget['active_or_pending_or_unknown_model_slots']) is not int
            or not 0 <= budget['active_or_pending_or_unknown_model_slots'] < 8):
        raise ValueError('Fresh $20 / eight-slot admission required')
    seconds = min(10800, int(((Decimal(20)-retained)*3600/rate)
                              .to_integral_value(rounding=ROUND_FLOOR))-660)
    if seconds < max(3600, 2*predicted):
        raise ValueError('At least two-times measured throughput headroom must fit')
    return {'worker_hard_seconds':seconds, 'startup_seconds':600,
            'platform_grace_seconds':60, 'hourly_rate_usd':str(rate),
            'throughput_prediction_seconds':str(predicted),
            'headroom_factor':str(Decimal(seconds)/predicted),
            'compute_upper_usd':str(rate*Decimal(seconds+660)/3600),
            'noncompute_allowance_usd':str(retained),
            'task_upper_usd':str(rate*Decimal(seconds+660)/3600+retained),
            'actual_invoice_claimed':False, 'automatic_retry':False}

"""One explicitly delegated infrastructure relaunch; original v3 science immutable."""
from copy import deepcopy
from decimal import Decimal, ROUND_FLOOR
from pathlib import Path
from experiments.p011.owner_0205_common import admit as original_admit
from experiments.p011.owner_0205_common import read, sha
from experiments.p011.forced_answer import CELLS

SPEC = 'reports/p011_20261020/forced_answer_relaunch_preflight_v1/SPEC.json'
ORIGINAL_SPEC = 'reports/p011_20261020/forced_answer_preflight_v3/SPEC.json'
SCOPE = 'p011-forced-answer-one-delegated-import-relaunch-CR'
LOCAL = Path('.local/p011_20261020/r1/forced_answer_r2')
PARENT = Path('.local/p011_20261020/r1/forced_answer_r1')
STORE = 'p011-forced-answer-20261022-r2'
# The original worker never imported/claimed and wrote no run/results. Reuse
# the existing uploaded input path and write the previously absent results.
REMOTE = '/evidence/p011-20261022-forced-answer-v1'


def checked_parent(spec):
    for item in spec['parent_evidence']:
        if sha(item['path']) != item['sha256']:
            raise ValueError('Immutable failed parent or upload evidence differs')
    records = read(PARENT/'collect/NAMED_RECORDS.json')
    status = read(PARENT/'collect/COMPLETED.json')['cell_statuses']
    stopped = read(PARENT/'collect/PROVIDER_STOPPED0.json')
    if (set(status) != set(CELLS) or records['claim'] is not None or records['terminal'] is not None
            or any(records['cell/'+cell] is not None for cell in status)
            or any(value != 'not_started' for value in status.values())
            or stopped['state'].lower() != 'stopped' or stopped['owned_containers'] != 0
            or stopped['app_id'] != spec['parent_app_id']):
        raise ValueError('Only the exact pre-claim import failure may be relaunched')
    return records


def admit(spec_path, review_path, scope=SCOPE):
    spec, cr = read(spec_path), read(review_path)
    if (str(spec_path) != SPEC or scope != SCOPE or cr.get('scope') != SCOPE
            or cr.get('decision') not in ('PASS', 'PASS-WITH-NOTES')
            or cr.get('spec_sha256') != sha(spec_path)
            or cr.get('source_files') != spec['source_files']
            or sha(cr['local_report_path']) != cr['report_sha256']
            or any(cr.get(flag) is not True for flag in spec['required_flags'])):
        raise ValueError('Exact delegated relaunch diff review required')
    for name, wanted in spec['source_files'].items():
        if sha(name) != wanted:
            raise ValueError('Relaunch source changed: '+name)
    for item in spec['authority_and_prior_reviews']:
        if sha(item['path']) != item['sha256']:
            raise ValueError('Exact direct delegation or original reviews differ')
    old = original_admit(ORIGINAL_SPEC, spec['original_source_review'],
                         'p011-forced-answer-complete-path-CR')
    a2 = read(spec['original_actual_review'])
    if (a2.get('scope') != 'p011-forced-answer-actual-input-A2-lite'
            or a2.get('decision') not in ('PASS', 'PASS-WITH-NOTES')
            or a2.get('spec_sha256') != sha(ORIGINAL_SPEC)
            or a2.get('input_manifest_sha256') != sha(Path(old['input_output'])/'INPUT_MANIFEST.json')
            or sha(a2['local_report_path']) != a2['report_sha256']
            or any(a2.get(k) is not True for k in old['required_A2_flags'])):
        raise ValueError('Unchanged original actual-input A2 required')
    checked_parent(spec)
    if read(PARENT/'upload/COMPLETED.json')['input_manifest_sha256'] != a2['input_manifest_sha256']:
        raise ValueError('Original completed upload must be reused exactly')
    routed = deepcopy(old)
    routed['local_root'] = str(LOCAL)
    routed['relaunch_spec'] = spec
    return routed


def checked_budget(budget, now):
    rate = Decimal(budget['hourly_rate_usd'])
    failed = Decimal(budget['failed_first_compute_upper_usd'])
    reported = Decimal(budget['failed_first_reported_tagged_usd'])
    prior = Decimal(budget['original_epoch_prior_nonforced_tagged_usd'])
    delayed = Decimal(budget['prior_unattributed_cost_allowance_usd'])
    if (not 0 <= now-budget['observed_epoch'] <= 3600
            or not all(x.is_finite() for x in (rate, failed, reported, prior, delayed))
            or rate <= 0 or failed < reported or reported < 0 or prior < 0
            or delayed < Decimal('20.02') or prior+delayed+12 > 150
            or type(budget['active_or_pending_or_unknown_model_slots']) is not int
            or not 0 <= budget['active_or_pending_or_unknown_model_slots'] < 8
            or budget['all_original_attempts_terminal'] is not True
            or budget['failed_first_app_id'] != 'ap-uPchVni8aP1OGmdNeMFyhL'
            or budget['total_forced_task_cap_usd'] != '12'
            or budget['original_noncompute_allowance_usd'] != '1.50'
            or budget['new_noncompute_allowance_usd'] != '1.50'):
        raise ValueError('Fresh cumulative $12/$150 or eight-slot contract failed')
    seconds = min(10800, int(((Decimal(12)-failed-Decimal(3))*3600/rate)
                            .to_integral_value(rounding=ROUND_FLOOR))-660)
    if seconds < 3600:
        raise ValueError('Less than original one-hour minimum fits; do not dispatch')
    compute = rate*Decimal(seconds+660)/3600
    return {'worker_hard_seconds':seconds, 'startup_seconds':600,
            'platform_grace_seconds':60, 'failed_first_compute_upper_usd':str(failed),
            'second_compute_upper_usd':str(compute), 'both_noncompute_allowances_usd':'3.00',
            'cumulative_task_upper_usd':str(failed+compute+3),
            'epoch_accounted_upper_usd':str(prior+delayed+12),
            'actual_invoice_claimed':False, 'further_automatic_retry':False}

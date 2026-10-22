"""Metadata-only continuation of four successful fresh reads; no network or models.

The original producer failed on uppercase State/Tasks before creating a budget.
Preserve its receipts and failure. Reuse those exact reads with the actual CLI
schema, original reviewed budget functions, and all three pending launch slots.
"""
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import json
import time

from experiments.p011.ext4b_runtime_contract import JOBS, cost_window
from experiments.p011.ext4b_path import ACTUAL, budget_check
from experiments.p011.forced_answer_relaunch import checked_budget
from experiments.p011.owner_0205_common import checked_metadata, create, read, sha, utc

R = Path('.local/p011_20261020/r1')
SOURCE = R / 'ext3b_runs_r1/budget_20261022T0707Z'


def shared_slots(apps, containers):
    if not isinstance(apps, list) or not isinstance(containers, list):
        raise ValueError('Unknown provider list schema')
    slots = 0
    identities = set()
    for row in apps:
        identity = row.get('app_id', row.get('App ID'))
        if not identity or identity in identities:
            raise ValueError('Missing or duplicate app identity')
        identities.add(identity)
        fields = {}
        for lower, upper in [('state', 'State'), ('tasks', 'Tasks')]:
            if lower in row and upper in row and row[lower] != row[upper]:
                raise ValueError('Conflicting provider field aliases')
            if lower not in row and upper not in row:
                raise ValueError('Missing provider slot field')
            fields[lower] = row[lower] if lower in row else row[upper]
        raw = str(fields['tasks'])
        if not raw.isdigit():
            raise ValueError('Unknown task count is not zero')
        tasks = int(raw)
        if str(fields['state']).lower() != 'stopped' or tasks:
            slots += max(1, tasks)
    return max(slots, len(containers))


def main():
    failure = read(SOURCE / 'FAILED.json')
    receipts = read(SOURCE / 'READ_RECEIPTS.json')
    if (failure['type'] != 'KeyError' or failure['message'] != "'State'"
            or [x['name'] for x in receipts] != ['rates', 'report', 'apps', 'containers']
            or any(x['exit'] != 0 for x in receipts)):
        raise ValueError('Exact completed read / pre-budget schema failure required')
    observed = min(x['started_epoch'] for x in receipts)
    if not 0 <= time.time() - observed < 3600:
        raise ValueError('Saved necessary snapshot has expired; do not refresh here')
    if list((R / 'ext3b_runs_r1/dispatch').glob('*/INTENT.json')):
        raise ValueError('Initial extension admission already consumed')
    if (R / 'forced_answer_r1/ONE_DELEGATED_RELAUNCH_FENCE.json').exists():
        raise ValueError('Forced relaunch already consumed')
    base_slots = shared_slots(read(SOURCE / 'apps.json'), read(SOURCE / 'containers.json'))
    if base_slots + 3 > 8:
        raise ValueError('Two training entries plus forced relaunch exceed eight slots')
    rates = read(SOURCE / 'rates.json')
    evidence = {str(SOURCE / n): sha(SOURCE / n) for n in
                ['rates.json', 'report.json', 'apps.json', 'containers.json', 'READ_RECEIPTS.json', 'FAILED.json']}
    evidence[str(Path(__file__).relative_to(Path.cwd()))] = sha(__file__)
    note = {'utc': utc(), 'original_failed_producer_preserved': True,
            'original_provider_reads_repeated': False, 'schema': 'state/tasks or exact equivalent aliases',
            'actual_provider_slots': base_slots, 'new_training_slots': 2,
            'one_forced_relaunch_slot': 1, 'all_three_pending_included': True,
            'source_receipts': str(SOURCE), 'evidence_files': evidence}
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out = R / 'ext3b_runs_r1' / ('budget_metadata_continuation_' + stamp)
    out.mkdir(exist_ok=False)
    create(out / 'ATTEMPT.json', note)
    rate = Decimal(rates['gpu_hour_cost_h100']) + 4*Decimal(rates['cpu_hour_cost']) + 96*Decimal(rates['mem_gib_hour_cost'])
    check = cost_window(rate, '0', '5')
    for job in JOBS:
        value = {'observed_epoch': observed, 'requested_job': job, 'requested_attempt': 1,
                 'pair_cap_usd': '90', 'per_cell_cap_usd': '45', 'hourly_rate_usd': str(rate),
                 'prior_job_compute_upper_usd': '0', 'retained_noncompute_usd': '5',
                 'other_cell_retained_upper_usd': '45',
                 'pair_total_upper_usd': str(Decimal(check['cumulative_cell_upper_usd']) + 45),
                 'slots_before': base_slots + 1, 'slots_after_requested': base_slots + 3,
                 'planned_forced_slot_included_before_dispatch': True,
                 'evidence_files': evidence, 'check': check,
                 'all_extension_app_reported_costs': {}, 'known_cell_reported_totals': {j: '0' for j in JOBS},
                 'prior_duration_bound_is_not_invoice': True, 'noncompute_allowance_is_not_zero_or_final_invoice': True,
                 'source_review_sha256': sha(R / 'EXT3B_FULL_RUNTIME_CR_ACCEPTED.json'),
                 'actual_review_sha256': sha(R / 'EXT3B_ACTUAL_A2_ACCEPTED.json'),
                 'actual_job_manifest_sha256': sha(ACTUAL),
                 'original_owner150_and_forced12_not_released_or_transferred': True}
        budget_check(value, job, 1, time.time())
        create(out / (job + '_BUDGET.json'), value)
    create(out / 'COMPLETED.json', {'utc': utc(), 'jobs': list(JOBS),
           'budgets': {j: sha(out / (j + '_BUDGET.json')) for j in JOBS}, 'final_invoice_claimed': False})
    print('EXT3B_BUDGET_DIRECTORY', out, flush=True)

    forced = R / 'forced_answer_r2' / ('budget_shared_receipts_' + stamp)
    forced.mkdir(parents=True, exist_ok=False)
    create(forced / 'ATTEMPT.json', note)
    try:
        original = read('reports/p011_20261020/forced_answer_preflight_v3/SPEC.json')
        prior = checked_metadata(original['terminal_cost_binding'])
        apps = set(prior['delayed_new_app_charges_usd'])
        parent_app = 'ap-uPchVni8aP1OGmdNeMFyhL'
        if parent_app in apps or prior['app_ids_without_reported_charge']:
            raise ValueError('Separate original epoch and failed forced app required')
        for row in prior['all_ten_original_attempts']:
            if row['status'] not in ('failed', 'completed') or sha(row['terminal_file']) != row['terminal_sha256']:
                raise ValueError('All original epoch attempts must remain terminal')
        costs = {a: None for a in apps | {parent_app}}
        for row in read(SOURCE / 'report.json'):
            if row.get('object_id') in costs:
                charge = Decimal(row['cost'])
                if not charge.is_finite() or charge < 0:
                    raise ValueError('Invalid tagged charge')
                key = row['object_id']
                costs[key] = str(Decimal(costs[key] or '0') + charge)
        if any(v is None for v in costs.values()):
            raise ValueError('Missing app charge is not zero')
        total = sum(max(Decimal(costs[k]), Decimal(prior['delayed_new_app_charges_usd'][k])) for k in apps)
        rate = Decimal(rates['gpu_hour_cost_h100']) + 4*Decimal(rates['cpu_hour_cost']) + 32*Decimal(rates['mem_gib_hour_cost'])
        parent = read(R / 'forced_answer_r1/dispatch/INTENT.json')
        exit_receipt = read(R / 'FORCED_V3_ORIGINAL_GPU_RUN_CLI_EXIT.json')
        elapsed = Decimal(str(datetime.fromisoformat(exit_receipt['finished_utc']).timestamp() - datetime.fromisoformat(exit_receipt['started_utc']).timestamp()))
        if elapsed < 0 or exit_receipt['exit_code'] != 1:
            raise ValueError('Exact original failed CLI interval required')
        failed = max(Decimal(costs[parent_app]), max(rate, Decimal(parent['budget']['hourly_rate_usd']))*(elapsed + 60)/3600)
        value = {'observed_epoch': observed, 'hourly_rate_usd': str(rate),
                 'original_epoch_prior_nonforced_tagged_usd': str(total), 'current_reported_app_costs_usd': costs,
                 'failed_first_app_id': parent_app, 'failed_first_reported_tagged_usd': costs[parent_app],
                 'failed_first_compute_upper_usd': str(failed), 'failed_first_wrapper_seconds': str(elapsed),
                 'prior_unattributed_cost_allowance_usd': '20.02', 'total_forced_task_cap_usd': '12',
                 'original_noncompute_allowance_usd': '1.50', 'new_noncompute_allowance_usd': '1.50',
                 'active_or_pending_or_unknown_model_slots': base_slots + 2,
                 'two_pending_training_slots_included': True, 'all_original_attempts_terminal': True,
                 'evidence_files': evidence, 'relaunch_review_sha256': sha(R / 'FORCED_RELAUNCH_CR_ACCEPTED.json'),
                 'original_parent_interval_is_upper_not_invoice': True,
                 'separate_90_dollar_training_extension_not_charged_to_original150': True, 'final_invoice_claimed': False}
        value['check'] = checked_budget(value, time.time())
        create(forced / 'BUDGET.json', value)
        create(forced / 'COMPLETED.json', {'utc': utc(), 'budget_sha256': sha(forced / 'BUDGET.json')})
        print('FORCED_BUDGET', forced / 'BUDGET.json', flush=True)
    except BaseException as exc:
        create(forced / 'FAILED.json', {'utc': utc(), 'type': type(exc).__name__, 'message': str(exc), 'automatic_retry': False})
        raise
    create(R / 'SHARED_FRESH_BUDGET_CONTINUATION_DONE.json', {'utc': utc(), 'extension_directory': str(out),
           'forced_directory': str(forced), 'provider_reads_repeated': False, 'source_receipts': str(SOURCE)})


if __name__ == '__main__':
    main()

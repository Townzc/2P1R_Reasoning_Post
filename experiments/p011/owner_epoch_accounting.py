"""All new owner jobs, including fallback controls, share one actual-cost epoch.

Completed worker durations tighten only an unbilled risk bound. They are never
labelled invoices. Delayed app charges are recorded separately; old failed
reservations do not enter this epoch. Unknown and pending jobs retain slots.
"""
from decimal import Decimal, ROUND_CEILING
from pathlib import Path
from experiments.sft_allocation_midpoint.common import read, sha, digest
from experiments.p011 import long_owner_path as original

OPTIONAL = ('A4', 'A3', 'A2', 'A8')
CONTROL_SPEC = 'reports/p011_20261020/fallback_clean_runtime_v1/SPEC.json'


def money(value):
    value = Decimal(str(value))
    if not value.is_finite() or value < 0:
        raise ValueError('Nonnegative finite cost required')
    return value


def cents(value):
    return money(value).quantize(Decimal('.01'), rounding=ROUND_CEILING)


def hourly(job, rates):
    resource = job['resources']
    return (money(rates['gpu_hour_cost_h100'])
            + money(resource['cpu']) * money(rates['cpu_hour_cost'])
            + money(resource['memory_mib']) / 1024 * money(rates['mem_gib_hour_cost']))


def observed_charges(report, apps):
    totals = {app: None for app in apps}
    for row in report:
        app = row.get('object_id')
        if app in totals:
            totals[app] = str(money(totals[app] or 0) + money(row['cost']))
    return totals


def snapshots(root):
    root = Path(root)
    specs = [read(root / original.SPEC), read(root / CONTROL_SPEC)]
    jobs = {name: job for spec in specs for name, job in spec['jobs'].items()}
    records = []
    for pattern in ('long_*_owner_r*/INTENT.json', 'fallback_*_r1/INTENT.json'):
        for p in sorted((root / original.LOCAL / 'dispatch').glob(pattern)):
            intent = read(p)
            name = intent['logical_id']
            if name not in jobs or intent['job_sha256'] != digest(jobs[name]):
                raise ValueError('Unknown new-epoch intent or changed job')
            result_path = p.parent / 'RESULT.json'
            result = read(result_path) if result_path.exists() else None
            if (p.parent / 'RETURN_ERROR.json').exists() and result is None:
                raise ValueError('New failed job requires actual cost reconciliation before optional spend')
            seconds = None
            if result is not None:
                if (result['status'] != 'completed' or result['logical_id'] != name
                        or result['app_id'] != intent['app_id']
                        or result['job_sha256'] != intent['job_sha256']):
                    raise ValueError('Exact successful original receipt required')
                seconds = result['finished_epoch'] - result['worker_start_epoch']
                if not 0 < seconds < jobs[name]['limits']['worker_seconds']:
                    raise ValueError('Original hard timer receipt differs')
            records.append(dict(logical_id=name, app_id=intent['app_id'], job=jobs[name],
                active=result is None, completed_worker_seconds=seconds,
                intent_file=str(p.relative_to(root)), intent_sha256=sha(p),
                result_file=str(result_path.relative_to(root)) if result else None,
                result_sha256=sha(result_path) if result else None))
    if len({r['logical_id'] for r in records}) != len(records):
        raise ValueError('Duplicate epoch record')
    return records


def check(root, spec, job, budget, records, observation, now):
    if not 0 <= now - budget['observed_epoch'] <= 3600 or now > original.LATEST_DISPATCH:
        raise ValueError('Fresh evidence and owner dispatch deadline required')
    if budget['owner_amendment_sha256'] != spec['owner_amendment_sha256']:
        raise ValueError('Direct owner authority differs')
    names = {r['logical_id'] for r in records}
    required = set(spec['initial_jobs']) | {
        f'fallback_t72_clean_s17_n{n}_k1_r1' for n in (400, 3200)}
    if not required.issubset(names):
        raise ValueError('All seven initial jobs and both controls must be included')
    if job['logical_id'] in names or job['cell'] not in OPTIONAL:
        raise ValueError('Only an unused owner optional job')
    for previous in OPTIONAL[:OPTIONAL.index(job['cell'])]:
        if not any(r['job']['cell'] == previous for r in records):
            raise ValueError('Owner optional order is A4 then A3 then A2/A8')
    active = [r for r in records if r['active']]
    known = {r['app_id'] for r in active}
    containers = observation['containers']
    unmatched = sum(c.get('app_id') not in known for c in containers)
    slots = max(len(active) + unmatched, len(containers))
    if slots >= 8:
        raise ValueError('Eight concurrent slots, including unknowns')
    for name, expected in budget['source_evidence_files'].items():
        if sha(Path(root) / name) != expected:
            raise ValueError('Budget evidence bytes changed')
    rates = budget['rates']
    for field in ('rates_file', 'meter_report_file'):
        if budget[field] not in budget['source_evidence_files']:
            raise ValueError('Original rates and metered report must be bound')
    if rates != read(Path(root) / budget['rates_file']):
        raise ValueError('Authenticated rate fields changed')
    grouped = {}
    for record in records:
        old = record['job']; limits = old['limits']
        # A completed success has a measured duration. Keep startup and platform
        # cleanup allowances because they are not included in that duration.
        worker = limits['worker_seconds'] if record['active'] else record['completed_worker_seconds']
        seconds = money(worker) + limits['startup_seconds'] + limits['platform_seconds'] - limits['worker_seconds']
        bound = cents(seconds * hourly(old, rates) / 3600)
        grouped[record['app_id']] = grouped.get(record['app_id'], Decimal(0)) + bound
    actuals = budget['new_epoch_app_observed_charges_usd']
    if actuals != observed_charges(read(Path(root) / budget['meter_report_file']), set(grouped)):
        raise ValueError('New app charges must match the original metered report')
    if set(actuals) != set(grouped):
        raise ValueError('All new apps, including both controls, require metering entries')
    exposure = sum(max(bound, money(actuals[app]) if actuals[app] is not None else Decimal(0))
                   for app, bound in grouped.items())
    limits = job['limits']
    fresh = cents((money(limits['platform_seconds']) + limits['startup_seconds']) * hourly(job, rates) / 3600)
    # One maximal archive egress plus three archive sizes stored for a day;
    # five dollars for unallocated image/build costs. This is a risk allowance,
    # never an asserted actual fee or a release of historical failed reserves.
    artifact_bytes = sum(r['job']['limits']['artifact_max_bytes'] for r in records) + limits['artifact_max_bytes']
    noncompute = cents(money(artifact_bytes) / (1024 ** 3) * (
        money(rates['egress_gib_cost']) + 3 * money(rates['volume_storage_gib_month_cost']) / 30) + 5)
    total = exposure + fresh + noncompute
    if total > 150:
        raise ValueError(f'New epoch hard cap: {total} > 150')
    return dict(new_reserved_usd=str(fresh), prior_reserved_usd='0', cap_usd='150',
        provider_slots=slots, epoch_unsettled_compute_upper_bound_usd=str(exposure),
        new_epoch_app_observed_charges_usd=actuals, noncompute_allowance_usd=str(noncompute),
        all_new_spend_upper_bound_after_usd=str(total), maximum_exposure_is_not_actual_expense=True,
        historical_failed_reservations_charged_to_new_epoch=False, prediction_gate_enabled=False,
        controls_included=sorted(r['logical_id'] for r in records if r['logical_id'].startswith('fallback_')),
        completed_worker_duration_is_not_an_invoice=True)

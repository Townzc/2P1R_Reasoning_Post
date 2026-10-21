"""Optional cells after the once-authorized A1 retry: all epoch attempts retained."""
from decimal import Decimal
from pathlib import Path
from experiments.p011 import owner_retry_accounting as retry,owner_epoch_accounting as base,long_owner_path as original
from experiments.sft_allocation_midpoint.common import read,sha
PARENT=retry.PARENT
RETRY=retry.RETRY
snapshots=retry.snapshots
observed_charges=base.observed_charges


def check(root,spec,job,budget,records,observation,now):
    if not 0<=now-budget['observed_epoch']<=3600 or now>original.LATEST_DISPATCH:
        raise ValueError('Fresh evidence and owner22:30 dispatch cutoff required')
    if budget['owner_amendment_sha256']!=spec['owner_amendment_sha256']:raise ValueError('Owner authority differs')
    names={r['logical_id'] for r in records}
    required=set(spec['initial_jobs'])|{f'fallback_t72_clean_s17_n{n}_k1_r1' for n in (400,3200)}|{RETRY}
    if not required.issubset(names):raise ValueError('All original jobs, controls and the A1 retry required')
    if job['logical_id'] in names or job['cell'] not in base.OPTIONAL:raise ValueError('Only an unused original optional cell')
    for previous in base.OPTIONAL[:base.OPTIONAL.index(job['cell'])]:
        if not any(r['job']['cell']==previous for r in records):raise ValueError('Owner optional order A4, A3, A2, A8')
    parent=[r for r in records if r['logical_id']==PARENT]
    if len(parent)!=1 or not parent[0]['failed'] or parent[0]['active']:raise ValueError('Original A1 must be terminal failed')
    active=[r for r in records if r['active']];known={r['app_id'] for r in active};containers=observation['containers']
    slots=max(len(active)+sum(c.get('app_id') not in known for c in containers),len(containers))
    if slots>=8:raise ValueError('Eight slots including unknowns')
    failure_spec=read(Path(root)/retry.RETRY_SPEC)
    for name,want in {**budget['source_evidence_files'],**failure_spec['failed_parent_files']}.items():
        if sha(Path(root)/name)!=want:raise ValueError('Exact current cost/failure evidence changed')
    for field in ('rates_file','meter_report_file'):
        if budget[field] not in budget['source_evidence_files']:raise ValueError('Rates and report must be bound')
    rates=budget['rates']
    if rates!=read(Path(root)/budget['rates_file']):raise ValueError('Authenticated rates differ')
    grouped={}
    for row in records:
        old=row['job'];lim=old['limits'];worker=lim['worker_seconds'] if row['active'] else row['completed_worker_seconds']
        seconds=base.money(worker)+lim['startup_seconds']+lim['platform_seconds']-lim['worker_seconds']
        bound=base.cents(seconds*base.hourly(old,rates)/3600)
        grouped[row['app_id']]=grouped.get(row['app_id'],Decimal(0))+bound
    actual=budget['new_epoch_app_observed_charges_usd']
    if actual!=base.observed_charges(read(Path(root)/budget['meter_report_file']),set(grouped)):
        raise ValueError('All new app charges must match saved live report')
    exposure=sum(max(bound,base.money(actual[app]) if actual[app] is not None else Decimal(0)) for app,bound in grouped.items())
    lim=job['limits'];fresh=base.cents((base.money(lim['platform_seconds'])+lim['startup_seconds'])*base.hourly(job,rates)/3600)
    size=sum(r['artifact_bytes_bound'] for r in records)+lim['artifact_max_bytes']
    noncompute=base.cents(base.money(size)/1024**3*(base.money(rates['egress_gib_cost'])+3*base.money(rates['volume_storage_gib_month_cost'])/30)+5)
    total=exposure+fresh+noncompute
    if total>150:raise ValueError(f'New epoch hard cap: {total} > 150')
    return dict(category=job['category'],new_reserved_usd=str(fresh),prior_reserved_usd='0',cap_usd='150',provider_slots=slots,
        epoch_unsettled_compute_upper_bound_usd=str(exposure),new_epoch_app_observed_charges_usd=actual,
        failed_parent_elapsed_upper_bound_not_invoice=True,old_failed_reserved_envelope_not_charged=True,
        noncompute_allowance_usd=str(noncompute),all_new_spend_upper_bound_after_usd=str(total),
        prediction_gate_enabled=False,maximum_exposure_is_not_actual_expense=True,completed_worker_duration_is_not_an_invoice=True,
        controls_included=sorted(r['logical_id'] for r in records if r['logical_id'].startswith('fallback_')))

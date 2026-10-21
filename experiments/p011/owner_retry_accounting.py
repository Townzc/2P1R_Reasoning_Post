"""Owner epoch ledger after the original A1 provider preemption.

Observed app charges remain separate from conservative unsettled-cost bounds.
A failed worker's bounded elapsed time is not an invoice or its old reservation.
"""
from decimal import Decimal
from pathlib import Path
from experiments.p011 import owner_epoch_accounting as base, long_owner_path as original
from experiments.sft_allocation_midpoint.common import read,sha,digest
RETRY_SPEC='reports/p011_20261020/owner_A1_infra_retry_runtime_v1/SPEC.json'
PARENT='long_A1_S-F15_s17_owner_r1'
RETRY='long_A1_S-F15_s17_owner_r2'


def checked_failure(root,spec,intent,error):
    for name,want in spec['failed_parent_files'].items():
        if sha(Path(root)/name)!=want:raise ValueError('Original preemption evidence changed')
    p=read(Path(root)/spec['failed_parent_preservation'])
    if (p['job']!=PARENT or not p['stable_inventory'] or p['terminal'] is not None
            or p['claim']['dispatch_sha256']!=digest(intent)
            or error['message']!='Original source/dispatch/report/window differs'
            or p['original_failure_observed_epoch']!=error['observed_epoch']):
        raise ValueError('Exact original failed call, claim and stable partial evidence required')
    elapsed=error['observed_epoch']-p['claim']['worker_start_epoch']
    if not 0<elapsed<=16260+600 or elapsed!=p['failed_duration_upper_bound_seconds']:
        raise ValueError('Failure elapsed bound is unavailable')
    size=p['copied_bytes']+sum(x['size'] for x in p['excluded_files'])
    return elapsed,size


def snapshots(root):
    root=Path(root);spec=read(root/RETRY_SPEC)
    specs=[read(root/original.SPEC),read(root/base.CONTROL_SPEC),spec]
    jobs={name:job for s in specs for name,job in s['jobs'].items()};records=[]
    for pattern in ('long_*_owner_r*/INTENT.json','fallback_*_r1/INTENT.json'):
        for p in sorted((root/original.LOCAL/'dispatch').glob(pattern)):
            intent=read(p);name=intent['logical_id']
            if name not in jobs or intent['job_sha256']!=digest(jobs[name]):raise ValueError('Unknown epoch attempt')
            rp=p.parent/'RESULT.json';ep=p.parent/'RETURN_ERROR.json';result=read(rp) if rp.exists() else None
            failed=False;seconds=None;artifact=jobs[name]['limits']['artifact_max_bytes']
            if result is not None:
                if (result['status']!='completed' or result['logical_id']!=name
                        or result['app_id']!=intent['app_id'] or result['job_sha256']!=intent['job_sha256']):
                    raise ValueError('Successful original receipt differs')
                seconds=result['finished_epoch']-result['worker_start_epoch']
                if not 0<seconds<jobs[name]['limits']['worker_seconds']:raise ValueError('Original hard timer differs')
                artifact=result['artifact']['tar_bytes']
            elif ep.exists():
                if name!=PARENT:raise ValueError('Another failed epoch job requires its own exact cost reconciliation')
                seconds,artifact=checked_failure(root,spec,intent,read(ep));failed=True
            records.append(dict(logical_id=name,app_id=intent['app_id'],job=jobs[name],active=result is None and not failed,
                failed=failed,completed_worker_seconds=seconds,artifact_bytes_bound=artifact,
                intent_file=str(p.relative_to(root)),intent_sha256=sha(p),
                result_file=str(rp.relative_to(root)) if result else None,result_sha256=sha(rp) if result else None,
                failure_return_sha256=sha(ep) if failed else None,failed_elapsed_is_upper_bound_not_invoice=failed))
    if len({r['logical_id'] for r in records})!=len(records):raise ValueError('Duplicate epoch attempt')
    return records


def check(root,spec,job,budget,records,observation,now):
    if not 0<=now-budget['observed_epoch']<=3600 or now>original.LATEST_DISPATCH:
        raise ValueError('Fresh evidence and owner22:30 dispatch cutoff required')
    if budget['owner_amendment_sha256']!=spec['owner_amendment_sha256']:raise ValueError('Owner authority differs')
    names={r['logical_id'] for r in records}
    if not set(spec['required_original_jobs']).issubset(names):raise ValueError('All original seven and both controls required')
    if job['logical_id']!=RETRY or RETRY in names or job['cell']!='A1':raise ValueError('Only the single unused A1 infrastructure retry')
    parent=[r for r in records if r['logical_id']==PARENT]
    if len(parent)!=1 or not parent[0]['failed'] or parent[0]['active']:raise ValueError('Original A1 must be terminal failed')
    active=[r for r in records if r['active']];known={r['app_id'] for r in active};containers=observation['containers']
    slots=max(len(active)+sum(c.get('app_id') not in known for c in containers),len(containers))
    if slots>=8:raise ValueError('Eight slots including unknowns')
    for name,want in {**budget['source_evidence_files'],**spec['failed_parent_files']}.items():
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

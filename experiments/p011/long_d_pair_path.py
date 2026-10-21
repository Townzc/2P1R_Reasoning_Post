"""Delegated D1/D2 F15 pair admission; original scientific bytes remain fixed.

A shared source/input/numeric review covers this path, never per-cell CR. Actual
configuration and numeric disposition remain data, not self-approval. A jobs are
unavailable here; the absence of A smoke selection is explicitly disclosed.
"""
from decimal import Decimal, ROUND_CEILING
from experiments.p011.long_protocol import ENDPOINT_BATCHES, resources
import fcntl
import hashlib
import math
from pathlib import Path
import re
import subprocess
import tempfile
import time
import traceback

from experiments.p011 import c1_admission as shared, c1_outer as lifecycle
from experiments.p011 import long_lr_r2_training as long_training, long_d_pair_execution as long_execution, long_d_pair_numeric as long_numeric
from experiments.p011 import long_transport, failed_attempt_ledger
from experiments.p011.c1_r2 import parent
from experiments.sft_allocation_midpoint.common import dump, read, sha, digest, verify

LOCAL=lifecycle.LOCAL
STORE=lifecycle.STORE
SPEC='reports/p011_20261020/long_d_pair_predicted_budget_runtime_v1/SPEC.json'
BUDGET_OWNER_SHA='364aaf6cd70fa9cf1a89902af6dedb33a1b64d7c47e73a12b37b6b97dfb69a2f'
LOCAL_INPUT_DIRECTORY='long_inputs_numeric_gold_r1'
AUDIT_METADATA_NAMES={'config.json','generation_config.json','tokenizer.json','tokenizer_config.json','special_tokens_map.json','vocab.json','merges.txt','added_tokens.json'}
CUTOFF=1792645200
SCOPE='p011-D-F15-pair-complete-path-CR-A1-A2-lite'
DECISION='reports/p011_20261020/review_c780b4e4_B100_and_long_disposition_accepted_v1/DECISION_LONG_LR_R2_FORECAST_FAILURES.md'
DECISION_SHA=long_numeric.DECISION_SHA
ORIGINAL_SPEC='reports/p011_20261020/long_current_runtime_v1/SPEC.json'
D_JOBS=('long_D1_S-F15_s17_r1','long_D2_S-F15_s17_r1')
INPUTS='/evidence/p011-20261020/long_inputs_r1'
BASE='/evidence/p011-20261020/long_runs_r1'


def logical(job):
    prefix='baseline' if job['kind']=='baseline' else job['cell']
    return 'long_'+prefix+'_'+job['arm']+'_s17_r1'


def key(job):return 'long/'+logical(job)


def validate(spec):
    if (set(spec.get('jobs',{}))!=set(D_JOBS)
            or spec.get('delegated_D_decision_sha256')!=DECISION_SHA
            or spec.get('D_both_or_neither') is not True
            or spec.get('D_F15_without_A_smoke_selection_disclosed') is not True
            or spec.get('original_numeric_SPEC_file')!=ORIGINAL_SPEC):
        raise ValueError('Only explicitly delegated D1/D2 F15 pair is available')
    for name,reserve in (('long_A7_S-F15_s17_r2','15.63'),('long_baseline_S-L15_s17_r2','12.17')):
        item=spec.get('failed_attempt_bindings',{}).get(name,{})
        if item.get('category')!='A' or item.get('reserved_usd')!=reserve:
            raise ValueError('Original long r2 failed parents/reserves must remain')
    if (spec.get('original_plan_commit')!=shared.PLAN or not spec.get('source_files')
            or not spec.get('jobs') or spec.get('measurement_exceptions')!=0
            or spec.get('budget_owner_decision_sha256')!=BUDGET_OWNER_SHA
            or not spec.get('prior_failed_C1') or not spec.get('failed_attempt_bindings')
            or spec.get('actual_input_directory')!=LOCAL_INPUT_DIRECTORY
            or not re.fullmatch(r'[0-9a-f]{64}',str(spec.get('actual_input_binding_sha256','')))
            or spec.get('result_cutoff_epoch')!=CUTOFF):
        raise ValueError('Exact original long-path plan/source/jobs required')
    if any(name not in spec['source_files'] for name in ('src/sft_data.py','src/__init__.py','experiments/p011/long_checkpoint.py','experiments/p011/long_protocol.py')):
        raise ValueError('R1 complete training source closure required')
    for name,job in spec['jobs'].items():
        kind,cell,arm=job['kind'],job['cell'],job['arm'];limits=job['limits'];model=job['model']
        if kind!='student' or cell not in ('D1','D2') or arm!='S-F15' or job['category']!='D':
            raise ValueError('No A, baseline or alternative-arm job admitted in D pair')
        if (kind not in ('baseline','student') or arm not in long_training.ARMS
                or name!=logical(job) or job['seed']!=17
                or job['category'] not in ('A','D')
                or (kind=='baseline' and (cell!='baseline' or arm=='S-F15' or job['category']!='A'))
                or (kind=='student' and cell not in ([f'A{i}' for i in range(1,9)]+['D1','D2']))
                or (kind=='student' and job['category']!=cell[0])
                or model['model_id']!=long_training.ARMS[arm]['model_id']
                or model['revision']!=long_training.ARMS[arm]['revision']
                or model['remote_path'] not in (
                    '/evidence/exploratory-20261014-r1/instruct_assets',
                    '/evidence/p011-20261020/models/qwen3b_instruct')
                or ('3B' in model['model_id']) != model['remote_path'].endswith('qwen3b_instruct')
                or not model['files'] or not model['producer_binding_files']
                or job.get('eos_token_ids')!=[151645,151643]
                or not job['input_files'] or not job['local_input_files']
                or job['local_input_files'].keys()!=job['input_files'].keys()|{'ENDPOINT_LOCAL.json'}
                or job['input_directory']!=cell
                or job['U']!=(654 if cell.startswith('A') else 64 if cell.startswith('D') else 0)
                or job['B']!=(41813212 if cell.startswith('A') else 4070922 if cell.startswith('D') else 0)
                or any(type(limits[n]) is not int or limits[n]<=0 for n in
                    ('worker_seconds','platform_seconds','startup_seconds','closeout_seconds','score_seconds','full_result_window_seconds'))
                or limits['startup_seconds']<600 or limits['platform_seconds']<limits['worker_seconds']+60
                or not 0<limits['score_seconds']<=33000
                or limits['closeout_seconds']<limits['score_seconds']+5
                or limits['full_result_window_seconds']<limits['startup_seconds']+limits['platform_seconds']+limits['closeout_seconds']
                or type(limits['artifact_max_bytes']) is not int or not 0<limits['artifact_max_bytes']<=100_000_000_000
                or not job['timing']['source_evidence_files']
                or job['timing'].get('whole_iteration_scope_accepted') is not True):
            raise ValueError('Unreviewed arm/dose/model/input/full-window configuration')
        metadata=model.get('local_audit_asset_files',{})
        prior=model.get('preflight_asset_readback',{})
        expected_readback=str(Path(LOCAL)/'long_preflight_io_r1/model_uploads'/model['revision']/'COMPLETED.json')
        if (not {'config.json','generation_config.json','tokenizer.json','tokenizer_config.json'}<=metadata.keys()
                or not metadata.keys()<=AUDIT_METADATA_NAMES
                or any(model['files'].get(n)!=v for n,v in metadata.items())
                or prior.get('path')!=expected_readback
                or not re.fullmatch(r'[0-9a-f]{64}',str(prior.get('sha256','')))):
            raise ValueError('Pinned local audit metadata and original preflight asset readback required')
        if job.get('resources') != resources(kind,arm):
            raise ValueError('Exact per-arm CPU/host-memory resources required')
        rates=job.get('resource_rates_usd_per_hour',{})
        if set(rates)!=set(('H100','cpu_core','GiB')) or any(not Decimal(str(v)).is_finite() or Decimal(str(v))<=0 for v in rates.values()):
            raise ValueError('Fresh full resource rate components required')
        expected_rate=Decimal(str(rates['H100']))+4*Decimal(str(rates['cpu_core']))+Decimal(job['resources']['memory_mib'])/1024*Decimal(str(rates['GiB']))
        if Decimal(str(limits['hourly_rate_usd']))!=expected_rate:
            raise ValueError('Host-memory cost must be included in admitted full rate')
        long_execution.engine_settings(job['context'])
        # No new measurement exception for A/D. Every initial model must have
        # a specific independently accepted complete-iteration timing basis.
        p=policy(job,1,'0');initial=long_numeric.forecast(p,job['U'],ENDPOINT_BATCHES,[],[],1)
        minimum=(Decimal(str(initial['projected_total_worker_seconds']))*Decimal('1.10')/100).to_integral_value(rounding=ROUND_CEILING)*100
        if limits['worker_seconds']<minimum or limits['worker_seconds']%100:
            raise ValueError('Explicit minimum10percent initial headroom and100second rounding required')
    return spec


def preparation_basis(spec,root):
    root=Path(root)
    if sha(root/DECISION)!=DECISION_SHA or sha(root/ORIGINAL_SPEC)!=spec['original_numeric_SPEC_sha256']:
        raise ValueError('Fixed delegated decision and original D job basis differ')
    original=read(root/ORIGINAL_SPEC)
    for name in D_JOBS:
        current=spec['jobs'][name];old=original['jobs'][name]
        if {k:v for k,v in current.items() if k not in ('limits','timing')}!={k:v for k,v in old.items() if k not in ('limits','timing')}:
            raise ValueError('Original D scientific job/input/model object changed')
        t=current['timing'];prior=old['timing']
        if (t['training_unit_seconds']!=prior['training_unit_seconds']
                or t['future_allowance_seconds']!=prior['future_allowance_seconds']
                or t['endpoint_batch_seconds']!=prior['endpoint_batch_seconds']+[600]
                or any(current['limits'][k]!=old['limits'][k] for k in
                    ('artifact_max_bytes','closeout_seconds','score_seconds','startup_seconds','hourly_rate_usd'))):
            raise ValueError('Only delegated forecast/proxy/headroom operational values may change')


def policy(job,start,prior):
    t=job['timing'];l=job['limits']
    p=dict(category=job['category'],worker_start_epoch=start,worker_hard_seconds=l['worker_seconds'],
        result_deadline_epoch=CUTOFF,full_result_seconds=l['full_result_window_seconds'],
        measurement_exceptions=0,projection_multiplier=1.2,uncalibrated_future_seconds=t['future_allowance_seconds'],
        training_unit_seconds=t['training_unit_seconds'],endpoint_batch_seconds=t['endpoint_batch_seconds'],
        hourly_rate_usd=l['hourly_rate_usd'],startup_allowance_seconds=l['startup_seconds'],
        reserved_usd=l['reserved_usd'],prior_reserved_usd=prior,platform_timeout_seconds=l['platform_seconds'],
        delegated_forecast_decision_sha256=DECISION_SHA,elapsed_multiplier=1.0,
        training_estimator='max_historical_proxy_observed_complete_cycle_mean',endpoint_uncalibrated_proxy_seconds=600)
    long_numeric.forecast(p,job['U'],ENDPOINT_BATCHES,[],[],start)
    return p


def reviewed(spec,path,review):
    validate(spec);result=shared.fixed_report(review)
    preparation_basis(spec,Path(path).resolve().parents[3])
    expected=dict(scope=SCOPE,original_plan_commit=shared.PLAN,spec_sha256=sha(path),
        source_files=spec['source_files'],jobs_sha256=digest(spec['jobs']),measurement_exceptions=0,
        budget_owner_decision_sha256=BUDGET_OWNER_SHA,
        prior_failed_C1_sha256=digest(spec['prior_failed_C1']),
        failed_attempt_bindings_sha256=digest(spec['failed_attempt_bindings']),
        actual_input_directory=LOCAL_INPUT_DIRECTORY,actual_input_binding_sha256=spec['actual_input_binding_sha256'],
        delegated_D_decision_sha256=DECISION_SHA,original_numeric_SPEC_sha256=spec['original_numeric_SPEC_sha256'])
    flags=('complete_source_closure_accepted','OT3_actual_A1_accepted','AM_actual_A1_accepted',
        'endpoint_native_inputs_A1_accepted','all_original_complete_timing_sources_accepted',
        'full_state_raw_scoring_window_and_budget_accepted','remote_paths_traced_to_producers',
        'current_owner_budget_and_failed_reservations_accepted',
        'completed_numeric_gold_inputs_and_prior_asset_reuse_accepted',
        'D_pair_F15_without_A_smoke_selection_explicitly_accepted',
        'elapsed_once_training_complete_cycle_mean_endpoint_max_accepted',
        'uncalibrated600_endpoint_and_unchanged963_future_accepted',
        'worker10percent_headroom_fixed_hard_limits_accepted',
        'both_D_reservations_sequential80percent_and_full_windows_accepted',
        'all_original_failed_parents_and_reservations_retained',
        'unchanged_frozen_LR_consumption_and_narrow_validator_accepted')
    if any(review.get(k)!=v for k,v in expected.items()) or any(review.get(k) is not True for k in flags):
        raise ValueError('Full shared long CR/A1/A2-lite absent')
    return result


def published(root,spec):
    def git(*a):return subprocess.check_output(['git',*a],cwd=root,timeout=45)
    if git('branch','--show-current').decode().strip()!='codex/icml-acl-2027':raise ValueError('Wrong branch')
    head=git('rev-parse','HEAD').decode().strip()
    if git('ls-remote','origin','refs/heads/codex/icml-acl-2027').decode().split()[0]!=head:
        raise ValueError('Execution HEAD not published')
    shared.exact_source(spec,root)
    preparation_basis(spec,root)
    for name in [*spec['source_files'],SPEC,DECISION,ORIGINAL_SPEC]:
        if git('show',head+':'+name)!=(Path(root)/name).read_bytes():raise ValueError('Uncommitted source/spec')
    return head


def selection(job,review):
    if logical(job) not in D_JOBS or review is not None:
        raise ValueError('Only explicit delegated D pair without a fabricated smoke result')
    return dict(delegated_decision_sha256=DECISION_SHA,arm='S-F15',
        no_A_smoke_selection=True,limitation_must_be_disclosed=True)


def pair_budget(spec,records,prior_D):
    attempted={r['logical_id'] for r in records};total=Decimal(str(prior_D));steps=[]
    for name in D_JOBS:
        if name in attempted:continue
        job=spec['jobs'][name];reserve=Decimal(str(job['limits']['reserved_usd']))
        if not reserve.is_finite() or reserve<=0 or reserve>Decimal('25')-total:
            raise ValueError('Both D full reservations must fit the remaining D cap')
        projection=long_numeric.forecast(policy(job,1,str(total)),job['U'],ENDPOINT_BATCHES,[],[],1)
        steps.append(dict(logical_id=name,prior_D_reserved_usd=str(total),reserved_usd=str(reserve),initial_forecast=projection))
        total+=reserve
    return steps


def budget_check(root,spec,job,budget,records,obs,now):
    totals,slots=shared.accounting(records,obs['containers'],obs['states'])
    reserve=Decimal(str(job['limits']['reserved_usd']));cat=job['category']
    if (type(now) not in (int,float) or not math.isfinite(now)
            or type(budget.get('observed_epoch')) not in (int,float) or not math.isfinite(budget['observed_epoch'])
            or not 0<=now-budget['observed_epoch']<=3600 or slots>=4
            or budget.get('all_attempted_reservations_usd')!=totals
            or budget.get('category')!=cat or budget.get('cap_usd')!=str(shared.CAPS[cat])
            or budget.get('overall_cap_usd')!='180' or budget.get('protected_usd')!='0'
            or budget.get('budget_owner_decision_sha256')!=BUDGET_OWNER_SHA
            or budget.get('reserve_release_used') is not False
            or budget.get('owner_estimate_used_as_balance') is not False
            or budget.get('availability_basis')!='owner_current_balance_minus_retained_P011_reserves_and_meter_growth'
            or Decimal(str(budget['hourly_rate_usd']))!=Decimal(str(job['limits']['hourly_rate_usd']))
            or not budget['source_evidence_files']
            or any(r['logical_id']==logical(job) for r in records)
            or (not Decimal(str(budget['available_after_retained_prior_reserves_usd'])).is_finite()
                or Decimal(str(budget['available_after_retained_prior_reserves_usd']))-reserve<0)
            or sum(map(Decimal,totals.values()))+reserve>180
            or now+job['limits']['full_result_window_seconds']>CUTOFF):
        raise ValueError('Fresh D1/unused/shared slots/full window failed')
    if not Decimal(str(budget['observed_gross_resource_usd'])).is_finite() or Decimal(str(budget['observed_gross_resource_usd']))<0:
        raise ValueError('Actual delayed gross observation required')
    for name,value in budget['source_evidence_files'].items():
        p=Path(name)
        if p.is_absolute() or '..' in p.parts or sha(Path(root)/p)!=value:raise ValueError('Budget bytes differ')
    initial=long_numeric.forecast(policy(job,now,totals[cat]),job['U'],ENDPOINT_BATCHES,[],[],now)
    pair=pair_budget(spec,records,totals['D'])
    return dict(pair_sequential_budget=pair,category=cat,new_reserved_usd=str(reserve),prior_reserved_usd=totals[cat],
        all_attempted_reservations_usd=totals,provider_slots=slots,initial_forecast=initial,
        protected_usd='0',budget_owner_decision_sha256=BUDGET_OWNER_SHA,not_actual_expense=True)


def submit(root,spec,job_id,review_file,budget_file,selection_file,store,worker,app_id,
           publication=published,observation=lifecycle.provider):
    root=Path(root);execution=publication(root,spec);job=spec['jobs'][job_id]
    review=read(review_file);clean=reviewed(spec,root/SPEC,review)
    chosen=selection(job,read(selection_file) if selection_file else None)
    raw=Path(review['local_report_path']).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=review['report_sha256']:raise ValueError('Report raw bytes differ')
    upload=read(root/LOCAL/'long_io_r1'/'upload'/job_id/'COMPLETED.json')
    if upload['job_sha256']!=digest(job) or upload['all_remote_file_bytes_read_back'] is not True:
        raise ValueError('Original uploaded job/asset evidence absent')
    budget=read(budget_file);base=root/LOCAL
    with (base/'dispatch.lock').open('a+') as lock:
        fcntl.flock(lock.fileno(),fcntl.LOCK_EX);records=parent.records_with_failed_parent(root,spec,failed_attempt_ledger.ledger(root,spec));parent.remote_fences(root,spec,store);failed_attempt_ledger.remote_fences(root,spec,store);obs=observation(root,records)
        checked=budget_check(root,spec,job,budget,records,obs,time.time())
        out=base/'dispatch'/job_id;k=key(job)
        if out.exists() or any(store.get(k+'/'+v) is not None for v in ('dispatch','claim','terminal')):
            raise ValueError('Any partial original attempt permanently blocks replay')
        if not re.fullmatch(r'ap-[A-Za-z0-9]+',app_id):raise ValueError('Actual app required')
        intent=dict(logical_id=job_id,job_id=job_id,execution=execution,app_id=app_id,
            spec_sha256=digest(spec),spec_file_sha256=sha(root/SPEC),job_sha256=digest(job),
            budget=checked,budget_source_sha256=sha(budget_file),budget_observed_epoch=budget['observed_epoch'],
            review=clean,selection=chosen,provider_observation=obs,prior_attempt_records=records,
            dispatch_epoch=time.time(),automatic_retry_allowed=False)
        out.mkdir(parents=True,exist_ok=False);dump(out/'INTENT.json',intent)
        (out/'BUDGET_SOURCE.json').write_bytes(Path(budget_file).read_bytes());(out/'ORIGINAL_REPORT.md').write_bytes(raw)
        if not store.put(k+'/dispatch',intent,skip_if_exists=True):raise ValueError('Remote dispatch already exists')
        call=worker.spawn(intent,raw.decode());dump(out/'SUBMITTED.json',dict(logical_id=job_id,app_id=app_id,call_id=call.object_id,submitted_epoch=time.time()))
    try:
        result=call.get();dump(out/'RESULT.json',result);return result
    except BaseException as exc:
        dump(out/'RETURN_ERROR.json',dict(type=type(exc).__name__,message=str(exc),cloud_failure_not_inferred=True,automatic_retry_allowed=False));raise


def worker_body(spec,path,source_root,intent,raw_report,store,volume,timer_factory,body=long_execution.worker_body):
    start=time.time();validate(spec);job=spec['jobs'][intent['job_id']];limits=job['limits'];k=key(job)
    timer=timer_factory(limits['worker_seconds']);out=Path(BASE)/logical(job);claimed=False
    try:
        shared.exact_source(spec,source_root)
        if (store.get(k+'/dispatch')!=intent or intent['spec_sha256']!=digest(spec)
                or intent['spec_file_sha256']!=sha(path) or intent['job_sha256']!=digest(job)
                or not 0<=start-intent['dispatch_epoch']<=limits['startup_seconds']
                or not 0<=start-intent['budget_observed_epoch']<=3600
                or start+limits['worker_seconds']+limits['closeout_seconds']>CUTOFF
                or hashlib.sha256(raw_report.encode()).hexdigest()!=intent['review']['report_sha256']):
            raise ValueError('Original source/dispatch/report/window differs')
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'report.md';p.write_bytes(raw_report.encode())
            reviewed(spec,path,{**intent['review'],'local_report_path':str(p)})
        if intent['selection']!=selection(job,None):
            raise ValueError('Exact delegated D no-smoke disclosure differs')
        volume.reload();inputs=Path(INPUTS)/job['input_directory'];verify(inputs,job['input_files'])
        verify(job['model']['remote_path'],job['model']['files'])
        if read(Path(job['model']['remote_path'])/'generation_config.json')['eos_token_id']!=job['eos_token_ids']:
            raise ValueError('Pinned native generation EOS list differs')
        if out.exists():raise ValueError('Remote partial output cannot retry')
        claim=dict(logical_id=logical(job),execution=intent['execution'],app_id=intent['app_id'],dispatch_sha256=digest(intent),worker_start_epoch=start)
        if not store.put(k+'/claim',claim,skip_if_exists=True):raise ValueError('Original claim exists')
        claimed=True;out.mkdir(parents=True,exist_ok=False);dump(out/'ADMISSION.json',intent);dump(out/'CLAIM.json',claim)
        timing=policy(job,start,intent['budget']['prior_reserved_usd']);dump(out/'TIMING_POLICY.json',timing)
        identity=dict(logical_id=logical(job),arm=job['arm'],job_sha256=digest(job),
            input_plan_sha256=job.get('input_plan_sha256'),execution=intent['execution'],source_files=spec['source_files'])
        dump(out/'IDENTITY.json',identity);volume.commit()
        result=body(job,inputs,out,identity,k,claim,start+limits['worker_seconds'],timing,store,volume)
        artifact=long_transport.pack(out,limits['artifact_max_bytes']);volume.commit();finished=time.time()
        if finished>=start+limits['worker_seconds']:raise TimeoutError('Packing exceeded original hard window')
        receipt=dict(status='completed',logical_id=logical(job),app_id=intent['app_id'],claim=claim,
            spec_sha256=digest(spec),spec_file_sha256=sha(path),job_sha256=digest(job),
            worker_start_epoch=start,finished_epoch=finished,artifact=artifact,result=result,actual_A3_accepted=False)
        dump(out/'TERMINAL.json',receipt);volume.commit()
        if not store.put(k+'/terminal',receipt,skip_if_exists=True):raise ValueError('Original terminal exists')
        return receipt
    except BaseException as exc:
        if claimed:
            failure=dict(status='failed',app_id=intent['app_id'],logical_id=logical(job),type=type(exc).__name__,message=str(exc),traceback=traceback.format_exc(),finished_epoch=time.time(),automatic_retry_allowed=False)
            dump(out/'FAILURE.json',failure);volume.commit();store.put(k+'/terminal',failure,skip_if_exists=True)
        raise
    finally:timer.cancel()


def terminate_owned_descendants(root_pid, read_children=None, kill=None):
    """Linux worker descendants only, never another app or a process-name match."""
    import os,signal
    if read_children is None:
        def read_children(pid):
            try:
                return [int(v) for v in Path(f'/proc/{pid}/task/{pid}/children').read_text().split()]
            except FileNotFoundError:return []
    if kill is None:kill=lambda pid:os.kill(pid,signal.SIGKILL)
    seen={root_pid};order=[]
    def visit(pid):
        for child in read_children(pid):
            if child in seen:continue
            seen.add(child);visit(child);order.append(child)
    visit(root_pid)
    for pid in order:
        try:kill(pid)
        except ProcessLookupError:pass
    return order

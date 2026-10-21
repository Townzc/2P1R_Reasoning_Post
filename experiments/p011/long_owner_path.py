"""Direct-owner execution amendment: one $150 A/D epoch, eight slots, async CR.

The original scientific inputs, training, LR tolerance, endpoints and scorer are
unchanged. Historical failed reservations remain evidence, not new expenditure.
"""
from decimal import Decimal
import fcntl
import hashlib
from pathlib import Path
import re
import subprocess
import tempfile
import time
import traceback
from experiments.p011 import c1_admission as shared, c1_outer as lifecycle
from experiments.p011 import long_owner_execution as long_execution, long_owner_numeric as long_numeric
from experiments.p011 import long_transport
from experiments.p011.long_protocol import ENDPOINT_BATCHES
from experiments.sft_allocation_midpoint.common import dump,read,sha,digest,verify

LOCAL=lifecycle.LOCAL
STORE=lifecycle.STORE
SPEC='reports/p011_20261020/owner150_runtime_v1/SPEC.json'
DECISION='reports/p011_20261020/owner150_runtime_v1/OWNER_DIRECT_AMENDMENT.txt'
ORIGINAL_SPEC='reports/p011_20261020/long_current_runtime_v1/SPEC.json'
LOCAL_INPUT_DIRECTORY='long_inputs_numeric_gold_r1'
INPUTS='/evidence/p011-20261020/long_inputs_r1'
BASE='/evidence/p011-20261020/long_owner150_runs_r1'
CUTOFF=1792645200
LATEST_DISPATCH=1792621800
SCOPE='p011-direct-owner150-execution'

def logical(job):return job['logical_id']
def key(job):return 'long_owner150/'+logical(job)

def validate(spec):
    if (spec.get('schema')!='p011-direct-owner150-v1' or spec.get('new_spending_cap_usd')!='150'
            or spec.get('concurrency_limit')!=8 or spec.get('predictive_termination') is not False
            or spec.get('smoke_rule_after_results') is not True or spec.get('asynchronous_review') is not True
            or spec.get('latest_dispatch_epoch')!=LATEST_DISPATCH or spec.get('result_cutoff_epoch')!=CUTOFF):
        raise ValueError('Exact direct-owner operational amendment required')
    for name,job in spec['jobs'].items():
        expected=9000 if job['cell'] in ('baseline','D1','D2') else 16200
        if (name!=logical(job) or job['limits']['worker_seconds']!=expected
                or job['limits']['platform_seconds']!=expected+60 or job['limits']['startup_seconds']!=600
                or job['arm']!=('S-L15' if job['kind']=='baseline' else 'S-F15') or job['seed']!=17):
            raise ValueError('Unapproved arm, timer, or identity')
    return spec

def reviewed(spec,path,review):
    validate(spec)
    if (review.get('decision')!='DIRECT_OWNER_AUTHORIZED_ASYNC_REVIEW'
            or review.get('scope')!=SCOPE or review.get('spec_sha256')!=sha(path)
            or review.get('source_files')!=spec['source_files']
            or review.get('report_sha256')!=spec['owner_amendment_sha256']
            or sha(review['local_report_path'])!=spec['owner_amendment_sha256']):
        raise ValueError('Direct human authorization/source binding differs')
    return review

def published(root,spec):
    def git(*a):return subprocess.check_output(['git',*a],cwd=root,timeout=45)
    head=git('rev-parse','HEAD').decode().strip()
    if git('branch','--show-current').decode().strip()!='codex/icml-acl-2027':raise ValueError('Wrong branch')
    if git('ls-remote','origin','refs/heads/codex/icml-acl-2027').decode().split()[0]!=head:
        raise ValueError('Execution HEAD not published')
    shared.exact_source(spec,root)
    for n in [*spec['source_files'],SPEC,DECISION]:
        if git('show',head+':'+n)!=(Path(root)/n).read_bytes():raise ValueError('Unpublished source/spec')
    if sha(Path(root)/ORIGINAL_SPEC)!=spec['original_scientific_spec_sha256']:raise ValueError('Original job basis changed')
    original=read(Path(root)/ORIGINAL_SPEC)
    for job in spec['jobs'].values():
        omit={'limits','logical_id','original_job_id','resource_rates_usd_per_hour'}
        if {k:v for k,v in job.items() if k not in omit}!={k:v for k,v in original['jobs'][job['original_job_id']].items() if k not in omit}:
            raise ValueError('Original scientific input/model/timing object changed')
    return head

def selection(job,review):
    if review is not None:raise ValueError('No fabricated pre-run smoke selection')
    return dict(direct_owner_authorized=True,smoke_gate_after_results=True,no_successful_smoke_selection_inferred=True)

def policy(job,start,prior):
    t=job['timing'];l=job['limits'];spec=read(Path(__file__).resolve().parents[2]/SPEC)
    return dict(category=job['category'],worker_start_epoch=start,worker_hard_seconds=l['worker_seconds'],
        result_deadline_epoch=CUTOFF,full_result_seconds=l['full_result_window_seconds'],
        measurement_exceptions=0,projection_multiplier=1.2,uncalibrated_future_seconds=t['future_allowance_seconds'],
        training_unit_seconds=t['training_unit_seconds'],endpoint_batch_seconds=t['endpoint_batch_seconds'],
        hourly_rate_usd=l['hourly_rate_usd'],startup_allowance_seconds=l['startup_seconds'],reserved_usd=l['reserved_usd'],
        prior_reserved_usd=prior,platform_timeout_seconds=l['platform_seconds'],owner_amendment_sha256=spec['owner_amendment_sha256'])

def epoch_records(root):
    out=[]
    for p in sorted((Path(root)/LOCAL/'dispatch').glob('long_*_owner_r*/INTENT.json')):
        v=read(p);out.append(dict(logical_id=v['logical_id'],app_id=v['app_id'],
            hard_compute_envelope_usd=v['budget']['new_reserved_usd'],intent_file=str(p.relative_to(root)),
            actual_attributed_charge_usd=None))
    return out

def budget_check(root,spec,job,budget,records,obs,now):
    cap=Decimal('150');envelope=Decimal(job['limits']['reserved_usd'])
    active_bound=sum(Decimal(r['hard_compute_envelope_usd']) for r in records)
    actual=Decimal(budget['new_epoch_actual_charged_usd'])
    # Active maximum exposure is not reported as expenditure. Prior failed
    # reservations never enter this new epoch. Closed charges require receipts.
    if (not 0<=now-budget['observed_epoch']<=3600 or now>LATEST_DISPATCH
            or any(r['logical_id']==logical(job) for r in records)
            or len(records)>=8 or max(len(records),len(obs['containers']))>=8
            or actual<0 or active_bound+envelope+actual>cap
            or budget.get('owner_amendment_sha256')!=spec['owner_amendment_sha256']):
        raise ValueError('New epoch hard spending cap, eight slots, freshness or latest dispatch failed')
    for name,value in budget['source_evidence_files'].items():
        if sha(Path(root)/name)!=value:raise ValueError('Budget evidence changed')
    return dict(category=job['category'],new_reserved_usd=str(envelope),prior_reserved_usd='0',
        epoch_hard_compute_exposure_after_usd=str(active_bound+envelope),new_epoch_actual_charged_usd=str(actual),
        cap_usd='150',historical_failed_reservations_charged_to_new_epoch=False,
        maximum_exposure_is_not_actual_expense=True,provider_slots=max(len(records),len(obs['containers'])),
        prediction_gate_enabled=False)

def submit(root,spec,job_id,review_file,budget_file,selection_file,store,worker,app_id,
           publication=published,observation=None):
    root=Path(root);execution=publication(root,spec);job=spec['jobs'][job_id]
    review=reviewed(spec,root/SPEC,read(review_file));raw=Path(review['local_report_path']).read_text()
    upload=read(root/LOCAL/'long_io_r1/upload'/job_id/'COMPLETED.json')
    if upload['job_sha256']!=digest(job) or upload['all_remote_file_bytes_read_back'] is not True:
        raise ValueError('Exact original byte upload/reuse proof absent')
    budget=read(budget_file);base=root/LOCAL
    with (base/'dispatch.lock').open('a+') as lock:
        fcntl.flock(lock.fileno(),fcntl.LOCK_EX);records=epoch_records(root)
        obs=observation(root,records)
        checked=budget_check(root,spec,job,budget,records,obs,time.time())
        out=base/'dispatch'/job_id;k=key(job)
        if out.exists() or any(store.get(k+'/'+v) is not None for v in ('dispatch','claim','terminal')):
            raise ValueError('Attempt already consumed; no implicit retry')
        intent=dict(logical_id=job_id,job_id=job_id,execution=execution,app_id=app_id,
            spec_sha256=digest(spec),spec_file_sha256=sha(root/SPEC),job_sha256=digest(job),budget=checked,
            budget_source_sha256=sha(budget_file),budget_observed_epoch=budget['observed_epoch'],review=review,
            selection=selection(job,None),provider_observation=obs,prior_attempt_records=records,
            dispatch_epoch=time.time(),automatic_retry_allowed=False)
        out.mkdir(parents=True,exist_ok=False);dump(out/'INTENT.json',intent)
        (out/'BUDGET_SOURCE.json').write_bytes(Path(budget_file).read_bytes());(out/'ORIGINAL_REPORT.md').write_text(raw)
        if not store.put(k+'/dispatch',intent,skip_if_exists=True):raise ValueError('Permanent remote fence exists')
        call=worker.spawn(intent,raw)
        dump(out/'SUBMITTED.json',dict(logical_id=job_id,app_id=app_id,call_id=call.object_id,submitted_epoch=time.time()))
    return call,out

def await_original(call,out):
    try:
        result=call.get();dump(out/'RESULT.json',result);return result
    except BaseException as exc:
        dump(out/'RETURN_ERROR.json',dict(type=type(exc).__name__,message=str(exc),observed_epoch=time.time(),automatic_retry_allowed=False));raise


def worker_body(spec,path,source_root,intent,raw_report,store,volume,timer_factory,body=long_execution.worker_body):
    start=time.time();validate(spec);job=spec['jobs'][intent['job_id']];limits=job['limits'];k=key(job)
    timer=timer_factory(limits['worker_seconds']);out=Path(BASE)/logical(job);claimed=False
    try:
        shared.exact_source(spec,source_root)
        if (store.get(k+'/dispatch')!=intent or intent['spec_sha256']!=digest(spec)
                or intent['spec_file_sha256']!=sha(path) or intent['job_sha256']!=digest(job)
                or not 0<=start-intent['dispatch_epoch']<=limits['startup_seconds']
                or not 0<=start-intent['budget_observed_epoch']<=3600
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

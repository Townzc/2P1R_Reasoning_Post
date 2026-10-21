"""Direct-owner T72 K1 fallback-removal controls; original short science reused."""
from pathlib import Path
from decimal import Decimal
import time,subprocess,fcntl,hashlib,tempfile,traceback
from experiments.p011 import c1_admission as shared,c1_outer as lifecycle,long_transport
from experiments.p011 import fallback_numeric as b_numeric,fallback_execution as b_student_execution,fallback_training as b_student_training
from experiments.sft_allocation_midpoint.common import read,dump,sha,digest,verify
LOCAL=lifecycle.LOCAL
STORE=lifecycle.STORE
SPEC='reports/p011_20261020/fallback_clean_runtime_v1/SPEC.json'
SPEC_FILES={'student':SPEC}
DECISION='reports/p011_20261020/fallback_clean_runtime_v1/OWNER_ADDENDUM.txt'
ASSET_RECEIPT='.local/midpoint_20261011/assets_receipts_r1/result.json'
ASSET_RECEIPT_SHA='0a6c9e265e39869382d3ba6c675453f6d4ba2c9ee9135a0e586b22e307769248'
INPUTS='/evidence/p011-20261020/fallback_clean_inputs_r1'
BASE='/evidence/p011-20261020/fallback_clean_runs_r1'
CUTOFF=1792645200
LATEST_DISPATCH=1792621800
SCOPE='p011-t72-fallback-removal-direct-owner-async'
def logical(job):return job['logical_id']
def key(job):return 'fallback/student/'+job['run_id']
def spec_path(spec):return SPEC
def phase_for_job(name):return 'student'
def local_inputs(root,job):return Path(root)/LOCAL/'fallback_clean_inputs_r1'/job['run_id']
def validate(spec):
    if spec.get('schema')!='p011-fallback-clean-v1' or spec.get('new_spending_cap_usd')!='150' or spec.get('concurrency_limit')!=8:
        raise ValueError('Direct owner shared cap and slots required')
    for name,j in spec['jobs'].items():
        n=j['config']['nominal_original_P'];l=j['limits']
        if (n not in (400,3200) or j['run_id']!=f't72_clean_s17_n{n}_k1' or name!=logical(j)
                or l['worker_seconds']!=4400 or l['platform_seconds']!=4460 or l['startup_seconds']!=600
                or j['config']['seed']!=17 or j['config']['targets']!=2097148 or j['config']['updates']!=1024):
            raise ValueError('Original short scientific dose, seed, or hard timer differs')
    return spec

def reviewed(spec,path,review):
    validate(spec)
    if (review.get('decision')!='DIRECT_OWNER_AUTHORIZED_ASYNC_REVIEW' or review.get('scope')!=SCOPE
            or review.get('source_files')!=spec['source_files'] or review.get('spec_sha256')!=sha(path)
            or review.get('report_sha256')!=spec['owner_addendum_sha256']
            or sha(review['local_report_path'])!=spec['owner_addendum_sha256']):raise ValueError('Exact direct human authorization differs')
    return review

def published(root,spec):
    def git(*a):return subprocess.check_output(['git',*a],cwd=root,timeout=45)
    head=git('rev-parse','HEAD').decode().strip()
    if git('branch','--show-current').decode().strip()!='codex/icml-acl-2027' or git('ls-remote','origin','refs/heads/codex/icml-acl-2027').decode().split()[0]!=head:raise ValueError('Execution HEAD unpublished')
    shared.exact_source(spec,root)
    for n in [*spec['source_files'],SPEC,DECISION]:
        if git('show',head+':'+n)!=(Path(root)/n).read_bytes():raise ValueError('Unpublished source')
    return head

def policy(job,start,prior):
    t=job['timing'];l=job['limits']
    return dict(kind='student',category='B',worker_start_epoch=start,worker_seconds=l['worker_seconds'],
        result_cutoff_epoch=CUTOFF,full_result_seconds=l['full_result_window_seconds'],measurement_exceptions=0,
        projection_multiplier=1.2,uncalibrated_future_seconds=t['future_allowance_seconds'],training_cycle_seconds=t['training_cycle_seconds'],
        batch_cycle_seconds=t['batch_cycle_seconds'],hourly_rate_usd=l['hourly_rate_usd'],startup_seconds=l['startup_seconds'],
        reserved_usd=l['reserved_usd'],prior_B_reserved_usd='0',platform_seconds=l['platform_seconds'])

def epoch_records(root):
    out=[];base=Path(root)/LOCAL/'dispatch'
    for pattern in ('long_*_owner_r*/INTENT.json','fallback_*_r1/INTENT.json'):
        for p in sorted(base.glob(pattern)):
            v=read(p);out.append(dict(logical_id=v['logical_id'],app_id=v['app_id'],
                hard_compute_envelope_usd=v['budget']['new_reserved_usd'],
                active=not (p.parent/'RESULT.json').exists() and not (p.parent/'PROVIDER_STOPPED0.json').exists()))
    return out

def budget_check(root,spec,job,budget,records,obs,now):
    exposure=sum(Decimal(r['hard_compute_envelope_usd']) for r in records);fresh=Decimal(job['limits']['reserved_usd'])
    active=[r for r in records if r['active']]
    known={r['app_id'] for r in active}
    unmatched=sum(c.get('app_id') not in known for c in obs['containers'])
    slots=max(len(active)+unmatched,len(obs['containers']))
    if (now>LATEST_DISPATCH or not 0<=now-budget['observed_epoch']<=3600 or slots>=8
            or exposure+fresh+Decimal(budget['new_epoch_actual_charged_usd'])>150
            or any(r['logical_id']==logical(job) for r in records)):
        raise ValueError('Owner shared150 exposure/eight-slot/latest-dispatch gate failed')
    for n,h in budget['source_evidence_files'].items():
        if sha(Path(root)/n)!=h:raise ValueError('Fresh evidence differs')
    return dict(new_reserved_usd=str(fresh),prior_reserved_usd='0',new_epoch_actual_charged_usd=budget['new_epoch_actual_charged_usd'],
        epoch_hard_compute_exposure_after_usd=str(exposure+fresh),provider_slots=slots,prediction_gate_enabled=False,
        historical_failed_reservations_charged_to_new_epoch=False,maximum_exposure_is_not_actual_expense=True)

def submit(root,spec,name,reviewfile,budgetfile,store,worker,app_id):
    root=Path(root);execution=published(root,spec);job=spec['jobs'][name];review=reviewed(spec,root/SPEC,read(reviewfile))
    raw=Path(review['local_report_path']).read_text();budget=read(budgetfile)
    upload=read(root/LOCAL/'fallback_io_r1/upload'/name/'COMPLETED.json')
    if upload['job_sha256']!=digest(job) or upload['all_remote_file_bytes_read_back'] is not True:raise ValueError('Exact completed input transfer required')
    with (root/LOCAL/'dispatch.lock').open('a+') as lock:
        fcntl.flock(lock.fileno(),fcntl.LOCK_EX);records=epoch_records(root)
        import json
        containers=json.loads(subprocess.check_output([str(root/'.local/midpoint_20261011/venv/bin/modal'),'container','list','--json'],text=True,timeout=60))
        obs=dict(containers=containers,observed_epoch=time.time());checked=budget_check(root,spec,job,budget,records,obs,time.time())
        out=root/LOCAL/'dispatch'/name;k=key(job)
        if out.exists() or any(store.get(k+'/'+x) is not None for x in ('dispatch','claim','terminal')):raise ValueError('Already attempted control')
        intent=dict(logical_id=name,job_id=name,execution=execution,app_id=app_id,spec_sha256=digest(spec),spec_file_sha256=sha(root/SPEC),
            job_sha256=digest(job),budget=checked,budget_source_sha256=sha(budgetfile),budget_observed_epoch=budget['observed_epoch'],review=review,
            provider_observation=obs,prior_attempt_records=records,dispatch_epoch=time.time(),automatic_retry_allowed=False)
        out.mkdir(parents=True,exist_ok=False);dump(out/'INTENT.json',intent);(out/'BUDGET_SOURCE.json').write_bytes(Path(budgetfile).read_bytes())
        if not store.put(k+'/dispatch',intent,skip_if_exists=True):raise ValueError('Permanent dispatch exists')
        call=worker.spawn(intent,raw);dump(out/'SUBMITTED.json',dict(logical_id=name,app_id=app_id,call_id=call.object_id,submitted_epoch=time.time()))
    print('SUBMITTED',name,flush=True)
    try:result=call.get();dump(out/'RESULT.json',result);return result
    except BaseException as exc:dump(out/'RETURN_ERROR.json',dict(type=type(exc).__name__,message=str(exc),observed_epoch=time.time()));raise

def body_worker(job,inputs,out,identity,k,claim,timing,stop,store,volume):
    return b_student_execution.worker_body(job,inputs,out,identity,k,claim,timing,stop,store,volume)

def worker_body(spec,path,source_root,intent,raw_report,store,volume,timer_factory,body=body_worker):
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
        volume.reload();inputs=Path(INPUTS)/job['input_directory'];verify(inputs,job['input_files'])
        verify(job['model']['remote_path'],job['model']['files'])
        if job['kind']=='student':
            b_student_training.checked_recipe(read(inputs/'config.json'),read(inputs/'encoded.json'),read(inputs/'plan.json'))
            if read(inputs/'config.json')!=job['config']:raise ValueError('Actual B input config differs')
        if out.exists():raise ValueError('Remote partial output cannot retry')
        claim=dict(logical_id=logical(job),execution=intent['execution'],app_id=intent['app_id'],dispatch_sha256=digest(intent),worker_start_epoch=start)
        if not store.put(k+'/claim',claim,skip_if_exists=True):raise ValueError('Original claim exists')
        claimed=True;out.mkdir(parents=True,exist_ok=False);dump(out/'ADMISSION.json',intent);dump(out/'CLAIM.json',claim)
        timing=policy(job,start,intent['budget']['prior_reserved_usd']);dump(out/'TIMING_POLICY.json',timing)
        identity=dict(logical_id=logical(job),run_id=job['run_id'],job_sha256=digest(job),
            config=job.get('config'),execution=intent['execution'],source_files=spec['source_files'])
        dump(out/'IDENTITY.json',identity);volume.commit()
        result=body(job,inputs,out,identity,k,claim,timing,start+limits['worker_seconds'],store,volume)
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

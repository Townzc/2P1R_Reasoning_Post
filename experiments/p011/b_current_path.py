"""Narrow current-owner accounting and saved failed-parent B admission revision.

Exact actual inputs, source review and numerical SPEC remain prerequisites.
No selected SPEC or production call is created by this source module.
"""
from decimal import Decimal, ROUND_CEILING
import fcntl
import hashlib
from pathlib import Path
import re
import subprocess
import tempfile
import time
import traceback
from experiments.p011 import c1_admission as shared, c1_outer as lifecycle
from experiments.p011.c1_r2 import parent
from experiments.p011 import b_numeric, b_generation_execution, b_generation_loader
from experiments.p011 import b_student_execution, b_student_training, long_transport
from experiments.p011.b_input_path import OWNER_SHA, OWNER_PATH
from experiments.p010.common import MODELS
from experiments.sft_allocation_midpoint.common import dump, read, sha, digest, verify

BUDGET_OWNER_SHA='364aaf6cd70fa9cf1a89902af6dedb33a1b64d7c47e73a12b37b6b97dfb69a2f'
LOCAL=lifecycle.LOCAL
STORE=lifecycle.STORE
SPEC_FILES={phase:f'reports/p011_20261020/b_{phase}_runtime_v1/SPEC.json' for phase in ('generation','student')}

def spec_path(spec):
    return SPEC_FILES[spec['phase']]

def phase_for_job(name):
    if name=='B_generation_t10_400x16_r1':return 'generation'
    if name in ('B_B1_s17_r1','B_B2_s17_r1','B_B3_s17_r1'):return 'student'
    raise ValueError('Only four original B logical jobs allowed')
CUTOFF=1792645200
SCOPE='p011-B-generation-student-complete-path-CR-A1-A2-lite'
INPUTS='/evidence/p011-20261020/b_inputs_r1'
BASE='/evidence/p011-20261020/b_runs_r1'


def logical(job):
    return 'B_generation_t10_400x16_r1' if job['kind']=='generation' else 'B_'+job['run_id']+'_s17_r1'


def key(job):
    return 'b/generation' if job['kind']=='generation' else 'b/student/'+job['run_id']


def local_inputs(root,job):
    return Path(root)/LOCAL/('b_generation_inputs_r1' if job['kind']=='generation'
        else 'b_runtime_student_inputs_r1/'+job['run_id'])


def validate(spec):
    if (spec.get('budget_owner_decision_sha256')!=BUDGET_OWNER_SHA
            or not spec.get('prior_failed_C1')
            or spec.get('original_plan_commit')!=shared.PLAN or not spec.get('source_files')
            or spec['source_files'].get(OWNER_PATH)!=OWNER_SHA or not spec.get('jobs')
            or spec.get('phase') not in SPEC_FILES
            or spec.get('measurement_exceptions')!=0 or spec.get('result_cutoff_epoch')!=CUTOFF):
        raise ValueError('Original B plan/owner/source/jobs required')
    for name,job in spec['jobs'].items():
        limits=job['limits'];model=job['model'];kind=job['kind']
        expected=(MODELS['t15'] if kind=='generation' else
            ('Qwen/Qwen2.5-1.5B','8faed761d45a263340a0528343f099c05c9a4323'))
        remote=('/evidence/mp-teacher-cost-20261012-r1/assets/model' if kind=='generation'
                else '/evidence/mp-engineering-20261012-r1/assets/model')
        required=({'GPU_PACK.json'} if kind=='generation' else
            {'rows.json','encoded.json','plan.json','config.json','MATH_ENDPOINT.json'})
        if (kind not in ('generation','student') or name!=logical(job)
                or spec['phase']!=kind or phase_for_job(name)!=kind
                or job['category']!='B' or job['owner_B16_sha256']!=OWNER_SHA
                or job['run_id']!=('generation' if kind=='generation' else job['run_id'])
                or (kind=='student' and job['run_id'] not in ('B1','B2','B3'))
                or (model['model_id'],model['revision'])!=expected or model['remote_path']!=remote
                or not model['files'] or not model['producer_binding_files']
                or (kind=='generation' and not model.get('remote_path_producer'))
                or set(job['input_files'])!=required or not job['local_input_files']
                or set(job['local_input_files'])!=required|({'PACK.json'} if kind=='generation' else {'GOLD.jsonl'}) or job['input_directory']!=job['run_id']
                or any(type(limits[n]) is not int or limits[n]<=0 for n in
                    ('worker_seconds','platform_seconds','startup_seconds','closeout_seconds','score_seconds','full_result_window_seconds'))
                or limits['startup_seconds']<600 or limits['platform_seconds']<limits['worker_seconds']+60
                or limits['score_seconds']>(62000 if kind=='generation' else 25200)
                or limits['closeout_seconds']<limits['score_seconds']+5
                or limits['full_result_window_seconds']<limits['startup_seconds']+limits['platform_seconds']+limits['closeout_seconds']
                or type(limits['artifact_max_bytes']) is not int or not 0<limits['artifact_max_bytes']<=100_000_000_000
                or not job['timing']['source_evidence_files']
                or job['timing'].get('whole_iteration_scope_accepted') is not True):
            raise ValueError('Exact B identity/assets/input/full-window configuration differs')
        if kind=='student' and (job['config']['run_id']!=job['run_id'] or job['config']['owner_B16_sha256']!=OWNER_SHA):
            raise ValueError('Original actual B student input configuration required')
        rates=job['resource_rates_usd_per_hour']
        if (job.get('resources')!={'gpu':'H100','cpu':4,'memory_mib':32768}
                or set(rates)!={'H100','cpu_core','GiB'}
                or any(not Decimal(str(v)).is_finite() or Decimal(str(v))<=0 for v in rates.values())):
            raise ValueError('Exact billed H100/4CPU/32GiB required')
        hourly=Decimal(str(rates['H100']))+4*Decimal(str(rates['cpu_core']))+32*Decimal(str(rates['GiB']))
        reserve=(hourly*Decimal(limits['startup_seconds']+limits['platform_seconds'])/3600).quantize(Decimal('.01'),rounding=ROUND_CEILING)
        if Decimal(str(limits['hourly_rate_usd']))!=hourly or Decimal(str(limits['reserved_usd']))!=reserve:
            raise ValueError('Full resource rate and billed-window reserve differ')
        policy(job,1,'0')
    expected_jobs=({'B_generation_t10_400x16_r1'} if spec['phase']=='generation'
        else {'B_B1_s17_r1','B_B2_s17_r1','B_B3_s17_r1'})
    if set(spec['jobs'])!=expected_jobs:
        raise ValueError('One immutable generation phase and all three student cells required')
    return spec


def policy(job,start,prior):
    t=job['timing'];l=job['limits']
    p=dict(kind=job['kind'],category='B',worker_start_epoch=start,worker_seconds=l['worker_seconds'],
        result_cutoff_epoch=CUTOFF,full_result_seconds=l['full_result_window_seconds'],
        measurement_exceptions=0,projection_multiplier=1.2,uncalibrated_future_seconds=t['future_allowance_seconds'],
        training_cycle_seconds=t['training_cycle_seconds'],batch_cycle_seconds=t['batch_cycle_seconds'],
        hourly_rate_usd=l['hourly_rate_usd'],startup_seconds=l['startup_seconds'],
        reserved_usd=l['reserved_usd'],prior_B_reserved_usd=prior,platform_seconds=l['platform_seconds'])
    n=(0,25) if job['kind']=='generation' else (64,10)
    b_numeric.forecast(p,*n,[],[],start)
    return p


def reviewed(spec,path,review):
    validate(spec);result=shared.fixed_report(review)
    expected=dict(scope=SCOPE,original_plan_commit=shared.PLAN,spec_sha256=sha(path),
        source_files=spec['source_files'],jobs_sha256=digest(spec['jobs']),measurement_exceptions=0,
        owner_B16_sha256=OWNER_SHA,budget_owner_decision_sha256=BUDGET_OWNER_SHA)
    flags=('complete_source_closure_accepted','complete_actual_input_A1_accepted',
        'original_P010_tokens_seeds_dose_and_endpoint_rules_unchanged',
        'all_original_complete_timing_sources_accepted','full_state_raw_scoring_window_and_budget_accepted',
        'remote_paths_traced_to_producers','owner_B16_selection_and_actual_Pcov_accepted',
        'current_owner_accounting_and_saved_failed_parent_accepted',
        'original_complete_cycle_interval_proxy_accepted')
    if any(review.get(k)!=v for k,v in expected.items()) or any(review.get(k) is not True for k in flags):
        raise ValueError('True shared B CR/actual A1/numeric A2-lite absent')
    return result


def published(root,spec):
    def git(*a):return subprocess.check_output(['git',*a],cwd=root,timeout=45)
    if git('branch','--show-current').decode().strip()!='codex/icml-acl-2027':raise ValueError('Wrong branch')
    head=git('rev-parse','HEAD').decode().strip()
    if git('ls-remote','origin','refs/heads/codex/icml-acl-2027').decode().split()[0]!=head:
        raise ValueError('Execution HEAD not published')
    shared.exact_source(spec,root)
    for name in [*spec['source_files'],spec_path(spec)]:
        if git('show',head+':'+name)!=(Path(root)/name).read_bytes():raise ValueError('Uncommitted source/spec')
    return head


def budget_check(root,spec,job,budget,records,obs,now):
    totals,slots=shared.accounting(records,obs['containers'],obs['states'])
    reserve=Decimal(str(job['limits']['reserved_usd']));cat=job['category']
    if (not 0<=now-budget['observed_epoch']<=3600 or slots>=4
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
    counts=(0,25) if job['kind']=='generation' else (64,10)
    initial=b_numeric.forecast(policy(job,now,totals[cat]),*counts,[],[],now)
    return dict(category=cat,new_reserved_usd=str(reserve),prior_reserved_usd=totals[cat],
        all_attempted_reservations_usd=totals,provider_slots=slots,initial_forecast=initial,
        protected_usd='0',budget_owner_decision_sha256=BUDGET_OWNER_SHA,not_actual_expense=True)


def submit(root,spec,job_id,review_file,budget_file,store,worker,app_id,
           publication=published,observation=lifecycle.provider):
    root=Path(root);execution=publication(root,spec);job=spec['jobs'][job_id]
    review=read(review_file);clean=reviewed(spec,root/spec_path(spec),review)
    raw=Path(review['local_report_path']).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=review['report_sha256']:raise ValueError('Report raw bytes differ')
    upload=read(root/LOCAL/'b_io_r1'/'upload'/job_id/'COMPLETED.json')
    if upload['job_sha256']!=digest(job) or upload['all_remote_file_bytes_read_back'] is not True:
        raise ValueError('Original uploaded job/asset evidence absent')
    budget=read(budget_file);base=root/LOCAL
    with (base/'dispatch.lock').open('a+') as lock:
        fcntl.flock(lock.fileno(),fcntl.LOCK_EX);records=parent.records_with_failed_parent(root,spec,lifecycle.ledger(root));parent.remote_fences(root,spec,store);obs=observation(root,records)
        checked=budget_check(root,spec,job,budget,records,obs,time.time())
        out=base/'dispatch'/job_id;k=key(job)
        if out.exists() or any(store.get(k+'/'+v) is not None for v in ('dispatch','claim','terminal')):
            raise ValueError('Any partial original attempt permanently blocks replay')
        if not re.fullmatch(r'ap-[A-Za-z0-9]+',app_id):raise ValueError('Actual app required')
        intent=dict(logical_id=job_id,job_id=job_id,execution=execution,app_id=app_id,
            spec_sha256=digest(spec),spec_file_sha256=sha(root/spec_path(spec)),job_sha256=digest(job),
            budget=checked,budget_source_sha256=sha(budget_file),budget_observed_epoch=budget['observed_epoch'],
            review=clean,provider_observation=obs,prior_attempt_records=records,
            dispatch_epoch=time.time(),automatic_retry_allowed=False)
        out.mkdir(parents=True,exist_ok=False);dump(out/'INTENT.json',intent)
        (out/'BUDGET_SOURCE.json').write_bytes(Path(budget_file).read_bytes());(out/'ORIGINAL_REPORT.md').write_bytes(raw)
        if not store.put(k+'/dispatch',intent,skip_if_exists=True):raise ValueError('Remote dispatch already exists')
        call=worker.spawn(intent,raw.decode());dump(out/'SUBMITTED.json',dict(logical_id=job_id,app_id=app_id,call_id=call.object_id,submitted_epoch=time.time()))
    try:
        result=call.get();dump(out/'RESULT.json',result);return result
    except BaseException as exc:
        dump(out/'RETURN_ERROR.json',dict(type=type(exc).__name__,message=str(exc),cloud_failure_not_inferred=True,automatic_retry_allowed=False));raise


def body_worker(job,inputs,out,identity,key,claim,timing,stop,store,volume):
    if job['kind']=='student':
        return b_student_execution.worker_body(job,inputs,out,identity,key,claim,timing,stop,store,volume)
    pack=read(Path(inputs)/'GPU_PACK.json')
    if set(pack)!={'ordered400','prompts','rows','source'} or any(set(x)!={'problem'} for x in pack['source'].values()):
        raise ValueError('Gold-free original B generation input projection required')
    llm,constructor,transport,engine=b_generation_loader.load(pack,job['model'])
    dump(Path(out)/'ENGINE.json',engine);volume.commit()
    def check():
        if time.time()>=stop-30 or store.get(key+'/claim')!=claim:
            raise TimeoutError('Original B generation deadline or claim changed')
    def remaining(left,times):return b_numeric.forecast(timing,0,left,[],times,time.time())
    result=b_generation_execution.generate(pack['ordered400'],pack['prompts'],pack['rows'],
        Path(out)/'generation',key,claim,store,volume.commit,llm,constructor,transport,remaining,check)
    dump(Path(out)/'RESULT.json',result);volume.commit();check();return result


def worker_body(spec,path,source_root,intent,raw_report,store,volume,timer_factory,body=body_worker):
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

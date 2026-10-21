"""Three specifically authorized engineering calls; separate IDs and A reserve cap6."""
from decimal import Decimal,ROUND_CEILING
from pathlib import Path
import fcntl,hashlib,math,re,subprocess,tempfile,time,traceback
from experiments.p011 import c1_admission as shared,c1_outer as lifecycle,long_training,long_transport
from experiments.p011.long_protocol import resources
from experiments.p011.c1_r2 import parent
from experiments.p011 import failed_attempt_ledger
from experiments.p011.long_preflight import subset,execution
from experiments.sft_allocation_midpoint.common import dump,read,sha,digest,verify

LOCAL=lifecycle.LOCAL;STORE=lifecycle.STORE;CUTOFF=1792645200
SPEC='reports/p011_20261020/long_preflight_failed_ledger_runtime_v1/SPEC.json'
SCOPE='p011-long-three-arm-engineering-preflight-CR-A1-A2-lite'
INPUTS='/evidence/p011-20261020/long_preflight_inputs_r1'
BASE='/evidence/p011-20261020/long_preflight_runs_r1'


def logical(job):return 'preflight_'+job['arm']+'_s17_r1'
def key(job):return 'engineering/'+logical(job)


def validate(spec):
    if (spec.get('original_plan_commit')!=shared.PLAN or not spec.get('source_files')
            or spec.get('owner_decision_sha256')!=subset.OWNER_SHA
            or spec.get('result_cutoff_epoch')!=CUTOFF or spec.get('engineering_preflight') is not True
            or not spec.get('failed_attempt_bindings')
            or spec.get('original_preflight_A1_A2_report_sha256')!='2dd1dc459fb00a0a52190b489de7b2d6db37e092130ba85cfb3a608ee60735c1'
            or spec.get('scientific_cell_result') is not False or spec.get('measurement_exceptions')!=3
            or set(spec.get('jobs',{}))!={'preflight_'+a+'_s17_r1' for a in long_training.ARMS}):
        raise ValueError('Exact three original arms and owner preflight scope required')
    total=Decimal('0')
    for name,j in spec['jobs'].items():
        l=j['limits'];a=j['arm'];m=j['model']
        if (name!=logical(j) or j['kind']!='engineering_preflight' or j['category']!='A' or j['seed']!=17
                or j['U']!=2 or j['endpoint_count']!=32 or j['input_directory']!=a
                or m['model_id']!=long_training.ARMS[a]['model_id'] or m['revision']!=long_training.ARMS[a]['revision']
                or m['remote_path'] not in ('/evidence/exploratory-20261014-r1/instruct_assets','/evidence/p011-20261020/models/qwen3b_instruct')
                or ('3B' in m['model_id'])!=m['remote_path'].endswith('qwen3b_instruct')
                or not m['files'] or not m['producer_binding_files'] or not j['input_files']
                or j['local_input_files'].keys()!=j['input_files'].keys()|{'ENDPOINT_LOCAL.json'}
                or j['eos_token_ids']!=[151645,151643] or j['resources']!=resources('student',a)
                or any(type(l[n]) is not int or l[n]<=0 for n in ('worker_seconds','platform_seconds','startup_seconds','closeout_seconds','full_result_window_seconds','artifact_max_bytes'))
                or l['worker_seconds']!=900 or l['platform_seconds']!=960 or l['startup_seconds']!=600
                or l['closeout_seconds']!=7200 or l['full_result_window_seconds']!=8760
                or not 0<l['artifact_max_bytes']<=100_000_000_000):
            raise ValueError('Exact reviewed engineering subset/resources/window required')
        rates=j['resource_rates_usd_per_hour']
        if set(rates)!={'H100','cpu_core','GiB'} or any(not Decimal(str(v)).is_finite() or Decimal(str(v))<=0 for v in rates.values()):raise ValueError('Full resource rates required')
        rate=Decimal(str(rates['H100']))+4*Decimal(str(rates['cpu_core']))+Decimal(j['resources']['memory_mib'])/1024*Decimal(str(rates['GiB']))
        reserve=(rate*Decimal(1560)/3600).quantize(Decimal('.01'),rounding=ROUND_CEILING)
        if Decimal(str(l['hourly_rate_usd']))!=rate or Decimal(str(l['reserved_usd']))!=reserve:raise ValueError('Whole billed engineering window reserve differs')
        total+=reserve;execution.original.engine_settings(j['context'])
    if total>6:raise ValueError('Three engineering reserves must total at most6')
    return spec


def policy(job,start,prior):
    return {'engineering_preflight':True,'owner_decision_sha256':subset.OWNER_SHA,
            'measurement_exceptions':1,'forecast_performed':False,'worker_start_epoch':start,
            'worker_hard_seconds':job['limits']['worker_seconds'],'prior_reserved_usd':prior,
            'not_formal_numeric_admission':True}


def reviewed(spec,path,review):
    validate(spec);result=shared.fixed_report(review)
    expected={'scope':SCOPE,'original_plan_commit':shared.PLAN,'spec_sha256':sha(path),
        'source_files':spec['source_files'],'jobs_sha256':digest(spec['jobs']),
        'owner_decision_sha256':subset.OWNER_SHA,'measurement_exceptions':3,
        'formal_repair_review_sha256':spec['formal_repair_review_sha256'],
        'failed_attempt_bindings_sha256':digest(spec['failed_attempt_bindings']),
        'original_preflight_A1_A2_report_sha256':spec['original_preflight_A1_A2_report_sha256']}
    flags=('complete_source_closure_accepted','actual_input_A1_accepted','formal_R1_R3_source_CR_accepted',
        'engineering_subset_of_formal_path_accepted','all_three_reserves_at_most6_accepted',
        'full_state_export_join_and_original_engine_accepted','original_failed_parent_retained',
        'current_owner_budget_scope_and_full_window_accepted','no_scientific_result_or_A3_A5_claim','failed_terminal_ledger_and_original_reservations_accepted',
        'original_three_preflight_jobs_unchanged')
    if any(review.get(k)!=v for k,v in expected.items()) or any(review.get(k) is not True for k in flags):
        raise ValueError('Exact source/input/numeric engineering review required')
    return result


def budget_check(root,spec,job,budget,records,obs,now):
    validate(spec);totals,slots=shared.accounting(records,obs['containers'],obs['states'])
    reserve=Decimal(str(job['limits']['reserved_usd']));prior=Decimal(totals['A'])
    if (type(now) not in (int,float) or not math.isfinite(now)
            or type(budget.get('observed_epoch')) not in (int,float) or not math.isfinite(budget['observed_epoch'])
            or not 0<=now-budget['observed_epoch']<=3600 or slots>=4
            or budget.get('all_attempted_reservations_usd')!=totals
            or budget.get('category')!='A' or budget.get('cap_usd')!='115' or budget.get('overall_cap_usd')!='180'
            or budget.get('protected_usd')!='0' or budget.get('budget_owner_decision_sha256')!=subset.OWNER_SHA
            or budget.get('reserve_release_used') is not False or budget.get('owner_estimate_used_as_balance') is not False
            or budget.get('availability_basis')!='owner_current_balance_minus_retained_P011_reserves_and_meter_growth'
            or Decimal(str(budget['hourly_rate_usd']))!=Decimal(str(job['limits']['hourly_rate_usd']))
            or not budget['source_evidence_files'] or any(x['logical_id']==logical(job) for x in records)
            or any(x['logical_id'].startswith('preflight_') and x['logical_id'] not in spec['jobs'] for x in records)
            or sum(map(Decimal,totals.values()))+reserve>180 or reserve>Decimal('.8')*(115-prior)
            or now+job['limits']['full_result_window_seconds']>CUTOFF):
        raise ValueError('Original engineering budget/unused/full-window admission failed')
    available=Decimal(str(budget['available_after_retained_prior_reserves_usd']));gross=Decimal(str(budget['observed_gross_resource_usd']))
    if not available.is_finite() or not gross.is_finite() or gross<0 or available<reserve:raise ValueError('Current conservative available funds insufficient')
    for n,value in budget['source_evidence_files'].items():
        p=Path(n)
        if p.is_absolute() or '..' in p.parts or sha(Path(root)/p)!=value:raise ValueError('Fresh accounting source changed')
    engineering=sum(Decimal(x['budget']['new_reserved_usd']) for x in records if x['logical_id'].startswith('preflight_'))
    if engineering+reserve>6:raise ValueError('Retained engineering failed/pending reservations exceed6')
    return {'category':'A','new_reserved_usd':str(reserve),'prior_reserved_usd':totals['A'],
        'all_attempted_reservations_usd':totals,'provider_slots':slots,'protected_usd':'0',
        'engineering_prior_reserved_usd':str(engineering),'owner_exception_sha256':subset.OWNER_SHA,
        'forecast_performed':False,'hard_bounded_measurement_only':True,'not_actual_expense':True}


def published(root,spec):
    def git(*a):return subprocess.check_output(['git',*a],cwd=root,timeout=45)
    if git('branch','--show-current').decode().strip()!='codex/icml-acl-2027':raise ValueError('Wrong branch')
    head=git('rev-parse','HEAD').decode().strip()
    if git('ls-remote','origin','refs/heads/codex/icml-acl-2027').decode().split()[0]!=head:
        raise ValueError('Execution HEAD not published')
    shared.exact_source(spec,root)
    for name in [*spec['source_files'],SPEC]:
        if git('show',head+':'+name)!=(Path(root)/name).read_bytes():raise ValueError('Uncommitted source/spec')
    return head

def submit(root,spec,job_id,review_file,budget_file,selection_file,store,worker,app_id,
           publication=published,observation=lifecycle.provider):
    root=Path(root);execution=publication(root,spec);job=spec['jobs'][job_id]
    review=read(review_file);clean=reviewed(spec,root/SPEC,review)
    if selection_file:raise ValueError("Engineering measurements cannot use smoke selection")
    chosen=None
    raw=Path(review['local_report_path']).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=review['report_sha256']:raise ValueError('Report raw bytes differ')
    upload=read(root/LOCAL/'long_preflight_io_r1'/'upload'/job_id/'COMPLETED.json')
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

def worker_body(spec,path,source_root,intent,raw_report,store,volume,timer_factory,body=execution.worker_body):
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
        if read(Path(job['model']['remote_path'])/'generation_config.json')['eos_token_id']!=job['eos_token_ids']:
            raise ValueError('Pinned native generation EOS list differs')
        if out.exists():raise ValueError('Remote partial output cannot retry')
        claim=dict(logical_id=logical(job),execution=intent['execution'],app_id=intent['app_id'],dispatch_sha256=digest(intent),worker_start_epoch=start)
        if not store.put(k+'/claim',claim,skip_if_exists=True):raise ValueError('Original claim exists')
        claimed=True;out.mkdir(parents=True,exist_ok=False);dump(out/'ADMISSION.json',intent);dump(out/'CLAIM.json',claim)
        timing=policy(job,start,intent['budget']['prior_reserved_usd']);dump(out/'TIMING_POLICY.json',timing)
        identity=dict(engineering_preflight=True,scientific_cell_result=False,logical_id=logical(job),arm=job['arm'],job_sha256=digest(job),
            input_plan_sha256=job.get('input_plan_sha256'),execution=intent['execution'],source_files=spec['source_files'])
        dump(out/'IDENTITY.json',identity);volume.commit()
        result=body(job,inputs,out,identity,k,claim,start+limits['worker_seconds'],timing,store,volume)
        artifact=long_transport.pack(out,limits['artifact_max_bytes']);volume.commit();finished=time.time()
        if finished>=start+limits['worker_seconds']:raise TimeoutError('Packing exceeded original hard window')
        receipt=dict(status='completed',logical_id=logical(job),app_id=intent['app_id'],claim=claim,
            spec_sha256=digest(spec),spec_file_sha256=sha(path),job_sha256=digest(job),
            worker_start_epoch=start,finished_epoch=finished,artifact=artifact,result=result,engineering_preflight=True,scientific_cell_result=False)
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

"""Current-owner A/D admission; original science and logical IDs remain fixed.

A shared source/input/numeric review covers this path, never per-cell CR. Actual
configuration, timing and Claude smoke selection remain data, not self-approval.
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
from experiments.p011 import long_training, long_execution, long_numeric, long_transport, failed_attempt_ledger
from experiments.p011.c1_r2 import parent
from experiments.sft_allocation_midpoint.common import dump, read, sha, digest, verify

LOCAL=lifecycle.LOCAL
STORE=lifecycle.STORE
SPEC='reports/p011_20261020/long_conditional_runtime_v1/SPEC.json'
ORIGINAL_SPEC='reports/p011_20261020/long_current_runtime_v1/SPEC.json'
ORIGINAL_SPEC_SHA='f0e9274459b17b25a9754b863ce88d4ecee5c35fe9804e3ffdd86f8ce92c522b'
DISPOSITION='reports/p011_20261020/review_02719f84_B_accepted_F15_complete_long_conditional_v1/REPORT_LONG_FORMAL_NUMERIC_A2_LITE_AND_7_4_DISPOSITION.md'
DISPOSITION_SHA='aac07df3b995480490ff2ba8844745849c06741efe03bf940f8460234d237f0b'
F15_PROOF='reports/p011_20261020/review_02719f84_B_accepted_F15_complete_long_conditional_v1/F15_COMPLETE_READONLY_PROOF.json'
INITIAL_JOBS=('long_A7_S-L15_s17_r1','long_A7_S-F15_s17_r1','long_baseline_S-L15_s17_r1')
BUDGET_OWNER_SHA='364aaf6cd70fa9cf1a89902af6dedb33a1b64d7c47e73a12b37b6b97dfb69a2f'
LOCAL_INPUT_DIRECTORY='long_inputs_numeric_gold_r1'
AUDIT_METADATA_NAMES={'config.json','generation_config.json','tokenizer.json','tokenizer_config.json','special_tokens_map.json','vocab.json','merges.txt','added_tokens.json'}
CUTOFF=1792645200
SCOPE='p011-long-A-D-complete-path-CR-A1-A2-lite'
INPUTS='/evidence/p011-20261020/long_inputs_r1'
BASE='/evidence/p011-20261020/long_runs_r1'


def logical(job):
    prefix='baseline' if job['kind']=='baseline' else job['cell']
    return 'long_'+prefix+'_'+job['arm']+'_s17_r1'


def key(job):return 'long/'+logical(job)


def validate(spec):
    # The original conditional report stays conditional. A new exact source
    # review binds this adapter; it cannot create additional scientific jobs.
    conditional_evidence(spec)
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
        policy(job,1,'0')
    return spec


def conditional_evidence(spec,root=None):
    root=Path(root) if root is not None else Path(__file__).resolve().parents[2]
    files=spec.get('conditional_evidence_files',{})
    if (set(files)!={ORIGINAL_SPEC,DISPOSITION,F15_PROOF}
            or files.get(ORIGINAL_SPEC)!=ORIGINAL_SPEC_SHA
            or files.get(DISPOSITION)!=DISPOSITION_SHA
            or spec.get('original_numeric_decision')!='PASS-WITH-CONDITIONS'
            or spec.get('initial_allowed_jobs')!=list(INITIAL_JOBS)):
        raise ValueError('Exact unchanged conditional disposition/evidence required')
    for name,value in files.items():
        p=root/name
        if p.is_symlink() or not re.fullmatch(r'[0-9a-f]{64}',str(value)) or sha(p)!=value:
            raise ValueError('Conditional evidence bytes changed')
    old=read(root/ORIGINAL_SPEC)
    if (not spec.get('jobs') or any(old['jobs'].get(k)!=v for k,v in spec['jobs'].items())
            or any(v['arm']=='S-L3' for v in spec['jobs'].values())
            or any(spec['source_files'].get(k)!=v for k,v in old['source_files'].items())):
        raise ValueError('Original job/source bytes changed or cancelled L3 restored')
    proof=read(root/F15_PROOF)
    if (proof.get('complete') is not True or proof.get('engineering_only') is not True
            or proof.get('no_score_computed') is not True
            or proof.get('job_sha256')!='08f754e10213e328109e7102c24cf50338c7a330a4c6c56ca8d9d80c0615fee6'
            or not 0<proof.get('completed_epoch',0)<1792587018.9038124
            or proof.get('full_state',{}).get('updates')!=2
            or proof['full_state'].get('targets')!=65082):
        raise ValueError('Actual original F15 local proof condition absent')
    return old


def policy(job,start,prior):
    t=job['timing'];l=job['limits']
    p=dict(category=job['category'],worker_start_epoch=start,worker_hard_seconds=l['worker_seconds'],
        result_deadline_epoch=CUTOFF,full_result_seconds=l['full_result_window_seconds'],
        measurement_exceptions=0,projection_multiplier=1.2,uncalibrated_future_seconds=t['future_allowance_seconds'],
        training_unit_seconds=t['training_unit_seconds'],endpoint_batch_seconds=t['endpoint_batch_seconds'],
        hourly_rate_usd=l['hourly_rate_usd'],startup_allowance_seconds=l['startup_seconds'],
        reserved_usd=l['reserved_usd'],prior_reserved_usd=prior,platform_timeout_seconds=l['platform_seconds'])
    long_numeric.forecast(p,job['U'],ENDPOINT_BATCHES,[],[],start)
    return p


def reviewed(spec,path,review):
    validate(spec);result=shared.fixed_report(review)
    expected=dict(scope=SCOPE,original_plan_commit=shared.PLAN,spec_sha256=sha(path),
        source_files=spec['source_files'],jobs_sha256=digest(spec['jobs']),measurement_exceptions=0,
        budget_owner_decision_sha256=BUDGET_OWNER_SHA,
        prior_failed_C1_sha256=digest(spec['prior_failed_C1']),
        failed_attempt_bindings_sha256=digest(spec['failed_attempt_bindings']),
        actual_input_directory=LOCAL_INPUT_DIRECTORY,actual_input_binding_sha256=spec['actual_input_binding_sha256'],
        source_appendix_scope='p011-long-conditional-initial3-adapter-CR',
        original_numeric_spec_sha256=ORIGINAL_SPEC_SHA,original_numeric_report_sha256=DISPOSITION_SHA,
        original_numeric_decision='PASS-WITH-CONDITIONS',
        conditional_evidence_files=spec['conditional_evidence_files'],initial_allowed_jobs=list(INITIAL_JOBS))
    flags=('complete_source_closure_accepted','OT3_actual_A1_accepted','AM_actual_A1_accepted',
        'endpoint_native_inputs_A1_accepted','all_original_complete_timing_sources_accepted',
        'full_state_raw_scoring_window_and_budget_accepted','remote_paths_traced_to_producers',
        'current_owner_budget_and_failed_reservations_accepted',
        'completed_numeric_gold_inputs_and_prior_asset_reuse_accepted',
        'original32_to_formal512_and_processed_token_scaling_scope_accepted',
        'new_A_D7200_scoring_cap_with_frozen_per_row_rules_and_full_window_accepted',
        'plan7_4_mandatory_remaining_budget_disposition_explicitly_accepted',
        'fullparameter_actual_local_oracle_accepted_after_preentry_disposition',
        'original_conditional_numeric_report_preserved_and_inherited',
        'only_initial_two_smokes_and_one_baseline_admitted',
        'all_L3_jobs_cancelled_and_later_jobs_require_reduced_selection',
        'actual_F15_full_local_proof_condition_satisfied',
        'original_jobs_science_limits_and_no_reserve_release_unchanged')
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
    for name in [*spec['source_files'],*spec['conditional_evidence_files'],SPEC]:
        if git('show',head+':'+name)!=(Path(root)/name).read_bytes():raise ValueError('Uncommitted source/spec')
    return head


def selection(job,review):
    if job['arm']=='S-L3':raise ValueError('L3 jobs cancelled by delegated disposition')
    if logical(job) in INITIAL_JOBS:return None
    if not isinstance(review,dict):raise ValueError('Real original smoke decision absent')
    value=shared.fixed_report(review)
    if (review.get('scope')!='p011-long-reduced-smoke-student-selection'
            or review.get('selection_rule_unchanged') is not True
            or review.get('conditional_disposition_sha256')!=DISPOSITION_SHA
            or review.get('chosen_arm')!=job['arm'] or logical(job) not in review.get('allowed_logical_ids',[])
            or review.get('both_retained_smokes_and_single_baseline_A3_accepted') is not True
            or review.get('mandatory_order_and_budget_feasibility_explicitly_decided') is not True
            or (job['category']=='D' and review.get('D_both_or_none_feasibility_accepted') is not True)):
        raise ValueError('Real reduced-smoke A3/Claude selection and budget decision required')
    return value


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
    return dict(category=cat,new_reserved_usd=str(reserve),prior_reserved_usd=totals[cat],
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
        if logical(job) not in INITIAL_JOBS:
            if intent['selection'] is None or logical(job) not in intent['selection']['allowed_logical_ids']:
                raise ValueError('Exact accepted smoke selection absent')
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

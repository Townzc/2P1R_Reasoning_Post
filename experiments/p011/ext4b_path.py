"""Exact new 4B launch, claim, cost timer and terminal artifact boundaries."""
from pathlib import Path
from decimal import Decimal
import fcntl
import hashlib
import json
import subprocess
import tarfile
import tempfile
import time
import traceback
from experiments.p011.ext4b_runtime_contract import (SPEC,SCOPE,A2_SCOPE,LOCAL,INPUTS,REMOTE,STORE,JOBS,review,cost_window,admit_attempt)
from experiments.p011.owner_0205_common import create,read,sha,digest,utc
from experiments.sft_allocation_midpoint.common import verify,manifest
from experiments.p011 import ext4b_execution
from experiments.p011.long_owner_path import terminate_owned_descendants

ACTUAL=Path('.local/p011_20261020/r1/ext4b_runtime_actual_r1/ACTUAL_JOB_MANIFEST.json')


def published(root,spec):
    def git(*args):return subprocess.check_output(['git',*args],cwd=root,text=False,timeout=60)
    head=git('rev-parse','HEAD').decode().strip()
    if git('branch','--show-current').decode().strip()!='codex/icml-acl-2027' or git('ls-remote','origin','refs/heads/codex/icml-acl-2027').decode().split()[0]!=head:
        raise ValueError('Exact extension execution HEAD must be published')
    for name in [SPEC,*spec['source_files']]:
        if git('show',head+':'+name)!=(Path(root)/name).read_bytes():raise ValueError('Unpublished extension source '+name)
    return head


def budget_check(budget,job,attempt,now):
    if not 0<=now-budget['observed_epoch']<=3600 or budget['pair_cap_usd']!='90' or budget['per_cell_cap_usd']!='45':
        raise ValueError('Fresh separate90/45 extension budget required')
    if (budget['requested_job']!=job or budget['requested_attempt']!=attempt
            or type(budget['slots_after_requested']) is not int or not 1<=budget['slots_after_requested']<=8):
        raise ValueError('Exact job/attempt and all unknown/pending shared slots required')
    check=cost_window(budget['hourly_rate_usd'],budget['prior_job_compute_upper_usd'],budget['retained_noncompute_usd'])
    pair=Decimal(budget['pair_total_upper_usd'])
    if (budget['check']!=check or not pair.is_finite()
            or budget['other_cell_retained_upper_usd']!='45'
            or pair!=Decimal(check['cumulative_cell_upper_usd'])+Decimal('45') or pair>Decimal('90')
            or (attempt==1 and Decimal(budget['prior_job_compute_upper_usd'])!=0)
            or (attempt==2 and Decimal(budget['prior_job_compute_upper_usd'])<=0)):
        raise ValueError('Combined initial/resume hard envelope differs')
    return check


def timing(job,intent,start):
    # One scientific timeline across resume; projections record only and never admit spend.
    previous=intent.get('resume')
    if previous is not None:return previous['original_timing']
    seconds=intent['budget_check']['worker_seconds']
    return {'category':'A','worker_start_epoch':start,'worker_hard_seconds':seconds,
        'result_deadline_epoch':start+50400+14405,'full_result_seconds':50400+14405,
        'measurement_exceptions':0,'projection_multiplier':1.2,'uncalibrated_future_seconds':963,
        'training_unit_seconds':[12.0],'endpoint_batch_seconds':[600.0],
        'hourly_rate_usd':intent['budget']['hourly_rate_usd'],'startup_allowance_seconds':600,
        'reserved_usd':'45','prior_reserved_usd':'0','platform_timeout_seconds':seconds+60,
        'owner_amendment_sha256':intent['owner_amendment_sha256']}


def terminal_archive(out,maximum,final_step):
    """Keep intermediate checkpoints remotely; archive each final state/export once."""
    out=Path(out)
    if (out/'evidence.tar').exists() or (out/'EVIDENCE_MEMBERS.json').exists():raise ValueError('Terminal archive already attempted')
    excluded={p.name:read(p/'manifest.json') for p in out.glob('checkpoint_*') if p.is_dir() and p.name!=f'checkpoint_{final_step:04d}'}
    create(out/'INTERMEDIATE_CHECKPOINTS_RETAINED_REMOTELY.json',{'directory':str(out),'checkpoints':excluded,'not_deleted':True,'private_intermediate_binaries_not_downloaded_or_independently_reviewed':True})
    members={}
    for p in sorted(out.rglob('*')):
        rel=p.relative_to(out)
        if p.is_symlink():raise ValueError('Symlink not allowed')
        if p.is_file() and rel.parts[0] not in excluded:members[str(rel)]={'bytes':p.stat().st_size,'sha256':sha(p)}
    if sum(v['bytes'] for v in members.values())>maximum:raise ValueError('Terminal artifact exceeds declared bound')
    create(out/'EVIDENCE_MEMBERS.json',members)
    with tarfile.open(out/'evidence.tar','x') as tar:
        for n in [*members,'EVIDENCE_MEMBERS.json']:tar.add(out/n,arcname=n,recursive=False)
    return {'members':members,'manifest_sha256':sha(out/'EVIDENCE_MEMBERS.json'),'tar_sha256':sha(out/'evidence.tar'),'tar_bytes':(out/'evidence.tar').stat().st_size,'intermediate_states_remain_remote':True,'original_binary_state_preserved':True}


def submit(root,job_id,attempt,source_review,actual_review,budget_file,store,worker,app_id,resume_file=None):
    root=Path(root);spec=review(root/SPEC,source_review,actual_review);execution=published(root,spec)
    actual=read(root/ACTUAL);a2=read(actual_review)
    if a2['actual_job_manifest_sha256']!=sha(root/ACTUAL) or actual['spec_sha256']!=sha(root/SPEC):raise ValueError('Exact actual job manifest required')
    job=actual['jobs'][job_id];budget=read(budget_file)
    if (budget['source_review_sha256']!=sha(source_review) or budget['actual_review_sha256']!=sha(actual_review)
            or budget['actual_job_manifest_sha256']!=sha(root/ACTUAL)):
        raise ValueError('Budget must bind this exact source/actual review and job manifest')
    for p,h in budget['evidence_files'].items():
        if sha(root/p)!=h:raise ValueError('Admission evidence changed')
    resume=read(resume_file) if resume_file else None
    name=admit_attempt(job_id,attempt,resume.get('parent_intent') if resume else None,resume.get('checkpoint') if resume else None,resume.get('failure') if resume else None)
    LOCAL.mkdir(parents=True,exist_ok=True)
    with (root/LOCAL/'dispatch.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        checked=budget_check(budget,job_id,attempt,time.time())
        cli=str(root/'.local/midpoint_20261011/venv/bin/modal')
        apps=json.loads(subprocess.check_output([cli,'app','list','--json'],text=True,timeout=60));containers=json.loads(subprocess.check_output([cli,'container','list','--json'],text=True,timeout=60))
        slots=max(len(containers),sum(max(1,int(a['Tasks'])) for a in apps if str(a['State']).lower()!='stopped'))
        if slots>=8:raise ValueError('Fresh shared model slot limit reached')
        upload=read(root/LOCAL/'upload/COMPLETED.json')
        if upload['actual_job_manifest_sha256']!=sha(root/ACTUAL) or upload['old_weights_uploaded']!=0:raise ValueError('Exact new-input transfer/readback receipt required')
        out=root/LOCAL/'dispatch'/name
        if out.exists() or store.get(name+'/dispatch') is not None:raise ValueError('Permanent attempt fence already exists')
        if attempt==2 and not store.put(job_id+'/single_resume_fence',{'attempt':2,'resume_sha256':sha(resume_file)},skip_if_exists=True):raise ValueError('Only one infrastructure resume is authorized')
        out.mkdir(parents=True,exist_ok=False)
        identity=resume['identity'] if resume else {'logical_id':job_id,'arm':'S-F15','job_sha256':digest(job),'input_plan_sha256':job['input_plan_sha256'],'execution':execution,'source_files':spec['source_files']}
        intent={'job':job_id,'attempt':attempt,'attempt_name':name,'job_spec':job,'identity':identity,'execution':execution,'app_id':app_id,'created_epoch':time.time(),'spec_sha256':sha(root/SPEC),'source_files':spec['source_files'],'source_review':read(source_review),'source_report_text':Path(read(source_review)['local_report_path']).read_text(),'actual_review':a2,'actual_report_text':Path(a2['local_report_path']).read_text(),'actual_job_manifest_sha256':sha(root/ACTUAL),'input_manifest_sha256':actual['input_manifest_sha256'],'budget':budget,'budget_check':checked,'owner_amendment_sha256':spec['owner_report_sha256'],'resume':resume,'provider_slots_at_entry':slots,'maximum_infrastructure_resumes':1}
        create(out/'INTENT.json',intent)
        if not store.put(name+'/dispatch',intent,skip_if_exists=True):raise ValueError('Remote attempt dispatch already exists')
        call=worker.with_options(timeout=checked['platform_seconds']).spawn(intent)
        create(out/'SUBMITTED.json',{'app_id':app_id,'call_id':call.object_id,'utc':utc()})
        print('SUBMITTED',name,call.object_id,flush=True)
    try:create(out/'RESULT.json',call.get())
    except BaseException as exc:
        create(out/'RETURN_ERROR.json',{'utc':utc(),'type':type(exc).__name__,'message':str(exc),'infrastructure_retry_not_inferred':True});raise


def worker_body(intent,store,volume,timer_factory):
    started=time.time();name=intent['attempt_name'];job=intent['job_spec'];out=Path(REMOTE)/'runs'/name
    check=budget_check(intent['budget'],intent['job'],intent['attempt'],started);timer=timer_factory(check['worker_seconds']);claimed=False
    try:
        spec=read(SPEC)
        if intent['spec_sha256']!=sha(SPEC) or intent['source_files']!=spec['source_files'] or store.get(name+'/dispatch')!=intent or started-intent['created_epoch']>600:
            raise ValueError('Exact source/dispatch/startup window mismatch')
        for value,text,scope,flags in ((intent['source_review'],intent['source_report_text'],SCOPE,spec['source_review_flags']),
                (intent['actual_review'],intent['actual_report_text'],A2_SCOPE,spec['actual_review_flags'])):
            if (value.get('scope')!=scope or value.get('decision') not in ('PASS','PASS-WITH-NOTES')
                    or value.get('spec_sha256')!=sha(SPEC)
                    or hashlib.sha256(text.encode()).hexdigest()!=value['report_sha256']
                    or any(value.get(k) is not True for k in flags)):
                raise ValueError('Worker exact source and actual review binding required')
        if intent['source_review']['source_files']!=spec['source_files']:
            raise ValueError('Worker review source roster differs')
        for p,h in spec['source_files'].items():
            if sha(p)!=h:raise ValueError('Reviewed worker source changed '+p)
        volume.reload();inputs=Path(REMOTE)/'inputs'
        if sha(inputs/'ACTUAL_JOB_MANIFEST.json')!=intent['actual_job_manifest_sha256']:raise ValueError('Actual A2 manifest changed')
        actual=read(inputs/'ACTUAL_JOB_MANIFEST.json')
        if (actual['jobs'].get(intent['job'])!=job or actual['spec_sha256']!=sha(SPEC)
                or intent['actual_review']['actual_job_manifest_sha256']!=intent['actual_job_manifest_sha256']
                or intent['actual_review']['input_manifest_sha256']!=actual['input_manifest_sha256']):
            raise ValueError('Worker exact actual job/input A2 binding differs')
        resume=intent.get('resume')
        if intent['attempt']==2:
            parent=resume['parent_intent'];parent_root=Path(REMOTE)/'runs'/parent['attempt_name']
            checkpoint=Path(resume['checkpoint'])
            if (parent['job']!=intent['job'] or parent['attempt']!=1
                    or store.get(parent['attempt_name']+'/dispatch')!=parent
                    or checkpoint.parent!=parent_root or not checkpoint.name.startswith('checkpoint_')
                    or resume['parent_output']!=str(parent_root)
                    or read(parent_root/'TIMING_POLICY.json')!=resume['original_timing']
                    or read(parent_root/'IDENTITY.json')!=intent['identity']
                    or store.get(intent['job']+'/single_resume_fence') is None):
                raise ValueError('Exact single stopped infrastructure parent/checkpoint required')
        verify(inputs,job['input_files']);verify(job['model']['remote_path'],job['model']['files'])
        if read(Path(job['model']['remote_path'])/'generation_config.json')['eos_token_id']!=job['eos_token_ids']:raise ValueError('Native model EOS changed')
        if out.exists():raise ValueError('Attempt output already exists; platform reentry is refused')
        claim={'job':intent['job'],'attempt':intent['attempt'],'app_id':intent['app_id'],'dispatch_sha256':digest(intent),'worker_start_epoch':started}
        if not store.put(name+'/claim',claim,skip_if_exists=True):raise ValueError('Permanent worker claim exists')
        claimed=True;out.mkdir(parents=True,exist_ok=False)
        for n,v in [('ADMISSION.json',intent),('CLAIM.json',claim),('IDENTITY.json',intent['identity']),('TIMING_POLICY.json',timing(job,intent,started))]:create(out/n,v)
        volume.commit();result=ext4b_execution.worker_body(job,inputs,out,intent['identity'],name,claim,started+check['worker_seconds'],timing(job,intent,started),store,volume,intent.get('resume'))
        artifact=terminal_archive(out,64*1024**3,job['U']);volume.commit();finished=time.time()
        if finished>=started+check['worker_seconds']:raise TimeoutError('Terminal packing exceeded hard cost timer')
        receipt={'status':'completed','job':intent['job'],'attempt':intent['attempt'],'app_id':intent['app_id'],'claim':claim,'worker_start_epoch':started,'finished_epoch':finished,'job_sha256':digest(job),'spec_sha256':intent['spec_sha256'],'result':result,'artifact':artifact,'actual_A3_accepted':False}
        create(out/'TERMINAL.json',receipt);volume.commit()
        if not store.put(name+'/terminal',receipt,skip_if_exists=True):raise ValueError('Terminal already exists')
        return receipt
    except BaseException as exc:
        if claimed:
            failure={'status':'failed','job':intent['job'],'attempt':intent['attempt'],'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc(),'finished_epoch':time.time(),'infrastructure_resume_requires_independent_failure_evidence':True}
            create(out/'FAILURE.json',failure);volume.commit();store.put(name+'/terminal',failure,skip_if_exists=True)
        raise
    finally:timer.cancel()

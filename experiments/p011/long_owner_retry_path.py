"""One direct-owner infrastructure retry, preserving the original scientific worker."""
from experiments.p011.long_owner_path import *
from experiments.p011 import long_owner_path as original,owner_retry_accounting as accounting
SPEC=accounting.RETRY_SPEC
PARENT=accounting.PARENT
RETRY=accounting.RETRY


def validate(spec):
    original.validate(spec)
    if set(spec['jobs'])!={RETRY} or spec['infrastructure_retry_number']!=1 or spec['failed_parent_job']!=PARENT:
        raise ValueError('Exactly one original A1 preemption retry')
    return spec


def published(root,spec):
    head=original.published(root,read(Path(root)/original.SPEC));validate(spec)
    prior=read(Path(root)/original.SPEC)['jobs'][PARENT];job=spec['jobs'][RETRY]
    if {k:v for k,v in prior.items() if k!='logical_id'}!={k:v for k,v in job.items() if k!='logical_id'}:
        raise ValueError('Retry must preserve every scientific and timer field')
    for name in [SPEC,*spec['source_files']]:
        if subprocess.check_output(['git','show',head+':'+name],cwd=root)!=(Path(root)/name).read_bytes():
            raise ValueError('Retry source or SPEC unpublished')
    shared.exact_source(spec,root)
    for name,want in spec['failed_parent_files'].items():
        if sha(Path(root)/name)!=want:raise ValueError('Preserved failed parent changed')
    return head


def reviewed(spec,path,review):
    validate(spec)
    return original.reviewed(spec,path,review)


def epoch_records(root):return accounting.snapshots(root)
def budget_check(root,spec,job,budget,records,obs,now):return accounting.check(root,spec,job,budget,records,obs,now)


def submit(root,spec,job_id,review_file,budget_file,selection_file,store,worker,app_id,
           publication=published,observation=None):
    root=Path(root);execution=publication(root,spec);job=spec['jobs'][job_id]
    review=reviewed(spec,root/SPEC,read(review_file));raw=Path(review['local_report_path']).read_text()
    old=read(root/original.SPEC)['jobs'][PARENT];uploadfile=root/LOCAL/'long_io_r1/upload'/PARENT/'COMPLETED.json'
    upload=read(uploadfile)
    if (sha(uploadfile)!=spec['original_upload_receipt_sha256'] or upload['job_sha256']!=digest(old)
            or upload['all_remote_file_bytes_read_back'] is not True):raise ValueError('Original A1 input upload receipt differs')
    budget=read(budget_file);base=root/LOCAL
    with (base/'dispatch.lock').open('a+') as lock:
        fcntl.flock(lock.fileno(),fcntl.LOCK_EX);records=epoch_records(root);obs=observation(root,records)
        checked=budget_check(root,spec,job,budget,records,obs,time.time());out=base/'dispatch'/job_id;k=key(job)
        retrykey='long_owner150/infra_retry_once/'+PARENT
        if out.exists() or any(store.get(n) is not None for n in [retrykey,*[k+'/'+v for v in ('dispatch','claim','terminal')]]):
            raise ValueError('The single infrastructure retry was already attempted')
        intent=dict(logical_id=job_id,job_id=job_id,execution=execution,app_id=app_id,
            spec_sha256=digest(spec),spec_file_sha256=sha(root/SPEC),job_sha256=digest(job),budget=checked,
            budget_source_sha256=sha(budget_file),budget_observed_epoch=budget['observed_epoch'],review=review,
            selection=selection(job,None),provider_observation=obs,prior_attempt_records=records,
            dispatch_epoch=time.time(),automatic_retry_allowed=False,infrastructure_retry_number=1,
            failed_parent_job=PARENT,failed_parent_files=spec['failed_parent_files'],original_input_upload_sha256=sha(uploadfile))
        out.mkdir(parents=True,exist_ok=False);dump(out/'INTENT.json',intent)
        (out/'BUDGET_SOURCE.json').write_bytes(Path(budget_file).read_bytes());(out/'ORIGINAL_REPORT.md').write_text(raw)
        if not store.put(retrykey,dict(logical_id=job_id,dispatch_sha256=digest(intent)),skip_if_exists=True):raise ValueError('Retry fence exists')
        if not store.put(k+'/dispatch',intent,skip_if_exists=True):raise ValueError('New dispatch fence exists')
        call=worker.spawn(intent,raw);dump(out/'SUBMITTED.json',dict(logical_id=job_id,app_id=app_id,call_id=call.object_id,submitted_epoch=time.time()))
    return call,out

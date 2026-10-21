"""Optional owner jobs: same scientific worker, complete new-epoch accounting."""
from experiments.p011.long_owner_path import *
from experiments.p011 import long_owner_path as original, owner_post_retry_accounting as accounting
CLIENT_BINDING='reports/p011_20261020/owner_optional_post_retry_accounting_v1/CLIENT_BINDING.json'

def published(root,spec):
    head=original.published(root,spec)
    if subprocess.check_output(['git','show',head+':'+CLIENT_BINDING],cwd=root)!=(Path(root)/CLIENT_BINDING).read_bytes():
        raise ValueError('Optional client binding is unpublished')
    for name,want in read(Path(root)/CLIENT_BINDING)['source_files'].items():
        if sha(Path(root)/name)!=want or subprocess.check_output(['git','show',head+':'+name],cwd=root)!=(Path(root)/name).read_bytes():
            raise ValueError('New optional admission source is unpublished')
    return head

def epoch_records(root):return accounting.snapshots(root)
def budget_check(root,spec,job,budget,records,obs,now):return accounting.check(root,spec,job,budget,records,obs,now)

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
            dispatch_epoch=time.time(),automatic_retry_allowed=False,admission_adapter_source_files=read(root/CLIENT_BINDING)['source_files'])
        out.mkdir(parents=True,exist_ok=False);dump(out/'INTENT.json',intent)
        (out/'BUDGET_SOURCE.json').write_bytes(Path(budget_file).read_bytes());(out/'ORIGINAL_REPORT.md').write_text(raw)
        if not store.put(k+'/dispatch',intent,skip_if_exists=True):raise ValueError('Permanent remote fence exists')
        call=worker.spawn(intent,raw)
        dump(out/'SUBMITTED.json',dict(logical_id=job_id,app_id=app_id,call_id=call.object_id,submitted_epoch=time.time()))
    return call,out

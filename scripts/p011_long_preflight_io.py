"""Single-use engineering transfer/collect/full readonly proof. No score command."""
import argparse,hashlib,json,os,subprocess,threading,time
from pathlib import Path
from experiments.p011.long_preflight import path,evidence
from experiments.p011 import long_transport,c1_outer as shared
from experiments.sft_allocation_midpoint.common import read,dump,sha,digest,verify
ROOT=Path(__file__).resolve().parents[1]

def original(spec,job,receipt,provider,records):
    k=path.key(job)
    if (receipt.get('status')!='completed' or receipt.get('logical_id')!=path.logical(job)
            or receipt.get('spec_sha256')!=digest(spec) or receipt.get('job_sha256')!=digest(job)
            or receipt.get('claim')!=records.get(k+'/claim') or records.get(k+'/terminal')!=receipt
            or provider.get('app_id')!=receipt.get('app_id') or provider.get('state')!='stopped'
            or provider.get('owned_containers')!=0 or provider['observed_epoch']<receipt['finished_epoch']
            or not 0<receipt['finished_epoch']-receipt['worker_start_epoch']<job['limits']['worker_seconds']):
        raise ValueError('Complete original receipt/claim/provider evidence required')

def transfer(volume,source,remote,files,out):
    from modal.exception import NotFoundError
    source=Path(source)
    for name,expected in files.items():
        p=Path(name)
        if p.is_absolute() or '..' in p.parts:raise ValueError('Unsafe transfer member')
        existing=None
        try:
            h=hashlib.sha256();size=0
            for b in volume.read_file(remote+'/'+name):h.update(b);size+=len(b)
            existing=dict(bytes=size,sha256=h.hexdigest())
        except (NotFoundError,FileNotFoundError):pass
        if existing is None:
            if sha(source/name)!=expected['sha256'] or (source/name).stat().st_size!=expected['bytes']:raise ValueError('Local transfer bytes differ')
            with volume.batch_upload(force=False) as upload:upload.put_file(source/name,remote+'/'+name)
            h=hashlib.sha256();size=0
            for b in volume.read_file(remote+'/'+name):h.update(b);size+=len(b)
            if dict(bytes=size,sha256=h.hexdigest())!=expected:raise ValueError('Original upload readback failed; no retry')
        elif existing!=expected:raise ValueError('Existing remote bytes differ; no overwrite')
        dump(out/(name+'.json'),dict(**expected,reused_identical=existing is not None))

def collect(root,out,spec,job,review):
    import modal
    run=root/path.LOCAL/'dispatch'/path.logical(job);sub=read(run/'SUBMITTED.json');receipt=read(run/'RESULT.json')
    if receipt.get('status')!='completed' or receipt.get('app_id')!=sub['app_id']:raise ValueError('Original completed call required')
    cli=str(root/'.local/midpoint_20261011/venv/bin/modal')
    def observe(*args):return json.loads(subprocess.check_output([cli,*args,'--json'],text=True,stderr=subprocess.PIPE,timeout=45))
    info=observe('app','info',sub['app_id']);containers=observe('container','list')
    provider=shared.closed_provider(sub['app_id'],info,containers,time.time())
    dump(out/'PROVIDER_RAW.json',dict(app=info,containers=containers));dump(out/'PROVIDER_STOPPED0.json',provider)
    store=modal.Dict.from_name(path.STORE,create_if_missing=False);k=path.key(job)
    records={}
    for name in [k+'/dispatch',*evidence.keys(job)[1:]]:
        value=store.get(name)
        if value is None:raise ValueError('Missing immutable original named record')
        records[name]=value;dump(out/'records'/(name.removeprefix(k+'/')+'.json'),value)
    original(spec,job,receipt,provider,records);dump(out/'RECORDS.json',records);dump(out/'ORIGINAL_RESULT.json',receipt)
    remote=(path.BASE+'/'+path.logical(job)+'/evidence.tar').removeprefix('/evidence')
    volume=modal.Volume.from_name('sft-allocation-midpoint-v1',create_if_missing=False);target=out/'evidence.tar'
    with target.open('xb') as f:
        for b in volume.read_file(remote):f.write(b)
    if target.stat().st_size!=receipt['artifact']['tar_bytes'] or sha(target)!=receipt['artifact']['tar_sha256']:raise ValueError('Original archive partial/mismatch')
    dump(out/'COMPLETED.json',dict(original_receipt_sha256=sha(out/'ORIGINAL_RESULT.json'),archive_sha256=sha(target),named_records=len(records),review=review,completed_epoch=time.time()))
    dump(run/'PROVIDER_STOPPED0.json',provider)


def window(mode,job,now,receipt=None):
    limits=job['limits']
    deadline=(path.CUTOFF-limits['full_result_window_seconds'] if mode=='upload' else
        min(path.CUTOFF,receipt['worker_start_epoch']+limits['worker_seconds']+limits['closeout_seconds']))
    if mode not in ('upload','collect','audit') or not 0<deadline-now:raise TimeoutError('Original engineering window unavailable')
    return min(3600,deadline-now),deadline


def upload(root,out,spec,job,review):
    import modal
    source=root/path.LOCAL/'long_preflight_inputs_r1'/job['input_directory'];verify(source,job['local_input_files'])
    store=modal.Dict.from_name(path.STORE,create_if_missing=True)
    intent={'job_sha256':digest(job),'source_files':spec['source_files'],'review':review}
    if not store.put(path.key(job)+'/upload',intent,skip_if_exists=True):raise ValueError('Original engineering upload attempted')
    dump(out/'UPLOAD_INTENT.json',intent)
    volume=modal.Volume.from_name('sft-allocation-midpoint-v1',create_if_missing=False)
    transfer(volume,source,path.INPUTS.removeprefix('/evidence')+'/'+job['input_directory'],job['input_files'],out/'inputs')
    # Share exactly one asset transfer/readback across the two 1.5B arms.
    m=job['model'];assetdir=root/path.LOCAL/'long_preflight_io_r1/model_uploads'/m['revision']
    if (assetdir/'COMPLETED.json').exists():
        assets=read(assetdir/'COMPLETED.json')
        if assets!={'model_files':m['files'],'remote_path':m['remote_path'],'all_remote_file_bytes_read_back':True}:raise ValueError('Original asset readback differs')
    else:
        assetdir.mkdir(parents=True,exist_ok=False)
        dump(assetdir/'ATTEMPT.json',{'model':m,'automatic_retry':False})
        if not store.put('engineering/model_upload/'+m['revision'],{'model':m},skip_if_exists=True):raise ValueError('Original model transfer already attempted')
        transfer(volume,root/m['local_path'],m['remote_path'].removeprefix('/evidence'),m['files'],assetdir/'files')
        assets={'model_files':m['files'],'remote_path':m['remote_path'],'all_remote_file_bytes_read_back':True};dump(assetdir/'COMPLETED.json',assets)
    dump(out/'COMPLETED.json',{**intent,'all_remote_file_bytes_read_back':True,
        'asset_readback_file_sha256':sha(assetdir/'COMPLETED.json'),'completed_epoch':time.time(),'model_calls':0})


def audit(root,out,spec,job,review):
    saved=root/path.LOCAL/'long_preflight_io_r1/collect'/path.logical(job);read(saved/'COMPLETED.json')
    receipt=read(saved/'ORIGINAL_RESULT.json');provider=read(saved/'PROVIDER_STOPPED0.json');records=read(saved/'RECORDS.json')
    original(spec,job,receipt,provider,records)
    dispatch=read(root/path.LOCAL/'dispatch'/path.logical(job)/'INTENT.json')
    if records[path.key(job)+'/dispatch']!=dispatch or dispatch['review']!=review:raise ValueError('Exact original engineering dispatch/review differs')
    budgetfile=root/path.LOCAL/'dispatch'/path.logical(job)/'BUDGET_SOURCE.json'
    if sha(budgetfile)!=dispatch['budget_source_sha256']:raise ValueError('Original budget evidence differs')
    if path.budget_check(root,spec,job,read(budgetfile),dispatch['prior_attempt_records'],dispatch['provider_observation'],dispatch['dispatch_epoch'])!=dispatch['budget']:raise ValueError('Original engineering numeric admission differs')
    long_transport.extract(saved/'evidence.tar',out/'payload',receipt['artifact'],job['limits']['artifact_max_bytes'])
    payload=out/'payload';identity=read(payload/'IDENTITY.json');timing=read(payload/'TIMING_POLICY.json')
    expected={'engineering_preflight':True,'scientific_cell_result':False,'logical_id':path.logical(job),'arm':job['arm'],
        'job_sha256':digest(job),'input_plan_sha256':job['input_plan_sha256'],'execution':dispatch['execution'],'source_files':spec['source_files']}
    if (identity!=expected or read(payload/'ADMISSION.json')!=dispatch or read(payload/'CLAIM.json')!=receipt['claim']
            or timing!=path.policy(job,receipt['worker_start_epoch'],dispatch['budget']['prior_reserved_usd'])
            or read(payload/'RESULT.json')!=receipt['result']):raise ValueError('Original full engineering outer bindings differ')
    inputs=root/path.LOCAL/'long_preflight_inputs_r1'/job['input_directory'];verify(inputs,job['local_input_files'])
    proof=evidence.check(payload,inputs,job,identity,records,timing)
    dump(out/'COMPLETE_READONLY_PROOF.json',{**proof,'source_files':spec['source_files'],
        'original_receipt_sha256':sha(saved/'ORIGINAL_RESULT.json'),'job_sha256':digest(job),'completed_epoch':time.time(),
        'independent_engineering_review_accepted':False,'actual_scientific_A3_A5':False})


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=('upload','collect','audit'));p.add_argument('--job',required=True);p.add_argument('--review',required=True);args=p.parse_args()
    spec=path.validate(read(ROOT/path.SPEC));path.published(ROOT,spec)
    review=path.reviewed(spec,ROOT/path.SPEC,read(args.review));job=spec['jobs'][args.job]
    receipt=None if args.mode=='upload' else read(ROOT/path.LOCAL/'dispatch'/args.job/'RESULT.json')
    seconds,deadline=window(args.mode,job,time.time(),receipt)
    out=ROOT/path.LOCAL/'long_preflight_io_r1'/args.mode/args.job;out.mkdir(parents=True,exist_ok=False)
    dump(out/'ATTEMPT.json',{'job_sha256':digest(job),'mode':args.mode,'original_absolute_deadline':deadline,'remaining_local_seconds':seconds,'automatic_retry':False})
    timer=threading.Timer(seconds,lambda:os._exit(124));timer.daemon=True;timer.start()
    try:{'upload':upload,'collect':collect,'audit':audit}[args.mode](ROOT,out,spec,job,review)
    except BaseException as e:
        dump(out/'FAILED.json',{'type':type(e).__name__,'message':str(e),'partial_retained':True,'automatic_retry':False});raise
    finally:timer.cancel()

if __name__=='__main__':main()

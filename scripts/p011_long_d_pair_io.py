"""D pair one-use upload, STOPPED0 collection, full state/raw oracle and scoring.

All closeout stages share original worker-start + worker + closeout, capped by
Oct22 05UTC. Unknown/partial/failed runs are retained, never scored as zeros.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import threading
import time
from experiments.p011 import long_d_pair_path as path,long_transport,long_d_pair_evidence as long_evidence,long_scoring,long_score_process
from experiments.p011 import c1_outer as shared
from experiments.sft_allocation_midpoint.common import read,dump,sha,digest,verify
ROOT=Path(__file__).resolve().parents[1]


def window(mode,job,now,receipt=None):
    limits=job['limits']
    deadline=(path.CUTOFF-limits['full_result_window_seconds'] if mode=='upload' else
        min(path.CUTOFF,receipt['worker_start_epoch']+limits['worker_seconds']+limits['closeout_seconds']))
    # Score keeps its entire admitted child window and5s owned cleanup; no new
    # independent deadline after collect/audit. Others have at most one hour.
    needed=limits['score_seconds']+5 if mode=='score' else 1
    if deadline-now<needed:raise TimeoutError('Original full result window exhausted')
    return min(deadline-now,needed if mode=='score' else 3600),deadline


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


def reused_assets(root,job):
    model=job['model'];binding=model['preflight_asset_readback'];p=Path(binding['path'])
    expected=Path(path.LOCAL)/'long_preflight_io_r1/model_uploads'/model['revision']/'COMPLETED.json'
    if p!=expected or (Path(root)/p).is_symlink() or sha(Path(root)/p)!=binding['sha256']:
        raise ValueError('Original complete asset readback binding differs')
    proof=read(Path(root)/p)
    if proof!={'model_files':model['files'],'remote_path':model['remote_path'],'all_remote_file_bytes_read_back':True}:
        raise ValueError('Original complete engineering asset readback required')
    return binding['sha256']


def upload(root,out,spec,job,review):
    import modal
    source=root/path.LOCAL/path.LOCAL_INPUT_DIRECTORY/job['input_directory'];verify(source,job['local_input_files'])
    asset_proof=reused_assets(root,job)
    store=modal.Dict.from_name(path.STORE,create_if_missing=True)
    intent=dict(job_sha256=digest(job),source_files=spec['source_files'],review=review)
    if not store.put(path.key(job)+'/upload',intent,skip_if_exists=True):raise ValueError('Upload already attempted')
    dump(out/'UPLOAD_INTENT.json',intent);volume=modal.Volume.from_name('sft-allocation-midpoint-v1',create_if_missing=False)
    transfer(volume,source,path.INPUTS.removeprefix('/evidence')+'/'+job['input_directory'],job['input_files'],out/'inputs')
    # Reuse the exact once-only engineering asset transfer/readback. Formal
    # upload cannot download, upload or reread already verified model weights.
    dump(out/'COMPLETED.json',dict(**intent,all_remote_file_bytes_read_back=True,
        asset_readback_file_sha256=asset_proof,completed_epoch=time.time(),model_calls=0))


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
    for name in [k+'/dispatch',*long_evidence.expected_record_keys(k,job['kind'],job['U'])]:
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


def audit(root,out,spec,job,review):
    io=root/path.LOCAL/'long_io_r1';saved=io/'collect'/path.logical(job);read(saved/'COMPLETED.json')
    receipt=read(saved/'ORIGINAL_RESULT.json');provider=read(saved/'PROVIDER_STOPPED0.json');records=read(saved/'RECORDS.json');k=path.key(job)
    original(spec,job,receipt,provider,records)
    dispatch=read(root/path.LOCAL/'dispatch'/path.logical(job)/'INTENT.json')
    if records[k+'/dispatch']!=dispatch or dispatch['review']!=review:raise ValueError('Exact original dispatch/review differs')
    budgetfile=root/path.LOCAL/'dispatch'/path.logical(job)/'BUDGET_SOURCE.json'
    if sha(budgetfile)!=dispatch['budget_source_sha256']:raise ValueError('Original budget changed')
    if path.budget_check(root,spec,job,read(budgetfile),dispatch['prior_attempt_records'],dispatch['provider_observation'],dispatch['dispatch_epoch'])!=dispatch['budget']:
        raise ValueError('Original numeric admission replay differs')
    long_transport.extract(saved/'evidence.tar',out/'payload',receipt['artifact'],job['limits']['artifact_max_bytes'])
    payload=out/'payload';intent=read(payload/'ADMISSION.json');claim=read(payload/'CLAIM.json');identity=read(payload/'IDENTITY.json');timing=read(payload/'TIMING_POLICY.json')
    if (intent!=dispatch or claim!=receipt['claim'] or timing!=path.policy(job,receipt['worker_start_epoch'],dispatch['budget']['prior_reserved_usd'])
            or identity!=dict(logical_id=path.logical(job),arm=job['arm'],job_sha256=digest(job),input_plan_sha256=job.get('input_plan_sha256'),execution=dispatch['execution'],source_files=spec['source_files'])):
        raise ValueError('Original complete worker identity/timing/basis differs')
    attempts,done=long_evidence.verify_journals(payload,k,job['kind'],job['U'],{n:v for n,v in records.items() if n!=k+'/dispatch'})
    inputs=root/path.LOCAL/path.LOCAL_INPUT_DIRECTORY/job['input_directory'];verify(inputs,job['local_input_files'])
    reused_assets(root,job)
    assets=root/job['model']['local_path'];verify(assets,job['model']['local_audit_asset_files']);config=read(assets/'config.json')
    train=None
    if job['kind']=='student':
        train=long_evidence.verify_training(payload,read(inputs/'encoded.json'),read(inputs/'plan.json'),read(inputs/('rates_'+job['arm']+'.json')),job['arm'],config,identity,attempts,done,timing)
    elif read(payload/'BASELINE_PROOF.json')!=dict(training_updates=0,model=job['model']):raise ValueError('Original baseline changed')
    from transformers import AutoTokenizer
    tokenizer=AutoTokenizer.from_pretrained(assets,local_files_only=True,trust_remote_code=False,use_fast=True)
    endpoint=long_evidence.verify_endpoint(payload,read(inputs/'ENDPOINT_LOCAL.json'),job['context'],job['eos_token_ids'],tokenizer,config,attempts,done,timing,train['training_seconds'] if train else [])
    if read(payload/'RESULT.json')!=receipt['result']:raise ValueError('Original returned result differs')
    dump(out/'SCORING_ROWS.json',endpoint.pop('scoring_rows'));dump(out/'DECODED.json',endpoint.pop('decoded'))
    dump(out/'COMPLETE_PROOF.json',dict(passed=True,receipt_sha256=sha(saved/'ORIGINAL_RESULT.json'),
        job_sha256=digest(job),source_files=spec['source_files'],endpoint=endpoint,
        training_state_verified=job['kind']=='student',training_proof=train,
        scoring_rows_sha256=sha(out/'SCORING_ROWS.json'),actual_A3_accepted=False,finished_epoch=time.time()))


def score(root,out,spec,job,review):
    auditdir=root/path.LOCAL/'long_io_r1'/'audit'/path.logical(job);proof=read(auditdir/'COMPLETE_PROOF.json')
    if proof.get('passed') is not True or proof['job_sha256']!=digest(job) or proof['source_files']!=spec['source_files'] or sha(auditdir/'SCORING_ROWS.json')!=proof['scoring_rows_sha256']:
        raise ValueError('Complete full-state/raw oracle required before scoring')
    rows=read(auditdir/'SCORING_ROWS.json');binding=dict(job_sha256=digest(job),source_files=spec['source_files'],oracle_sha256=sha(auditdir/'COMPLETE_PROOF.json'),review=review)
    result=long_score_process.supervise_once(out/'owned_score',rows,binding,job['limits']['score_seconds'])
    checked=long_scoring.verify_saved_scores(out/'owned_score/payload',rows,binding,job['limits']['score_seconds'])
    dump(out/'COMPLETED.json',dict(result=result,read_only_saved_score_proof=checked,actual_A3_accepted=False,
        independent_smoke_selection_performed=False,completed_epoch=time.time()))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('mode',choices=['upload','collect','audit','score']);parser.add_argument('--job',required=True);parser.add_argument('--review',required=True);args=parser.parse_args()
    spec=path.validate(read(ROOT/path.SPEC));path.published(ROOT,spec);review=path.reviewed(spec,ROOT/path.SPEC,read(args.review));job=spec['jobs'][args.job]
    receipt=None if args.mode=='upload' else read(ROOT/path.LOCAL/'dispatch'/args.job/'RESULT.json')
    seconds,deadline=window(args.mode,job,time.time(),receipt)
    out=ROOT/path.LOCAL/'long_io_r1'/args.mode/args.job;out.mkdir(parents=True,exist_ok=False)
    dump(out/'ATTEMPT.json',dict(job_sha256=digest(job),mode=args.mode,original_absolute_deadline=deadline,remaining_local_seconds=seconds,automatic_retry=False))
    # Scorer owns and reaps its separate process group; no abrupt parent timer
    # may orphan it. supervise_once enforces the same admitted cap +5s cleanup.
    timer=None
    if args.mode!='score':timer=threading.Timer(seconds,lambda:os._exit(124));timer.daemon=True;timer.start()
    try:
        {'upload':upload,'collect':collect,'audit':audit,'score':score}[args.mode](ROOT,out,spec,job,review)
        if time.time()>=deadline:raise TimeoutError('Original absolute result cutoff exceeded')
    except BaseException as exc:
        dump(out/'FAILED.json',dict(type=type(exc).__name__,message=str(exc),partial_retained=True,whole_helper_retry_allowed=False));raise
    finally:
        if timer:timer.cancel()

if __name__=='__main__':main()

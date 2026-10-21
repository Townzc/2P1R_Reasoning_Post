"""C2 complete source-bound upload, raw/state collection, oracle and frozen scoring.

New C2 jobs only. Every local closeout shares its original worker absolute
window; failed/partial evidence never authorizes retry or completed collection.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import threading
import time
from experiments.p011 import c2_path as path, long_transport, c2_numeric
from experiments.p011 import c2_generation_evidence, c2_generation_loader, c2_student_evidence
from experiments.p011 import c2_scoring,c2_score_process,c1_outer as shared
from experiments.p010 import student_scoring,student_score_process
from experiments.sft_allocation_midpoint.common import read,dump,sha,digest,verify
ROOT=Path(__file__).resolve().parents[1]


def gold_rows(pack):
    """Same original supported solution parser; no answer/model scoring."""
    from experiments.learning_regime_p009.math_scoring import last_box
    rows=[]
    for pid in pack['plan']['window_parents']:
        original=pack['source'][pid];answer=last_box(original['solution'])['answer']
        if not isinstance(answer,str) or not answer:raise ValueError('Original supported gold required')
        rows.append({'problem_id':pid,'gold':answer,'original_source_row_sha256':digest(original)})
    return rows


def expected_records(job):
    k=path.key(job)
    if job['kind']=='student':return [k+'/dispatch',*c2_student_evidence.expected_record_keys(job['run_id'])]
    return [k+'/'+v for v in ('dispatch','claim','terminal','window')]+[
        k+f'/{kind}/{i:03d}' for kind in ('batch','batch_done') for i in range(job['new_generation_batches'])]


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


def upload(root,out,spec,job,review):
    import modal
    source=path.local_inputs(root,job);verify(source,job['local_input_files'])
    store=modal.Dict.from_name(path.STORE,create_if_missing=True)
    intent=dict(job_sha256=digest(job),source_files=spec['source_files'],review=review)
    if not store.put(path.key(job)+'/upload',intent,skip_if_exists=True):raise ValueError('Upload already attempted')
    dump(out/'UPLOAD_INTENT.json',intent);volume=modal.Volume.from_name('sft-allocation-midpoint-v1',create_if_missing=False)
    transfer(volume,source,path.INPUTS.removeprefix('/evidence')+'/'+job['input_directory'],job['input_files'],out/'inputs')
    transfer(volume,root/job['model']['local_path'],job['model']['remote_path'].removeprefix('/evidence'),job['model']['files'],out/'assets')
    dump(out/'COMPLETED.json',dict(**intent,all_remote_file_bytes_read_back=True,completed_epoch=time.time(),model_calls=0))


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
    for name in expected_records(job):
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
    saved=root/path.LOCAL/'c2_io_r1'/'collect'/path.logical(job);read(saved/'COMPLETED.json')
    receipt=read(saved/'ORIGINAL_RESULT.json');provider=read(saved/'PROVIDER_STOPPED0.json');records=read(saved/'RECORDS.json');k=path.key(job)
    original(spec,job,receipt,provider,records)
    if set(records)!=set(expected_records(job)):raise ValueError('Exact complete original named records required')
    dispatch=read(root/path.LOCAL/'dispatch'/path.logical(job)/'INTENT.json')
    if records[k+'/dispatch']!=dispatch or dispatch['review']!=review:raise ValueError('Original dispatch/review differs')
    budgetfile=root/path.LOCAL/'dispatch'/path.logical(job)/'BUDGET_SOURCE.json'
    if sha(budgetfile)!=dispatch['budget_source_sha256']:raise ValueError('Original budget changed')
    if path.budget_check(root,spec,job,read(budgetfile),dispatch['prior_attempt_records'],dispatch['provider_observation'],dispatch['dispatch_epoch'])!=dispatch['budget']:
        raise ValueError('Original full numerical admission replay differs')
    long_transport.extract(saved/'evidence.tar',out/'payload',receipt['artifact'],job['limits']['artifact_max_bytes'])
    payload=out/'payload';identity=read(payload/'IDENTITY.json');timing=read(payload/'TIMING_POLICY.json')
    expected_identity=dict(logical_id=path.logical(job),run_id=job['run_id'],job_sha256=digest(job),
        config=job.get('config'),execution=dispatch['execution'],source_files=spec['source_files'])
    if (read(payload/'ADMISSION.json')!=dispatch or read(payload/'CLAIM.json')!=receipt['claim']
            or identity!=expected_identity or timing!=path.policy(job,receipt['worker_start_epoch'],dispatch['budget']['prior_reserved_usd'])
            or read(payload/'RESULT.json')!=receipt['result']):
        raise ValueError('Original complete identity/timing/receipt differs')
    inputs=path.local_inputs(root,job);verify(inputs,job['local_input_files'])
    assets=root/job['model']['local_path'];verify(assets,job['model']['files']);cfg=read(assets/'config.json')
    from transformers import AutoTokenizer
    tokenizer=AutoTokenizer.from_pretrained(assets,local_files_only=True,trust_remote_code=False,use_fast=True)
    from experiments.learning_regime_p009.high_throughput_v1 import validate_observed_engine
    trained=None
    if job['kind']=='generation':
        pack=read(inputs/'PACK.json');gpu=read(inputs/'GPU_PACK.json')
        expected={'plan':pack['plan'],'source':{pid:{'problem':pack['source'][pid]['problem']}
            for pid in pack['plan']['window_parents']},'prompts':pack['prompts']}
        if gpu!=expected:raise ValueError('Original gold-free finite C2 GPU projection differs')
        requests=c2_generation_evidence.checked_plan(pack['plan'])
        if len(requests)!=job['new_request_count']:
            raise ValueError('Exact original new-only queue count differs')
        engine=read(payload/'ENGINE.json');validate_observed_engine(engine['engine'])
        if engine['model']!=job['model']:raise ValueError('Original teacher asset binding differs')
        c2_generation_loader.check_native_prompts(tokenizer,gpu)
        transport=c2_generation_loader.transport_reader(tokenizer,cfg['vocab_size'])
        total=job['new_generation_batches']
        def replay(left,times):
            f=read(payload/'generation/batches'/f'{total-left:03d}'/'FORECAST.json')
            return c2_numeric.forecast(timing,0,left,[],times,timing['worker_start_epoch']+f['elapsed_seconds'])
        proof=c2_generation_evidence.check_body(pack['plan'],payload/'generation',k,
            receipt['claim'],records,transport,replay)
        raw=[];decoded=[]
        for i in range(total):
            part=payload/'generation/batches'/f'{i:03d}'
            raw.extend(read(part/'RAW.json'));decoded.extend(read(part/'TRANSPORT.json'))
        scoring=c2_generation_loader.score_rows(pack['plan'],gold_rows(pack),raw,decoded)
        dump(out/'RAW_ORDERED.json',raw);dump(out/'TRANSPORT_ORDERED.json',decoded)
        endpoint=dict(technical_unknown=0,outputs=len(requests),body_proof=proof,
            original_output_decodes_repeated=0)

    else:
        if sha(inputs/'GOLD.jsonl')!=c2_student_evidence.GOLD_SHA256:raise ValueError('Original frozen MATH gold differs')
        goldrows=[json.loads(s) for s in (inputs/'GOLD.jsonl').read_text().splitlines() if s]
        gold={r['problem_id']:r for r in goldrows}
        if len(goldrows)!=500 or len(gold)!=500:raise ValueError('Exact frozen500 gold rows required')
        trained=c2_student_evidence.verify_training(payload,inputs.parent,timing,job['run_id'],identity,records,tokenizer)
        endpoint=c2_student_evidence.verify_endpoint(payload,read(inputs/'MATH_ENDPOINT.json'),timing,job['run_id'],records,trained,tokenizer,gold,cfg['vocab_size'])
        scoring=endpoint.pop('scoring_rows');dump(out/'DECODED.json',endpoint.pop('decoded'))
    dump(out/'SCORING_ROWS.json',scoring)
    dump(out/'COMPLETE_PROOF.json',dict(passed=True,receipt_sha256=sha(saved/'ORIGINAL_RESULT.json'),
        job_sha256=digest(job),source_files=spec['source_files'],endpoint=endpoint,
        training_state_verified=job['kind']=='student',training_proof=trained,
        scoring_rows_sha256=sha(out/'SCORING_ROWS.json'),actual_A3_accepted=False,finished_epoch=time.time()))


def score(root,out,spec,job,review):
    auditdir=root/path.LOCAL/'c2_io_r1'/'audit'/path.logical(job);proof=read(auditdir/'COMPLETE_PROOF.json')
    if proof.get('passed') is not True or proof['job_sha256']!=digest(job) or proof['source_files']!=spec['source_files'] or sha(auditdir/'SCORING_ROWS.json')!=proof['scoring_rows_sha256']:
        raise ValueError('Complete full-state/raw oracle required before scoring')
    rows=read(auditdir/'SCORING_ROWS.json');binding=dict(job_sha256=digest(job),source_files=spec['source_files'],oracle_sha256=sha(auditdir/'COMPLETE_PROOF.json'),review=review)
    process,payload=(c2_score_process,c2_scoring) if job['kind']=='generation' else (student_score_process,student_scoring)
    result=process.supervise_once(out/'owned_score',rows,binding,job['limits']['score_seconds'])
    checked=payload.verify_saved_scores(out/'owned_score/payload',rows,binding,job['limits']['score_seconds'])
    extra={}
    if job['kind']=='generation':
        pack=read(path.local_inputs(root,job)/'PACK.json')
        records,selection=c2_generation_loader.selected_records(pack['plan'],gold_rows(pack),
            read(auditdir/'RAW_ORDERED.json'),read(auditdir/'TRANSPORT_ORDERED.json'),
            read(out/'owned_score/payload/ALL_SCORED_ROWS.json'),pack['ordered_e1d'],
            pack['t72_records'],pack['t15_records'],set(pack['s1_ids']))
        dump(out/'RECORDS.json',records);dump(out/'SELECTION.json',selection)
        extra=dict(records_sha256=digest(records),selection_sha256=digest(selection),common_support_complete=selection.get('complete') is True,requires_owner_disposition=selection.get('requires_owner_disposition',False))
    dump(out/'COMPLETED.json',dict(result=result,read_only_saved_score_proof=checked,actual_A3_accepted=False,
        **extra,completed_epoch=time.time()))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('mode',choices=['upload','collect','audit','score']);parser.add_argument('--job',required=True);parser.add_argument('--review',required=True);args=parser.parse_args()
    specfile=ROOT/path.SPEC_FILES[path.phase_for_job(args.job)]
    spec=path.validate(read(specfile));path.published(ROOT,spec);review=path.reviewed(spec,specfile,read(args.review));job=spec['jobs'][args.job]
    receipt=None if args.mode=='upload' else read(ROOT/path.LOCAL/'dispatch'/args.job/'RESULT.json')
    seconds,deadline=window(args.mode,job,time.time(),receipt)
    out=ROOT/path.LOCAL/'c2_io_r1'/args.mode/args.job;out.mkdir(parents=True,exist_ok=False)
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

"""Only new4B input transfer and complete-result local closes, each fenced once."""
import argparse
from pathlib import Path
import hashlib
import json
import subprocess
import time
from experiments.p011 import ext4b_path as path
from experiments.p011.ext4b_runtime_contract import review,INPUTS,LOCAL,SPEC,REMOTE,STORE
from experiments.p011.ext4b_encoded import EncodedRows
from experiments.p011.owner_0205_common import create,read,sha,digest,utc
from experiments.p011 import long_owner_evidence as evidence,long_transport,long_scoring,long_score_process
from experiments.p011.c1_outer import closed_provider
from experiments.sft_allocation_midpoint.common import verify


def remaining_window(dispatch,required=0):
    intent=read(dispatch/'INTENT.json');receipt=read(dispatch/'RESULT.json')
    policy=path.timing(intent['job_spec'],intent,receipt['worker_start_epoch'])
    left=policy['result_deadline_epoch']-time.time()
    if left<=required:raise TimeoutError('Original extension closeout deadline has elapsed')
    return left


def transfer(spec,out):
    import modal
    actual=read(path.ACTUAL);files=next(iter(actual['jobs'].values()))['input_files']
    store=modal.Dict.from_name(STORE,create_if_missing=True)
    if not store.put('new_input_upload',{'utc':utc(),'manifest_sha256':sha(path.ACTUAL)},skip_if_exists=True):raise ValueError('Input upload was already attempted')
    volume=modal.Volume.from_name('sft-allocation-midpoint-v1',create_if_missing=False)
    sources={n:INPUTS/n for n in files};sources['ACTUAL_JOB_MANIFEST.json']=path.ACTUAL
    inventory={**files,'ACTUAL_JOB_MANIFEST.json':{'bytes':path.ACTUAL.stat().st_size,'sha256':sha(path.ACTUAL)}}
    for n,p in sources.items():
        if p.stat().st_size!=inventory[n]['bytes'] or sha(p)!=inventory[n]['sha256']:raise ValueError('Actual new GPU input differs')
    with volume.batch_upload(force=False) as batch:
        for n,p in sources.items():batch.put_file(p,(REMOTE+'/inputs/'+n).removeprefix('/evidence'))
    for n,expected in inventory.items():
        h=hashlib.sha256();size=0
        for b in volume.read_file((REMOTE+'/inputs/'+n).removeprefix('/evidence')):h.update(b);size+=len(b)
        if {'bytes':size,'sha256':h.hexdigest()}!=expected:raise ValueError('First new transfer readback differs')
    create(out/'COMPLETED.json',{'utc':utc(),'actual_job_manifest_sha256':sha(path.ACTUAL),'transferred_files':inventory,'old_weights_uploaded':0,'gold_evaluation_payload_uploaded':False})


def collect(out,dispatch):
    import modal
    remaining_window(dispatch)
    intent=read(dispatch/'INTENT.json');receipt=read(dispatch/'RESULT.json');sub=read(dispatch/'SUBMITTED.json');job=intent['job_spec'];key=intent['attempt_name']
    if receipt.get('status')!='completed' or receipt['job_sha256']!=digest(job) or receipt['app_id']!=sub['app_id']:raise ValueError('Only a complete original call may collect')
    cli='.local/midpoint_20261011/venv/bin/modal'
    info=json.loads(subprocess.check_output([cli,'app','info',sub['app_id'],'--json'],text=True,timeout=60));containers=json.loads(subprocess.check_output([cli,'container','list','--json'],text=True,timeout=60))
    stopped=closed_provider(sub['app_id'],info,containers,time.time());create(out/'PROVIDER_RAW.json',{'app':info,'containers':containers});create(out/'PROVIDER_STOPPED0.json',stopped)
    store=modal.Dict.from_name(STORE,create_if_missing=False);raw={};derived={};mapping={}
    prefix=receipt['result']['restored_training_prefix_step'];evalprefix=set(receipt['result']['reused_endpoint_prefix']);parent=(intent.get('resume') or {}).get('parent_intent',{}).get('attempt_name')
    for wanted in evidence.expected_record_keys(key,'student',job['U']):
        suffix=wanted[len(key)+1:];parts=suffix.split('/');origin=wanted
        if len(parts)==2 and parent:
            unit=parts[1]
            if ((unit.startswith('update_') and int(unit.split('_')[1])<=prefix) or unit in evalprefix
                    or (receipt['result'].get('reused_terminal_training') and unit in ('terminal_state','terminal_model_export'))):origin=parent+'/'+suffix
        if origin not in raw:
            raw[origin]=store.get(origin)
            if raw[origin] is None:raise ValueError('Missing actual named record '+origin)
        derived[wanted]=raw[origin];mapping[wanted]=origin
    for source in [key+'/dispatch']+([parent+'/dispatch',parent+'/terminal'] if parent else []):raw[source]=store.get(source)
    if raw[key+'/dispatch']!=intent or derived[key+'/terminal']!=receipt:raise ValueError('Original local/cloud dispatch and terminal differ')
    create(out/'ACTUAL_NAMED_RECORDS.json',raw);create(out/'DERIVED_LEDGER_VIEW.json',derived);create(out/'LEDGER_SOURCE_MAP.json',mapping)
    create(out/'ORIGINAL_RESULT.json',receipt);create(out/'ORIGINAL_INTENT.json',intent)
    volume=modal.Volume.from_name('sft-allocation-midpoint-v1',create_if_missing=False);file=out/'evidence.tar'
    with file.open('xb') as stream:
        for b in volume.read_file((REMOTE+'/runs/'+key+'/evidence.tar').removeprefix('/evidence')):stream.write(b)
    if file.stat().st_size!=receipt['artifact']['tar_bytes'] or sha(file)!=receipt['artifact']['tar_sha256']:raise ValueError('Terminal artifact partial or changed')
    create(out/'COMPLETED.json',{'utc':utc(),'receipt_sha256':sha(out/'ORIGINAL_RESULT.json'),'new_archive_sha256':sha(file),'actual_named_records':len(raw),'derived_ledger_view_not_fabricated_remote_keys':True})


def audit(out,dispatch):
    from transformers import AutoTokenizer
    remaining_window(dispatch)
    intent=read(dispatch/'INTENT.json');job=intent['job_spec'];key=intent['attempt_name'];saved=LOCAL/'collect'/key
    read(saved/'COMPLETED.json');receipt=read(saved/'ORIGINAL_RESULT.json');ledger=read(saved/'DERIVED_LEDGER_VIEW.json');mapping=read(saved/'LEDGER_SOURCE_MAP.json');raw=read(saved/'ACTUAL_NAMED_RECORDS.json')
    if any(ledger[k]!=raw[origin] for k,origin in mapping.items()) or raw[key+'/dispatch']!=intent:raise ValueError('Actual source mapping changed')
    long_transport.extract(saved/'evidence.tar',out/'payload',receipt['artifact'],64*1024**3)
    payload=out/'payload';identity=read(payload/'IDENTITY.json');timing=read(payload/'TIMING_POLICY.json')
    if identity!=intent['identity'] or read(payload/'CLAIM.json')!=receipt['claim'] or read(payload/'ADMISSION.json')!=intent or timing!=path.timing(job,intent,receipt['worker_start_epoch']):raise ValueError('Scientific identity/admission/timing changed')
    attempts,done=evidence.verify_journals(payload,key,'student',job['U'],ledger)
    verify(INPUTS,job['local_input_files']);model=Path(job['model']['local_path']);verify(model,job['model']['local_audit_asset_files']);config=read(model/'config.json')
    rows=EncodedRows(INPUTS/'ENCODED.jsonl',read(INPUTS/'ROW_METADATA.json'),job['questions']);plan=read(INPUTS/(job['logical_id']+'_PLAN.json'));rates=read(INPUTS/'RATES_S-F15.json')
    trained=evidence.verify_training(payload,rows,plan,rates,'S-F15',config,identity,attempts,done,timing)
    tok=AutoTokenizer.from_pretrained(model,local_files_only=True,trust_remote_code=False,use_fast=True)
    endpoint=evidence.verify_endpoint(payload,read(INPUTS/'ENDPOINT_LOCAL.json'),job['context'],job['eos_token_ids'],tok,config,attempts,done,timing,trained['training_seconds'])
    if read(payload/'RESULT.json')!=receipt['result']:raise ValueError('Returned full result differs')
    create(out/'SCORING_ROWS.json',endpoint.pop('scoring_rows'));create(out/'DECODED.json',endpoint.pop('decoded'))
    create(out/'COMPLETE_PROOF.json',{'utc':utc(),'passed':True,'job_sha256':digest(job),'training':trained,'endpoint':endpoint,'scoring_rows_sha256':sha(out/'SCORING_ROWS.json'),'private_binary_independently_reviewed':False,'original_scientific_functions_unchanged':True,'derived_resume_ledger_source_map':str(saved/'LEDGER_SOURCE_MAP.json'),'actual_A3_accepted':False})


def score(out,dispatch):
    cap=min(7200,int(remaining_window(dispatch,5)-5))
    intent=read(dispatch/'INTENT.json');key=intent['attempt_name'];a=LOCAL/'audit'/key;proof=read(a/'COMPLETE_PROOF.json')
    if proof['passed'] is not True or sha(a/'SCORING_ROWS.json')!=proof['scoring_rows_sha256']:raise ValueError('Full original state/native oracle first')
    rows=read(a/'SCORING_ROWS.json');binding={'job_sha256':digest(intent['job_spec']),'source_files':intent['source_files'],'oracle_sha256':sha(a/'COMPLETE_PROOF.json'),'source_review':intent['source_review'],'actual_review':intent['actual_review']}
    result=long_score_process.supervise_once(out/'owned_score',rows,binding,cap)
    verified=long_scoring.verify_saved_scores(out/'owned_score/payload',rows,binding,cap)
    create(out/'COMPLETED.json',{'utc':utc(),'result':result,'saved_score_proof':verified,'score_cap_seconds':cap,'absolute_closeout_deadline_not_reset':True,'actual_A3_accepted':False})


def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['upload','collect','audit','score']);p.add_argument('--source-review',required=True);p.add_argument('--actual-review',required=True);p.add_argument('--attempt-name');a=p.parse_args()
    spec=review(SPEC,a.source_review,a.actual_review)
    if a.mode!='upload' and not a.attempt_name:raise ValueError('Exact attempt name required')
    out=LOCAL/a.mode
    if a.attempt_name:out=out/a.attempt_name
    # Full parameter oracle concurrency is one on the local24GiB host.
    import fcntl
    LOCAL.mkdir(parents=True,exist_ok=True)
    with (LOCAL/'local_oracle.lock').open('a+') as lock:
        if a.mode=='audit':fcntl.flock(lock,fcntl.LOCK_EX)
        out.mkdir(parents=True,exist_ok=False);create(out/'ATTEMPT.json',{'utc':utc(),'mode':a.mode,'automatic_retry':False})
        try:
            if a.mode=='upload':transfer(spec,out)
            else:globals()[a.mode](out,LOCAL/'dispatch'/a.attempt_name)
        except BaseException as exc:create(out/'FAILED.json',{'utc':utc(),'type':type(exc).__name__,'message':str(exc),'automatic_retry':False});raise


if __name__=='__main__':main()

"""New3B transfer and exact complete-MATH scoped closeout, each fenced once."""
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
from experiments.p011 import long_owner_evidence as evidence,long_transport
from experiments.p011 import ext3b_math_scope as scope,ext3b_math_scoring as long_scoring,ext3b_math_score_process as long_score_process
from experiments.p011.long_d2_scope import training_view
from experiments.p011.c1_outer import closed_provider
from experiments.sft_allocation_midpoint.common import verify


def remaining_window(dispatch,required=0):
    intent=read(dispatch/'INTENT.json');saved=LOCAL/'collect'/intent['attempt_name']
    if (dispatch/'RESULT.json').exists():start=read(dispatch/'RESULT.json')['worker_start_epoch']
    elif (saved/'DERIVED_LEDGER_VIEW.json').exists():
        claim=read(saved/'DERIVED_LEDGER_VIEW.json')[intent['attempt_name']+'/claim']
        start=claim['worker_start_epoch'] if claim else intent['created_epoch']
    else:start=intent['created_epoch']  # Conservative before first original claim retrieval.
    policy=path.timing(intent['job_spec'],intent,start);left=policy['result_deadline_epoch']-time.time()
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


def failed_payload_once(volume,remote,out,final_step):
    """Single stream of original failed bytes; keep intermediate states remotely."""
    base=remote.removeprefix('/evidence').strip('/')
    def inventory():
        return sorted([{'path':x.path,'size':x.size,'type':int(x.type),'mtime':x.mtime} for x in volume.iterdir('/'+base,recursive=True)],key=lambda x:x['path'])
    before=inventory();create(out/'REMOTE_INVENTORY_BEFORE.json',before);members={};excluded=[]
    if sum(x['size'] for x in before if x['type']==1)>128*1024**3:raise ValueError('Unexpected original failed inventory size')
    payload=out/'payload';payload.mkdir(exist_ok=False)
    for item in before:
        if item['type']!=1:continue
        full=item['path'].lstrip('/')
        if not full.startswith(base+'/'):raise ValueError('Foreign inventory path')
        rel=Path(full[len(base)+1:])
        if rel.is_absolute() or '..' in rel.parts:raise ValueError('Unsafe preserved payload path')
        if rel.name=='evidence.tar' or (rel.parts[0].startswith('checkpoint_') and rel.parts[0]!=f'checkpoint_{final_step:04d}' and rel.name=='state.pt'):
            excluded.append(item);continue
        target=payload/rel;target.parent.mkdir(parents=True,exist_ok=True);h=hashlib.sha256();size=0
        with target.open('xb') as stream:
            for block in volume.read_file('/'+full):stream.write(block);h.update(block);size+=len(block)
        if size!=item['size']:raise ValueError('Preserved failed file size changed')
        members[str(rel)]={'bytes':size,'sha256':h.hexdigest()}
    after=inventory();create(out/'REMOTE_INVENTORY_AFTER.json',after)
    if before!=after:raise ValueError('Original failed inventory changed during preservation')
    create(out/'PRESERVED_FILES.json',{'files':members,'not_downloaded_still_remote':excluded,'original_failed_bytes_not_modified':True})
    return payload


def collect(out,dispatch):
    import modal
    remaining_window(dispatch)
    intent=read(dispatch/'INTENT.json');sub=read(dispatch/'SUBMITTED.json');job=intent['job_spec'];key=intent['attempt_name']
    receipt=read(dispatch/'RESULT.json') if (dispatch/'RESULT.json').exists() else None
    cli_exit=read(LOCAL/'cli'/key/'CLI_EXIT.json')
    if receipt:
        if receipt.get('status')!='completed' or receipt['job_sha256']!=digest(job) or receipt['app_id']!=sub['app_id'] or cli_exit['exit_code']!=0:raise ValueError('Original successful call/CLI mismatch')
    elif not (dispatch/'RETURN_ERROR.json').exists() or cli_exit['exit_code']==0:
        raise ValueError('Original terminal failed call and consumed CLI evidence required')
    cli='.local/midpoint_20261011/venv/bin/modal'
    info=json.loads(subprocess.check_output([cli,'app','info',sub['app_id'],'--json'],text=True,timeout=60));containers=json.loads(subprocess.check_output([cli,'container','list','--json'],text=True,timeout=60))
    stopped=closed_provider(sub['app_id'],info,containers,time.time());create(out/'PROVIDER_RAW.json',{'app':info,'containers':containers});create(out/'PROVIDER_STOPPED0.json',stopped)
    store=modal.Dict.from_name(STORE,create_if_missing=False);raw={};derived={};mapping={};resume=intent.get('resume')
    prefix=(job['U'] if resume.get('training_terminal_complete') else resume['checkpoint_record']['step']) if resume else 0
    evalprefix=set(resume.get('completed_endpoint_prefix',[])) if resume else set();parent=resume['parent_intent']['attempt_name'] if resume else None
    for wanted in scope.expected_record_keys(key,job['U']):
        suffix=wanted[len(key)+1:];parts=suffix.split('/');origin=wanted
        if len(parts)==2 and parent:
            unit=parts[1]
            if ((unit.startswith('update_') and int(unit.split('_')[1])<=prefix) or unit in evalprefix
                    or (resume.get('training_terminal_complete') and unit in ('terminal_state','terminal_model_export'))):origin=parent+'/'+suffix
        if origin not in raw:raw[origin]=store.get(origin)
        derived[wanted]=raw[origin];mapping[wanted]=origin
    for source in [key+'/dispatch']+([parent+'/dispatch',parent+'/terminal'] if parent else []):raw[source]=store.get(source)
    if raw[key+'/dispatch']!=intent or (receipt is not None and derived[key+'/terminal']!=receipt):raise ValueError('Original local/cloud dispatch or terminal differs')
    claim=derived[key+'/claim']
    if claim and (claim['app_id']!=sub['app_id'] or claim['dispatch_sha256']!=digest(intent)):raise ValueError('Original claim differs')
    create(out/'ACTUAL_NAMED_RECORDS.json',raw);create(out/'DERIVED_LEDGER_VIEW.json',derived);create(out/'LEDGER_SOURCE_MAP.json',mapping)
    create(out/'ORIGINAL_INTENT.json',intent);create(out/'ORIGINAL_CLI_EXIT.json',cli_exit)
    volume=modal.Volume.from_name('sft-allocation-midpoint-v1',create_if_missing=False)
    if receipt:
        create(out/'ORIGINAL_RESULT.json',receipt);file=out/'evidence.tar';h=hashlib.sha256();size=0
        with file.open('xb') as stream:
            for block in volume.read_file((REMOTE+'/runs/'+key+'/evidence.tar').removeprefix('/evidence')):stream.write(block);h.update(block);size+=len(block)
        if size!=receipt['artifact']['tar_bytes'] or h.hexdigest()!=receipt['artifact']['tar_sha256']:raise ValueError('Terminal archive partial or changed')
        result={'format':'original_terminal_archive','new_archive_sha256':h.hexdigest(),'receipt_sha256':sha(out/'ORIGINAL_RESULT.json')}
    else:
        create(out/'ORIGINAL_RETURN_ERROR.json',read(dispatch/'RETURN_ERROR.json'))
        if claim:failed_payload_once(volume,REMOTE+'/runs/'+key,out,job['U'])
        result={'format':'preserved_failed_payload' if claim else 'preclaim_failure_no_payload','failure_remains_failed':True,'complete_MATH_scope_requires_full_training_oracle':True}
    create(out/'COMPLETED.json',{'utc':utc(),**result,'original_worker_completed':receipt is not None,'actual_named_records':len(raw),'collection_completion_is_not_scientific_success':True})


def audit(out,dispatch):
    from transformers import AutoTokenizer
    remaining_window(dispatch)
    intent=read(dispatch/'INTENT.json');job=intent['job_spec'];key=intent['attempt_name'];saved=LOCAL/'collect'/key
    collected=read(saved/'COMPLETED.json');ledger=read(saved/'DERIVED_LEDGER_VIEW.json');mapping=read(saved/'LEDGER_SOURCE_MAP.json');raw=read(saved/'ACTUAL_NAMED_RECORDS.json')
    if any(ledger[k]!=raw[origin] for k,origin in mapping.items()) or raw[key+'/dispatch']!=intent:raise ValueError('Actual source mapping changed')
    claim=ledger[key+'/claim']
    if claim is None:raise ValueError('No claimed/trained state; no scientific oracle or score authorized')
    receipt=read(saved/'ORIGINAL_RESULT.json') if collected['original_worker_completed'] else None
    if receipt:
        long_transport.extract(saved/'evidence.tar',out/'payload',receipt['artifact'],64*1024**3);payload=out/'payload'
    else:payload=saved/'payload'
    identity=read(payload/'IDENTITY.json');timing=read(payload/'TIMING_POLICY.json')
    if identity!=intent['identity'] or read(payload/'CLAIM.json')!=claim or read(payload/'ADMISSION.json')!=intent or timing!=path.timing(job,intent,claim['worker_start_epoch']):raise ValueError('Scientific identity/admission/timing changed')
    attempts,done=scope.journals(payload,key,job['U'],ledger)
    verify(INPUTS,job['local_input_files']);model=Path(job['model']['local_path']);verify(model,job['model']['local_audit_asset_files']);config=read(model/'config.json')
    rows=EncodedRows(INPUTS/'ENCODED.jsonl',read(INPUTS/'ROW_METADATA.json'),job['questions']);plan=read(INPUTS/(job['logical_id']+'_PLAN.json'));rates=read(INPUTS/'RATES_S-F15.json')
    view=payload if (payload/'RESULT.json').exists() else training_view(payload,out/'DERIVED_TRAINING_ONLY_VIEW')
    trained=evidence.verify_training(view,rows,plan,rates,'S-F15',config,identity,attempts,done,timing)
    tok=AutoTokenizer.from_pretrained(model,local_files_only=True,trust_remote_code=False,use_fast=True)
    endpoint=scope.endpoint(payload,read(INPUTS/'ENDPOINT_LOCAL.json'),job['context'],job['eos_token_ids'],tok,config,attempts,done,timing,trained['training_seconds'])
    if receipt and (read(payload/'RESULT.json')!=receipt['result'] or endpoint['outputs_decoded']!=2500):raise ValueError('Returned full MATH result differs')
    create(out/'SCORING_ROWS.json',endpoint.pop('scoring_rows'));create(out/'DECODED.json',endpoint.pop('decoded'))
    create(out/'COMPLETE_PROOF.json',{'utc':utc(),'passed':True,'job_sha256':digest(job),'training':trained,'endpoint':endpoint,'scoring_rows_sha256':sha(out/'SCORING_ROWS.json'),'private_binary_independently_reviewed':False,'original_training_native_scalar_functions_unchanged':True,'derived_resume_ledger_source_map':str(saved/'LEDGER_SOURCE_MAP.json'),'original_worker_completed':collected['original_worker_completed'],'scoped_endpoint_completion_not_worker_success':True,'actual_A3_accepted':False})


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

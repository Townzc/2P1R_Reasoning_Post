"""One finite H100 attempt for two extension cells, after real source CR and actual A2-lite."""
from pathlib import Path
import json
import os
import signal
import subprocess
import time
import modal
from experiments.p011.owner_0205_common import create, read, sha, utc
from experiments.p011.forced_answer_ext3b import (admit, actual, SPEC, SCOPE, LOCAL, STORE, REMOTE, CELLS, checked_budget)
from experiments.p011.provider_slots import shared_slots

ROOT=Path(__file__).resolve().parents[2]
spec=read(ROOT/SPEC)
app=modal.App('p011-forced-answer-ext3b-20261022-v1')
volume=modal.Volume.from_name('sft-allocation-midpoint-v1',create_if_missing=False)
image=(modal.Image.debian_slim(python_version='3.12')
    .pip_install_from_requirements(ROOT/'experiments/learning_regime_p009/requirements_p0.txt')
    .env({'PYTHONPATH':'/workspace','HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1',
          'TOKENIZERS_PARALLELISM':'false','VLLM_USE_V1':'1'}))
for name in [*spec['source_files'],SPEC]:
    image=image.add_local_file(ROOT/name,'/workspace/'+name,copy=True)


@app.function(image=image,gpu='H100!',cpu=(4,4),memory=(32768,32768),timeout=10860,
    startup_timeout=600,retries=0,max_containers=1,min_containers=0,buffer_containers=0,
    scaledown_window=2,single_use_containers=True,include_source=False,volumes={'/evidence':volume})
def worker(intent):
    os.chdir('/workspace');started=time.time()
    store=modal.Dict.from_name(STORE,create_if_missing=False)
    store.put('imported',{'utc':utc(),'epoch':started,'module':__name__},skip_if_exists=True)
    if store.get('dispatch')!=intent or not store.put('claim',{'started_epoch':started,'intent':intent},skip_if_exists=True):
        raise ValueError('New forced-answer worker already claimed; no retry or resume')
    if checked_budget(intent['budget'],started)!=intent['budget_check']:
        raise ValueError('Fresh cost envelope differs at worker admission')
    for name,want in spec['source_files'].items():
        if sha(name)!=want:raise ValueError('Reviewed new source differs')
    volume.reload()
    if sha(Path(REMOTE)/'inputs/INPUT_MANIFEST.json')!=intent['input_manifest_sha256']:
        raise ValueError('Actual A2-lite input binding differs')
    deadline=started+intent['budget_check']['worker_hard_seconds']
    out=Path(REMOTE)/'run'
    if out.exists() or any((Path(REMOTE)/'results'/c).exists() for c in CELLS):
        raise ValueError('New task run/results must not exist')
    out.mkdir(parents=True,exist_ok=False)
    create(out/'ADMISSION.json',intent);volume.commit()
    completed=[]
    try:
        for cell in CELLS:
            remaining=deadline-time.time()
            if remaining<=0:raise TimeoutError('Shared hard timer reached before next cell')
            command=['python','-m','experiments.p011.forced_answer_ext3b_cell','--cell',cell,'--deadline',str(deadline)]
            proc=subprocess.Popen(command,start_new_session=True)
            try:
                code=proc.wait(timeout=remaining)
            except BaseException:
                if proc.poll() is None:os.killpg(proc.pid,signal.SIGKILL)
                proc.wait();raise
            volume.reload()
            if code!=0:raise RuntimeError(f'Cell {cell} exited {code}; completed cells retained, no retry')
            if store.get('cell/'+cell)['status']!='completed':raise ValueError('Missing durable cell completion')
            completed.append(cell)
        result={'status':'completed','cells':completed,'finished_utc':utc(),'worker_start_epoch':started}
        create(out/'COMPLETED.json',result);volume.commit();store.put('terminal',result,skip_if_exists=True)
        return result
    except BaseException as exc:
        result={'status':'failed','completed_cells':completed,'utc':utc(),'type':type(exc).__name__,'message':str(exc),'automatic_retry':False}
        create(out/'FAILED.json',result);volume.commit();store.put('terminal',result,skip_if_exists=True);raise


@app.local_entrypoint()
def main(review:str,budget_json:str):
    os.chdir(ROOT)
    routed=admit(SPEC,review,SCOPE)
    a2=actual(routed);budget=read(budget_json)
    for name,want in budget['evidence_files'].items():
        if sha(name)!=want:raise ValueError('Fresh budget evidence differs')
    checked=checked_budget(budget,time.time())
    upload=read(LOCAL/'upload/COMPLETED.json')
    if upload['input_manifest_sha256']!=a2['input_manifest_sha256']:
        raise ValueError('Exact new completed upload required')
    head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    remote=subprocess.check_output(['git','ls-remote','origin','refs/heads/codex/icml-acl-2027'],text=True).split()[0]
    if head!=remote:raise ValueError('Execution source not yet published')
    for name in [*spec['source_files'],SPEC]:
        if subprocess.check_output(['git','show',head+':'+name])!=Path(name).read_bytes():
            raise ValueError('Unpublished source/SPEC')
    cli='.local/midpoint_20261011/venv/bin/modal'
    apps=json.loads(subprocess.check_output([cli,'app','list','--json'],text=True,timeout=60))
    containers=json.loads(subprocess.check_output([cli,'container','list','--json'],text=True,timeout=60))
    slots=shared_slots(apps,containers)
    if slots>8:raise ValueError('Shared eight-slot ceiling exceeded including this pending app')
    create(LOCAL/'ONE_MODEL_ATTEMPT_FENCE.json',{'utc':utc(),'source_review_sha256':sha(review),'automatic_retry':False})
    out=LOCAL/'dispatch';out.mkdir(parents=True,exist_ok=False)
    store=modal.Dict.from_name(STORE,create_if_missing=True)
    intent={'execution':head,'app_id':app.app_id,'created_epoch':time.time(),
        'source_CR':read(review),'actual_A2':a2,'provider_slots_at_entry':slots,
        'upload_sha256':sha(LOCAL/'upload/COMPLETED.json'),
        'input_manifest_sha256':a2['input_manifest_sha256'],
        'budget':budget,'budget_check':checked,'automatic_retry':False}
    create(out/'INTENT.json',intent)
    if not store.put('dispatch',intent,skip_if_exists=True):raise ValueError('Permanent task dispatch fence exists')
    call=worker.with_options(timeout=checked['worker_hard_seconds']+60).spawn(intent)
    create(out/'SUBMITTED.json',{'app_id':app.app_id,'call_id':call.object_id,'utc':utc()})
    try:create(out/'RESULT.json',call.get())
    except BaseException as exc:
        create(out/'RETURN_ERROR.json',{'type':type(exc).__name__,'message':str(exc),'utc':utc(),'automatic_retry':False});raise

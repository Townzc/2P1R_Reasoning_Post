"""Bounded ephemeral Modal model jobs, atomically admitted once per immutable slot."""
import json
from pathlib import Path
import subprocess
import time
import modal

ROOT=Path(__file__).resolve().parents[2]
SOURCE_FILES=[
    'src/sft_data.py','src/real_math_audit.py',
    'analyses/completion_contract.py','analyses/gsm8k_answer_audit.py',
    'analyses/e017_stopping.py','analyses/e017_audit.py',
    *['experiments/sft_allocation_midpoint/'+n for n in ('guard.py','common.py','checkpoint.py','runtime.py','modal_runner.py')],
    'requirements.txt','configs/models.lock.json']
app=modal.App('sft-allocation-midpoint-models')
volume=modal.Volume.from_name('sft-allocation-midpoint-v1',create_if_missing=False)
image=(modal.Image.debian_slim(python_version='3.12')
       .pip_install('torch==2.8.0',index_url='https://download.pytorch.org/whl/cu128')
       .pip_install_from_requirements(ROOT/'requirements.txt')
       .pip_install('peft==0.17.1')
       .env({'PYTHONPATH':'/workspace','CUBLAS_WORKSPACE_CONFIG':':4096:8',
             'TOKENIZERS_PARALLELISM':'false','HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1'}))
for name in SOURCE_FILES:image=image.add_local_file(ROOT/name,'/workspace/'+name,copy=True)
OPTIONS=dict(image=image,cpu=(4,4),memory=(32768,32768),timeout=7200,startup_timeout=600,
             retries=0,max_containers=2,min_containers=0,buffer_containers=0,scaledown_window=2,
             single_use_containers=True,serialized=True,include_source=False,volumes={'/evidence':volume})


@app.function(gpu='A100-80GB',**OPTIONS)
def run_gpu(plan,config,release):
    import os,sys,threading,uuid,traceback
    sys.path.insert(0,'/workspace')
    from experiments.sft_allocation_midpoint.common import dump,digest,sha,manifest,verify,read
    from experiments.sft_allocation_midpoint.guard import RunGuard
    from experiments.sft_allocation_midpoint import runtime
    # Construct lazy network handles inside the worker, not in serialized globals.
    claims=modal.Dict.from_name('sft-allocation-midpoint-claims-v1',create_if_missing=False)
    for name,expected in release['source_files'].items():
        if sha(Path('/workspace')/name)!=expected:raise ValueError('Published image source differs')
    guard=RunGuard(claims,plan);guard.register(now_epoch=time.time())
    seconds=config['max_seconds']
    if not 60<=seconds<=6600:raise ValueError('Invalid finite job duration')
    admission=guard.admit(dict(run_id=config['run_id'],config_sha256=digest(config),
        source_sha256=digest(release['source_files']),data_sha256=config['input_sha256']),
        attempt_id=uuid.uuid4().hex,now_epoch=time.time(),max_runtime_seconds=seconds+60)
    started=time.time();stop_at=min(started+seconds,plan['deadline_epoch']-30)
    timer=threading.Timer(max(1,stop_at-time.time()),lambda:os._exit(124));timer.daemon=True;timer.start()
    out=Path('/evidence')/plan['campaign_id']/config['run_id']
    reserve=plan['slots'][config['run_id']]['reserved_cents']
    # Reserve includes 600s startup and host resources, rather than model time alone.
    if reserve<math_cost_cents(seconds+600):raise ValueError('Insufficient conservative GPU reservation')
    def check():
        if time.time()>stop_at-30:raise TimeoutError('Finite work deadline; preserve closeout time')
        guard.check_active(admission,now_epoch=time.time(),spent_cents=0,next_cost_cents=reserve)
    try:
        volume.reload();out.mkdir(parents=True,exist_ok=False)
        dump(out/'intent.json',dict(config=config,release=release,plan=plan,started_epoch=started,
                                    reserved_cents=reserve))
        assets=Path('/evidence')/config['asset_campaign']/'assets'
        if sha(assets/'inputs/manifest.json')!=config['input_sha256']:raise ValueError('Input release differs')
        verify(assets,read(assets/'result.json')['files'])
        dump(out/'environment.json',runtime.environment());volume.commit()
        identity=dict(config=config,source_commit=release['commit'],source_sha256=digest(release['source_files']))
        journal=runtime.Journal(out,'midpoint/'+plan['campaign_id']+'/'+config['run_id'],claims,volume.commit,check)
        kind=config['kind']
        if kind=='engineering':result=runtime.engineering(assets,out,journal,identity)
        elif kind=='resume':
            profile=Path('/evidence')/config['profile_campaign']/'profile'
            result=runtime.resume_probe(assets,profile,out,journal,identity)
        elif kind=='main':
            if config['arm'] not in ('repeat','solutions','mixed','breadth') or config['seed'] not in (17,23):
                raise ValueError('Unapproved arm or seed')
            gates=Path('/evidence')/config['profile_campaign']
            if not read(gates/'profile/result.json')['engineering_fit_gate'] or not read(gates/'resume/result.json')['recovery_gate']:
                raise ValueError('Engineering admission gates not passed')
            result=runtime.main_train(assets,out,journal,identity,config['arm'],config['seed'])
        elif kind=='base':
            model,tok=runtime.new_model(assets/'model',17,adapt=False)
            result=dict(status='completed',committed_updates=0,physical_generated_outputs=431,
                endpoint=runtime.evaluate(model,tok,runtime.read_jsonl(assets/'inputs/endpoint431.jsonl'),out,'endpoint431',journal))
        else:raise ValueError('Unapproved kind')
        result.update(wall_seconds=time.time()-started,reserved_cost_usd=reserve/100,provider_invoice_usd=None,
                      runtime_rate_estimate_usd=(time.time()-started)*2.942784/3600)
        dump(out/'result.json',result);volume.commit()
        files=manifest(out);dump(out/'artifact_manifest.json',files);volume.commit()
        receipt=guard.finish(admission,status='completed',evidence_sha256=digest(files),
                             actual_cost_cents=reserve,finished_epoch=time.time())
        return dict(result=result,artifact_manifest=files,receipt=receipt)
    except BaseException as exc:
        if out.exists():
            failure=dict(status='failed',error=repr(exc),traceback=traceback.format_exc(),wall_seconds=time.time()-started,
                         instruction='Preserve completed, attempted and ambiguous work. Reconcile before any continuation.')
            dump(out/'failure.json',failure);volume.commit()
            files=manifest(out);dump(out/'failure_manifest.json',files);volume.commit()
            guard.finish(admission,status='failed',evidence_sha256=digest(files),actual_cost_cents=reserve,finished_epoch=time.time())
        raise
    finally:timer.cancel()


def math_cost_cents(seconds):
    import math
    return math.ceil(seconds*2.942784/36)+25


@app.function(image=image,cpu=(2,2),memory=(8192,8192),timeout=900,startup_timeout=300,
              retries=0,max_containers=1,min_containers=0,buffer_containers=0,scaledown_window=2,
              single_use_containers=True,serialized=True,include_source=False,volumes={'/evidence':volume})
def audit(plan,config,release):
    import sys,uuid
    sys.path.insert(0,'/workspace')
    from experiments.sft_allocation_midpoint.common import read,verify,digest,sha,dump
    from experiments.sft_allocation_midpoint.guard import RunGuard
    claims=modal.Dict.from_name('sft-allocation-midpoint-claims-v1',create_if_missing=False)
    guard=RunGuard(claims,plan);guard.register(now_epoch=time.time())
    admission=guard.admit(dict(run_id='audit',config_sha256=digest(config),source_sha256=digest(release['source_files']),
        data_sha256=config['input_sha256']),attempt_id=uuid.uuid4().hex,now_epoch=time.time(),max_runtime_seconds=840)
    volume.reload();root=Path('/evidence')/plan['campaign_id'];results={}
    for name in ('profile','resume'):
        directory=root/name;files=read(directory/'artifact_manifest.json');verify(directory,files)
        results[name]=dict(files_verified=len(files),manifest_sha256=sha(directory/'artifact_manifest.json'),
            checkpoints={str(p.parent.name):read(p) for p in directory.glob('checkpoint_*/manifest.json')},
            result=read(directory/'result.json'))
    dump(root/'audit.json',results);volume.commit()
    receipt=guard.finish(admission,status='completed',evidence_sha256=digest(results),actual_cost_cents=100,finished_epoch=time.time())
    return dict(results=results,receipt=receipt)


@app.local_entrypoint()
def main(plan_json:str,config_json:str,receipt_dir:str):
    from experiments.sft_allocation_midpoint.common import sha,dump
    plan=json.loads(Path(plan_json).read_text());config=json.loads(Path(config_json).read_text());out=Path(receipt_dir)
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    remote=subprocess.check_output(['git','ls-remote','origin','refs/heads/codex/icml-acl-2027'],cwd=ROOT,text=True).split()[0]
    if commit!=remote:raise ValueError('Publish source on assigned branch before execution')
    for name in SOURCE_FILES:
        if subprocess.check_output(['git','show','HEAD:'+name],cwd=ROOT)!=(ROOT/name).read_bytes():
            raise ValueError('Source differs from published commit: '+name)
    release=dict(commit=commit,source_files={name:sha(ROOT/name) for name in SOURCE_FILES})
    out.mkdir(parents=True,exist_ok=False);dump(out/'intent.json',dict(plan=plan,config=config,release=release))
    try:
        result=audit.remote(plan,config,release) if config['kind']=='audit' else run_gpu.remote(plan,config,release)
        dump(out/'result.json',result)
    finally:
        claims=modal.Dict.from_name('sft-allocation-midpoint-claims-v1',create_if_missing=False)
        prefix='midpoint/'+plan['campaign_id']+'/'
        dump(out/'admission_ledger.json',{k:v for k,v in claims.items() if k.startswith(prefix)})

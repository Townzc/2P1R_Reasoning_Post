"""One bounded CPU-only fetch of the locked base and upload of verified inputs."""
import hashlib
import json
from pathlib import Path
import subprocess
import time
import modal

ROOT=Path(__file__).resolve().parents[2]
app=modal.App('sft-allocation-midpoint-assets')
volume=modal.Volume.from_name('sft-allocation-midpoint-v1',create_if_missing=False)
image=modal.Image.debian_slim(python_version='3.12').pip_install('requests==2.31.0')
for name in ('guard.py','common.py'):
    image=image.add_local_file(ROOT/'experiments/sft_allocation_midpoint'/name, '/opt/midpoint/'+name,copy=True)


@app.function(image=image,cpu=(2,2),memory=(4096,4096),timeout=900,startup_timeout=300,
              retries=0,max_containers=1,min_containers=0,buffer_containers=0,
              scaledown_window=2,single_use_containers=True,serialized=True,include_source=False,
              volumes={'/evidence':volume})
def fetch(plan, source, lock, payload, input_hash):
    import os, sys, threading, requests
    sys.path.insert(0,'/opt/midpoint')
    from guard import RunGuard,identity_hash
    from common import dump,sha,verify,manifest
    claims=modal.Dict.from_name('sft-allocation-midpoint-claims-v1',create_if_missing=False)
    guard=RunGuard(claims,plan); guard.register(now_epoch=time.time())
    intent=dict(run_id='assets',config_sha256=identity_hash(lock),source_sha256=source,data_sha256=input_hash)
    admission=guard.admit(intent,attempt_id='original',now_epoch=time.time(),max_runtime_seconds=840)
    timer=threading.Timer(850,lambda:os._exit(124));timer.daemon=True;timer.start()
    out=Path('/evidence')/plan['campaign_id']/'assets';out.mkdir(parents=True,exist_ok=False)
    started=time.time()
    try:
        dump(out/'intent.json',dict(intent=intent,plan=plan,started_epoch=started))
        inputs=out/'inputs';inputs.mkdir()
        for name,data in payload.items():
            if Path(name).name!=name:raise ValueError('Unsafe input filename')
            with (inputs/name).open('xb') as f:f.write(data)
        if sha(inputs/'manifest.json')!=input_hash:raise ValueError('Input manifest hash differs')
        mf=json.loads((inputs/'manifest.json').read_text());verify(inputs,mf['files'])
        model=out/'model';model.mkdir()
        for r in lock['files']:
            guard.check_active(admission,now_epoch=time.time(),spent_cents=0,next_cost_cents=100)
            name=r['rfilename'];target=model/name
            url=f"https://huggingface.co/{lock['repo_id']}/resolve/{lock['revision']}/{name}"
            with requests.get(url,stream=True,timeout=(20,60)) as response:
                response.raise_for_status()
                with target.open('xb') as f:
                    for block in response.iter_content(2**20):
                        if time.time()-started>780:raise TimeoutError('CPU asset deadline')
                        f.write(block)
                    f.flush();os.fsync(f.fileno())
            if target.stat().st_size!=r['size']:raise ValueError('Source size differs: '+name)
            if 'lfs' in r:
                if sha(target)!=r['lfs']['sha256']:raise ValueError('Locked weight hash differs')
            else:
                raw=target.read_bytes();gitsha=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
                if gitsha!=r['blobId']:raise ValueError('Locked Git blob differs: '+name)
            print(json.dumps({'verified_asset':name,'bytes':target.stat().st_size}),flush=True)
        result=dict(status='completed',files=manifest(out),seconds=time.time()-started,model_revision=lock['revision'],
                    new_model_calls=0,reserved_cost_usd=1,provider_invoice_usd=None)
        dump(out/'result.json',result);volume.commit()
        guard.finish(admission,status='completed',evidence_sha256=identity_hash(result),
                     actual_cost_cents=100,finished_epoch=time.time())
        return result
    except BaseException as exc:
        failure=dict(status='failed',error=repr(exc),seconds=time.time()-started,new_model_calls=0)
        dump(out/'failure.json',failure);volume.commit()
        guard.finish(admission,status='failed',evidence_sha256=identity_hash(failure),
                     actual_cost_cents=100,finished_epoch=time.time())
        raise
    finally:timer.cancel()


@app.local_entrypoint()
def main(plan_json:str,inputs_dir:str,receipt_dir:str):
    from experiments.sft_allocation_midpoint.common import sha,dump,digest
    plan=json.loads(Path(plan_json).read_text());inputs=Path(inputs_dir);out=Path(receipt_dir)
    if plan['slots'].get('assets')!={'stage':'engineering','reserved_cents':100}:
        raise ValueError('Exact one-dollar CPU reservation required')
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    remote=subprocess.check_output(['git','ls-remote','origin','refs/heads/codex/icml-acl-2027'],cwd=ROOT,text=True).split()[0]
    files=['experiments/sft_allocation_midpoint/'+name for name in ('guard.py','common.py','modal_assets.py')]
    files+=['configs/models.lock.json']
    if commit!=remote:raise ValueError('Publish first')
    for name in files:
        if subprocess.check_output(['git','show','HEAD:'+name],cwd=ROOT)!=(ROOT/name).read_bytes():
            raise ValueError('Published source differs')
    source={name:sha(ROOT/name) for name in files};payload={p.name:p.read_bytes() for p in inputs.iterdir() if p.is_file()}
    out.mkdir(parents=True,exist_ok=False)
    dump(out/'intent.json',dict(plan=plan,source=source,commit=commit,input_sha256=sha(inputs/'manifest.json')))
    result=fetch.remote(plan,digest(source),json.loads((ROOT/'configs/models.lock.json').read_text())['main'],payload,sha(inputs/'manifest.json'))
    dump(out/'result.json',result)

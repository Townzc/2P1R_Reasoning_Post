"""Bounded CPU-only download of two pinned public teacher models; no inference."""
from pathlib import Path
import modal
from experiments.p010.common import MODELS

ROOT=Path(__file__).resolve().parents[2]
app=modal.App('p010-pinned-teacher-assets')
volume=modal.Volume.from_name('sft-allocation-midpoint-v1',create_if_missing=False)
image=(modal.Image.debian_slim(python_version='3.12')
    .pip_install('huggingface-hub==0.34.4','hf-xet==1.1.10')
    .env({'HF_HUB_DISABLE_PROGRESS_BARS':'1','PYTHONPATH':'/workspace'}))
for name in ('experiments/__init__.py','experiments/p010/__init__.py',
    'experiments/p010/common.py','experiments/sft_allocation_midpoint/__init__.py',
    'experiments/sft_allocation_midpoint/common.py'):
    image = image.add_local_file(ROOT/name,'/workspace/'+name,copy=True)


@app.function(image=image,cpu=(2,2),memory=(8192,8192),timeout=3600,startup_timeout=600,
    retries=0,max_containers=2,min_containers=0,scaledown_window=2,
    serialized=True,include_source=False,single_use_containers=True,volumes={'/evidence':volume})
def download(model,descriptor,execution_commit):
    import hashlib,json,time
    from huggingface_hub import snapshot_download,HfApi
    from pathlib import Path
    start=time.time()
    store=modal.Dict.from_name('p010-once-20261019',create_if_missing=True)
    if model not in ('t7','t72') or not store.put('assets/'+model,
        {'model':descriptor,'commit':execution_commit},skip_if_exists=True):
        raise ValueError('Unknown model or already attempted cache job; no whole-job retry')
    root=Path('/evidence/p010-20261019/assets')/model
    volume.reload();root.mkdir(parents=True,exist_ok=False)
    try:
        # Hash every downloaded shard against the fixed Hub LFS identity.
        info=HfApi().model_info(descriptor[0],revision=descriptor[1],files_metadata=True)
        if info.sha!=descriptor[1]:raise ValueError('Pinned revision differs')
        snapshot_download(descriptor[0],revision=descriptor[1],local_dir=root,
            allow_patterns=['*.safetensors','*.json','*.txt','*.model'],max_workers=8)
        files={}
        for f in sorted(root.iterdir()):
            if not f.is_file():continue
            h=hashlib.sha256()
            with f.open('rb') as stream:
                for block in iter(lambda:stream.read(8*1024**2),b''):h.update(block)
            files[f.name]={'bytes':f.stat().st_size,'sha256':h.hexdigest()}
        expected = [f for f in info.siblings if f.rfilename.endswith(('.safetensors','.json','.txt','.model'))]
        if not expected or not any(f.rfilename.endswith('.safetensors') for f in expected):
            raise ValueError('Empty model inventory')
        for f in expected:
            if f.rfilename not in files or files[f.rfilename]['bytes'] != f.size:
                raise ValueError('Missing or incomplete pinned model file: '+f.rfilename)
            if f.lfs and files[f.rfilename]['sha256']!=f.lfs.sha256:
                raise ValueError('Original shard SHA differs: '+f.rfilename)
        result={'model':descriptor,'files':files,'seconds':time.time()-start,
            'new_model_generations':0,'execution_commit':execution_commit}
        with (root/'DOWNLOAD_VERIFIED.json').open('x') as stream:json.dump(result,stream,indent=2)
        volume.commit();return result
    except BaseException as exc:
        with (root/'DOWNLOAD_FAILED.json').open('x') as stream:json.dump({'type':type(exc).__name__,'error':str(exc)},stream)
        volume.commit();raise


@app.local_entrypoint()
def main(model:str,receipt_dir:str):
    import time
    from experiments.p010.common import dump,require_published,budget_check
    if model != 't72':raise ValueError('T7 original call already submitted; only T72 is unused')
    out=Path(receipt_dir);out.mkdir(parents=True,exist_ok=False)
    commit=require_published(ROOT)
    budget=budget_check('G',0 if model=='t7' else '.5','.5','.2')
    dump(out/'INTENT.json',dict(model=model,revision=MODELS[model],budget=budget,
        cpu_only=True,max_seconds=3600,execution_commit=commit,epoch=time.time()))
    call=download.spawn(model,list(MODELS[model]),commit)
    dump(out/'SUBMITTED.json',dict(app_id=app.app_id,call_id=call.object_id,model=model))
    try:dump(out/'RESULT.json',call.get())
    except BaseException as exc:
        dump(out/'ERROR.json',dict(type=type(exc).__name__,error=str(exc)));raise

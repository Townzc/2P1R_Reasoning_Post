"""Seven direct-owner jobs spawn before waiting; immutable scientific workers."""
from pathlib import Path
import concurrent.futures
import json
import subprocess
import time
import modal
from experiments.p011 import long_owner_post_retry_optional_path as path
from experiments.sft_allocation_midpoint.common import read
ROOT=Path(__file__).resolve().parents[2]
spec=path.validate(read(ROOT/path.SPEC))
app=modal.App('p011-owner150-optional')
volume=modal.Volume.from_name('sft-allocation-midpoint-v1',create_if_missing=False)
image=(modal.Image.debian_slim(python_version='3.12')
    .pip_install_from_requirements(ROOT/'experiments/learning_regime_p009/requirements_p0.txt')
    .env({'PYTHONPATH':'/workspace','HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1',
          'TOKENIZERS_PARALLELISM':'false','CUBLAS_WORKSPACE_CONFIG':':4096:8','VLLM_USE_V1':'1'}))
for n in [*spec['source_files'],path.SPEC,path.DECISION,path.ORIGINAL_SPEC]:
    image=image.add_local_file(ROOT/n,'/workspace/'+n,copy=True)

def make_worker(job_id):
    job=spec['jobs'][job_id];limits=job['limits'];resources=job['resources']
    @app.function(name=job_id,image=image,gpu='H100!',cpu=(4,4),memory=(resources['memory_mib'],resources['memory_mib']),
        timeout=limits['platform_seconds'],startup_timeout=limits['startup_seconds'],retries=0,
        max_containers=1,min_containers=0,buffer_containers=0,scaledown_window=2,
        single_use_containers=True,serialized=True,include_source=False,volumes={'/evidence':volume})
    def worker(intent,raw_report):
        import os,threading
        from experiments.p011 import long_owner_path as run
        if intent['job_id']!=job_id:raise ValueError('Wrong scientific worker')
        def timer(seconds):
            def stop():
                try:run.terminate_owned_descendants(os.getpid())
                finally:os._exit(124)
            t=threading.Timer(seconds,stop);t.daemon=True;t.start();return t
        store=modal.Dict.from_name(run.STORE,create_if_missing=False)
        return run.worker_body(read(Path('/workspace')/run.SPEC),Path('/workspace')/run.SPEC,'/workspace',intent,raw_report,store,volume,timer)
    return worker

workers={n:make_worker(n) for n,j in spec['jobs'].items() if j['cell'] in ('A4','A3','A2','A8')}

@app.local_entrypoint()
def main(review_json:str,budget_json:str,jobs:str):
    names=jobs.split(',')
    if any(n not in workers for n in names):raise ValueError('Only owner optional jobs')
    if not names or len(names)>8 or len(set(names))!=len(names):raise ValueError('At most eight distinct jobs')
    store=modal.Dict.from_name(path.STORE,create_if_missing=False)
    cli=str(ROOT/'.local/midpoint_20261011/venv/bin/modal')
    containers=json.loads(subprocess.check_output([cli,'container','list','--json'],text=True,timeout=60))
    observed=time.time()
    def observation(root,records):
        if time.time()-observed>120:raise ValueError('Entry container snapshot stale')
        return dict(containers=containers,states={app.app_id:'running'},observed_epoch=observed)
    calls=[]
    for name in names:
        calls.append(path.submit(ROOT,spec,name,review_json,budget_json,None,store,workers[name],app.app_id,observation=observation))
        print('SUBMITTED',name,flush=True)
    errors=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(calls)) as pool:
        futures={pool.submit(path.await_original,call,out):out.name for call,out in calls}
        for f in concurrent.futures.as_completed(futures):
            try:f.result();print('COMPLETED',futures[f],flush=True)
            except BaseException as exc:errors.append((futures[f],str(exc)));print('FAILED',futures[f],str(exc),flush=True)
    if errors:raise RuntimeError(str(errors))

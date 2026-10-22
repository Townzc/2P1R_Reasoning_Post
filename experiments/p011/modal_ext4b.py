"""One separately stopped app per cell/attempt, so the pair can run concurrently."""
from pathlib import Path
if __name__ == 'modal_ext4b':
    raise RuntimeError('Use modal run -m experiments.p011.modal_ext4b; filename entry is unsupported')
import modal
from experiments.p011 import ext4b_path as path
from experiments.p011.owner_0205_common import read
ROOT=Path(__file__).resolve().parents[2]
spec=read(ROOT/path.SPEC)
app=modal.App('p011-ext4B-two-cells')
volume=modal.Volume.from_name('sft-allocation-midpoint-v1',create_if_missing=False)
image=(modal.Image.debian_slim(python_version='3.12')
    .pip_install_from_requirements(ROOT/'experiments/learning_regime_p009/requirements_p0.txt')
    .env({'PYTHONPATH':'/workspace','HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1','TOKENIZERS_PARALLELISM':'false','CUBLAS_WORKSPACE_CONFIG':':4096:8','VLLM_USE_V1':'1'}))
for n in [*spec['source_files'],path.SPEC]:image=image.add_local_file(ROOT/n,'/workspace/'+n,copy=True)


@app.function(image=image,gpu='H100!',cpu=(4,4),memory=(98304,98304),timeout=50460,startup_timeout=600,
    retries=0,max_containers=1,min_containers=0,buffer_containers=0,scaledown_window=2,
    single_use_containers=True,serialized=True,include_source=False,volumes={'/evidence':volume})
def worker(intent):
    import os,threading
    os.chdir('/workspace')
    def timer(seconds):
        def stop():
            try:path.terminate_owned_descendants(os.getpid())
            finally:os._exit(124)
        t=threading.Timer(seconds,stop);t.daemon=True;t.start();return t
    store=modal.Dict.from_name(path.STORE,create_if_missing=False)
    return path.worker_body(intent,store,volume,timer)


@app.local_entrypoint()
def main(job:str,source_review:str,actual_review:str,budget_json:str,attempt:int=1,resume_json:str=''):
    import os
    os.chdir(ROOT)
    store=modal.Dict.from_name(path.STORE,create_if_missing=False)
    path.submit(ROOT,job,attempt,source_review,actual_review,budget_json,store,worker,app.app_id,resume_json or None)

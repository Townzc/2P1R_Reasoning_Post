"""Retained B1/B3 entry; absent exact actual-input SPEC fails before Modal work."""
from pathlib import Path
import os
import modal
from experiments.p011 import b_students_post_long_failure_path as path
from experiments.sft_allocation_midpoint.common import read
ROOT=Path(__file__).resolve().parents[2]
phase=os.environ.get('P011_B_PHASE')
if phase not in path.SPEC_FILES:raise ValueError('Explicit student immutable SPEC phase required')
spec=path.validate(read(ROOT/path.SPEC_FILES[phase]))
if spec['phase']!=phase:raise ValueError('Immutable B SPEC phase differs')
app=modal.App('p011-B-students-post-long-failure')
volume=modal.Volume.from_name('sft-allocation-midpoint-v1',create_if_missing=False)
image=(modal.Image.debian_slim(python_version='3.12')
    .pip_install_from_requirements(ROOT/'experiments/learning_regime_p009/requirements_p0.txt')
    .env({'PYTHONPATH':'/workspace','HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1',
          'TOKENIZERS_PARALLELISM':'false','CUBLAS_WORKSPACE_CONFIG':':4096:8','VLLM_USE_V1':'1'}))
for n in [*spec['source_files'],path.spec_path(spec)]:image=image.add_local_file(ROOT/n,'/workspace/'+n,copy=True)
# Each function has its own exact spec-bound billed window. All still share the
# one local dispatch lock, permanent ledger and four-slot provider accounting.
def make_worker(job_id):
    limits=spec['jobs'][job_id]['limits']
    @app.function(name=job_id,image=image,gpu='H100!',cpu=(4,4),memory=(32768,32768),
        timeout=limits['platform_seconds'],startup_timeout=limits['startup_seconds'],
        retries=0,max_containers=4,min_containers=0,buffer_containers=0,
        scaledown_window=2,single_use_containers=True,serialized=True,include_source=False,
        volumes={'/evidence':volume})
    def worker(intent,raw_report):
        import os,threading
        from experiments.p011 import b_students_post_long_failure_path as run
        if intent['job_id']!=job_id:raise ValueError('Function/job configuration mismatch')
        def timer(seconds):
            def hard_stop():
                try:run.terminate_owned_descendants(os.getpid())
                finally:os._exit(124)
            t=threading.Timer(seconds,hard_stop);t.daemon=True;t.start();return t
        store=modal.Dict.from_name(run.STORE,create_if_missing=False)
        p=Path('/workspace')/run.SPEC_FILES[phase]
        return run.worker_body(read(p),p,'/workspace',intent,raw_report,store,volume,timer)
    return worker
workers={name:make_worker(name) for name in spec['jobs']}

@app.local_entrypoint()
def main(job_id:str,review_json:str,budget_json:str):
    store=modal.Dict.from_name(path.STORE,create_if_missing=False)
    return path.submit(ROOT,spec,job_id,review_json,budget_json,store,workers[job_id],app.app_id)

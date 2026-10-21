"""Future C1 full entry. No actual SPEC exists yet: importing fails closed.

The whole-path CR, actual input A1 and numerical timing review must precede
any invocation. Synthetic draft test values are never an actual runtime spec.
"""
from pathlib import Path
import modal
from experiments.p011 import c1_outer, c1_execution
from experiments.sft_allocation_midpoint.common import read

ROOT = Path(__file__).resolve().parents[2]
spec = read(ROOT/c1_outer.SPEC)
c1_execution.validate_spec(spec)
app = modal.App('p011-c1-original-token-base-forward')
volume = modal.Volume.from_name('sft-allocation-midpoint-v1', create_if_missing=False)
image = (modal.Image.debian_slim(python_version='3.12')
    .pip_install_from_requirements(ROOT/'experiments/learning_regime_p009/requirements_p0.txt')
    .env({'PYTHONPATH': '/workspace', 'HF_HUB_OFFLINE': '1',
          'TRANSFORMERS_OFFLINE': '1', 'TOKENIZERS_PARALLELISM': 'false',
          'CUBLAS_WORKSPACE_CONFIG': ':4096:8'}))
for name in [*spec['source_files'], c1_outer.SPEC]:
    image = image.add_local_file(ROOT/name, '/workspace/'+name, copy=True)


@app.function(image=image, gpu='H100!', cpu=(4, 4), memory=(32768, 32768),
    timeout=spec['limits']['platform_seconds'], startup_timeout=spec['limits']['startup_seconds'],
    retries=0, max_containers=4, min_containers=0, buffer_containers=0,
    scaledown_window=2, single_use_containers=True, serialized=True,
    include_source=False, volumes={'/evidence': volume})
def worker(intent, raw_report):
    import os
    import threading
    from experiments.p011 import c1_outer as outer
    from experiments.sft_allocation_midpoint.common import read as load
    def timer(seconds):
        value = threading.Timer(seconds, lambda: os._exit(124))
        value.daemon = True
        value.start()
        return value
    store = modal.Dict.from_name(outer.STORE, create_if_missing=False)
    path = Path('/workspace')/outer.SPEC
    return outer.worker_body(load(path), path, '/workspace', intent, raw_report, store, volume, timer)


@app.local_entrypoint()
def main(review_json: str, budget_json: str):
    # Store exists only after a separately reviewed, one-time input upload.
    store = modal.Dict.from_name(c1_outer.STORE, create_if_missing=False)
    c1_outer.submit(ROOT, spec, ROOT/c1_outer.SPEC, review_json, budget_json,
        store, worker, app.app_id)

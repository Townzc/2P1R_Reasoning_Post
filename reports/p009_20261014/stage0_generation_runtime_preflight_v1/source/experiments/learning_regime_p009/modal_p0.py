"""Single-use P009 P0. Importing this module does not admit or run a job."""
from pathlib import Path
import subprocess
import sys
import modal
from experiments.learning_regime_p009.p0_contract import (
    WORKER_SECONDS, PLATFORM_SECONDS, STARTUP_SECONDS, FULL_WINDOW,
    RESERVED_CENTS, validate_release)

ROOT = Path(__file__).resolve().parents[2]
SPEC = 'reports/p009_20261014/p0_runtime_preflight_v1/ADMISSION.json'
SOURCES = [
    'experiments/learning_regime_p009/__init__.py',
    'experiments/learning_regime_p009/gates.py',
    'experiments/learning_regime_p009/p0_contract.py',
    'experiments/learning_regime_p009/p0_engine.py',
    'experiments/learning_regime_p009/p0_runtime.py',
    'experiments/learning_regime_p009/modal_p0.py',
    'experiments/sft_allocation_midpoint/common.py',
    'experiments/sft_allocation_midpoint/guard.py',
    'experiments/sft_allocation_midpoint/checkpoint.py',
    'experiments/sft_allocation_p008/evidence_bundle.py',
    'experiments/sft_allocation_p008/student_concurrency.py',
    'experiments/sft_allocation_p008/provider_release.py',
    'analyses/completion_contract.py', 'analyses/gsm8k_answer_audit.py',
    'src/__init__.py', 'src/real_math_audit.py',
    'scripts/audit_p009_p0.py', 'scripts/p009_p0_io.py',
    'experiments/learning_regime_p009/requirements_p0.txt',
]
app = modal.App('p009-p0-vllm-parity')
volume = modal.Volume.from_name('sft-allocation-midpoint-v1', create_if_missing=False)
image = (modal.Image.debian_slim(python_version='3.12')
    .pip_install_from_requirements(ROOT/'experiments/learning_regime_p009/requirements_p0.txt')
    .env({'PYTHONPATH':'/workspace', 'HF_HUB_OFFLINE':'1', 'TRANSFORMERS_OFFLINE':'1',
          'TOKENIZERS_PARALLELISM':'false', 'VLLM_WORKER_MULTIPROC_METHOD':'spawn'}))
for name in SOURCES:
    image = image.add_local_file(ROOT/name, '/workspace/'+name, copy=True)
image = image.add_local_file(ROOT/SPEC, '/workspace/'+SPEC, copy=True)


@app.function(image=image, gpu='H100!', cpu=(4,4), memory=(32768,32768),
    timeout=PLATFORM_SECONDS, startup_timeout=STARTUP_SECONDS, retries=0,
    max_containers=1, min_containers=0, buffer_containers=0,
    scaledown_window=2, single_use_containers=True, serialized=True,
    include_source=False, volumes={'/evidence':volume})
def finite_work(plan, release):
    import os, threading, time, traceback, uuid
    start = time.time(); stop = start+WORKER_SECONDS
    def hard_stop():
        import psutil
        try:
            for process in psutil.Process().children(recursive=True):
                try:
                    process.kill()
                except psutil.Error:
                    pass
        finally:
            os._exit(124)
    timer = threading.Timer(WORKER_SECONDS, hard_stop); timer.daemon=True; timer.start()
    from experiments.sft_allocation_midpoint.common import read, dump, sha, digest, manifest
    from experiments.sft_allocation_midpoint.guard import RunGuard
    from experiments.sft_allocation_p008.evidence_bundle import pack
    from experiments.learning_regime_p009.p0_runtime import execute
    spec = read('/workspace/'+SPEC); validate_release(spec, plan, release)
    if set(SOURCES) != set(spec['source_files']):
        raise ValueError('Missing source in release')
    for name, expected in spec['source_files'].items():
        if sha(Path('/workspace')/name) != expected:
            raise ValueError('Runtime source drift')
    store = modal.Dict.from_name('sft-allocation-midpoint-claims-v1', create_if_missing=False)
    guard = RunGuard(store, plan); guard.register(now_epoch=time.time())
    run = 'p0_parity_pair'
    claim = guard.admit(dict(run_id=run, source_sha256=digest(spec['source_files']),
        config_sha256=digest(spec), data_sha256=digest(spec['inputs'])),
        attempt_id=uuid.uuid4().hex, now_epoch=time.time(), max_runtime_seconds=max(1.,stop-time.time()))
    out = Path('/evidence')/plan['campaign_id']/run
    try:
        volume.reload(); out.mkdir(parents=True, exist_ok=False)
        dump(out/'intent.json', dict(plan=plan, release=release, spec=spec,
            worker_started_epoch=start, hard_deadline_epoch=stop, new_training_updates=0))
        volume.commit()
        result = execute(spec, out, store, guard, claim, volume.commit, start, stop)
        dump(out/'result.json', result); volume.commit(); pack(out); volume.commit()
        files = manifest(out); dump(out/'artifact_manifest.json', files); volume.commit()
        if time.time() >= stop-5:
            raise TimeoutError('Closing exceeded finite worker cap')
        receipt = guard.finish(claim, status='completed', evidence_sha256=digest(files),
            actual_cost_cents=RESERVED_CENTS, finished_epoch=time.time())
        return dict(result=result, artifact_manifest=files, receipt=receipt)
    except BaseException as exc:
        if out.exists():
            dump(out/'failure.json', dict(type=type(exc).__name__, error=str(exc),
                 traceback=traceback.format_exc(), retry_authorized=False))
            volume.commit(); files=manifest(out); dump(out/'failure_manifest.json',files); volume.commit()
            guard.finish(claim, status='failed', evidence_sha256=digest(files),
                actual_cost_cents=RESERVED_CENTS, finished_epoch=time.time())
        raise
    finally:
        timer.cancel()


@app.local_entrypoint()
def main(plan_json: str, gates_json: str, receipt_dir: str):
    import json, time
    from modal.exception import NotFoundError
    from experiments.sft_allocation_midpoint.common import read, dump, sha
    from experiments.sft_allocation_p008.student_concurrency import dispatch_lock
    plan=read(plan_json); gate=read(gates_json); spec=read(ROOT/SPEC)
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    remote=subprocess.check_output(['git','ls-remote','origin','refs/heads/codex/icml-acl-2027'],cwd=ROOT,text=True).split()[0]
    if commit != remote:
        raise ValueError('Publish source before dispatch')
    for name in SOURCES+[SPEC]:
        if subprocess.check_output(['git','show','HEAD:'+name],cwd=ROOT) != (ROOT/name).read_bytes():
            raise ValueError('Unpublished bytes')
    release=dict(gate, execution_commit=commit, source_files={n:sha(ROOT/n) for n in SOURCES})
    validate_release(spec,plan,release)
    for name in ('design_review','runtime_review'):
        if sha(Path(release[name]['local_report_path'])) != release[name]['report_sha256']:
            raise ValueError('Original scoped review file missing or altered')
    now=time.time()
    if not 0 <= now-release['budget']['observed_epoch'] <= 3600:
        raise ValueError('Fresh budget observation required')
    root=Path(plan_json).parent; dest=Path(receipt_dir); run='p0_parity_pair'
    if dest.resolve() != (root/'runs'/run).resolve():
        raise ValueError('Canonical receipt path required')
    with dispatch_lock(root):
        if time.time()+FULL_WINDOW > plan['deadline_epoch'] or dest.exists():
            raise ValueError('No complete window or prior local attempt')
        store=modal.Dict.from_name('sft-allocation-midpoint-claims-v1',create_if_missing=False)
        prefix='midpoint/'+plan['campaign_id']+'/'
        if any(k.startswith(prefix) for k in store.keys()):
            raise ValueError('Any prior P0 campaign record permanently blocks redispatch')
        try:
            list(volume.iterdir('/'+plan['campaign_id']))
        except NotFoundError:
            pass
        else:
            # Frozen inputs live separately; campaign directory is exclusively output.
            raise ValueError('Prior remote output or unknown partial attempt')
        cli=str(Path(sys.executable).with_name('modal'))
        containers=json.loads(subprocess.check_output([cli,'container','list','--json'],text=True))
        if containers:
            raise ValueError('Initial P0 requires zero existing/unknown workspace containers')
        if time.time()+FULL_WINDOW > plan['deadline_epoch']:
            raise ValueError('Full window elapsed during preflight')
        dest.mkdir(parents=True,exist_ok=False)
        dump(dest/'dispatch_intent.json',dict(plan=plan,release=release,run_id=run,
            provider_app_id=app.app_id,provider_before=containers,created_epoch=time.time()))
        call=finite_work.spawn(plan,release)
        dump(dest/'submitted.json',dict(call_id=call.object_id))
    try:
        dump(dest/'result.json',call.get())
    except BaseException as exc:
        dump(dest/'return_error.json',dict(type=type(exc).__name__,error=str(exc),retry_authorized=False))
        raise

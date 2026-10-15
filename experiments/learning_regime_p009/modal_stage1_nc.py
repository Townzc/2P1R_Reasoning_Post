"""Two original NC slots only; exact review is prerequisite to each single call."""
from pathlib import Path
import modal
from experiments.sft_allocation_midpoint.common import read as _read

ROOT = Path(__file__).resolve().parents[2]
SPEC = 'reports/p009_20261014/stage1_nc_runtime_preflight_v1/ADMISSION.json'
SOURCES = list(_read(ROOT/SPEC)['source_files'])
app = modal.App('p009-two-original-NC-students')
volume = modal.Volume.from_name('sft-allocation-midpoint-v1', create_if_missing=False)
image = (modal.Image.debian_slim(python_version='3.12')
    .pip_install_from_requirements(ROOT/'experiments/learning_regime_p009/requirements_p0.txt')
    .env({'PYTHONPATH':'/workspace', 'HF_HUB_OFFLINE':'1', 'TRANSFORMERS_OFFLINE':'1',
          'TOKENIZERS_PARALLELISM':'false', 'VLLM_WORKER_MULTIPROC_METHOD':'spawn',
          'VLLM_USE_V1':'1', 'CUBLAS_WORKSPACE_CONFIG':':4096:8'}))
for name in SOURCES+[SPEC]:
    image = image.add_local_file(ROOT/name, '/workspace/'+name, copy=True)


@app.function(image=image, gpu='H100!', cpu=(4,4), memory=(32768,32768),
    timeout=4560, startup_timeout=600, retries=0, max_containers=1, min_containers=0,
    buffer_containers=0, scaledown_window=2, single_use_containers=True,
    serialized=True, include_source=False, volumes={'/evidence':volume})
def work(plan, run, release):
    import os, threading, time, traceback, uuid
    start = time.time(); stop = start+4500
    def hard_stop():
        import psutil
        try:
            for child in psutil.Process().children(recursive=True):
                try: child.kill()
                except psutil.Error: pass
        finally:
            os._exit(124)
    timer = threading.Timer(4500, hard_stop); timer.daemon = True; timer.start()
    try:
        from experiments.sft_allocation_midpoint.common import read, dump, sha, digest, manifest
        from experiments.sft_allocation_midpoint.guard import RunGuard
        from experiments.sft_allocation_p008.evidence_bundle import pack
        from experiments.learning_regime_p009.stage1_nc_binding import (
            CAMPAIGN, validate, dispatch_key, logical_key, marker, intent)
        from experiments.learning_regime_p009.stage1_nc_runtime import execute
        spec = read('/workspace/'+SPEC); cap = validate(spec, plan, run, release)
        for name, expected in spec['source_files'].items():
            if sha(Path('/workspace')/name) != expected:
                raise ValueError('Exact source bytes changed')
        store = modal.Dict.from_name('sft-allocation-midpoint-claims-v1', create_if_missing=False)
        if any(store.get(k) != marker(spec, run, release) for k in (dispatch_key(run),logical_key(run))):
            raise ValueError('Permanent original dispatch fences differ')
        for key, value in spec['required_records'].items():
            if store.get(key) != value:
                raise ValueError('Completed/failed scientific dependencies changed')
        guard = RunGuard(store, plan); guard.register(now_epoch=time.time())
        claim = guard.admit(intent(spec,run), attempt_id=uuid.uuid4().hex,
                            now_epoch=time.time(), max_runtime_seconds=max(1.,stop-time.time()))
        out = Path('/evidence')/CAMPAIGN/run
        try:
            volume.reload(); out.mkdir(parents=True, exist_ok=False)
            dump(out/'intent.json', dict(plan=plan,spec=spec,run_id=run,release=release,
                 worker_started_epoch=start,hard_deadline_epoch=stop)); volume.commit()
            result = execute(spec,plan,run,out,store,guard,claim,volume.commit,start,stop)
            dump(out/'result.json',result); volume.commit(); pack(out); volume.commit()
            files = manifest(out); dump(out/'artifact_manifest.json',files); volume.commit()
            if time.time() >= stop-5:
                raise TimeoutError('Packing must fit the original whole-worker cap')
            terminal = guard.finish(claim,status='completed',evidence_sha256=digest(files),
                actual_cost_cents=cap['reserved_cents'],finished_epoch=time.time())
            return dict(result=result,artifact_manifest=files,receipt=terminal)
        except BaseException as exc:
            if out.exists():
                dump(out/'failure.json',dict(type=type(exc).__name__,error=str(exc),
                     traceback=traceback.format_exc(),retry_authorized=False)); volume.commit()
                files = manifest(out); dump(out/'failure_manifest.json',files); volume.commit()
                guard.finish(claim,status='failed',evidence_sha256=digest(files),
                             actual_cost_cents=cap['reserved_cents'],finished_epoch=time.time())
            raise
    finally:
        timer.cancel()


@app.local_entrypoint()
def main(plan_json:str, run_id:str, gates_json:str, receipt_dir:str):
    import json, subprocess, sys, time
    from modal.exception import NotFoundError
    from experiments.sft_allocation_midpoint.common import read,dump,sha
    from experiments.sft_allocation_p008.student_concurrency import dispatch_lock,occupied_capacity
    from experiments.sft_allocation_p008.provider_release import read_stopped_apps
    from experiments.learning_regime_p009.stage1_nc_binding import (
        CAMPAIGN, RUNS, validate, require_unused, dispatch_key, logical_key, marker)
    spec = read(ROOT/SPEC); plan = read(plan_json); gate = read(gates_json)
    commit = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    remote = subprocess.check_output(['git','ls-remote','origin','refs/heads/codex/icml-acl-2027'],
                                     cwd=ROOT,text=True).split()[0]
    if commit != remote:
        raise ValueError('Publish the exact full source before any call')
    for name in SOURCES+[SPEC]:
        if subprocess.check_output(['git','show','HEAD:'+name],cwd=ROOT) != (ROOT/name).read_bytes():
            raise ValueError('Unpublished source/spec bytes')
    release = dict(gate, source_files={n:sha(ROOT/n) for n in SOURCES}, execution_commit=commit)
    cap = validate(spec,plan,run_id,release)
    for key in ('runtime_review','core_review','input_review','G0_review','internal_only_review'):
        review = release[key]
        if sha(review['local_report_path']) != review['report_sha256']:
            raise ValueError('The original full fixed review must be present')
    if not 0 <= time.time()-release['budget']['observed_epoch'] <= 3600:
        raise ValueError('A necessary current project budget snapshot is required')
    root = Path(plan_json).parent; dest = Path(receipt_dir)
    if dest.resolve() != (root/'runs'/run_id).resolve():
        raise ValueError('Only the canonical original receipt directory is permitted')
    with dispatch_lock(root.parent/'stage1_dispatch'):
        if dest.exists() or time.time()+cap['full_window_seconds'] > plan['deadline_epoch']:
            raise ValueError('Prior local work or incomplete full dispatch window')
        store = modal.Dict.from_name('sft-allocation-midpoint-claims-v1',create_if_missing=False)
        prefix = 'midpoint/'+CAMPAIGN+'/'
        records = {k:store.get(k) for k in store.keys() if k.startswith(prefix)}
        require_unused(records,run_id,plan)
        if store.get(logical_key(run_id)) is not None:
            raise ValueError('Logical NC slot already dispatched/unknown')
        for key, value in spec['required_records'].items():
            if store.get(key) != value:
                raise ValueError('Original scientific dependency evidence differs')
        try:
            volume.listdir(CAMPAIGN+'/'+run_id,recursive=True)
        except NotFoundError:
            pass
        else:
            raise ValueError('Original remote output directory already exists')
        cli = str(Path(sys.executable).with_name('modal'))
        containers = json.loads(subprocess.check_output([cli,'container','list','--json'],text=True))
        apps = spec['required_stopped_app_ids']; owned = [c for c in containers if c.get('app_id') in apps]
        dependencies = read_stopped_apps(cli,apps,owned)
        pending = []
        for prior in RUNS:
            sent = records.get(dispatch_key(prior))
            if not sent: continue
            app_id = sent['provider_app_id']
            info = json.loads(subprocess.check_output([cli,'app','info',app_id,'--json'],text=True,timeout=30))
            terminal = records.get(prefix+'terminal/'+prior)
            stopped = (info.get('app_id')==app_id and info.get('lifecycle',{}).get('state')=='stopped'
                and info['lifecycle'].get('stopped_at') and not any(c.get('app_id')==app_id for c in containers))
            if not (terminal and stopped):pending.append(dict(run_id=prior,provider_app_id=app_id))
        if occupied_capacity(pending,containers) >= 4:
            raise ValueError('Pending/unknown/unmatched containers consume capacity')
        if time.time()+cap['full_window_seconds'] > plan['deadline_epoch']:
            raise ValueError('Admission checks consumed the full window')
        dest.mkdir(parents=True,exist_ok=False); release['dispatch_app_id'] = app.app_id
        value = marker(spec,run_id,release)
        for key in (dispatch_key(run_id),logical_key(run_id)):
            if not store.put(key,value,skip_if_exists=True):
                raise ValueError('Partial/prior fence is permanent; never resubmit')
        dump(dest/'dispatch_intent.json',dict(plan=plan,run_id=run_id,release=release,
            provider_app_id=app.app_id,provider_before=containers,pending_before=pending,
            dependency_provider=dependencies,created_epoch=time.time()))
        call = work.spawn(plan,run_id,release)
        dump(dest/'submitted.json',dict(call_id=call.object_id))
    try:
        dump(dest/'result.json',call.get())
    except BaseException as exc:
        dump(dest/'return_error.json',dict(type=type(exc).__name__,error=str(exc),retry_authorized=False))
        raise

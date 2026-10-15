"""Three named finite workers; never a controller, retry or P0 re-generation."""
from pathlib import Path
import modal
from experiments.sft_allocation_midpoint.common import read as _read
from experiments.learning_regime_p009.stage0_generation_contract_v2 import SLOTS, slot_checked

ROOT = Path(__file__).resolve().parents[2]
SPEC = 'reports/p009_20261014/stage0_generation_runtime_preflight_v2/ADMISSION.json'
SOURCES = list(_read(ROOT/SPEC)['source_files'])
app = modal.App('p009-finite-stage0-generation-funded-v2')
volume = modal.Volume.from_name('sft-allocation-midpoint-v1', create_if_missing=False)
image = (modal.Image.debian_slim(python_version='3.12')
    .pip_install_from_requirements(ROOT/'experiments/learning_regime_p009/requirements_p0.txt')
    .env({'PYTHONPATH':'/workspace','HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1',
          'TOKENIZERS_PARALLELISM':'false','VLLM_WORKER_MULTIPROC_METHOD':'spawn','VLLM_USE_V1':'1'}))
for name in SOURCES+[SPEC]:
    image = image.add_local_file(ROOT/name, '/workspace/'+name, copy=True)


def worker(plan, run, release):
    import os, threading, time, traceback, uuid
    start = time.time(); seconds = slot_checked(run)['worker_seconds']; stop = start+seconds
    def hard_stop():
        import psutil
        try:
            for child in psutil.Process().children(recursive=True):
                try: child.kill()
                except psutil.Error: pass
        finally:
            os._exit(124)
    timer = threading.Timer(seconds, hard_stop); timer.daemon = True; timer.start()
    try:
        from experiments.sft_allocation_midpoint.common import read,dump,sha,digest,manifest
        from experiments.sft_allocation_midpoint.guard import RunGuard
        from experiments.sft_allocation_p008.evidence_bundle import pack
        from experiments.learning_regime_p009.stage0_generation_binding_v2 import (
            CAMPAIGN, validate_release, dispatch_key, dataset_key, marker, intent)
        from experiments.learning_regime_p009.stage0_generation_runtime_v2 import execute
        spec = read('/workspace/'+SPEC); slot = validate_release(spec,plan,run,release)
        for name, expected in spec['source_files'].items():
            if sha(Path('/workspace')/name) != expected:
                raise ValueError('Exact published source changed')
        store = modal.Dict.from_name('sft-allocation-midpoint-claims-v1',create_if_missing=False)
        expected = marker(spec,run,release)
        for key in [dispatch_key(run)]+[dataset_key(n) for n in SLOTS[run]['datasets']]:
            if store.get(key) != expected:
                raise ValueError('Permanent original dispatch/dataset fence differs')
        for key,value in spec['required_P0_records'].items():
            if store.get(key) != value:
                raise ValueError('P0 completed/failed lineage differs')
        guard = RunGuard(store,plan);guard.register(now_epoch=time.time())
        claim = guard.admit(intent(spec,run), attempt_id=uuid.uuid4().hex,
            now_epoch=time.time(),max_runtime_seconds=max(1.,stop-time.time()))
        out = Path('/evidence')/CAMPAIGN/run
        try:
            volume.reload();out.mkdir(parents=True,exist_ok=False)
            dump(out/'intent.json',dict(plan=plan,spec=spec,run_id=run,release=release,
                worker_started_epoch=start,hard_deadline_epoch=stop));volume.commit()
            result = execute(spec,run,out,store,guard,claim,volume.commit,start,stop)
            dump(out/'result.json',result);volume.commit();pack(out);volume.commit()
            files=manifest(out);dump(out/'artifact_manifest.json',files);volume.commit()
            if time.time() >= stop-5:
                raise TimeoutError('Closing exceeded original worker cap')
            receipt=guard.finish(claim,status='completed',evidence_sha256=digest(files),
                actual_cost_cents=slot['reserved_cents'],finished_epoch=time.time())
            return dict(result=result,artifact_manifest=files,receipt=receipt)
        except BaseException as exc:
            if out.exists():
                dump(out/'failure.json',dict(type=type(exc).__name__,error=str(exc),
                    traceback=traceback.format_exc(),retry_authorized=False));volume.commit()
                files=manifest(out);dump(out/'failure_manifest.json',files);volume.commit()
                guard.finish(claim,status='failed',evidence_sha256=digest(files),
                    actual_cost_cents=slot['reserved_cents'],finished_epoch=time.time())
            raise
    finally:
        timer.cancel()


settings=dict(image=image,gpu='H100!',cpu=(4,4),memory=(32768,32768),startup_timeout=600,
    retries=0,max_containers=1,min_containers=0,buffer_containers=0,scaledown_window=2,
    single_use_containers=True,serialized=True,include_source=False,volumes={'/evidence':volume})


@app.function(timeout=7260,**settings)
def teacher_work(plan,release):
    return worker(plan,'teacher_p2_p3',release)


@app.function(timeout=1860,**settings)
def qwen_work(plan,release):
    return worker(plan,'qwen_p3',release)


@app.function(timeout=1860,**settings)
def olmo_work(plan,release):
    return worker(plan,'olmo_p3',release)


@app.local_entrypoint()
def main(plan_json:str,run_id:str,gates_json:str,receipt_dir:str):
    import json,subprocess,sys,time
    from modal.exception import NotFoundError
    from experiments.sft_allocation_midpoint.common import read,dump,sha
    from experiments.sft_allocation_p008.student_concurrency import dispatch_lock,occupied_capacity
    from experiments.sft_allocation_p008.provider_release import read_stopped_apps
    from experiments.learning_regime_p009.stage0_generation_binding_v2 import (
        CAMPAIGN,validate_release,require_unused,dispatch_key,dataset_key,marker)
    spec=read(ROOT/SPEC);plan=read(plan_json);gate=read(gates_json)
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    remote=subprocess.check_output(['git','ls-remote','origin','refs/heads/codex/icml-acl-2027'],cwd=ROOT,text=True).split()[0]
    if commit != remote: raise ValueError('Publish current exact source first')
    for name in SOURCES+[SPEC]:
        if subprocess.check_output(['git','show','HEAD:'+name],cwd=ROOT)!=(ROOT/name).read_bytes():
            raise ValueError('Unpublished runtime/spec bytes')
    release=dict(gate,source_files={n:sha(ROOT/n) for n in SOURCES},execution_commit=commit)
    slot=validate_release(spec,plan,run_id,release)
    for key in ('runtime_review','internal_only_review','p0_integrity_review'):
        review=release[key]
        if sha(review['local_report_path'])!=review['report_sha256']:
            raise ValueError('Original full fixed review is absent/changed')
    if not 0<=time.time()-release['budget']['observed_epoch']<=3600:
        raise ValueError('A necessary current budget snapshot is required')
    root=Path(plan_json).parent;dest=Path(receipt_dir)
    if dest.resolve()!=(root/'runs'/run_id).resolve(): raise ValueError('Use canonical receipt directory')
    with dispatch_lock(root):
        if dest.exists() or time.time()+slot['full_window_seconds']>plan['deadline_epoch']:
            raise ValueError('Existing local attempt or incomplete window')
        store=modal.Dict.from_name('sft-allocation-midpoint-claims-v1',create_if_missing=False)
        prefix='midpoint/'+CAMPAIGN+'/'
        records={k:store.get(k) for k in store.keys() if k.startswith(prefix)}
        require_unused(records,run_id,plan)
        for key,value in spec['required_P0_records'].items():
            if store.get(key)!=value:raise ValueError('Original P0 evidence differs')
        for name in SLOTS[run_id]['datasets']:
            if store.get(dataset_key(name)) is not None:raise ValueError('Dataset already dispatched/unknown')
        try:list(volume.iterdir('/'+CAMPAIGN+'/'+run_id))
        except NotFoundError:pass
        else:raise ValueError('Original remote run directory already exists')
        cli=str(Path(sys.executable).with_name('modal'))
        containers=json.loads(subprocess.check_output([cli,'container','list','--json'],text=True))
        owned=[c for c in containers if c.get('app_id') in spec['P0_app_ids']]
        p0_provider=read_stopped_apps(cli,spec['P0_app_ids'],owned)
        pending=[]
        for prior in SLOTS:
            dispatch=records.get(dispatch_key(prior))
            if not dispatch:continue
            app_id=dispatch['provider_app_id']
            info=json.loads(subprocess.check_output([cli,'app','info',app_id,'--json'],text=True,timeout=30))
            terminal=records.get(prefix+'terminal/'+prior)
            stopped=(info.get('app_id')==app_id and info.get('lifecycle',{}).get('state')=='stopped'
                     and info['lifecycle'].get('stopped_at') and not any(c.get('app_id')==app_id for c in containers))
            if not (terminal and stopped):pending.append(dict(run_id=prior,provider_app_id=app_id))
        if occupied_capacity(pending,containers)>=3:
            raise ValueError('Pending/unknown/unmatched containers consume the three-worker capacity')
        if time.time()+slot['full_window_seconds']>plan['deadline_epoch']:
            raise ValueError('Preflight consumed full dispatch window')
        dest.mkdir(parents=True,exist_ok=False);release['dispatch_app_id']=app.app_id
        value=marker(spec,run_id,release)
        # Every partially written fence is permanent. No clear or retry path.
        for key in [dispatch_key(run_id)]+[dataset_key(n) for n in SLOTS[run_id]['datasets']]:
            if not store.put(key,value,skip_if_exists=True):
                raise ValueError('Ambiguous/prior dispatch fence; never resubmit')
        dump(dest/'dispatch_intent.json',dict(plan=plan,run_id=run_id,release=release,
            provider_app_id=app.app_id,provider_before=containers,pending_before=pending,
            P0_provider=p0_provider,created_epoch=time.time()))
        fn={'teacher_p2_p3':teacher_work,'qwen_p3':qwen_work,'olmo_p3':olmo_work}[run_id]
        call=fn.spawn(plan,release);dump(dest/'submitted.json',dict(call_id=call.object_id))
    try:dump(dest/'result.json',call.get())
    except BaseException as exc:
        dump(dest/'return_error.json',dict(type=type(exc).__name__,error=str(exc),retry_authorized=False))
        raise

"""Unattempted suffix only; inherit saved Plan-A outputs without normalization."""
from pathlib import Path
import modal
from experiments.learning_regime_p009.p0_fast_remaining_contract import (
    CAMPAIGN, RUN, PARENT_CAMPAIGN, PARENT_RUN, RETIRED_CAMPAIGN, WORKER_SECONDS,
    PLATFORM_SECONDS, STARTUP_SECONDS, FULL_WINDOW, RESERVED_CENTS, validate_release,
    ANCESTOR_CAMPAIGN, ANCESTOR_RUN,
)

ROOT = Path(__file__).resolve().parents[2]
SPEC = 'reports/p009_20261014/p0_fast_remaining_preflight_v1/ADMISSION.json'
# Original nineteen bytes remain immutable; this imports no old Modal entry.
from experiments.sft_allocation_midpoint.common import read as _local_read
SOURCES = list(_local_read(ROOT/SPEC)['source_files'])
app = modal.App('p009-p0-fast-unattempted-remainder')
volume = modal.Volume.from_name('sft-allocation-midpoint-v1', create_if_missing=False)
image = (modal.Image.debian_slim(python_version='3.12')
    .pip_install_from_requirements(ROOT/'experiments/learning_regime_p009/requirements_p0.txt')
    .env({'PYTHONPATH': '/workspace', 'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1',
          'TOKENIZERS_PARALLELISM': 'false', 'VLLM_WORKER_MULTIPROC_METHOD': 'spawn', 'VLLM_USE_V1': '1'}))
for name in SOURCES+[SPEC]:
    image = image.add_local_file(ROOT/name, '/workspace/'+name, copy=True)


@app.function(image=image, gpu='H100!', cpu=(4,4), memory=(32768,32768),
    timeout=PLATFORM_SECONDS, startup_timeout=STARTUP_SECONDS, retries=0,
    max_containers=1, min_containers=0, buffer_containers=0, scaledown_window=2,
    single_use_containers=True, serialized=True, include_source=False,
    volumes={'/evidence': volume})
def finite_work(plan, release):
    import os, threading, time, traceback, uuid
    start = time.time(); stop = start+WORKER_SECONDS
    def hard_stop():
        import psutil
        try:
            for child in psutil.Process().children(recursive=True):
                try:
                    child.kill()
                except psutil.Error:
                    pass
        finally:
            os._exit(124)
    timer = threading.Timer(WORKER_SECONDS, hard_stop); timer.daemon = True; timer.start()
    from experiments.sft_allocation_midpoint.common import read, dump, sha, digest, manifest
    from experiments.sft_allocation_midpoint.guard import RunGuard
    from experiments.sft_allocation_p008.evidence_bundle import pack
    from experiments.learning_regime_p009.p0_fast_remaining_runtime import execute
    spec = read('/workspace/'+SPEC); validate_release(spec, plan, release)
    for name, expected in spec['source_files'].items():
        if sha(Path('/workspace')/name) != expected:
            raise ValueError('Exact reviewed source changed')
    store = modal.Dict.from_name('sft-allocation-midpoint-claims-v1', create_if_missing=False)
    guard = RunGuard(store, plan); guard.register(now_epoch=time.time())
    claim = guard.admit(dict(run_id=RUN, source_sha256=digest(spec['source_files']),
        config_sha256=digest(spec), data_sha256=digest(spec['inputs'])),
        attempt_id=uuid.uuid4().hex, now_epoch=time.time(), max_runtime_seconds=max(1.,stop-time.time()))
    out = Path('/evidence')/CAMPAIGN/RUN
    try:
        volume.reload(); out.mkdir(parents=True, exist_ok=False)
        dump(out/'intent.json', dict(plan=plan, release=release, spec=spec,
            worker_started_epoch=start, hard_deadline_epoch=stop, new_training_updates=0))
        volume.commit()
        result = execute(spec, out, store, guard, claim, volume.commit, start, stop)
        dump(out/'result.json', result); volume.commit(); pack(out); volume.commit()
        files = manifest(out); dump(out/'artifact_manifest.json', files); volume.commit()
        if time.time() >= stop-5:
            raise TimeoutError('Closing exceeded fast worker cap')
        receipt = guard.finish(claim, status='completed', evidence_sha256=digest(files),
            actual_cost_cents=RESERVED_CENTS, finished_epoch=time.time())
        return dict(result=result, artifact_manifest=files, receipt=receipt)
    except BaseException as exc:
        if out.exists():
            dump(out/'failure.json', dict(type=type(exc).__name__, error=str(exc),
                traceback=traceback.format_exc(), retry_authorized=False))
            volume.commit(); files = manifest(out); dump(out/'failure_manifest.json', files); volume.commit()
            guard.finish(claim, status='failed', evidence_sha256=digest(files),
                actual_cost_cents=RESERVED_CENTS, finished_epoch=time.time())
        raise
    finally:
        timer.cancel()


@app.local_entrypoint()
def main(plan_json: str, gates_json: str, receipt_dir: str):
    import json, subprocess, sys, time
    from modal.exception import NotFoundError
    from experiments.sft_allocation_midpoint.common import read, dump, sha
    from experiments.sft_allocation_p008.student_concurrency import dispatch_lock
    from experiments.sft_allocation_p008.provider_release import read_stopped_apps
    plan = read(plan_json); gate = read(gates_json); spec = read(ROOT/SPEC)
    commit = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    remote = subprocess.check_output(['git','ls-remote','origin','refs/heads/codex/icml-acl-2027'],
                                    cwd=ROOT,text=True).split()[0]
    if commit != remote:
        raise ValueError('Publish exact source first')
    for name in SOURCES+[SPEC]:
        if subprocess.check_output(['git','show','HEAD:'+name],cwd=ROOT) != (ROOT/name).read_bytes():
            raise ValueError('Unpublished runtime bytes')
    release = dict(gate, execution_commit=commit, source_files={n:sha(ROOT/n) for n in SOURCES})
    validate_release(spec, plan, release)
    for name in ('runtime_review',):
        review = release[name]
        if sha(review['local_report_path']) != review['report_sha256']:
            raise ValueError('Real fixed report missing/changed')
    if not 0 <= time.time()-release['budget']['observed_epoch'] <= 3600:
        raise ValueError('Fresh budget evidence required')
    root = Path(plan_json).parent; dest = Path(receipt_dir)
    if dest.resolve() != (root/'runs'/RUN).resolve():
        raise ValueError('Canonical receipt required')
    # Share the original P0 local dispatch lock as well as its permanent marker.
    parent_root = root.parent/'p0_r1'
    with dispatch_lock(parent_root):
        if time.time()+FULL_WINDOW > plan['deadline_epoch'] or dest.exists():
            raise ValueError('Prior local attempt or insufficient complete window')
        store = modal.Dict.from_name('sft-allocation-midpoint-claims-v1', create_if_missing=False)
        prefix = 'midpoint/'+CAMPAIGN+'/'
        if any(k.startswith((prefix, 'midpoint/'+RETIRED_CAMPAIGN+'/')) for k in store.keys()):
            raise ValueError('Any prior child record permanently blocks redispatch')
        parent_prefix = 'midpoint/'+PARENT_CAMPAIGN+'/'
        ancestor_prefix = 'midpoint/'+ANCESTOR_CAMPAIGN+'/'
        original = spec['parent_spec']
        if (store.get(parent_prefix+'claim/'+PARENT_RUN) != spec['parent_claim'] or
                store.get(parent_prefix+'terminal/'+PARENT_RUN) != spec['parent_terminal'] or
                store.get(parent_prefix+'continuation/'+PARENT_RUN) is not None or
                store.get(ancestor_prefix+'claim/'+ANCESTOR_RUN) != original['parent_claim'] or
                store.get(ancestor_prefix+'terminal/'+ANCESTOR_RUN) != original['parent_terminal'] or
                store.get(ancestor_prefix+'continuation/'+ANCESTOR_RUN) != spec['ancestor_marker']):
            raise ValueError('Failed lineage differs or any suffix already attempted')
        for campaign in (CAMPAIGN, RETIRED_CAMPAIGN):
            try:
                list(volume.iterdir('/'+campaign))
            except NotFoundError:
                pass
            else:
                raise ValueError('Any prior fast/suffix output prevents dispatch')
        cli = str(Path(sys.executable).with_name('modal'))
        containers = json.loads(subprocess.check_output([cli,'container','list','--json'],text=True))
        if containers:
            raise ValueError('Require zero workspace active/pending/unknown containers')
        parent_provider = read_stopped_apps(cli, [spec['parent_spec']['parent_app_id'],spec['parent_app_id']], [])
        if time.time()+FULL_WINDOW > plan['deadline_epoch']:
            raise ValueError('Complete window elapsed during preflight')
        dest.mkdir(parents=True, exist_ok=False)
        dump(dest/'dispatch_intent.json', dict(plan=plan, release=release, run_id=RUN,
            provider_app_id=app.app_id, parent_provider=parent_provider,
            provider_before=containers, created_epoch=time.time()))
        call = finite_work.spawn(plan, release)
        dump(dest/'submitted.json', dict(call_id=call.object_id))
    try:
        dump(dest/'result.json', call.get())
    except BaseException as exc:
        dump(dest/'return_error.json', dict(type=type(exc).__name__, error=str(exc), retry_authorized=False))
        raise

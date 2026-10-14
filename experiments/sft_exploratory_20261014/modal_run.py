"""Exactly three owner-authorized slots, one submission each, no retry path."""
from pathlib import Path
import json
import subprocess
import sys
import modal

ROOT=Path(__file__).resolve().parents[2]
SPEC='reports/exploratory_20261014/admission_v1/ADMISSION.json'
# Filled once before the immutable review packet is published.
SOURCES=['analyses/completion_contract.py', 'analyses/e017_audit.py', 'analyses/e017_stopping.py', 'analyses/gsm8k_answer_audit.py', 'configs/models.lock.json', 'experiments/sft_allocation_acquisition/policy_contract.py', 'experiments/sft_allocation_acquisition/token_contract.py', 'experiments/sft_allocation_acquisition/token_student_runtime.py', 'experiments/sft_allocation_midpoint/checkpoint.py', 'experiments/sft_allocation_midpoint/common.py', 'experiments/sft_allocation_midpoint/completion.py', 'experiments/sft_allocation_midpoint/guard.py', 'experiments/sft_allocation_midpoint/monitor.py', 'experiments/sft_allocation_midpoint/runtime.py', 'experiments/sft_allocation_p008/block_journal.py', 'experiments/sft_allocation_p008/contract.py', 'experiments/sft_allocation_p008/evidence_bundle.py', 'experiments/sft_allocation_p008/frozen_student_plan.py', 'experiments/sft_allocation_p008/parallel_guard.py', 'experiments/sft_allocation_p008/schedule.py', 'experiments/sft_allocation_p008/student_concurrency.py', 'experiments/sft_allocation_p008/student_runtime.py', 'experiments/sft_exploratory_20261014/__init__.py', 'experiments/sft_exploratory_20261014/contract.py', 'experiments/sft_exploratory_20261014/modal_run.py', 'experiments/sft_exploratory_20261014/runtime.py', 'requirements.txt', 'scripts/audit_exploratory_20261014.py', 'scripts/audit_midpoint_local.py', 'scripts/audit_token_student.py', 'scripts/fetch_real_math_sources.py', 'scripts/plan_real_math_scale.py', 'scripts/prepare_exploratory_20261014.py', 'scripts/prepare_real_math_audit.py', 'src/__init__.py', 'src/real_math_audit.py', 'src/sft_data.py']
app=modal.App('exploratory-20261014-three-slots')
volume=modal.Volume.from_name('sft-allocation-midpoint-v1',create_if_missing=False)
image=(modal.Image.debian_slim(python_version='3.12')
    .pip_install('torch==2.8.0',index_url='https://download.pytorch.org/whl/cu128')
    .pip_install_from_requirements(ROOT/'requirements.txt').pip_install('peft==0.17.1')
    .env({'PYTHONPATH':'/workspace','HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1',
          'TOKENIZERS_PARALLELISM':'false','CUBLAS_WORKSPACE_CONFIG':':4096:8'}))
for name in SOURCES:image=image.add_local_file(ROOT/name,'/workspace/'+name,copy=True)
image=image.add_local_file(ROOT/SPEC,'/workspace/'+SPEC,copy=True)


def validate_release(spec,plan,config,release):
    from experiments.sft_exploratory_20261014.contract import validate_release as validate
    validate(spec,plan,config,release)


def download_instruct(inputs,root,commit,check):
    """One pinned GET; partial download preserved. No HF automatic fetch/retry."""
    import urllib.request,hashlib,shutil,time
    from experiments.sft_allocation_midpoint.common import read,dump,verify
    lock=read(inputs/'instruct_model_lock.json')
    verify(inputs/'instruct_model',lock['metadata_files'])
    root.mkdir(exist_ok=False)
    for name in lock['metadata_files']:shutil.copyfile(inputs/'instruct_model'/name,root/name)
    url=f"https://huggingface.co/{lock['repo_id']}/resolve/{lock['revision']}/model.safetensors"
    dump(root/'download_intent.json',dict(url=url,expected=lock['weight'],started_epoch=time.time(),retry=False));commit()
    part=root/'model.safetensors.partial';h=hashlib.sha256();size=0
    with urllib.request.urlopen(url,timeout=60) as source,part.open('xb') as target:
        while True:
            check();block=source.read(2**20)
            if not block:break
            target.write(block);size+=len(block);h.update(block)
            if size>lock['weight']['size']:raise ValueError('Oversized official weight')
    if size!=lock['weight']['size'] or h.hexdigest()!=lock['weight']['sha256']:
        raise ValueError('Pinned official weight hash differs')
    part.rename(root/'model.safetensors')
    dump(root/'download_verified.json',dict(bytes=size,sha256=h.hexdigest(),finished_epoch=time.time(),retry=False))
    commit();return root


def work(plan,config,release):
    import os,time,threading,uuid,traceback
    start=time.time();stop=min(start+6001,plan['deadline_epoch']-30)
    timer=threading.Timer(max(1,stop-start),lambda:os._exit(124));timer.daemon=True;timer.start()
    sys.path.insert(0,'/workspace')
    from experiments.sft_allocation_midpoint.common import read,dump,sha,digest,verify,manifest
    from experiments.sft_allocation_midpoint.guard import RunGuard
    from experiments.sft_allocation_p008.parallel_guard import ParallelActiveCheck
    from experiments.sft_allocation_midpoint.runtime import environment
    from experiments.sft_allocation_p008.block_journal import BlockTrainingJournal
    from experiments.sft_allocation_midpoint.monitor import GPURecorder
    from experiments.sft_allocation_p008.evidence_bundle import pack
    spec=read('/workspace/'+SPEC);validate_release(spec,plan,config,release)
    for name,h in release['source_files'].items():
        if sha(Path('/workspace')/name)!=h:raise ValueError('Source bytes changed')
    if set(release['source_files'])!=set(SOURCES):raise ValueError('Incomplete source release')
    claims=modal.Dict.from_name('sft-allocation-midpoint-claims-v1',create_if_missing=False)
    guard=RunGuard(claims,plan);guard.register(now_epoch=time.time());run=config['run_id']
    admitted=guard.admit(dict(run_id=run,source_sha256=digest(release['source_files']),
        config_sha256=digest(config),data_sha256=config['input_sha256']),attempt_id=uuid.uuid4().hex,
        now_epoch=time.time(),max_runtime_seconds=max(1,stop-time.time()+30))
    reserve=plan['slots'][run]['reserved_cents'];out=Path('/evidence')/plan['campaign_id']/run
    active=ParallelActiveCheck(guard);recorder=None;journal=None
    def deadline():
        if time.time()>stop-30:raise TimeoutError('Exploratory finite worker cap')
    def check():
        deadline();active.check_active(admitted,spent_cents=0,next_cost_cents=reserve);deadline()
    try:
        volume.reload();out.mkdir(parents=True,exist_ok=False)
        dump(out/'intent.json',dict(plan=plan,config=config,release=release,started_epoch=start,reserved_cents=reserve))
        dump(out/'admission.json',spec);volume.commit()
        inputs=Path('/evidence')/plan['campaign_id']/'inputs'
        if sha(inputs/'manifest.json')!=config['input_sha256']:raise ValueError('Input hash differs')
        verify(inputs,read(inputs/'manifest.json')['files'])
        assets=Path('/evidence/mp-engineering-20261012-r1/assets')
        if run!='instruct_0shot':verify(assets,read(assets/'result.json')['files'])
        dump(out/'environment.json',environment(expected_gpu='H100'));volume.commit()
        instruct=None
        if run=='instruct_0shot':
            # Assets stay outside compact scientific bundles; source/provenance
            # is retained separately and expected bytes are frozen in inputs.
            instruct=download_instruct(inputs,out.parent/'instruct_assets',volume.commit,deadline)
            dump(out/'official_model_readback.json',dict(lock=read(inputs/'instruct_model_lock.json'),
                download=read(instruct/'download_verified.json')));volume.commit()
        recorder=GPURecorder(out);recorder.start()
        journal=BlockTrainingJournal(out,'midpoint/'+plan['campaign_id']+'/'+run,claims,volume.commit,
            check,deadline=deadline,expected_updates=config['updates'])
        identity=dict(config=config,source_commit=release['commit'],source_sha256=digest(release['source_files']))
        from experiments.sft_exploratory_20261014.runtime import run as execute
        result=execute(assets,inputs,out,journal,identity,instruct)
        journal.assert_training_complete();dump(out/'block_journal_metrics.json',journal.metrics)
        recorder.stop();recorder=None
        result.update(wall_seconds=time.time()-start,reserved_cost_usd=reserve/100,provider_invoice_usd=None,
            runtime_rate_estimate_usd=(time.time()-start)*4.393584/3600)
        dump(out/'guard_read_metrics.json',active.metrics);dump(out/'result.json',result)
        volume.commit();pack(out);volume.commit();files=manifest(out);dump(out/'artifact_manifest.json',files);volume.commit()
        receipt=guard.finish(admitted,status='completed',evidence_sha256=digest(files),actual_cost_cents=reserve,finished_epoch=time.time())
        return dict(result=result,artifact_manifest=files,receipt=receipt)
    except BaseException as exc:
        if recorder:recorder.stop()
        if out.exists():
            dump(out/'failure.json',dict(error_type=type(exc).__name__,error=str(exc),traceback=traceback.format_exc(),
                wall_seconds=time.time()-start,retry_authorized=False))
            volume.commit();files=manifest(out);dump(out/'failure_manifest.json',files);volume.commit()
            guard.finish(admitted,status='failed',evidence_sha256=digest(files),actual_cost_cents=reserve,finished_epoch=time.time())
        raise
    finally:active.close();timer.cancel()


@app.function(image=image,gpu='H100!',cpu=(4,4),memory=(32768,32768),timeout=6061,startup_timeout=600,
    retries=0,max_containers=3,min_containers=0,buffer_containers=0,scaledown_window=2,
    single_use_containers=True,serialized=True,include_source=False,volumes={'/evidence':volume})
def finite_work(plan,config,release):
    return work(plan,config,release)


@app.local_entrypoint()
def main(plan_json:str,config_json:str,gates_json:str,receipt_dir:str):
    import time
    from experiments.sft_allocation_midpoint.common import read,dump,sha
    from experiments.sft_allocation_p008.student_concurrency import dispatch_lock,occupied_capacity
    plan=read(plan_json);cfg=read(config_json);gate=read(gates_json);spec=read(ROOT/SPEC)
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    remote=subprocess.check_output(['git','ls-remote','origin','refs/heads/codex/icml-acl-2027'],cwd=ROOT,text=True).split()[0]
    if commit!=remote:raise ValueError('Publish exact source before execution')
    source={n:sha(ROOT/n) for n in SOURCES}
    for n in SOURCES+[SPEC]:
        if subprocess.check_output(['git','show','HEAD:'+n],cwd=ROOT)!=(ROOT/n).read_bytes():raise ValueError('Unpublished bytes')
    release=dict(commit=commit,source_files=source,**gate);validate_release(spec,plan,cfg,release)
    root=Path(plan_json).parent;dest=Path(receipt_dir);run=cfg['run_id']
    if dest.resolve()!=(root/'runs'/run).resolve():raise ValueError('Canonical receipt required')
    with dispatch_lock(root):
        if time.time()+6701>plan['deadline_epoch']:raise ValueError('Complete worker plus 700s window required')
        if dest.exists():raise ValueError('Prior local submission/attempt; never repeat')
        claims=modal.Dict.from_name('sft-allocation-midpoint-claims-v1',create_if_missing=False)
        prefix='midpoint/'+plan['campaign_id']+'/'
        for kind in ('claim','intent','terminal'):
            if claims.get(prefix+kind+'/'+run) is not None:raise ValueError('Prior remote attempt')
        if any(k.startswith(prefix+run+'/') or k.startswith(prefix+'attempt/'+run+'/') for k in claims.keys()):
            raise ValueError('Prior unit or attempt')
        from modal.exception import NotFoundError
        try:list(volume.iterdir('/'+plan['campaign_id']+'/'+run))
        except NotFoundError:pass
        else:raise ValueError('Prior remote output directory')
        cli=str(Path(sys.executable).with_name('modal'))
        containers=json.loads(subprocess.check_output([cli,'container','list','--json'],text=True))
        occupied=[]
        for path in (root/'runs').glob('*/dispatch_intent.json'):
            entry=read(path);terminal=claims.get(prefix+'terminal/'+entry['run_id'])
            if terminal is None:occupied.append(entry)
        # Every unmatched container and unresolved call consumes capacity.
        count=occupied_capacity(occupied,containers)
        if count>=3:raise ValueError('Three-worker ceiling includes every pending or unmatched container')
        if time.time()+6701>plan['deadline_epoch']:raise ValueError('Full window elapsed during checks')
        dest.mkdir(parents=True,exist_ok=False)
        dump(dest/'dispatch_intent.json',dict(run_id=run,provider_app_id=app.app_id,occupied_capacity_before=count,
            config=cfg,plan=plan,release=release,provider_before=containers,occupied_before=occupied))
        call=finite_work.spawn(plan,cfg,release);dump(dest/'submitted.json',dict(call_id=call.object_id))
    try:dump(dest/'result.json',call.get())
    except BaseException as exc:
        dump(dest/'return_error.json',dict(type=type(exc).__name__,error=str(exc),retry_authorized=False));raise

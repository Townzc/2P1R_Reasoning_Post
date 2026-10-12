"""One bounded H100 teacher pilot with immutable claims and no student training."""
import json,subprocess,time
from pathlib import Path
import modal
ROOT=Path(__file__).resolve().parents[2]
SOURCES=['src/real_math_audit.py','analyses/gsm8k_answer_audit.py','requirements.txt',
    'configs/acquisition_teacher.lock.json',
    *['experiments/sft_allocation_midpoint/'+n for n in ('guard.py','common.py','monitor.py')],
    *['experiments/sft_allocation_acquisition/'+n for n in ('contract.py','runtime.py','modal_runner.py')]]
app=modal.App('sft-allocation-teacher-cost-pilot')
volume=modal.Volume.from_name('sft-allocation-midpoint-v1',create_if_missing=False)
image=(modal.Image.debian_slim(python_version='3.12')
    .pip_install('torch==2.8.0',index_url='https://download.pytorch.org/whl/cu128')
    .pip_install_from_requirements(ROOT/'requirements.txt')
    .env({'PYTHONPATH':'/workspace','TOKENIZERS_PARALLELISM':'false',
          'HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1'}))
for name in SOURCES:image=image.add_local_file(ROOT/name,'/workspace/'+name,copy=True)


@app.function(image=image,gpu='H100!',cpu=(4,4),memory=(32768,32768),timeout=5500,startup_timeout=600,
    retries=0,max_containers=1,min_containers=0,buffer_containers=0,scaledown_window=2,
    single_use_containers=True,serialized=True,include_source=False,volumes={'/evidence':volume})
def pilot(plan,config,release):
    import os,sys,uuid,threading,traceback
    sys.path.insert(0,'/workspace')
    from experiments.sft_allocation_midpoint.common import dump,read,sha,digest,manifest
    from experiments.sft_allocation_midpoint.guard import RunGuard
    from experiments.sft_allocation_midpoint.monitor import GPURecorder
    from experiments.sft_allocation_acquisition.runtime import run,RATE_USD_PER_HOUR
    from experiments.sft_allocation_acquisition.contract import SAMPLING,REVISION
    if config['run_id']!='pilot' or config['sampling']!=SAMPLING or config['teacher_revision']!=REVISION or config['max_seconds']!=5400:
        raise ValueError('Frozen pilot configuration differs')
    claims=modal.Dict.from_name('sft-allocation-midpoint-claims-v1',create_if_missing=False)
    volume.reload()
    gate=config['main_gate']
    main_audit=read(Path('/evidence/mp-completion-20261012-r1/audit.json'))
    terminal=claims.get('midpoint/mp-completion-20261012-r1/terminal/audit')
    if terminal!=gate['terminal'] or terminal['status']!='completed' or digest(main_audit)!=terminal['evidence_sha256']:
        raise ValueError('Main independent audit gate differs')
    if len([k for k in main_audit if not k.startswith('_')])!=9:
        raise ValueError('Main gate is incomplete')
    if not isinstance(gate.get('local_closeout_sha256'),str) or len(gate['local_closeout_sha256'])!=64:
        raise ValueError('Local verification binding absent')
    guard=RunGuard(claims,plan);guard.register(now_epoch=time.time())
    for name,value in release['source_files'].items():
        if sha(Path('/workspace')/name)!=value:raise ValueError('Source bytes differ')
    reserve=plan['slots']['pilot']['reserved_cents']
    if reserve<1000:raise ValueError('Insufficient reservation including startup/host resources')
    admission=guard.admit(dict(run_id='pilot',config_sha256=digest(config),source_sha256=digest(release['source_files']),
        data_sha256=config['input_sha256']),attempt_id=uuid.uuid4().hex,now_epoch=time.time(),max_runtime_seconds=5460)
    started=time.time();stop=min(started+5400,plan['deadline_epoch']-30)
    timer=threading.Timer(max(1,stop-time.time()),lambda:os._exit(124));timer.daemon=True;timer.start()
    out=Path('/evidence')/plan['campaign_id']/'pilot';recorder=None
    class Journal:
        commit=staticmethod(volume.commit)
        def check(self):
            if time.time()>stop-60:raise TimeoutError('Finite pilot deadline')
            guard.check_active(admission,now_epoch=time.time(),spent_cents=0,next_cost_cents=reserve)
        def begin(self,name,value):
            self.check()
            if not claims.put(guard.prefix+'pilot/unit/'+name,value,skip_if_exists=True):raise ValueError('Attempt already exists')
            dump(out/'intents'/(name+'.json'),value)
        def end(self,name,value):
            dump(out/'completed'/(name+'.json'),value)
            if not claims.put(guard.prefix+'pilot/done/'+name,value,skip_if_exists=True):raise ValueError('Completion already exists')
    try:
        volume.reload();out.mkdir(parents=True,exist_ok=False)
        dump(out/'intent.json',dict(config=config,plan=plan,release=release,started_epoch=started,reserved_cents=reserve))
        assets=Path('/evidence')/plan['campaign_id']/'assets'
        if sha(assets/'inputs/manifest.json')!=config['input_sha256']:raise ValueError('Input hash differs')
        recorder=GPURecorder(out);recorder.start()
        result=run(assets,out,Journal())
        recorder.stop();recorder=None
        result.update(wall_seconds=time.time()-started,reserved_cost_usd=reserve/100,
            runtime_rate_estimate_usd=(time.time()-started)*RATE_USD_PER_HOUR/3600,
            startup_and_asset_cost_excluded_from_runtime_estimate=True)
        dump(out/'result.json',result);volume.commit()
        files=manifest(out);dump(out/'artifact_manifest.json',files);volume.commit()
        receipt=guard.finish(admission,status='completed',evidence_sha256=digest(files),actual_cost_cents=reserve,finished_epoch=time.time())
        return dict(result=result,artifact_manifest=files,receipt=receipt)
    except BaseException as exc:
        if recorder:recorder.stop();recorder=None
        if out.exists():
            dump(out/'failure.json',dict(error_type=type(exc).__name__,error=str(exc),traceback=traceback.format_exc(),
                wall_seconds=time.time()-started,rule='Preserve all intents/raw/unknowns; no automatic replay.'))
            volume.commit();files=manifest(out);dump(out/'failure_manifest.json',files);volume.commit()
            guard.finish(admission,status='failed',evidence_sha256=digest(files),actual_cost_cents=reserve,finished_epoch=time.time())
        raise
    finally:timer.cancel()


@app.local_entrypoint()
def main(plan_json:str,config_json:str,receipt_dir:str):
    from experiments.sft_allocation_midpoint.common import sha,dump
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    remote=subprocess.check_output(['git','ls-remote','origin','refs/heads/codex/icml-acl-2027'],cwd=ROOT,text=True).split()[0]
    if commit!=remote:raise ValueError('Publish source first')
    for name in SOURCES:
        if subprocess.check_output(['git','show','HEAD:'+name],cwd=ROOT)!=(ROOT/name).read_bytes():raise ValueError('Unpublished source')
    plan=json.loads(Path(plan_json).read_text());config=json.loads(Path(config_json).read_text())
    out=Path(receipt_dir);out.mkdir(parents=True,exist_ok=False)
    release=dict(commit=commit,source_files={n:sha(ROOT/n) for n in SOURCES})
    dump(out/'intent.json',dict(plan=plan,config=config,release=release))
    result=pilot.remote(plan,config,release);dump(out/'result.json',result)

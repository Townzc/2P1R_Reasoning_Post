"""Bounded P007B acquisition only; no controller, automatic retry or student dispatch."""
import json
import subprocess
import sys
import time
from pathlib import Path
import modal

ROOT=Path(__file__).resolve().parents[2]
SOURCES=['src/real_math_audit.py','analyses/gsm8k_answer_audit.py','requirements.txt',
    'configs/acquisition_teacher.lock.json','reports/sft_allocation_midpoint_20261011/P007B_ADMISSION.json',
    *['experiments/sft_allocation_midpoint/'+n for n in ('guard.py','common.py','monitor.py')],
    *['experiments/sft_allocation_acquisition/'+n for n in ('contract.py','wallet.py','policy_contract.py',
                                                         'policy_runtime.py','modal_policy_runner.py')]]
app=modal.App('sft-allocation-cost-matched-acquisition')
volume=modal.Volume.from_name('sft-allocation-midpoint-v1',create_if_missing=False)
image=(modal.Image.debian_slim(python_version='3.12')
    .pip_install('torch==2.8.0',index_url='https://download.pytorch.org/whl/cu128')
    .pip_install_from_requirements(ROOT/'requirements.txt')
    .env({'PYTHONPATH':'/workspace','TOKENIZERS_PARALLELISM':'false',
          'HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1'}))
for name in SOURCES:image=image.add_local_file(ROOT/name,'/workspace/'+name,copy=True)


@app.function(image=image,gpu='H100!',cpu=(4,4),memory=(32768,32768),timeout=1900,startup_timeout=600,
    retries=0,max_containers=2,min_containers=0,buffer_containers=0,scaledown_window=2,
    single_use_containers=True,serialized=True,include_source=False,volumes={'/evidence':volume})
def acquire(plan,config,release):
    import os,sys,uuid,threading,traceback
    sys.path.insert(0,'/workspace')
    from experiments.sft_allocation_midpoint.common import dump,read,sha,digest,manifest
    from experiments.sft_allocation_midpoint.guard import RunGuard
    from experiments.sft_allocation_midpoint.monitor import GPURecorder
    from experiments.sft_allocation_acquisition.policy_runtime import run
    spec=read('/workspace/reports/sft_allocation_midpoint_20261011/P007B_ADMISSION.json')
    run_id=config['run_id']
    if (digest(plan)!=spec['plan_sha256'] or run_id not in spec['acquisition_config_sha256']
            or digest(config)!=spec['acquisition_config_sha256'][run_id]):
        raise ValueError('Unadmitted acquisition configuration')
    claims=modal.Dict.from_name('sft-allocation-midpoint-claims-v1',create_if_missing=False)
    volume.reload()
    gate=claims.get('midpoint/mp-teacher-cost-20261012-r1/terminal/pilot')
    if gate!=config['pilot_gate']['terminal'] or gate['status']!='completed':
        raise ValueError('Verified pilot gate differs')
    if len(config['pilot_gate']['local_audit_sha256'])!=64:
        raise ValueError('Local independent pilot verification is required')
    guard=RunGuard(claims,plan);guard.register(now_epoch=time.time())
    for name,value in release['source_files'].items():
        if sha(Path('/workspace')/name)!=value:raise ValueError('Source differs')
    admission=guard.admit(dict(run_id=run_id,config_sha256=digest(config),
        source_sha256=digest(release['source_files']),data_sha256=config['input_sha256']),
        attempt_id=uuid.uuid4().hex,now_epoch=time.time(),max_runtime_seconds=1860)
    started=time.time();stop=min(started+1800,plan['deadline_epoch']-30)
    timer=threading.Timer(max(1,stop-time.time()),lambda:os._exit(124));timer.daemon=True;timer.start()
    out=Path('/evidence')/plan['campaign_id']/run_id;recorder=None
    reserve=plan['slots'][run_id]['reserved_cents']
    class Journal:
        commit=staticmethod(volume.commit)
        def check(self):
            if time.time()>stop-60:raise TimeoutError('Finite acquisition deadline')
            guard.check_active(admission,now_epoch=time.time(),spent_cents=0,next_cost_cents=reserve)
        def begin(self,name,value):
            self.check()
            if not claims.put(guard.prefix+run_id+'/unit/'+name,value,skip_if_exists=True):
                raise ValueError('Batch already attempted')
            dump(out/'intents'/(name+'.json'),value)
        def end(self,name,value):
            dump(out/'completed'/(name+'.json'),value)
            if not claims.put(guard.prefix+run_id+'/done/'+name,value,skip_if_exists=True):
                raise ValueError('Duplicate completion')
    try:
        out.mkdir(parents=True,exist_ok=False)
        dump(out/'intent.json',dict(config=config,plan=plan,release=release,started_epoch=started,
            reserved_cents=reserve))
        inputs=Path('/evidence')/plan['campaign_id']/'inputs'
        if sha(inputs/'manifest.json')!=config['input_sha256']:raise ValueError('Input manifest differs')
        recorder=GPURecorder(out);recorder.start()
        result=run(Path('/evidence/mp-teacher-cost-20261012-r1/assets'),inputs,out,Journal(),config)
        recorder.stop();recorder=None
        result.update(wall_seconds=time.time()-started,reserved_cost_usd=reserve/100,
            closing_and_setup_cost_excluded_from_scientific_wallet=True,
            runtime_rate_estimate_usd=(time.time()-started)*config['hourly_nanodollars']/1e9/3600)
        dump(out/'result.json',result);volume.commit()
        files=manifest(out);dump(out/'artifact_manifest.json',files);volume.commit()
        receipt=guard.finish(admission,status='completed',evidence_sha256=digest(files),
            actual_cost_cents=reserve,finished_epoch=time.time())
        return dict(result=result,artifact_manifest=files,receipt=receipt)
    except BaseException as exc:
        if recorder:recorder.stop();recorder=None
        if out.exists():
            dump(out/'failure.json',dict(error_type=type(exc).__name__,error=str(exc),traceback=traceback.format_exc(),
                wall_seconds=time.time()-started,rule='Retain raw returns, unknown attempts and cost; no automatic replay.'))
            volume.commit();files=manifest(out);dump(out/'failure_manifest.json',files);volume.commit()
            guard.finish(admission,status='failed',evidence_sha256=digest(files),
                actual_cost_cents=reserve,finished_epoch=time.time())
        raise
    finally:timer.cancel()


@app.local_entrypoint()
def main(plan_json:str,config_json:str,receipt_dir:str):
    from experiments.sft_allocation_midpoint.common import dump,sha,digest
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    remote=subprocess.check_output(['git','ls-remote','origin','refs/heads/codex/icml-acl-2027'],cwd=ROOT,text=True).split()[0]
    if commit!=remote:raise ValueError('Publish source first')
    for name in SOURCES:
        if subprocess.check_output(['git','show','HEAD:'+name],cwd=ROOT)!=(ROOT/name).read_bytes():
            raise ValueError('Unpublished execution source')
    plan=json.loads(Path(plan_json).read_text());config=json.loads(Path(config_json).read_text())
    spec=json.loads((ROOT/'reports/sft_allocation_midpoint_20261011/P007B_ADMISSION.json').read_text())
    if digest(plan)!=spec['plan_sha256'] or digest(config)!=spec['acquisition_config_sha256'][config['run_id']]:
        raise ValueError('Local admission differs')
    # This is a local admission check in addition to permanent remote claims.
    containers=json.loads(subprocess.check_output([str(Path(sys.executable).with_name('modal')),'container','list','--json'],text=True))
    if len(containers)>=2:raise ValueError('Two-container ceiling; inspect before dispatch')
    claims=modal.Dict.from_name('sft-allocation-midpoint-claims-v1',create_if_missing=False)
    prefix='midpoint/'+plan['campaign_id']+'/'
    for key in ('claim/','terminal/','intent/'):
        if claims.get(prefix+key+config['run_id']) is not None:
            raise ValueError('Previously attempted or ambiguous slot; never dispatch again')
    out=Path(receipt_dir);out.mkdir(parents=True,exist_ok=False)
    release=dict(commit=commit,source_files={n:sha(ROOT/n) for n in SOURCES})
    dump(out/'intent.json',dict(plan=plan,config=config,release=release,admission_containers=containers))
    result=acquire.remote(plan,config,release);dump(out/'result.json',result)

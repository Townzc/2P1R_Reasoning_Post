"""Eight finite corrected-token-tariff slots; original two students remain pilots.

No acquisition dispatch, automatic retry or long-running controller. A local
operator checks actual providers/claims before each one-time call.
"""
import json
from pathlib import Path
import subprocess
import sys
import time
import modal
ROOT=Path(__file__).resolve().parents[2]
SOURCES=['src/sft_data.py','src/real_math_audit.py','analyses/completion_contract.py',
    'analyses/gsm8k_answer_audit.py','analyses/e017_stopping.py','analyses/e017_audit.py',
    *['experiments/sft_allocation_midpoint/'+n for n in ('guard.py','common.py','checkpoint.py','runtime.py','monitor.py')],
    *['experiments/sft_allocation_acquisition/'+n for n in ('token_contract.py','policy_contract.py','token_student_runtime.py','modal_token_student_runner.py')],
    'requirements.txt','configs/models.lock.json',
    'reports/sft_allocation_midpoint_20261011/P007B_TOKEN_RETIREMENT.json',
    'reports/sft_allocation_midpoint_20261011/P007B_TOKEN_STUDENT_ADMISSION.json']
app=modal.App('sft-allocation-token-tariff-students')
volume=modal.Volume.from_name('sft-allocation-midpoint-v1',create_if_missing=False)
image=(modal.Image.debian_slim(python_version='3.12')
    .pip_install('torch==2.8.0',index_url='https://download.pytorch.org/whl/cu128')
    .pip_install_from_requirements(ROOT/'requirements.txt').pip_install('peft==0.17.1')
    .env({'PYTHONPATH':'/workspace','CUBLAS_WORKSPACE_CONFIG':':4096:8',
          'TOKENIZERS_PARALLELISM':'false','HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1'}))
for name in SOURCES:image=image.add_local_file(ROOT/name,'/workspace/'+name,copy=True)


@app.function(image=image,gpu='H100!',cpu=(4,4),memory=(32768,32768),timeout=10900,startup_timeout=600,
    retries=0,max_containers=2,min_containers=0,buffer_containers=0,scaledown_window=2,
    single_use_containers=True,serialized=True,include_source=False,volumes={'/evidence':volume})
def student(plan,config,release):
    import os,uuid,threading,traceback,math
    sys.path.insert(0,'/workspace')
    from experiments.sft_allocation_midpoint.common import dump,read,sha,digest,manifest,verify
    from experiments.sft_allocation_midpoint.guard import RunGuard
    from experiments.sft_allocation_midpoint.monitor import GPURecorder
    from experiments.sft_allocation_midpoint import runtime
    from experiments.sft_allocation_acquisition.token_student_runtime import run
    spec=read('/workspace/reports/sft_allocation_midpoint_20261011/P007B_TOKEN_STUDENT_ADMISSION.json')
    run_id=config['run_id']
    if digest(plan)!=spec['plan_sha256'] or digest(config)!=spec['config_sha256'].get(run_id):
        raise ValueError('No exact published student admission')
    if config['max_seconds']!=10800 or plan['slots'][run_id]['reserved_cents']!=1800:
        raise ValueError('Finite student reservation differs')
    claims=modal.Dict.from_name('sft-allocation-midpoint-claims-v1',create_if_missing=False)
    volume.reload()
    for cell,gate in config['acquisition_gates'].items():
        terminal=claims.get('midpoint/'+gate['campaign']+'/terminal/'+gate['run_id'])
        if terminal!=gate['terminal'] or terminal['status']!='completed' or len(gate['local_audit_sha256'])!=64:
            raise ValueError('All acquisition audits must precede student training')
        directory=Path('/evidence')/gate['campaign']/gate['run_id']
        if digest(read(directory/'artifact_manifest.json'))!=terminal['evidence_sha256']:
            raise ValueError('Acquisition evidence changed')
    if set(config['acquisition_gates'])!={'breadth_p0','depth_p0','breadth_p4','depth_p4'}:
        raise ValueError('Missing acquisition cell')
    for name,value in release['source_files'].items():
        if sha(Path('/workspace')/name)!=value:raise ValueError('Unpublished source bytes')
    for name in ('breadth_p0_s17','depth_p0_s17'):
        prior=claims.get('midpoint/mp-policy-cost-20261012-r1/terminal/'+name)
        if not prior or prior['status']!='completed':
            raise ValueError('Both original pilots must complete before new dispatch')
    guard=RunGuard(claims,plan);guard.register(now_epoch=time.time())
    admission=guard.admit(dict(run_id=run_id,config_sha256=digest(config),
        source_sha256=digest(release['source_files']),data_sha256=config['input_sha256']),
        attempt_id=uuid.uuid4().hex,now_epoch=time.time(),max_runtime_seconds=10860)
    started=time.time();stop=min(started+10800,plan['deadline_epoch']-30)
    timer=threading.Timer(max(1,stop-time.time()),lambda:os._exit(124));timer.daemon=True;timer.start()
    out=Path('/evidence')/plan['campaign_id']/run_id;recorder=None
    reserve=plan['slots'][run_id]['reserved_cents']
    def check():
        if time.time()>stop-60:raise TimeoutError('Finite student deadline')
        guard.check_active(admission,now_epoch=time.time(),spent_cents=0,next_cost_cents=reserve)
    try:
        out.mkdir(parents=True,exist_ok=False)
        dump(out/'intent.json',dict(config=config,plan=plan,release=release,started_epoch=started,reserved_cents=reserve))
        inputs=Path('/evidence')/plan['campaign_id']/'student_inputs'
        if sha(inputs/'manifest.json')!=config['input_sha256']:raise ValueError('Student inputs differ')
        assets=Path('/evidence/mp-engineering-20261012-r1/assets')
        verify(assets,read(assets/'result.json')['files'])
        environment=runtime.environment(expected_gpu='H100');dump(out/'environment.json',environment)
        volume.commit();recorder=GPURecorder(out);recorder.start()
        identity=dict(config=config,source_commit=release['commit'],source_sha256=digest(release['source_files']))
        journal=runtime.Journal(out,'midpoint/'+plan['campaign_id']+'/'+run_id,claims,volume.commit,check)
        result=run(assets,inputs,out,journal,identity)
        recorder.stop();recorder=None
        result.update(wall_seconds=time.time()-started,reserved_cost_usd=reserve/100,provider_invoice_usd=None,
                      runtime_rate_estimate_usd=(time.time()-started)*4.3952/3600)
        dump(out/'result.json',result);volume.commit();files=manifest(out)
        dump(out/'artifact_manifest.json',files);volume.commit()
        receipt=guard.finish(admission,status='completed',evidence_sha256=digest(files),
            actual_cost_cents=reserve,finished_epoch=time.time())
        return dict(result=result,artifact_manifest=files,receipt=receipt)
    except BaseException as exc:
        if recorder:recorder.stop();recorder=None
        if out.exists():
            dump(out/'failure.json',dict(error_type=type(exc).__name__,error=str(exc),traceback=traceback.format_exc(),
                wall_seconds=time.time()-started,rule='Keep all checkpoints, updates and ambiguous intents. Never replay automatically.'))
            volume.commit();files=manifest(out);dump(out/'failure_manifest.json',files);volume.commit()
            guard.finish(admission,status='failed',evidence_sha256=digest(files),actual_cost_cents=reserve,finished_epoch=time.time())
        raise
    finally:timer.cancel()


@app.function(image=image,cpu=(2,2),memory=(8192,8192),timeout=3400,startup_timeout=300,
    retries=0,max_containers=1,min_containers=0,buffer_containers=0,scaledown_window=2,
    single_use_containers=True,serialized=True,include_source=False,volumes={'/evidence':volume})
def audit_cloud(plan,config,release):
    import os,uuid,threading,traceback
    sys.path.insert(0,'/workspace')
    from experiments.sft_allocation_midpoint.common import dump,read,verify,sha,digest,manifest
    from experiments.sft_allocation_midpoint.guard import RunGuard
    from experiments.sft_allocation_midpoint import checkpoint as ck
    spec=read('/workspace/reports/sft_allocation_midpoint_20261011/P007B_TOKEN_STUDENT_ADMISSION.json')
    if (config['run_id']!='audit' or digest(config)!=spec['config_sha256']['audit'] or
            digest(plan)!=spec['plan_sha256'] or config['max_seconds']!=3300):
        raise ValueError('Unadmitted final audit')
    claims=modal.Dict.from_name('sft-allocation-midpoint-claims-v1',create_if_missing=False)
    expected={f'{c}_s{s}' for c in ('breadth_p0','depth_p0','breadth_p4','depth_p4') for s in (17,23)}
    if set(config['student_runs'])!=expected:raise ValueError('Audit roster differs')
    for name in expected:
        terminal=claims.get('midpoint/'+plan['campaign_id']+'/terminal/'+name)
        if not terminal or terminal['status']!='completed':raise ValueError('Student not finished; do not dispatch audit yet')
    for name,value in release['source_files'].items():
        if sha(Path('/workspace')/name)!=value:raise ValueError('Source differs')
    for name in ('breadth_p0_s17','depth_p0_s17'):
        prior=claims.get('midpoint/mp-policy-cost-20261012-r1/terminal/'+name)
        if not prior or prior['status']!='completed':
            raise ValueError('Both original pilots must complete before new dispatch')
    guard=RunGuard(claims,plan);guard.register(now_epoch=time.time())
    admission=guard.admit(dict(run_id='audit',config_sha256=digest(config),data_sha256=config['input_sha256'],
        source_sha256=digest(release['source_files'])),attempt_id=uuid.uuid4().hex,
        now_epoch=time.time(),max_runtime_seconds=3360)
    timer=threading.Timer(3300,lambda:os._exit(124));timer.daemon=True;timer.start()
    base=Path('/evidence')/plan['campaign_id'];out=base/'audit'
    try:
        volume.reload();out.mkdir(exist_ok=False)
        dump(out/'intent.json',dict(plan=plan,config=config,release=release));results={}
        roster=[(name,spec['inputs_manifest']['acquisition_audits'][name]['campaign'],name) for name in ('breadth_p0','depth_p0','breadth_p4','depth_p4')]
        roster += [(name,plan['campaign_id'],name) for name in sorted(expected)]
        roster += [('original_pilot_'+name,'mp-policy-cost-20261012-r1',name) for name in ('breadth_p0_s17','depth_p0_s17')]
        for label,source_campaign,name in roster:
            guard.check_active(admission,now_epoch=time.time(),spent_cents=0,next_cost_cents=300)
            folder=Path('/evidence')/source_campaign/name;files=read(folder/'artifact_manifest.json')
            terminal=claims.get('midpoint/'+source_campaign+'/terminal/'+name)
            if not terminal or terminal['status']!='completed' or digest(files)!=terminal['evidence_sha256']:
                raise ValueError('Result/terminal binding differs')
            verify(folder,files);checkpoints={}
            for path in sorted(folder.glob('checkpoint_*')):
                state=ck.load(path);checkpoints[path.name]=read(path/'manifest.json');del state
            results[label]=dict(source_campaign=source_campaign,files_verified=len(files),manifest_digest=digest(files),terminal=terminal,
                               checkpoints=checkpoints,result=read(folder/'result.json'))
            dump(out/(label+'.json'),results[label]);volume.commit()
        dump(out/'result.json',results);volume.commit();files=manifest(out)
        dump(out/'artifact_manifest.json',files);volume.commit()
        receipt=guard.finish(admission,status='completed',evidence_sha256=digest(files),actual_cost_cents=300,finished_epoch=time.time())
        return dict(result=results,artifact_manifest=files,receipt=receipt)
    except BaseException as exc:
        if out.exists():
            dump(out/'failure.json',dict(error_type=type(exc).__name__,error=str(exc),traceback=traceback.format_exc(),
                rule='Retain prior results and partial audit. No repeated model work.'))
            volume.commit();files=manifest(out);dump(out/'failure_manifest.json',files);volume.commit()
            guard.finish(admission,status='failed',evidence_sha256=digest(files),actual_cost_cents=300,finished_epoch=time.time())
        raise
    finally:timer.cancel()


@app.local_entrypoint()
def main(plan_json:str,config_json:str,receipt_dir:str):
    from experiments.sft_allocation_midpoint.common import dump,sha,digest
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    remote=subprocess.check_output(['git','ls-remote','origin','refs/heads/codex/icml-acl-2027'],cwd=ROOT,text=True).split()[0]
    if commit!=remote:raise ValueError('Publish first')
    for name in SOURCES:
        if subprocess.check_output(['git','show','HEAD:'+name],cwd=ROOT)!=(ROOT/name).read_bytes():raise ValueError('Unpublished source')
    plan=json.loads(Path(plan_json).read_text());config=json.loads(Path(config_json).read_text())
    spec=json.loads((ROOT/'reports/sft_allocation_midpoint_20261011/P007B_TOKEN_STUDENT_ADMISSION.json').read_text())
    if digest(plan)!=spec['plan_sha256'] or digest(config)!=spec['config_sha256'].get(config['run_id']):raise ValueError('No exact admission')
    pilots=Path(plan_json).parent/'PRIOR_PILOTS_VERIFIED.json'
    if not pilots.exists():raise ValueError('Close out and independently audit both retained pilots first')
    pilot_proof=json.loads(pilots.read_text())
    if not pilot_proof['both_passed'] or not pilot_proof['both_provider_stopped']:raise ValueError('Unverified prior pilots')
    containers=json.loads(subprocess.check_output([str(Path(sys.executable).with_name('modal')),'container','list','--json'],text=True))
    if len(containers)>=2:raise ValueError('Global two-GPU ceiling')
    claims=modal.Dict.from_name('sft-allocation-midpoint-claims-v1',create_if_missing=False)
    for kind in ('claim','intent','terminal'):
        if claims.get('midpoint/'+plan['campaign_id']+'/'+kind+'/'+config['run_id']) is not None:
            raise ValueError('Slot previously attempted/ambiguous; do not dispatch')
    out=Path(receipt_dir);out.mkdir(parents=True,exist_ok=False)
    release=dict(commit=commit,source_files={n:sha(ROOT/n) for n in SOURCES})
    dump(out/'intent.json',dict(plan=plan,config=config,release=release,admission_containers=containers))
    result=(audit_cloud if config['run_id']=='audit' else student).remote(plan,config,release)
    dump(out/'result.json',result)

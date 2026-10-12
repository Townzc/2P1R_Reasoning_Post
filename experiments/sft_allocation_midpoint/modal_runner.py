"""Bounded ephemeral Modal model jobs, atomically admitted once per immutable slot."""
import json
from pathlib import Path
import subprocess
import time
import modal

ROOT=Path(__file__).resolve().parents[2]
SOURCE_FILES=[
    'src/sft_data.py','src/real_math_audit.py',
    'analyses/completion_contract.py','analyses/gsm8k_answer_audit.py',
    'analyses/e017_stopping.py','analyses/e017_audit.py',
    *['experiments/sft_allocation_midpoint/'+n for n in ('guard.py','common.py','checkpoint.py','runtime.py','dispatch.py','monitor.py','completion.py','modal_runner.py')],
    'requirements.txt','configs/models.lock.json']
app=modal.App('sft-allocation-midpoint-models')
volume=modal.Volume.from_name('sft-allocation-midpoint-v1',create_if_missing=False)
image=(modal.Image.debian_slim(python_version='3.12')
       .pip_install('torch==2.8.0',index_url='https://download.pytorch.org/whl/cu128')
       .pip_install_from_requirements(ROOT/'requirements.txt')
       .pip_install('peft==0.17.1')
       .env({'PYTHONPATH':'/workspace','CUBLAS_WORKSPACE_CONFIG':':4096:8',
             'TOKENIZERS_PARALLELISM':'false','HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1'}))
for name in SOURCE_FILES:image=image.add_local_file(ROOT/name,'/workspace/'+name,copy=True)
OPTIONS=dict(image=image,cpu=(4,4),memory=(32768,32768),timeout=7200,startup_timeout=600,
             retries=0,max_containers=2,min_containers=0,buffer_containers=0,scaledown_window=2,
             single_use_containers=True,serialized=True,include_source=False,volumes={'/evidence':volume})


@app.function(gpu='A100-80GB',**OPTIONS)
def run_gpu(plan,config,release):
    import os,sys,threading,uuid,traceback
    sys.path.insert(0,'/workspace')
    from experiments.sft_allocation_midpoint.common import dump,digest,sha,manifest,verify,read
    from experiments.sft_allocation_midpoint.guard import RunGuard
    from experiments.sft_allocation_midpoint import runtime
    from experiments.sft_allocation_midpoint.monitor import GPURecorder
    # Construct lazy network handles inside the worker, not in serialized globals.
    claims=modal.Dict.from_name('sft-allocation-midpoint-claims-v1',create_if_missing=False)
    for name,expected in release['source_files'].items():
        if sha(Path('/workspace')/name)!=expected:raise ValueError('Published image source differs')
    guard=RunGuard(claims,plan);guard.register(now_epoch=time.time())
    seconds=config['max_seconds']
    if not 60<=seconds<=6600:raise ValueError('Invalid finite job duration')
    admission=guard.admit(dict(run_id=config['run_id'],config_sha256=digest(config),
        source_sha256=digest(release['source_files']),data_sha256=config['input_sha256']),
        attempt_id=uuid.uuid4().hex,now_epoch=time.time(),max_runtime_seconds=seconds+60)
    started=time.time();stop_at=min(started+seconds,plan['deadline_epoch']-30)
    timer=threading.Timer(max(1,stop_at-time.time()),lambda:os._exit(124));timer.daemon=True;timer.start()
    out=Path('/evidence')/plan['campaign_id']/config['run_id']
    reserve=plan['slots'][config['run_id']]['reserved_cents']
    # Reserve includes 600s startup and host resources, rather than model time alone.
    if reserve<math_cost_cents(seconds+600):raise ValueError('Insufficient conservative GPU reservation')
    def check():
        if time.time()>stop_at-30:raise TimeoutError('Finite work deadline; preserve closeout time')
        guard.check_active(admission,now_epoch=time.time(),spent_cents=0,next_cost_cents=reserve)
    recorder=None
    try:
        volume.reload();out.mkdir(parents=True,exist_ok=False)
        dump(out/'intent.json',dict(config=config,release=release,plan=plan,started_epoch=started,
                                    reserved_cents=reserve))
        assets=Path('/evidence')/config['asset_campaign']/'assets'
        if sha(assets/'inputs/manifest.json')!=config['input_sha256']:raise ValueError('Input release differs')
        verify(assets,read(assets/'result.json')['files'])
        environment=runtime.environment()
        dump(out/'environment.json',environment);volume.commit()
        recorder=GPURecorder(out);recorder.start()
        identity=dict(config=config,source_commit=release['commit'],source_sha256=digest(release['source_files']))
        journal=runtime.Journal(out,'midpoint/'+plan['campaign_id']+'/'+config['run_id'],claims,volume.commit,check)
        kind=config['kind']
        if kind=='engineering':result=runtime.engineering(assets,out,journal,identity)
        elif kind=='resume':
            profile=Path('/evidence')/config['profile_campaign']/'profile'
            result=runtime.resume_probe(assets,profile,out,journal,identity)
        elif kind=='main':
            if config['arm'] not in ('repeat','solutions','mixed','breadth') or config['seed'] not in (17,23):
                raise ValueError('Unapproved arm or seed')
            gates=Path('/evidence')/config['profile_campaign']
            if not read(gates/'profile/result.json')['engineering_fit_gate'] or not read(gates/'resume/result.json')['recovery_gate']:
                raise ValueError('Engineering admission gates not passed')
            independent=read(gates/'audit.json')
            for name in ('profile','resume'):
                if independent[name]['manifest_sha256']!=sha(gates/name/'artifact_manifest.json'):
                    raise ValueError('Independent engineering verification differs')
            result=runtime.main_train(assets,out,journal,identity,config['arm'],config['seed'])
        elif kind=='continue_main':
            from experiments.sft_allocation_midpoint.completion import continue_main
            recovery=config['recovery']
            parent_prefix='midpoint/'+recovery['parent_campaign']+'/'
            if (config['run_id']!='breadth_17_resume' or config['arm']!='breadth' or config['seed']!=17 or
                    claims.get(parent_prefix+'terminal/breadth_17')!=recovery['parent_terminal'] or
                    recovery['parent_terminal']['status']!='failed' or
                    recovery['parent_terminal']['evidence_sha256']!=recovery['failure_manifest_digest'] or
                    claims.get(parent_prefix+'terminal/controller')!=recovery['controller_terminal'] or
                    recovery['controller_terminal']['status']!='failed'):
                raise ValueError('Stateful continuation does not match failed parent')
            parent=Path('/evidence')/recovery['parent_campaign']/'breadth_17'
            if 'zero_work_attempt' in recovery:
                zero=recovery['zero_work_attempt'];old_prefix='midpoint/'+zero['campaign']+'/'
                zroot=Path('/evidence')/zero['campaign']/'breadth_17_resume'
                zfiles=read(zroot/'failure_manifest.json')
                if (claims.get(old_prefix+'terminal/breadth_17_resume')!=zero['terminal'] or
                        zero['terminal']['status']!='failed' or digest(zfiles)!=zero['terminal']['evidence_sha256'] or
                        any(n.startswith(('intents/','completed/','checkpoint_','observed80_','endpoint431')) for n in zfiles) or
                        any(claims.get(old_prefix+'breadth_17_resume/unit/'+n) is not None for n in
                            ('update_0129','observed80_step128_remaining_batch_0000'))):
                    raise ValueError('Failed preflight may have attempted work; refuse replay')
                verify(zroot,zfiles)
            result=continue_main(assets,parent,out,journal,config,environment)
        elif kind=='base':
            model,tok=runtime.new_model(assets/'model',17,adapt=False)
            result=dict(status='completed',committed_updates=0,physical_generated_outputs=431,
                endpoint=runtime.evaluate(model,tok,runtime.read_jsonl(assets/'inputs/endpoint431.jsonl'),out,'endpoint431',journal))
        else:raise ValueError('Unapproved kind')
        result.update(wall_seconds=time.time()-started,reserved_cost_usd=reserve/100,provider_invoice_usd=None,
                      runtime_rate_estimate_usd=(time.time()-started)*2.942784/3600)
        recorder.stop();recorder=None
        dump(out/'result.json',result);volume.commit()
        files=manifest(out);dump(out/'artifact_manifest.json',files);volume.commit()
        receipt=guard.finish(admission,status='completed',evidence_sha256=digest(files),
                             actual_cost_cents=reserve,finished_epoch=time.time())
        return dict(result=result,artifact_manifest=files,receipt=receipt)
    except BaseException as exc:
        if recorder is not None:recorder.stop();recorder=None
        if out.exists():
            failure=dict(status='failed',error=repr(exc),traceback=traceback.format_exc(),wall_seconds=time.time()-started,
                         instruction='Preserve completed, attempted and ambiguous work. Reconcile before any continuation.')
            dump(out/'failure.json',failure);volume.commit()
            files=manifest(out);dump(out/'failure_manifest.json',files);volume.commit()
            guard.finish(admission,status='failed',evidence_sha256=digest(files),actual_cost_cents=reserve,finished_epoch=time.time())
        raise
    finally:timer.cancel()


def math_cost_cents(seconds):
    import math
    return math.ceil(seconds*2.942784/36)+25


@app.function(image=image,cpu=(2,2),memory=(8192,8192),timeout=3600,startup_timeout=300,
              retries=0,max_containers=1,min_containers=0,buffer_containers=0,scaledown_window=2,
              single_use_containers=True,serialized=True,include_source=False,volumes={'/evidence':volume})
def audit(plan,config,release):
    import sys,uuid,threading,os
    sys.path.insert(0,'/workspace')
    from experiments.sft_allocation_midpoint.common import read,verify,digest,sha,dump
    from experiments.sft_allocation_midpoint.guard import RunGuard
    claims=modal.Dict.from_name('sft-allocation-midpoint-claims-v1',create_if_missing=False)
    guard=RunGuard(claims,plan);guard.register(now_epoch=time.time())
    seconds=config['max_seconds']
    if not 60<=seconds<=3300:raise ValueError('Invalid bounded CPU audit duration')
    admission=guard.admit(dict(run_id='audit',config_sha256=digest(config),source_sha256=digest(release['source_files']),
        data_sha256=config['input_sha256']),attempt_id=uuid.uuid4().hex,now_epoch=time.time(),max_runtime_seconds=seconds)
    timer=threading.Timer(seconds,lambda:os._exit(124));timer.daemon=True;timer.start()
    try:
        volume.reload();root=Path('/evidence')/plan['campaign_id'];results={}
        names=config.get('audit_runs',['profile','resume'])
        allowed={'profile','resume','base'} | {f'{a}_{s}' for a in ('repeat','solutions','mixed','breadth') for s in (17,23)}
        if not names or len(names)!=len(set(names)) or set(names)-allowed:raise ValueError('Unapproved audit targets')
        for name in names:
            guard.check_active(admission,now_epoch=time.time(),spent_cents=0,next_cost_cents=100)
            source=config.get('audit_sources',{}).get(name,[plan['campaign_id'],name])
            if (len(source)!=2 or any('/' in x or '..' in x for x in source) or
                    source[1] not in allowed|{'breadth_17_resume'}):raise ValueError('Unsafe audit source')
            directory=Path('/evidence')/source[0]/source[1]
            files=read(directory/'artifact_manifest.json');verify(directory,files)
            results[name]=dict(files_verified=len(files),manifest_sha256=sha(directory/'artifact_manifest.json'),
                source=source,
                checkpoints={str(p.parent.name):read(p) for p in directory.glob('checkpoint_*/manifest.json')},
                result=read(directory/'result.json'))
            dump(root/f'audit_progress_{name}.json',results[name]);volume.commit()
        if 'parent_failure' in config:
            parent=config['parent_failure']
            if parent['run']!='breadth_17' or '/' in parent['campaign'] or '..' in parent['campaign']:
                raise ValueError('Unexpected failure audit source')
            directory=Path('/evidence')/parent['campaign']/parent['run']
            files=read(directory/'failure_manifest.json')
            if digest(files)!=parent['manifest_digest']:raise ValueError('Failure audit binding changed')
            verify(directory,files)
            results['_failed_parent_breadth17']=dict(files_verified=len(files),manifest_digest=digest(files),
                source=[parent['campaign'],parent['run']],status='failed_preserved')
        dump(root/'audit.json',results);volume.commit()
        receipt=guard.finish(admission,status='completed',evidence_sha256=digest(results),actual_cost_cents=100,finished_epoch=time.time())
        return dict(results=results,receipt=receipt)
    finally:timer.cancel()


@app.local_entrypoint()
def main(plan_json:str,config_json:str,receipt_dir:str):
    from experiments.sft_allocation_midpoint.common import sha,dump
    plan=json.loads(Path(plan_json).read_text());config=json.loads(Path(config_json).read_text());out=Path(receipt_dir)
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    remote=subprocess.check_output(['git','ls-remote','origin','refs/heads/codex/icml-acl-2027'],cwd=ROOT,text=True).split()[0]
    if commit!=remote:raise ValueError('Publish source on assigned branch before execution')
    for name in SOURCE_FILES:
        if subprocess.check_output(['git','show','HEAD:'+name],cwd=ROOT)!=(ROOT/name).read_bytes():
            raise ValueError('Source differs from published commit: '+name)
    release=dict(commit=commit,source_files={name:sha(ROOT/name) for name in SOURCE_FILES})
    out.mkdir(parents=True,exist_ok=False);dump(out/'intent.json',dict(plan=plan,config=config,release=release))
    try:
        result=audit.remote(plan,config,release) if config['kind']=='audit' else run_gpu.remote(plan,config,release)
        dump(out/'result.json',result)
    finally:
        claims=modal.Dict.from_name('sft-allocation-midpoint-claims-v1',create_if_missing=False)
        prefix='midpoint/'+plan['campaign_id']+'/'
        dump(out/'admission_ledger.json',{k:v for k,v in claims.items() if k.startswith(prefix)})


@app.local_entrypoint()
def grid(plan_json:str,queue_json:str,receipt_dir:str):
    """Four paired-seed conditions, at most two concurrent jobs; stop after a failed pair."""
    from experiments.sft_allocation_midpoint.common import sha,dump
    plan=json.loads(Path(plan_json).read_text());queue=json.loads(Path(queue_json).read_text());out=Path(receipt_dir)
    expected=[(arm,seed) for arm in ('repeat','solutions','breadth','mixed') for seed in (17,23)]
    if [(c.get('arm'),c.get('seed')) for c in queue]!=expected or any(c['kind']!='main' for c in queue):
        raise ValueError('Exactly the approved eight-run queue is required')
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    remote=subprocess.check_output(['git','ls-remote','origin','refs/heads/codex/icml-acl-2027'],cwd=ROOT,text=True).split()[0]
    if commit!=remote:raise ValueError('Publish first')
    for name in SOURCE_FILES:
        if subprocess.check_output(['git','show','HEAD:'+name],cwd=ROOT)!=(ROOT/name).read_bytes():
            raise ValueError('Execution source differs: '+name)
    release=dict(commit=commit,source_files={name:sha(ROOT/name) for name in SOURCE_FILES})
    out.mkdir(parents=True,exist_ok=False);dump(out/'intent.json',dict(plan=plan,queue=queue,release=release))
    completed=[]
    try:
        for start in range(0,8,2):
            results=list(run_gpu.starmap([(plan,c,release) for c in queue[start:start+2]],return_exceptions=True))
            failed=False
            for config,result in zip(queue[start:start+2],results):
                if isinstance(result,BaseException):
                    failed=True;dump(out/(config['run_id']+'_failure.json'),{'error':repr(result)})
                else:
                    dump(out/(config['run_id']+'_result.json'),result);completed.append(config['run_id'])
            if failed:raise RuntimeError('A main pair failed; future inputs remain unattempted, reconcile first')
        dump(out/'completed.json',dict(run_ids=completed,status='all_eight_completed'))
    finally:
        claims=modal.Dict.from_name('sft-allocation-midpoint-claims-v1',create_if_missing=False)
        prefix='midpoint/'+plan['campaign_id']+'/'
        dump(out/'admission_ledger.json',{k:v for k,v in claims.items() if k.startswith(prefix)})


@app.function(image=image,cpu=(1,1),memory=(1024,1024),timeout=40000,startup_timeout=300,
              retries=0,max_containers=1,min_containers=0,buffer_containers=0,scaledown_window=2,
              nonpreemptible=True,single_use_containers=True,serialized=True,include_source=False,volumes={'/evidence':volume})
def controller(plan,queue,base_config,audit_config,release,binding=None):
    """Finite cloud parent survives a disconnected laptop; every child owns one claim."""
    import sys,uuid,os,threading,traceback
    sys.path.insert(0,'/workspace')
    from experiments.sft_allocation_midpoint.common import dump,digest,manifest,sha
    from experiments.sft_allocation_midpoint.guard import RunGuard
    from experiments.sft_allocation_midpoint.dispatch import spawn_once,wait_existing,validate_replacement
    from experiments.sft_allocation_midpoint.completion import validate_completion
    remaining=binding is not None and binding.get('schema')=='remaining_work_v1'
    expected=[(a,s) for a in ('repeat','solutions','breadth','mixed') for s in (17,23)]
    if not remaining and ([(c['arm'],c['seed']) for c in queue]!=expected or any(c['kind']!='main' for c in queue)):
        raise ValueError('Only the exact eight-run scientific queue is permitted')
    if not remaining and (base_config['run_id']!='base' or base_config['kind']!='base' or audit_config['audit_runs']!=[c['run_id'] for c in queue]+['base']):
        raise ValueError('Base/audit queue mismatch')
    for name,value in release['source_files'].items():
        if sha(Path('/workspace')/name)!=value:raise ValueError('Controller image differs from published source')
    claims=modal.Dict.from_name('sft-allocation-midpoint-claims-v1',create_if_missing=False)
    guard=RunGuard(claims,plan);guard.register(now_epoch=time.time())
    if remaining:validate_completion(claims,plan,binding,queue,base_config,audit_config)
    elif binding is not None:validate_replacement(claims,plan,binding)
    reserve=plan['slots']['controller']['reserved_cents']
    if reserve<300:raise ValueError('Nonpreemptible CPU controller requires a three-dollar reservation')
    admission=guard.admit(dict(run_id='controller',config_sha256=digest([queue,base_config,audit_config,binding]),
        source_sha256=digest(release['source_files']),data_sha256=queue[0]['input_sha256']),
        attempt_id=uuid.uuid4().hex,now_epoch=time.time(),max_runtime_seconds=39000)
    timer=threading.Timer(39000,lambda:os._exit(124));timer.daemon=True;timer.start()
    out=Path('/evidence')/plan['campaign_id']/'controller'
    try:
        volume.reload();out.mkdir(parents=True,exist_ok=False)
        dump(out/'intent.json',dict(plan=plan,queue=queue,base_config=base_config,audit_config=audit_config,release=release,binding=binding));volume.commit()
        def check():guard.check_active(admission,now_epoch=time.time(),spent_cents=0,next_cost_cents=reserve)
        def spawn(config,function):
            name=config['run_id']
            def persist(suffix,record):
                dump(out/'dispatch'/f'{name}_{suffix}.json',record);volume.commit()
            return spawn_once(claims,'midpoint/'+plan['campaign_id']+'/dispatch/'+name,
                function,(plan,config,release),dict(run_id=name,config_sha256=digest(config)),persist)
        def wait(call,config):
            def failed():
                terminal=claims.get('midpoint/'+plan['campaign_id']+'/terminal/'+config['run_id'])
                return terminal is not None and terminal['status']!='completed'
            return wait_existing(call,check,failed)
        completed=[]
        for start in range(0,len(queue),2):
            check()
            pair=queue[start:start+2]
            calls=[spawn(c,run_gpu) for c in pair]
            results=[]
            for call,config in zip(calls,pair):
                try:results.append(wait(call,config))
                except Exception as exc:results.append(exc)
            volume.reload();failed=False
            for config,result in zip(queue[start:start+2],results):
                if isinstance(result,BaseException):
                    failed=True;dump(out/(config['run_id']+'_failure.json'),dict(error=repr(result)))
                else:
                    dump(out/(config['run_id']+'_result.json'),result);completed.append(config['run_id'])
            volume.commit()
            if failed:raise RuntimeError('One pair failed; later inputs remain unattempted. Reconcile, never replay.')
        check()
        base=wait(spawn(base_config,run_gpu),base_config)
        volume.reload();dump(out/'base_result.json',base);volume.commit()
        checked=wait(spawn(audit_config,audit),audit_config)
        volume.reload();dump(out/'audit_result.json',checked)
        result=dict(status='completed',main_runs=completed,base_completed=True,independent_audit_completed=True,
                    controller_reserved_usd=reserve/100,provider_invoice_usd=None)
        dump(out/'completed.json',result);volume.commit()
        guard.finish(admission,status='completed',evidence_sha256=digest(manifest(out)),actual_cost_cents=reserve,finished_epoch=time.time())
        return result
    except BaseException as exc:
        if out.exists():
            dump(out/'failure.json',dict(error=repr(exc),traceback=traceback.format_exc()));volume.commit()
            guard.finish(admission,status='failed',evidence_sha256=digest(manifest(out)),actual_cost_cents=reserve,finished_epoch=time.time())
        raise
    finally:timer.cancel()


@app.local_entrypoint()
def submit(plan_json:str,queue_json:str,base_json:str,audit_json:str,receipt_dir:str,amendment_json:str=''):
    """Use modal run --detach ...::submit, then inspect the actual cloud claims."""
    import sys
    from experiments.sft_allocation_midpoint.common import sha,dump
    if '--detach' not in sys.argv:raise ValueError('Detached app is required for the finite cloud controller')
    plan=json.loads(Path(plan_json).read_text());queue=json.loads(Path(queue_json).read_text())
    base=json.loads(Path(base_json).read_text());audit_config=json.loads(Path(audit_json).read_text())
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    remote=subprocess.check_output(['git','ls-remote','origin','refs/heads/codex/icml-acl-2027'],cwd=ROOT,text=True).split()[0]
    if commit!=remote:raise ValueError('Publish first')
    for name in SOURCE_FILES:
        if subprocess.check_output(['git','show','HEAD:'+name],cwd=ROOT)!=(ROOT/name).read_bytes():
            raise ValueError('Published source differs: '+name)
    release=dict(commit=commit,source_files={name:sha(ROOT/name) for name in SOURCE_FILES})
    claims=modal.Dict.from_name('sft-allocation-midpoint-claims-v1',create_if_missing=False)
    binding=json.loads(Path(amendment_json).read_text()) if amendment_json else None
    if binding is not None:
        if binding.get('schema')=='remaining_work_v1':
            from experiments.sft_allocation_midpoint.completion import validate_completion
            validate_completion(claims,plan,binding,queue,base,audit_config)
        else:
            from experiments.sft_allocation_midpoint.dispatch import validate_replacement
            validate_replacement(claims,plan,binding)
    if any(claims.get('midpoint/'+plan['campaign_id']+'/claim/'+name) is not None for name in plan['slots']):
        raise ValueError('A campaign input is already claimed; reconcile rather than resubmit')
    out=Path(receipt_dir);out.mkdir(parents=True,exist_ok=False)
    dump(out/'intent.json',dict(plan=plan,queue=queue,base_config=base,audit_config=audit_config,release=release,binding=binding))
    call=controller.spawn(plan,queue,base,audit_config,release,binding)
    dump(out/'submitted.json',dict(call_id=call.object_id,submitted_epoch=time.time(),campaign=plan['campaign_id']))
    print(json.dumps({'finite_controller_submitted':True,'call_id':call.object_id}),flush=True)


@app.local_entrypoint()
def submit_one(plan_json:str,config_json:str,receipt_dir:str):
    """One manually reconciled zero-work preflight repair; no controller or retry."""
    import sys
    from experiments.sft_allocation_midpoint.common import read,sha,dump,digest
    from experiments.sft_allocation_midpoint.dispatch import spawn_once
    if '--detach' not in sys.argv:raise ValueError('Use one detached finite call')
    plan=read(plan_json);config=read(config_json)
    if (set(plan['slots'])!={'breadth_17_resume'} or config['kind']!='continue_main' or
            config['run_id']!='breadth_17_resume' or 'zero_work_attempt' not in config['recovery']):
        raise ValueError('Only the reviewed zero-work resume repair is admitted')
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    remote=subprocess.check_output(['git','ls-remote','origin','refs/heads/codex/icml-acl-2027'],cwd=ROOT,text=True).split()[0]
    if commit!=remote:raise ValueError('Publish before execution')
    for name in SOURCE_FILES:
        if subprocess.check_output(['git','show','HEAD:'+name],cwd=ROOT)!=(ROOT/name).read_bytes():
            raise ValueError('Execution source is not published')
    release=dict(commit=commit,source_files={name:sha(ROOT/name) for name in SOURCE_FILES})
    claims=modal.Dict.from_name('sft-allocation-midpoint-claims-v1',create_if_missing=False)
    if claims.get('midpoint/'+plan['campaign_id']+'/claim/'+config['run_id']) is not None:
        raise ValueError('Already claimed; no repeat')
    out=Path(receipt_dir);out.mkdir(parents=True,exist_ok=False)
    dump(out/'intent.json',dict(plan=plan,config=config,release=release))
    call=spawn_once(claims,'midpoint/'+plan['campaign_id']+'/dispatch/'+config['run_id'],run_gpu,
        (plan,config,release),dict(run_id=config['run_id'],config_sha256=digest(config)),
        lambda suffix,record:dump(out/('dispatch_'+suffix+'.json'),record))
    dump(out/'submitted.json',dict(call_id=call.object_id,campaign=plan['campaign_id'],submitted_epoch=time.time()))
    print(json.dumps({'single_finite_call_submitted':call.object_id}),flush=True)

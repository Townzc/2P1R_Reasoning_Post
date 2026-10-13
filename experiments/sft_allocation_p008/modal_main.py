"""Prepared finite P008 main worker. No dispatch without numeric admission/review.

One slot per local invocation. Never retries an existing or uncertain call.
"""
from pathlib import Path
import json,subprocess,sys
import modal
ROOT=Path(__file__).resolve().parents[2]
SOURCES=['experiments/sft_allocation_acquisition/policy_contract.py', 'analyses/completion_contract.py', 'analyses/e017_audit.py', 'analyses/e017_stopping.py', 'analyses/gsm8k_answer_audit.py', 'configs/models.lock.json', 'experiments/sft_allocation_acquisition/contract.py', 'experiments/sft_allocation_midpoint/checkpoint.py', 'experiments/sft_allocation_midpoint/common.py', 'experiments/sft_allocation_midpoint/guard.py', 'experiments/sft_allocation_midpoint/monitor.py', 'experiments/sft_allocation_midpoint/runtime.py', 'experiments/sft_allocation_p008/contract.py', 'experiments/sft_allocation_p008/evidence_bundle.py', 'experiments/sft_allocation_p008/main_binding.py', 'experiments/sft_allocation_p008/modal_main.py', 'experiments/sft_allocation_p008/pool_runtime.py', 'experiments/sft_allocation_p008/procurement.py', 'experiments/sft_allocation_p008/requirements_teacher.txt', 'experiments/sft_allocation_p008/student_runtime.py', 'requirements.txt', 'src/real_math_audit.py', 'src/sft_data.py']
SPEC='reports/p008_20261013/main_admission_v1/ADMISSION.json'
app=modal.App('p008-finite-main')
volume=modal.Volume.from_name('sft-allocation-midpoint-v1',create_if_missing=False)
hf=(modal.Image.debian_slim(python_version='3.12')
 .pip_install('torch==2.8.0',index_url='https://download.pytorch.org/whl/cu128')
 .pip_install_from_requirements(ROOT/'requirements.txt').pip_install('peft==0.17.1'))
teacher=(modal.Image.debian_slim(python_version='3.12')
 .pip_install_from_requirements(ROOT/'experiments/sft_allocation_p008/requirements_teacher.txt'))
images=[]
for image in (hf,teacher):
 image=image.env({'PYTHONPATH':'/workspace','HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1',
 'TOKENIZERS_PARALLELISM':'false','CUBLAS_WORKSPACE_CONFIG':':4096:8','VLLM_USE_V1':'1'})
 for name in SOURCES:image=image.add_local_file(ROOT/name,'/workspace/'+name,copy=True)
 image=image.add_local_file(ROOT/SPEC,'/workspace/'+SPEC,copy=True)
 images.append(image)
hf,teacher=images


def work(plan,config,release,expected_roles):
 import os,time,threading,uuid,traceback
 sys.path.insert(0,'/workspace')
 from experiments.sft_allocation_midpoint.common import read,dump,sha,digest,verify,manifest
 from experiments.sft_allocation_midpoint.guard import RunGuard
 from experiments.sft_allocation_midpoint.runtime import Journal,environment
 from experiments.sft_allocation_midpoint.monitor import GPURecorder
 from experiments.sft_allocation_p008.main_binding import validate_binding
 from experiments.sft_allocation_p008.evidence_bundle import pack
 spec=read('/workspace/'+SPEC);role=config['role'];run=config['run_id']
 validate_binding(plan,config,release,spec)
 if role not in expected_roles:raise ValueError('Wrong finite worker')
 for n,h in release['source_files'].items():
  if sha(Path('/workspace')/n)!=h:raise ValueError('Published source changed')
 if set(release['source_files'])!=set(SOURCES):raise ValueError('Incomplete source binding')
 claims=modal.Dict.from_name('sft-allocation-midpoint-claims-v1',create_if_missing=False)
 for gate in release['gates']['required_terminals']:
  if claims.get('midpoint/'+gate['campaign']+'/terminal/'+gate['run_id'])!=gate['terminal'] or gate['terminal']['status']!='completed':
   raise ValueError('Required real terminal differs')
 guard=RunGuard(claims,plan);guard.register(now_epoch=time.time())
 admitted=guard.admit(dict(run_id=run,source_sha256=digest(release['source_files']),config_sha256=digest(config),data_sha256=config['input_sha256']),
  attempt_id=uuid.uuid4().hex,now_epoch=time.time(),max_runtime_seconds=config['max_seconds']+30)
 start=time.time();stop=min(start+config['max_seconds'],plan['deadline_epoch']-30)
 timer=threading.Timer(max(1,stop-time.time()),lambda:os._exit(124));timer.daemon=True;timer.start()
 reserve=plan['slots'][run]['reserved_cents'];out=Path('/evidence')/plan['campaign_id']/run;recorder=None
 def check():
  if time.time()>stop-30:raise TimeoutError('Finite P008 deadline')
  guard.check_active(admitted,now_epoch=time.time(),spent_cents=0,next_cost_cents=reserve)
 try:
  volume.reload();out.mkdir(parents=True,exist_ok=False)
  dump(out/'intent.json',dict(plan=plan,config=config,release=release,started_epoch=start,reserved_cents=reserve));dump(out/'admission.json',spec);volume.commit()
  inputs=out.parent/config['input_directory']
  if sha(inputs/'manifest.json')!=config['input_sha256']:raise ValueError('Input hash differs')
  verify(inputs,read(inputs/'manifest.json')['files'])
  assets=Path('/evidence')/('mp-teacher-cost-20261012-r1' if role=='pool' else 'mp-engineering-20261012-r1')/'assets'
  verify(assets,read(assets/'result.json')['files'])
  if role=='pool':
   import importlib.metadata,torch
   versions={n:importlib.metadata.version(n) for n in ('torch','vllm','transformers','tokenizers','numpy')}
   if not torch.cuda.is_available() or torch.cuda.device_count()!=1 or 'H100' not in torch.cuda.get_device_name(0):raise ValueError('One actual H100 required')
   checked={**versions,'torch':versions['torch'].split('+')[0]}
   if checked!={'torch':'2.8.0','vllm':'0.11.0','transformers':'4.56.2','tokenizers':'0.22.1','numpy':'2.2.6'}:raise ValueError('Pinned teacher environment differs')
   env=dict(versions=versions,gpu=torch.cuda.get_device_name(0),cuda=torch.version.cuda,nvidia_smi=subprocess.check_output(['nvidia-smi'],text=True))
  else:env=environment(expected_gpu='H100')
  dump(out/'environment.json',env);volume.commit()
  recorder=GPURecorder(out);recorder.start()
  journal=Journal(out,'midpoint/'+plan['campaign_id']+'/'+run,claims,volume.commit,check)
  identity=dict(config=config,source_commit=release['commit'],source_sha256=digest(release['source_files']))
  if role=='pool':
   from experiments.sft_allocation_p008.pool_runtime import run as execute
   result=execute(config,inputs,assets,out,journal)
  else:
   from experiments.sft_allocation_p008.student_runtime import run as execute
   result=execute(assets,inputs,out,journal,identity)
  recorder.stop();recorder=None
  result.update(wall_seconds=time.time()-start,reserved_cost_usd=reserve/100,provider_invoice_usd=None,
    runtime_rate_estimate_usd=(time.time()-start)*4.393584/3600)
  dump(out/'result.json',result);volume.commit();pack(out);volume.commit()
  files=manifest(out);dump(out/'artifact_manifest.json',files);volume.commit()
  receipt=guard.finish(admitted,status='completed',evidence_sha256=digest(files),actual_cost_cents=reserve,finished_epoch=time.time())
  return dict(result=result,artifact_manifest=files,receipt=receipt)
 except BaseException as exc:
  if recorder:recorder.stop();recorder=None
  if out.exists():
   dump(out/'failure.json',dict(error_type=type(exc).__name__,error=str(exc),traceback=traceback.format_exc(),wall_seconds=time.time()-start,
    rule='Preserve every unit, raw return and unknown. No automatic retry or claim reset.'))
   volume.commit();files=manifest(out);dump(out/'failure_manifest.json',files);volume.commit()
   guard.finish(admitted,status='failed',evidence_sha256=digest(files),actual_cost_cents=reserve,finished_epoch=time.time())
  raise
 finally:timer.cancel()


@app.function(image=teacher,gpu='H100!',cpu=(4,4),memory=(32768,32768),timeout=10900,startup_timeout=600,
 retries=0,max_containers=2,min_containers=0,buffer_containers=0,scaledown_window=2,
 single_use_containers=True,serialized=True,include_source=False,volumes={'/evidence':volume})
def pool_work(plan,config,release):
 return work(plan,config,release,('pool',))


@app.function(image=hf,gpu='H100!',cpu=(4,4),memory=(32768,32768),timeout=10900,startup_timeout=600,
 retries=0,max_containers=4,min_containers=0,buffer_containers=0,scaledown_window=2,
 single_use_containers=True,serialized=True,include_source=False,volumes={'/evidence':volume})
def student_work(plan,config,release):
 return work(plan,config,release,('main','bridge','base'))


@app.local_entrypoint()
def main(plan_json:str,config_json:str,gates_json:str,receipt_dir:str):
 from experiments.sft_allocation_midpoint.common import read,dump,sha,digest
 from experiments.sft_allocation_p008.main_binding import validate_binding
 import time
 plan=read(plan_json);cfg=read(config_json);gates=read(gates_json);spec=read(ROOT/SPEC);run=cfg['run_id']
 if cfg['role']=='pool' and time.time()>spec['start_no_later_epoch']:raise ValueError('Frozen forecast start window expired; hold for result-blind reconciliation')
 commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
 remote=subprocess.check_output(['git','ls-remote','origin','refs/heads/codex/icml-acl-2027'],cwd=ROOT,text=True).split()[0]
 if commit!=remote:raise ValueError('Ordinary publication required')
 files={n:sha(ROOT/n) for n in SOURCES}
 for n in SOURCES:
  if subprocess.check_output(['git','show','HEAD:'+n],cwd=ROOT)!=(ROOT/n).read_bytes():raise ValueError('Unpublished source')
 release=dict(commit=commit,source_files=files,gates=gates,spec_sha256=digest(spec));validate_binding(plan,cfg,release,spec)
 root=Path(plan_json).parent;destination=Path(receipt_dir)
 if destination.exists():raise ValueError('Existing local attempt: reconcile, never replay')
 claims=modal.Dict.from_name('sft-allocation-midpoint-claims-v1',create_if_missing=False)
 prefix='midpoint/'+plan['campaign_id']+'/'
 for kind in ('claim','intent','terminal'):
  if claims.get(prefix+kind+'/'+run) is not None:raise ValueError('Existing or uncertain remote attempt')
 # Single-owner sequential dispatcher: even a submitted call without a claim occupies a slot.
 occupied=[]
 for prior in root.glob('runs/*/dispatch_intent.json'):
  item=read(prior);name=item['run_id'];terminal=claims.get(prefix+'terminal/'+name)
  if terminal is None:occupied.append(name)
 cli=str(Path(sys.executable).with_name('modal'))
 containers=json.loads(subprocess.check_output([cli,'container','list','--json'],text=True))
 if len(occupied)>=4 or len(containers)>=4:raise ValueError('Four-GPU limit including uncertain submissions')
 # New main starts only after Phase0 release. Pool generation finishes before any student.
 if cfg['role']!='pool' and any(x.startswith('pool_') for x in occupied):raise ValueError('Pool worker still active/uncertain')
 if destination.resolve().parent!=(root/'runs').resolve() or destination.name!=run:raise ValueError('Receipt path must be canonical campaign runs/RUN')
 destination.mkdir(parents=True,exist_ok=False)
 dump(destination/'dispatch_intent.json',dict(run_id=run,config=cfg,plan=plan,release=release,provider_before=containers,occupied_before=occupied))
 fn=pool_work if cfg['role']=='pool' else student_work
 call=fn.spawn(plan,cfg,release);dump(destination/'submitted.json',dict(call_id=call.object_id))
 try:dump(destination/'result.json',call.get())
 except BaseException as exc:
  dump(destination/'return_error.json',dict(type=type(exc).__name__,error=str(exc)));raise

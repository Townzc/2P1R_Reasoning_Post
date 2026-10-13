"""One finite four-GPU Phase0 application, dispatched only after fixed-source G0."""
import json
from pathlib import Path
import subprocess
import sys
import modal
ROOT=Path(__file__).resolve().parents[2]
SOURCES=['src/sft_data.py','src/real_math_audit.py','analyses/completion_contract.py',
 'analyses/gsm8k_answer_audit.py','analyses/e017_stopping.py','analyses/e017_audit.py',
 *['experiments/sft_allocation_midpoint/'+n for n in ('guard.py','common.py','checkpoint.py','runtime.py','monitor.py')],
 'experiments/sft_allocation_acquisition/contract.py',
 *['experiments/sft_allocation_p008/'+n for n in ('contract.py','phase0_runtime.py','modal_phase0.py','requirements_teacher.txt')],
 'requirements.txt','configs/models.lock.json','reports/p008_20261013/PHASE0_ADMISSION.json']
app=modal.App('p008-finite-phase0')
volume=modal.Volume.from_name('sft-allocation-midpoint-v1',create_if_missing=False)
hf=(modal.Image.debian_slim(python_version='3.12')
 .pip_install('torch==2.8.0',index_url='https://download.pytorch.org/whl/cu128')
 .pip_install_from_requirements(ROOT/'requirements.txt').pip_install('peft==0.17.1'))
teacher_image=(modal.Image.debian_slim(python_version='3.12')
 .pip_install_from_requirements(ROOT/'experiments/sft_allocation_p008/requirements_teacher.txt'))
images=[]
for image in (hf,teacher_image):
 image=image.env({'PYTHONPATH':'/workspace','HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1',
    'TOKENIZERS_PARALLELISM':'false','CUBLAS_WORKSPACE_CONFIG':':4096:8','VLLM_USE_V1':'1'})
 for name in SOURCES:image=image.add_local_file(ROOT/name,'/workspace/'+name,copy=True)
 images.append(image)
hf,teacher_image=images


def work(plan,config,release,expected_roles):
 import os,time,threading,uuid,traceback
 sys.path.insert(0,'/workspace')
 from experiments.sft_allocation_midpoint.common import read,dump,sha,digest,verify,manifest
 from experiments.sft_allocation_midpoint.guard import RunGuard
 from experiments.sft_allocation_midpoint.runtime import Journal
 from experiments.sft_allocation_p008 import phase0_runtime as rt
 spec=read('/workspace/reports/p008_20261013/PHASE0_ADMISSION.json');role=config['run_id']
 if role not in expected_roles or digest(plan)!=spec['plan_sha256'] or digest(config)!=spec['config_sha256'].get(role):
  raise ValueError('Not the admitted Phase0 role/config')
 for name,value in release['source_files'].items():
  if sha(Path('/workspace')/name)!=value:raise ValueError('Published source bytes differ')
 if set(release['source_files'])!=set(SOURCES) or release['g0']['source_files']!=release['source_files'] or release['g0']['verdict'] not in ('PASS','PASS-WITH-NOTES'):
  raise ValueError('Fixed source G0 not accepted')
 if release['g0']['phase0_plan_sha256']!=digest(plan):raise ValueError('G0 plan differs')
 claims=modal.Dict.from_name('sft-allocation-midpoint-claims-v1',create_if_missing=False)
 guard=RunGuard(claims,plan);guard.register(now_epoch=time.time())
 admission=guard.admit(dict(run_id=role,source_sha256=digest(release['source_files']),
   config_sha256=digest(config),data_sha256=config['input_sha256']),attempt_id=uuid.uuid4().hex,
   now_epoch=time.time(),max_runtime_seconds=config['max_seconds']+30)
 start=time.time();stop=min(start+config['max_seconds'],plan['deadline_epoch']-30)
 timer=threading.Timer(max(1,stop-time.time()),lambda:os._exit(124));timer.daemon=True;timer.start()
 reserve=plan['slots'][role]['reserved_cents'];out=Path('/evidence')/plan['campaign_id']/role
 def check():
  if time.time()>stop-30:raise TimeoutError('Finite Phase0 deadline')
  guard.check_active(admission,now_epoch=time.time(),spent_cents=0,next_cost_cents=reserve)
 try:
  volume.reload();out.mkdir(parents=True,exist_ok=False)
  dump(out/'intent.json',dict(plan=plan,config=config,release=release,started_epoch=start,reserved_cents=reserve));volume.commit()
  concurrent=rt.gpu_probe(config,out,claims,'midpoint/'+plan['campaign_id'],volume,check)
  inputs=out.parent/'inputs'
  if sha(inputs/'manifest.json')!=config['input_sha256']:raise ValueError('Input manifest changed')
  verify(inputs,read(inputs/'manifest.json')['files'])
  journal=Journal(out,'midpoint/'+plan['campaign_id']+'/'+role,claims,volume.commit,check)
  if role=='teacher_calibration':
   assets=Path('/evidence/mp-teacher-cost-20261012-r1/assets');verify(assets,read(assets/'result.json')['files'])
   result=rt.teacher(inputs,assets,out,journal)
  elif role=='student_smoke':
   assets=Path('/evidence/mp-engineering-20261012-r1/assets');verify(assets,read(assets/'result.json')['files'])
   result=rt.smoke(inputs,assets,out,journal,dict(config=config,release=release))
  else:result=dict(outputs=0,updates=0,engineering_only=True)
  result.update(concurrency=concurrent,wall_seconds=time.time()-start,reserved_cents=reserve,
    provider_invoice_usd=None,runtime_rate_estimate_usd=(time.time()-start)*4.3952/3600)
  dump(out/'result.json',result);volume.commit();files=manifest(out);dump(out/'artifact_manifest.json',files);volume.commit()
  receipt=guard.finish(admission,status='completed',evidence_sha256=digest(files),actual_cost_cents=reserve,finished_epoch=time.time())
  return dict(result=result,artifact_manifest=files,receipt=receipt)
 except BaseException as exc:
  if out.exists():
   dump(out/'failure.json',dict(error_type=type(exc).__name__,error=str(exc),traceback=traceback.format_exc(),
      wall_seconds=time.time()-start,rule='Preserve attempted and ambiguous work. Never retry automatically.'))
   volume.commit();files=manifest(out);dump(out/'failure_manifest.json',files);volume.commit()
   guard.finish(admission,status='failed',evidence_sha256=digest(files),actual_cost_cents=reserve,finished_epoch=time.time())
  raise
 finally:timer.cancel()


@app.function(image=teacher_image,gpu='H100!',cpu=(4,4),memory=(32768,32768),timeout=2500,startup_timeout=600,
 retries=0,max_containers=1,min_containers=0,buffer_containers=0,scaledown_window=2,
 single_use_containers=True,serialized=True,include_source=False,volumes={'/evidence':volume})
def teacher_work(plan,config,release):
 return work(plan,config,release,('teacher_calibration',))


@app.function(image=hf,gpu='H100!',cpu=(4,4),memory=(32768,32768),timeout=1600,startup_timeout=600,
 retries=0,max_containers=3,min_containers=0,buffer_containers=0,scaledown_window=2,
 single_use_containers=True,serialized=True,include_source=False,volumes={'/evidence':volume})
def hf_work(plan,config,release):
 return work(plan,config,release,('student_smoke','io_probe_a','io_probe_b'))


@app.local_entrypoint()
def main(plan_json:str,receipt_dir:str,g0_json:str):
 from experiments.sft_allocation_midpoint.common import read,dump,sha,digest
 from experiments.sft_allocation_p008.contract import PHASE0_ROLES
 plan=read(plan_json);spec=read(ROOT/'reports/p008_20261013/PHASE0_ADMISSION.json');g0=read(g0_json)
 if digest(plan)!=spec['plan_sha256']:raise ValueError('Unknown phase0 plan')
 commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
 remote=subprocess.check_output(['git','ls-remote','origin','refs/heads/codex/icml-acl-2027'],cwd=ROOT,text=True).split()[0]
 if commit!=remote:raise ValueError('Ordinary publication required first')
 files={n:sha(ROOT/n) for n in SOURCES}
 for name in SOURCES:
  if subprocess.check_output(['git','show','HEAD:'+name],cwd=ROOT)!=(ROOT/name).read_bytes():raise ValueError('Unpublished source')
 if g0['source_files']!=files or g0['phase0_plan_sha256']!=digest(plan) or g0['verdict'] not in ('PASS','PASS-WITH-NOTES') or len(g0['review_commit'])!=40:
  raise ValueError('Exact source/plan G0 acceptance required')
 upload=read(Path(plan_json).parent/'UPLOAD_VERIFIED.json')
 if not upload['passed'] or upload['input_sha256']!=spec['input_sha256']:raise ValueError('Exact readback upload proof required')
 cli=str(Path(sys.executable).with_name('modal'))
 containers=json.loads(subprocess.check_output([cli,'container','list','--json'],text=True))
 if containers:raise ValueError('Phase0 starts only after all previous owned workers exit')
 claims=modal.Dict.from_name('sft-allocation-midpoint-claims-v1',create_if_missing=False)
 for role in PHASE0_ROLES:
  for kind in ('claim','intent','terminal'):
   if claims.get('midpoint/'+plan['campaign_id']+'/'+kind+'/'+role) is not None:raise ValueError('Existing/uncertain attempt; do not redispatch')
 out=Path(receipt_dir);out.mkdir(parents=True,exist_ok=False)
 release=dict(commit=commit,source_files=files,g0=g0)
 dump(out/'intent.json',dict(plan=plan,release=release,containers=containers))
 calls=[]
 for role in PHASE0_ROLES:
  cfg=spec['configs'][role];fn=teacher_work if role=='teacher_calibration' else hf_work
  # Save dispatch intent BEFORE the network call; a lost acknowledgement is not permission to replay.
  dump(out/(role+'_dispatch_intent.json'),dict(config=cfg,plan_sha256=digest(plan)))
  call=fn.spawn(plan,cfg,release);dump(out/(role+'_submitted.json'),dict(call_id=call.object_id))
  calls.append((role,call))
 errors=[]
 for role,call in calls:
  try:dump(out/(role+'_result.json'),call.get())
  except BaseException as exc:
   dump(out/(role+'_return_error.json'),dict(type=type(exc).__name__,error=str(exc)));errors.append(role)
 if errors:raise RuntimeError('Preserved failed/uncertain roles: '+','.join(errors))

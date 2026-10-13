"""Two authorized, independently identified zero-update replacements.

Original failed slots and their costs remain. Each new physical slot has one
call, 818 cents and 6,001 seconds. Exact replacement source/spec review, reused
input proof and the shared maximum-eight dispatch lock are required.
"""
from pathlib import Path
import json,subprocess,sys
import modal
ROOT=Path(__file__).resolve().parents[2]
SOURCES=['experiments/sft_allocation_p008/student_concurrency.py', 'experiments/sft_allocation_p008/completion_student_binding.py', 'experiments/sft_allocation_p008/block_journal.py', 'experiments/sft_allocation_p008/block_student_runtime.py', 'experiments/sft_allocation_p008/parallel_guard.py', 'experiments/sft_allocation_acquisition/policy_contract.py', 'analyses/completion_contract.py', 'analyses/e017_audit.py', 'analyses/e017_stopping.py', 'analyses/gsm8k_answer_audit.py', 'configs/models.lock.json', 'experiments/sft_allocation_acquisition/contract.py', 'experiments/sft_allocation_midpoint/checkpoint.py', 'experiments/sft_allocation_midpoint/common.py', 'experiments/sft_allocation_midpoint/guard.py', 'experiments/sft_allocation_midpoint/monitor.py', 'experiments/sft_allocation_midpoint/runtime.py', 'experiments/sft_allocation_p008/contract.py', 'experiments/sft_allocation_p008/evidence_bundle.py', 'experiments/sft_allocation_p008/main_binding.py', 'experiments/sft_allocation_p008/modal_student_replacements.py', 'experiments/sft_allocation_p008/completion_queue.py', 'experiments/sft_allocation_p008/pool_lineage.py', 'experiments/sft_allocation_p008/pool_runtime.py', 'experiments/sft_allocation_p008/procurement.py', 'experiments/sft_allocation_p008/requirements_teacher.txt', 'experiments/sft_allocation_p008/student_runtime.py', 'requirements.txt', 'src/real_math_audit.py', 'src/sft_data.py', 'experiments/sft_allocation_p008/frozen_student_plan.py', 'experiments/sft_allocation_p008/frozen_lr_block_student_runtime.py', 'experiments/sft_allocation_p008/student_replacement_binding.py', 'experiments/sft_allocation_p008/provider_release.py']
SPEC='reports/p008_20261013/student_lr_replacement_admission_v1/ADMISSION.json'
app=modal.App('p008-two-zero-update-replacements')
volume=modal.Volume.from_name('sft-allocation-midpoint-v1',create_if_missing=False)
hf=(modal.Image.debian_slim(python_version='3.12')
 .pip_install('torch==2.8.0',index_url='https://download.pytorch.org/whl/cu128')
 .pip_install_from_requirements(ROOT/'requirements.txt').pip_install('peft==0.17.1'))
hf=hf.env({'PYTHONPATH':'/workspace','HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1',
 'TOKENIZERS_PARALLELISM':'false','CUBLAS_WORKSPACE_CONFIG':':4096:8'})
for name in SOURCES:hf=hf.add_local_file(ROOT/name,'/workspace/'+name,copy=True)
hf=hf.add_local_file(ROOT/SPEC,'/workspace/'+SPEC,copy=True)



def work(plan,config,release,expected_roles):
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
 from experiments.sft_allocation_p008.student_replacement_binding import validate_binding,require_parent_records,MAPPING,PARENT_CAMPAIGN
 from experiments.sft_allocation_p008.evidence_bundle import pack
 spec=read('/workspace/'+SPEC);role=config['role'];run=config['run_id']
 if run not in MAPPING:raise ValueError('Only two new physical replacement slots admitted')
 science=validate_binding(plan,config,release,spec)
 if role not in expected_roles:raise ValueError('Wrong finite worker')
 for n,h in release['source_files'].items():
  if sha(Path('/workspace')/n)!=h:raise ValueError('Published source changed')
 if set(release['source_files'])!=set(SOURCES):raise ValueError('Incomplete source binding')
 claims=modal.Dict.from_name('sft-allocation-midpoint-claims-v1',create_if_missing=False)
 require_parent_records(claims,spec)
 guard=RunGuard(claims,plan);guard.register(now_epoch=time.time())
 admitted=guard.admit(dict(run_id=run,source_sha256=digest(release['source_files']),config_sha256=digest(config),data_sha256=config['input_sha256']),
  attempt_id=uuid.uuid4().hex,now_epoch=time.time(),max_runtime_seconds=max(1,stop-time.time()+30))
 reserve=plan['slots'][run]['reserved_cents'];out=Path('/evidence')/plan['campaign_id']/run;recorder=None;journal=None
 active_check=ParallelActiveCheck(guard)
 def deadline():
  if time.time()>stop-30:raise TimeoutError('Finite P008 deadline')
 def check():
  deadline()
  active_check.check_active(admitted,spent_cents=0,next_cost_cents=reserve)
  if time.time()>stop-30:raise TimeoutError('Finite P008 deadline after guard reads')
 try:
  volume.reload();out.mkdir(parents=True,exist_ok=False)
  dump(out/'intent.json',dict(plan=plan,config=config,release=release,started_epoch=start,reserved_cents=reserve));dump(out/'admission.json',spec);volume.commit()
  dump(out/'replacement_lineage.json',dict(logical_run_id=config['logical_run_id'],physical_run_id=run,parent=spec['parents'][config['logical_run_id']],zero_update_reconciliation_sha256=spec['zero_update_reconciliation_sha256'],owner_sha256=digest(spec['owner'])))
  inputs=Path('/evidence')/PARENT_CAMPAIGN/config['input_directory']
  if sha(inputs/'manifest.json')!=config['input_sha256']:raise ValueError('Input hash differs')
  verify(inputs,read(inputs/'manifest.json')['files'])
  assets=Path('/evidence')/'mp-engineering-20261012-r1'/'assets'
  verify(assets,read(assets/'result.json')['files'])
  env=environment(expected_gpu='H100')
  dump(out/'environment.json',env);volume.commit()
  recorder=GPURecorder(out);recorder.start()
  journal=BlockTrainingJournal(out,'midpoint/'+plan['campaign_id']+'/'+run,claims,volume.commit,check,deadline=deadline,expected_updates=config['updates'])
  identity=dict(config=science,physical_run_id=run,source_commit=release['commit'],source_sha256=digest(release['source_files']))
  from experiments.sft_allocation_p008.frozen_lr_block_student_runtime import run as execute
  result=execute(assets,inputs,out,journal,identity)
  result.update(physical_run_id=run,logical_run_id=config['logical_run_id'],replacement_of_failed_parent=True)
  journal.assert_training_complete()
  dump(out/'block_journal_metrics.json',journal.metrics)
  recorder.stop();recorder=None
  result.update(wall_seconds=time.time()-start,reserved_cost_usd=reserve/100,provider_invoice_usd=None,
    runtime_rate_estimate_usd=(time.time()-start)*4.393584/3600)
  dump(out/'guard_read_metrics.json',active_check.metrics)
  dump(out/'result.json',result);volume.commit();pack(out);volume.commit()
  files=manifest(out);dump(out/'artifact_manifest.json',files);volume.commit()
  receipt=guard.finish(admitted,status='completed',evidence_sha256=digest(files),actual_cost_cents=reserve,finished_epoch=time.time())
  return dict(result=result,artifact_manifest=files,receipt=receipt)
 except BaseException as exc:
  if recorder:recorder.stop();recorder=None
  if out.exists():
   if journal is not None and not (out/'block_journal_metrics.json').exists():
    dump(out/'block_journal_metrics.json',journal.metrics)
   if not (out/'guard_read_metrics.json').exists():dump(out/'guard_read_metrics.json',active_check.metrics)
   dump(out/'failure.json',dict(error_type=type(exc).__name__,error=str(exc),traceback=traceback.format_exc(),wall_seconds=time.time()-start,
    rule='Preserve every unit, raw return and unknown. No automatic retry or claim reset.'))
   volume.commit();files=manifest(out);dump(out/'failure_manifest.json',files);volume.commit()
   guard.finish(admitted,status='failed',evidence_sha256=digest(files),actual_cost_cents=reserve,finished_epoch=time.time())
  raise
 finally:
  active_check.close();timer.cancel()


@app.function(image=hf,gpu='H100!',cpu=(4,4),memory=(32768,32768),timeout=6061,startup_timeout=600,
 retries=0,max_containers=8,min_containers=0,buffer_containers=0,scaledown_window=2,
 single_use_containers=True,serialized=True,include_source=False,volumes={'/evidence':volume})
def student_work(plan,config,release):
 return work(plan,config,release,('main','bridge','base'))


@app.local_entrypoint()
def main(plan_json:str,config_json:str,gates_json:str,receipt_dir:str):
 from experiments.sft_allocation_midpoint.common import read,dump,sha,digest
 from experiments.sft_allocation_p008.student_replacement_binding import validate_binding,require_parent_records,MAPPING,PARENT_CAMPAIGN
 import time
 plan=read(plan_json);cfg=read(config_json);gates=read(gates_json);spec=read(ROOT/SPEC);run=cfg['run_id']
 if run not in MAPPING:raise ValueError('Only independent physical replacements, never original failed slots')
 if time.time()+cfg['max_seconds']+700>plan['deadline_epoch']:raise ValueError('Insufficient complete runtime/startup window; leave slot pending, never shorten dose')
 commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
 remote=subprocess.check_output(['git','ls-remote','origin','refs/heads/codex/icml-acl-2027'],cwd=ROOT,text=True).split()[0]
 if commit!=remote:raise ValueError('Ordinary publication required')
 files={n:sha(ROOT/n) for n in SOURCES}
 for n in SOURCES:
  if subprocess.check_output(['git','show','HEAD:'+n],cwd=ROOT)!=(ROOT/n).read_bytes():raise ValueError('Unpublished source')
 release=dict(commit=commit,source_files=files,gates=gates,spec_sha256=digest(spec));validate_binding(plan,cfg,release,spec)
 root=Path(plan_json).parent;destination=Path(receipt_dir)
 shared=root.parent/'student_completion_r1'
 if read(shared/'plan.json')!=spec['original_execution_plan']:raise ValueError('Original shared queue identity differs')
 from experiments.sft_allocation_p008.student_concurrency import dispatch_lock,require_capacity
 with dispatch_lock(shared):
  if destination.exists():raise ValueError('Existing local attempt: reconcile, never replay')
  claims=modal.Dict.from_name('sft-allocation-midpoint-claims-v1',create_if_missing=False)
  require_parent_records(claims,spec)
  from experiments.sft_allocation_p008.provider_release import read_stopped_apps
  cli=str(Path(sys.executable).with_name('modal'))
  before=json.loads(subprocess.check_output([cli,'container','list','--json'],text=True))
  parent_apps=spec['parent_provider_apps']
  read_stopped_apps(cli,parent_apps,[c for c in before if c['app_id'] in parent_apps])
  prefix='midpoint/'+plan['campaign_id']+'/'
  for kind in ('claim','intent','terminal'):
   if claims.get(prefix+kind+'/'+run) is not None:raise ValueError('Existing or uncertain remote attempt')
  if any(k.startswith(prefix+run+'/') or k.startswith(prefix+'attempt/'+run+'/') for k in claims.keys()):
   raise ValueError('Existing or uncertain replacement unit or attempt')
  # Two physical queues share one lock; pending calls in either consume capacity.
  occupied=[]
  for queue in (shared,root):
   qplan=read(queue/'plan.json');qprefix='midpoint/'+qplan['campaign_id']+'/'
   for prior in queue.glob('runs/*/dispatch_intent.json'):
    item=read(prior);name=item['run_id'];terminal=claims.get(qprefix+'terminal/'+name)
    if terminal is None:occupied.append(dict(run_id=qplan['campaign_id']+'/'+name,provider_app_id=item['provider_app_id']))
  # Every original T1 must already have its first submission; T8 still requires N2.
  for name,c in spec['original_spec']['configs'].items():
   if c.get('training_multiple')==1 and name not in spec['owner']['logical_runs']:
    if not (shared/'runs'/name/'submitted.json').exists():raise ValueError('Original T1 submission missing')
   if c.get('training_multiple')==8 and (shared/'runs'/name/'dispatch_intent.json').exists():
    raise ValueError('T8 cannot precede replacement completion and N2')
  from modal.exception import NotFoundError
  try:list(volume.iterdir('/'+plan['campaign_id']+'/'+run))
  except NotFoundError:pass
  else:raise ValueError('Existing or uncertain remote replacement directory')
  cli=str(Path(sys.executable).with_name('modal'))
  containers=json.loads(subprocess.check_output([cli,'container','list','--json'],text=True))
  count=require_capacity(occupied,containers)
  # Actual completed walls, without using scores, address reviewer cap-headroom note.
  completed=[]
  for name,c in spec['original_spec']['configs'].items():
   result_file=shared/'runs'/name/'result.json'
   if c.get('training_multiple')!=1 or name in spec['owner']['logical_runs'] or not result_file.exists():continue
   envelope=read(result_file);terminal=claims.get('midpoint/'+PARENT_CAMPAIGN+'/terminal/'+name)
   if terminal!=envelope['receipt'] or terminal['status']!='completed':raise ValueError('Changed completed T1 evidence')
   if digest(envelope['artifact_manifest'])!=terminal['evidence_sha256']:raise ValueError('Completed T1 manifest differs')
   entry=read(shared/'runs'/name/'dispatch_intent.json')
   read_stopped_apps(cli,[entry['provider_app_id']],[x for x in containers if x['app_id']==entry['provider_app_id']])
   completed.append(dict(run_id=name,wall_seconds=envelope['result']['wall_seconds'],provider_app_id=entry['provider_app_id']))
  if len(completed)<2:raise ValueError('Wait for at least two original T1 completed and released calls')
  if any(x['wall_seconds']>=5400 for x in completed):
   raise ValueError('Measured T1 wall approaches cap; preserve and flag headroom before dispatch')
  if destination.resolve().parent!=(root/'runs').resolve() or destination.name!=run:raise ValueError('Receipt path must be canonical campaign runs/RUN')
  if time.time()+cfg['max_seconds']+700>plan['deadline_epoch']:raise ValueError('Full dispatch window expired during preflight')
  destination.mkdir(parents=True,exist_ok=False)
  dump(destination/'dispatch_intent.json',dict(run_id=run,provider_app_id=app.app_id,occupied_capacity_before=count,config=cfg,plan=plan,release=release,provider_before=containers,occupied_before=occupied,completed_T1_timing_before=completed))
  fn=student_work
  call=fn.spawn(plan,cfg,release);dump(destination/'submitted.json',dict(call_id=call.object_id))
 try:dump(destination/'result.json',call.get())
 except BaseException as exc:
  dump(destination/'return_error.json',dict(type=type(exc).__name__,error=str(exc)));raise

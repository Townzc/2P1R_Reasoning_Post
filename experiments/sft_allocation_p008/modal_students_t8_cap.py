"""Owner-authorized +40s operational amendment; original failed N2 retained. No dispatch before exact-input G1.

Original pool runner/spec/deadline stay immutable. A separate finite student ledger binds direct owner completion authority and retires unattempted original slots without adding budget. Failed D2 is an explicit dependency. This module uses a new student spec
that does not exist until both real pools and joint plans are locally verified.

One slot per local invocation. Never retries an existing or uncertain call.
"""
from pathlib import Path
import json,subprocess,sys
import modal
ROOT=Path(__file__).resolve().parents[2]
SOURCES=['experiments/sft_allocation_p008/student_concurrency.py', 'experiments/sft_allocation_p008/completion_student_binding.py', 'experiments/sft_allocation_p008/block_journal.py', 'experiments/sft_allocation_p008/block_student_runtime.py', 'experiments/sft_allocation_p008/parallel_guard.py', 'experiments/sft_allocation_acquisition/policy_contract.py', 'analyses/completion_contract.py', 'analyses/e017_audit.py', 'analyses/e017_stopping.py', 'analyses/gsm8k_answer_audit.py', 'configs/models.lock.json', 'experiments/sft_allocation_acquisition/contract.py', 'experiments/sft_allocation_midpoint/checkpoint.py', 'experiments/sft_allocation_midpoint/common.py', 'experiments/sft_allocation_midpoint/guard.py', 'experiments/sft_allocation_midpoint/monitor.py', 'experiments/sft_allocation_midpoint/runtime.py', 'experiments/sft_allocation_p008/contract.py', 'experiments/sft_allocation_p008/evidence_bundle.py', 'experiments/sft_allocation_p008/main_binding.py', 'experiments/sft_allocation_p008/modal_students_t8_cap.py', 'experiments/sft_allocation_p008/completion_queue.py', 'experiments/sft_allocation_p008/pool_lineage.py', 'experiments/sft_allocation_p008/pool_runtime.py', 'experiments/sft_allocation_p008/procurement.py', 'experiments/sft_allocation_p008/requirements_teacher.txt', 'experiments/sft_allocation_p008/student_runtime.py', 'requirements.txt', 'src/real_math_audit.py', 'src/sft_data.py', 'experiments/sft_allocation_p008/frozen_student_plan.py', 'experiments/sft_allocation_p008/frozen_lr_block_student_runtime.py', 'experiments/sft_allocation_p008/student_t8_binding.py', 'experiments/sft_allocation_p008/provider_release.py', 'experiments/sft_allocation_p008/student_t8_cap_binding.py']
SPEC='reports/p008_20261013/student_t8_cap_9600_v1/ADMISSION.json'
app=modal.App('p008-eight-t8-owner-cap-9600')
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
 start=time.time();stop=min(start+9600,plan['deadline_epoch']-30)
 timer=threading.Timer(max(1,stop-start),lambda:os._exit(124));timer.daemon=True;timer.start()
 sys.path.insert(0,'/workspace')
 from experiments.sft_allocation_midpoint.common import read,dump,sha,digest,verify,manifest
 from experiments.sft_allocation_midpoint.guard import RunGuard
 from experiments.sft_allocation_p008.parallel_guard import ParallelActiveCheck
 from experiments.sft_allocation_midpoint.runtime import environment
 from experiments.sft_allocation_p008.block_journal import BlockTrainingJournal
 from experiments.sft_allocation_midpoint.monitor import GPURecorder
 from experiments.sft_allocation_p008.student_t8_cap_binding import validate_student_binding,require_timing_terminals,register_amendment,reserve_supplement,verify_supplement,supplement_key,AMENDMENT_KEY,amendment_record
 from experiments.sft_allocation_p008.evidence_bundle import pack
 spec=read('/workspace/'+SPEC);role=config['role'];run=config['run_id']
 if config.get('training_multiple')!=8:
  raise ValueError('Existing base or failed attempt is not admitted by this unattempted-only amendment')
 validate_student_binding(plan,config,release,spec)
 if role not in expected_roles:raise ValueError('Wrong finite worker')
 for n,h in release['source_files'].items():
  if sha(Path('/workspace')/n)!=h:raise ValueError('Published source changed')
 if set(release['source_files'])!=set(SOURCES):raise ValueError('Incomplete source binding')
 claims=modal.Dict.from_name('sft-allocation-midpoint-claims-v1',create_if_missing=False)
 require_timing_terminals(claims,release['gates'])
 for gate in release['gates']['required_terminals']+release['gates']['pool_terminals']:
  if claims.get('midpoint/'+gate['campaign']+'/terminal/'+gate['run_id'])!=gate['terminal']:
   raise ValueError('Required real terminal differs')
 from experiments.sft_allocation_p008.completion_queue import require_handoff
 require_handoff(claims,plan,spec['original_spec']['original_plan'],release['gates']['student_completion_owner'],run)
 guard=RunGuard(claims,plan);guard.register(now_epoch=time.time())
 register_amendment(claims,spec)
 admitted=guard.admit(dict(run_id=run,source_sha256=digest(release['source_files']),config_sha256=digest(config),data_sha256=config['input_sha256']),
  attempt_id=uuid.uuid4().hex,now_epoch=time.time(),max_runtime_seconds=9630)
 supplement=reserve_supplement(claims,spec,admitted)
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
  dump(out/'intent.json',dict(plan=plan,config=config,release=release,started_epoch=start,reserved_cents=reserve,effective_worker_seconds=9600,total_reserved_cents=reserve+5,supplement=supplement));dump(out/'admission.json',spec);volume.commit()
  inputs=out.parent/config['input_directory']
  if sha(inputs/'manifest.json')!=config['input_sha256']:raise ValueError('Input hash differs')
  verify(inputs,read(inputs/'manifest.json')['files'])
  assets=Path('/evidence')/'mp-engineering-20261012-r1'/'assets'
  verify(assets,read(assets/'result.json')['files'])
  env=environment(expected_gpu='H100')
  dump(out/'environment.json',env);volume.commit()
  recorder=GPURecorder(out);recorder.start()
  journal=BlockTrainingJournal(out,'midpoint/'+plan['campaign_id']+'/'+run,claims,volume.commit,check,deadline=deadline,expected_updates=config['updates'])
  identity=dict(config=config,source_commit=release['commit'],source_sha256=digest(release['source_files']))
  from experiments.sft_allocation_p008.frozen_lr_block_student_runtime import run as execute
  result=execute(assets,inputs,out,journal,identity)
  journal.assert_training_complete()
  dump(out/'block_journal_metrics.json',journal.metrics)
  recorder.stop();recorder=None
  result.update(wall_seconds=time.time()-start,reserved_cost_usd=(reserve+5)/100,registered_slot_reserved_usd=reserve/100,supplement_reserved_usd=.05,provider_invoice_usd=None,
    runtime_rate_estimate_usd=(time.time()-start)*4.393584/3600)
  dump(out/'guard_read_metrics.json',active_check.metrics)
  dump(out/'result.json',result);volume.commit();pack(out);volume.commit()
  verify_supplement(claims,spec,run)
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


@app.function(image=hf,gpu='H100!',cpu=(4,4),memory=(32768,32768),timeout=9660,startup_timeout=600,
 retries=0,max_containers=8,min_containers=0,buffer_containers=0,scaledown_window=2,
 single_use_containers=True,serialized=True,include_source=False,volumes={'/evidence':volume})
def student_work(plan,config,release):
 return work(plan,config,release,('main','bridge','base'))


@app.local_entrypoint()
def main(plan_json:str,config_json:str,gates_json:str,receipt_dir:str):
 from experiments.sft_allocation_midpoint.common import read,dump,sha,digest
 from experiments.sft_allocation_p008.student_t8_cap_binding import validate_student_binding,require_timing_terminals,register_amendment,reserve_supplement,verify_supplement,supplement_key,AMENDMENT_KEY,amendment_record
 import time
 plan=read(plan_json);cfg=read(config_json);gates=read(gates_json);spec=read(ROOT/SPEC);run=cfg['run_id']
 if cfg.get('training_multiple')!=8:
  raise ValueError('Existing base or failed attempt is excluded; no automatic retry')
 if time.time()+9600+700>plan['deadline_epoch']:raise ValueError('Insufficient complete runtime/startup window; leave slot pending, never shorten dose')
 commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
 remote=subprocess.check_output(['git','ls-remote','origin','refs/heads/codex/icml-acl-2027'],cwd=ROOT,text=True).split()[0]
 if commit!=remote:raise ValueError('Ordinary publication required')
 files={n:sha(ROOT/n) for n in SOURCES}
 for n in SOURCES:
  if subprocess.check_output(['git','show','HEAD:'+n],cwd=ROOT)!=(ROOT/n).read_bytes():raise ValueError('Unpublished source')
 release=dict(commit=commit,source_files=files,gates=gates,spec_sha256=digest(spec));validate_student_binding(plan,cfg,release,spec)
 root=Path(plan_json).parent;destination=Path(receipt_dir)
 from experiments.sft_allocation_p008.student_concurrency import dispatch_lock,require_capacity
 with dispatch_lock(root):
  if destination.exists():raise ValueError('Existing local attempt: reconcile, never replay')
  claims=modal.Dict.from_name('sft-allocation-midpoint-claims-v1',create_if_missing=False)
  from experiments.sft_allocation_p008.completion_queue import require_handoff
  require_handoff(claims,plan,spec['original_spec']['original_plan'],gates['student_completion_owner'],run)
  prefix='midpoint/'+plan['campaign_id']+'/'
  for kind in ('claim','intent','terminal'):
   if claims.get(prefix+kind+'/'+run) is not None:raise ValueError('Existing or uncertain remote attempt')
  if claims.get(supplement_key(run)) is not None:raise ValueError('Existing supplement; no replay')
  old_amendment=claims.get(AMENDMENT_KEY)
  if old_amendment is not None and old_amendment!=amendment_record(spec):raise ValueError('Conflicting immutable amendment')
  # One lock for original and replacement queues, including calls without claims.
  from experiments.sft_allocation_p008.student_t8_binding import pending_across_queues,ORIGINAL,REPLACEMENTS
  require_timing_terminals(claims,gates)
  replacement_root=root.parent/'student_lr_replacements_r1'
  occupied=pending_across_queues(((root,ORIGINAL),(replacement_root,REPLACEMENTS)),claims)
  if any(k.startswith(prefix+run+'/') or k.startswith(prefix+'attempt/'+run+'/') for k in claims.keys()):
   raise ValueError('Existing or uncertain T8 unit or attempt')
  from modal.exception import NotFoundError
  try:list(volume.iterdir('/'+plan['campaign_id']+'/'+run))
  except NotFoundError:pass
  else:raise ValueError('Existing or uncertain T8 directory')
  cli=str(Path(sys.executable).with_name('modal'))
  containers=json.loads(subprocess.check_output([cli,'container','list','--json'],text=True))
  count=require_capacity(occupied,containers)
  from experiments.sft_allocation_p008.provider_release import read_stopped_apps
  dependency_apps=[]
  for item in gates['t1_terminal_records']:
   queue=root if item['campaign']==ORIGINAL else replacement_root
   sent=read(queue/'runs'/item['run_id']/'dispatch_intent.json')
   if sent['run_id']!=item['run_id'] or sent['plan']['campaign_id']!=item['campaign']:
    raise ValueError('T1 provider identity differs')
   dependency_apps.append(sent['provider_app_id'])
  if len(set(dependency_apps))!=13:raise ValueError('Ambiguous physical T1 provider roster')
  read_stopped_apps(cli,dependency_apps,[x for x in containers if x['app_id'] in dependency_apps])

  # New main starts only after Phase0 release. Pool generation finishes before any student.
  if any(x['run_id'].startswith('pool_') for x in occupied):raise ValueError('Pool worker still active/uncertain')
  if destination.resolve().parent!=(root/'runs').resolve() or destination.name!=run:raise ValueError('Receipt path must be canonical campaign runs/RUN')
  if time.time()+9600+700>plan['deadline_epoch']:raise ValueError('Full dispatch window expired during preflight')
  destination.mkdir(parents=True,exist_ok=False)
  dump(destination/'dispatch_intent.json',dict(run_id=run,provider_app_id=app.app_id,occupied_capacity_before=count,config=cfg,plan=plan,release=release,provider_before=containers,occupied_before=occupied))
  fn=student_work
  call=fn.spawn(plan,cfg,release);dump(destination/'submitted.json',dict(call_id=call.object_id))
 try:dump(destination/'result.json',call.get())
 except BaseException as exc:
  dump(destination/'return_error.json',dict(type=type(exc).__name__,error=str(exc)));raise

"""One reviewed D2 suffix worker. No retries, parent replay or implicit admission."""
from pathlib import Path
import json, subprocess, sys, time
import modal
ROOT=Path(__file__).resolve().parents[2]
SOURCES=['analyses/completion_contract.py', 'analyses/e017_audit.py', 'analyses/e017_stopping.py', 'analyses/gsm8k_answer_audit.py', 'configs/models.lock.json', 'experiments/sft_allocation_acquisition/contract.py', 'experiments/sft_allocation_acquisition/policy_contract.py', 'experiments/sft_allocation_midpoint/checkpoint.py', 'experiments/sft_allocation_midpoint/common.py', 'experiments/sft_allocation_midpoint/guard.py', 'experiments/sft_allocation_midpoint/monitor.py', 'experiments/sft_allocation_midpoint/runtime.py', 'experiments/sft_allocation_p008/continuation_binding.py', 'experiments/sft_allocation_p008/continuation_guard.py', 'experiments/sft_allocation_p008/contract.py', 'experiments/sft_allocation_p008/evidence_bundle.py', 'experiments/sft_allocation_p008/main_binding.py', 'experiments/sft_allocation_p008/modal_main.py', 'experiments/sft_allocation_p008/modal_pool_continuation.py', 'experiments/sft_allocation_p008/parallel_guard.py', 'experiments/sft_allocation_p008/provider_release.py', 'experiments/sft_allocation_p008/pool_continuation_prefix.py', 'experiments/sft_allocation_p008/pool_continuation_runtime.py', 'experiments/sft_allocation_p008/pool_prefix.py', 'experiments/sft_allocation_p008/pool_runtime.py', 'experiments/sft_allocation_p008/procurement.py', 'experiments/sft_allocation_p008/requirements_teacher.txt', 'experiments/sft_allocation_p008/student_runtime.py', 'requirements.txt', 'src/real_math_audit.py', 'src/sft_data.py']
SPEC='reports/p008_20261013/d2_continuation_admission_v2/ADMISSION.json'
app=modal.App('p008-d2-remaining-only')
volume=modal.Volume.from_name('sft-allocation-midpoint-v1',create_if_missing=False)
image=(modal.Image.debian_slim(python_version='3.12')
 .pip_install_from_requirements(ROOT/'experiments/sft_allocation_p008/requirements_teacher.txt')
 .env({'PYTHONPATH':'/workspace','HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1',
       'TOKENIZERS_PARALLELISM':'false','CUBLAS_WORKSPACE_CONFIG':':4096:8','VLLM_USE_V1':'1'}))
for name in SOURCES:image=image.add_local_file(ROOT/name,'/workspace/'+name,copy=True)
image=image.add_local_file(ROOT/SPEC,'/workspace/'+SPEC,copy=True)


def work(plan,config,release):
 import os,threading,uuid,traceback
 start=time.time();stop=min(start+7200,plan['deadline_epoch'])
 timer=threading.Timer(max(.001,stop-time.time()),lambda:os._exit(124));timer.daemon=True;timer.start()
 sys.path.insert(0,'/workspace')
 from experiments.sft_allocation_midpoint.common import read,dump,sha,digest,verify,manifest
 from experiments.sft_allocation_midpoint.guard import RunGuard
 from experiments.sft_allocation_midpoint.runtime import Journal
 from experiments.sft_allocation_midpoint.monitor import GPURecorder
 from experiments.sft_allocation_p008.continuation_binding import validate_continuation_binding,probe_forecast,PROBE
 from experiments.sft_allocation_p008.continuation_guard import ContinuationActiveCheck
 from experiments.sft_allocation_p008.evidence_bundle import pack
 out=Path('/evidence')/plan['campaign_id']/config['run_id']
 admitted=None;active=None;recorder=None
 try:
  spec=read('/workspace/'+SPEC);validate_continuation_binding(plan,config,release,spec)
  if start+7200>plan['deadline_epoch']:raise ValueError('Full worker window no longer available')
  if set(release['source_files'])!=set(SOURCES):raise ValueError('Incomplete source binding')
  for n,h in release['source_files'].items():
   if sha(Path('/workspace')/n)!=h:raise ValueError('Published source changed')
  claims=modal.Dict.from_name('sft-allocation-midpoint-claims-v1',create_if_missing=False)
  for key,value in spec['parent_records'].items():
   if claims.get(key)!=value:raise ValueError('Original parent/D1 dependency changed before admission')
  guard=RunGuard(claims,plan);guard.register(now_epoch=time.time())
  admitted=guard.admit(dict(run_id=config['run_id'],source_sha256=digest(release['source_files']),
    config_sha256=digest(config),data_sha256=config['prefix_manifest_sha256']),
    attempt_id=uuid.uuid4().hex,now_epoch=time.time(),max_runtime_seconds=stop-time.time())
  active=ContinuationActiveCheck(guard,spec['parent_records'])
  def check():
   if time.time()>=stop-30:raise TimeoutError('Finite child soft deadline')
   active.check_active(admitted,spent_cents=0,next_cost_cents=1200)
   if time.time()>=stop-30:raise TimeoutError('Finite child deadline after complete read set')
  volume.reload();out.mkdir(parents=True,exist_ok=False)
  dump(out/'intent.json',dict(plan=plan,config=config,release=release,started_epoch=start,reserved_cents=1200,
    hard_stop_epoch=stop,soft_stop_epoch=stop-30));dump(out/'admission.json',spec);volume.commit()
  inputs=Path('/evidence')/'p008-main-20261013-r1'/'pool_inputs'
  prefix=out.parent/config['prefix_directory']
  for p,h in ((inputs,config['input_sha256']),(prefix,config['prefix_manifest_sha256'])):
   if sha(p/'manifest.json')!=h:raise ValueError('Frozen input manifest differs')
   verify(p,read(p/'manifest.json')['files'])
  # Pinned assets are reused; no new model download or source mutation.
  assets=Path('/evidence')/'mp-teacher-cost-20261012-r1'/'assets'
  verify(assets,read(assets/'result.json')['files'])
  import importlib.metadata,torch
  versions={n:importlib.metadata.version(n) for n in ('torch','vllm','transformers','tokenizers','numpy')}
  if not torch.cuda.is_available() or torch.cuda.device_count()!=1 or 'H100' not in torch.cuda.get_device_name(0):raise ValueError('One actual H100 required')
  checked={**versions,'torch':versions['torch'].split('+')[0]}
  if checked!={'torch':'2.8.0','vllm':'0.11.0','transformers':'4.56.2','tokenizers':'0.22.1','numpy':'2.2.6'}:raise ValueError('Pinned teacher environment differs')
  dump(out/'environment.json',dict(versions=versions,gpu=torch.cuda.get_device_name(0),cuda=torch.version.cuda,
    nvidia_smi=subprocess.check_output(['nvidia-smi'],text=True)))
  # Exactly three full dependency checks on this already admitted, billed host.
  samples=[]
  for _ in range(PROBE['samples']):
   tick=time.monotonic();check();samples.append(time.monotonic()-tick)
  measurement=probe_forecast(samples,stop-30-time.time())
  measurement.update(complete_keys_per_check=active.metrics['complete_keys_per_check'],pre_model=True,
                     charged_to_this_worker=True,worker_elapsed_seconds=time.time()-start)
  dump(out/'PRE_MODEL_TIMING.json',measurement);volume.commit()
  if not measurement['passed']:raise TimeoutError('Measured host cannot satisfy frozen timing proxy')
  check();recorder=GPURecorder(out);recorder.start()
  journal=Journal(out,'midpoint/'+plan['campaign_id']+'/'+config['run_id'],claims,volume.commit,check)
  from experiments.sft_allocation_p008.pool_continuation_runtime import run
  result=run(config,inputs,assets,out,journal,prefix)
  recorder.stop();recorder=None;check()
  result.update(wall_seconds=time.time()-start,reserved_cost_usd=12,provider_invoice_usd=None,
    runtime_rate_estimate_usd=(time.time()-start)*4.393584/3600)
  dump(out/'guard_read_metrics.json',active.metrics);dump(out/'result.json',result);volume.commit()
  pack(out);volume.commit();check()
  files=manifest(out);dump(out/'artifact_manifest.json',files);volume.commit()
  receipt=guard.finish(admitted,status='completed',evidence_sha256=digest(files),actual_cost_cents=1200,finished_epoch=time.time())
  return dict(result=result,artifact_manifest=files,receipt=receipt)
 except BaseException as exc:
  if recorder:recorder.stop();recorder=None
  if admitted is not None:
   if not out.exists():out.mkdir(parents=True,exist_ok=False)
   if active:dump(out/'failure_guard_metrics.json',active.metrics)
   dump(out/'failure.json',dict(error_type=type(exc).__name__,error=str(exc),traceback=traceback.format_exc(),
      wall_seconds=time.time()-start,rule='Preserve original parent and all child intents/returns/unknown; never retry'))
   volume.commit();files=manifest(out);dump(out/'failure_manifest.json',files);volume.commit()
   guard.finish(admitted,status='failed',evidence_sha256=digest(files),actual_cost_cents=1200,finished_epoch=time.time())
  raise
 finally:
  if active:active.close()
  timer.cancel()


@app.function(image=image,gpu='H100!',cpu=(4,4),memory=(32768,32768),timeout=7300,startup_timeout=600,
 retries=0,max_containers=1,min_containers=0,buffer_containers=0,scaledown_window=2,
 single_use_containers=True,serialized=True,include_source=False,volumes={'/evidence':volume})
def pool_work(plan,config,release):return work(plan,config,release)


@app.local_entrypoint()
def main(plan_json:str,config_json:str,gates_json:str,receipt_dir:str):
 from modal.exception import NotFoundError
 from experiments.sft_allocation_midpoint.common import read,dump,sha,digest
 from experiments.sft_allocation_p008.continuation_binding import validate_continuation_binding
 plan=read(plan_json);cfg=read(config_json);gates=read(gates_json);spec=read(ROOT/SPEC)
 if time.time()+7200+700>plan['deadline_epoch']:raise ValueError('Complete startup/runtime window expired')
 commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
 remote=subprocess.check_output(['git','ls-remote','origin','refs/heads/codex/icml-acl-2027'],cwd=ROOT,text=True).split()[0]
 if commit!=remote:raise ValueError('Ordinary source publication required')
 files={n:sha(ROOT/n) for n in SOURCES}
 for n in SOURCES:
  if subprocess.check_output(['git','show','HEAD:'+n],cwd=ROOT)!=(ROOT/n).read_bytes():raise ValueError('Unpublished source')
 if subprocess.check_output(['git','show','HEAD:'+SPEC],cwd=ROOT)!=(ROOT/SPEC).read_bytes():raise ValueError('Unpublished spec')
 release=dict(commit=commit,source_files=files,gates=gates,spec_sha256=digest(spec))
 validate_continuation_binding(plan,cfg,release,spec)
 destination=Path(receipt_dir);root=Path(plan_json).parent
 if destination.resolve()!=(root/'runs'/cfg['run_id']).resolve() or destination.exists():raise ValueError('Existing or noncanonical attempt')
 claims=modal.Dict.from_name('sft-allocation-midpoint-claims-v1',create_if_missing=False)
 for key,value in spec['parent_records'].items():
  if claims.get(key)!=value:raise ValueError('Parent/D1 records differ')
 prefix='midpoint/'+plan['campaign_id']+'/'
 # New campaign has no permitted prior record of any kind, even an orphan unit.
 if any(k.startswith(prefix) for k,_ in claims.items()):raise ValueError('Existing child campaign evidence; reconcile, never replay')
 try:
  list(volume.iterdir('/'+plan['campaign_id']+'/'+cfg['run_id']))
  raise ValueError('Existing remote run directory')
 except NotFoundError:pass
 cli=str(Path(sys.executable).with_name('modal'))
 from experiments.sft_allocation_p008.provider_release import read_stopped_apps
 containers=json.loads(subprocess.check_output([cli,'container','list','--json'],text=True))
 apps=read_stopped_apps(cli,spec['original_apps'],containers)
 if time.time()+7900>plan['deadline_epoch']:raise ValueError('Window expired during preflight')
 destination.mkdir(parents=True,exist_ok=False)
 dump(destination/'dispatch_intent.json',dict(plan=plan,config=cfg,release=release,provider_before=apps,containers_before=containers,run_id=cfg['run_id']))
 call=pool_work.spawn(plan,cfg,release);dump(destination/'submitted.json',dict(call_id=call.object_id))
 try:dump(destination/'result.json',call.get())
 except BaseException as exc:
  dump(destination/'return_error.json',dict(type=type(exc).__name__,error=str(exc)));raise

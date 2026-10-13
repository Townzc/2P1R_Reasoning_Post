"""Prepared one-shot P008 CPU integrity audit. No admission or model calls here.

The future exact admission file deliberately does not exist until every source
run is complete, locally re-scored, externally gated and released. This entry
has no GPU, training, generation, controller or automatic retry.
"""
from pathlib import Path
import json,subprocess,sys,time
import modal

ROOT=Path(__file__).resolve().parents[2]
SOURCES=['experiments/sft_allocation_midpoint/common.py','experiments/sft_allocation_midpoint/checkpoint.py',
 'experiments/sft_allocation_midpoint/guard.py','experiments/sft_allocation_p008/contract.py',
 'experiments/sft_allocation_p008/evidence_bundle.py','experiments/sft_allocation_p008/audit_bundle.py',
 'experiments/sft_allocation_p008/audit_binding.py','experiments/sft_allocation_p008/modal_audit.py']
SPEC='reports/p008_20261013/final_audit_admission_v1/ADMISSION.json'
app=modal.App('p008-finite-final-cpu-audit')
volume=modal.Volume.from_name('sft-allocation-midpoint-v1',create_if_missing=False)
image=(modal.Image.debian_slim(python_version='3.12')
 .pip_install('torch==2.8.0',index_url='https://download.pytorch.org/whl/cpu').pip_install('numpy==2.2.6')
 .env({'PYTHONPATH':'/workspace'}))
for name in SOURCES:image=image.add_local_file(ROOT/name,'/workspace/'+name,copy=True)
image=image.add_local_file(ROOT/SPEC,'/workspace/'+SPEC,copy=True)


@app.function(image=image,cpu=(4,4),memory=(16384,16384),timeout=3500,startup_timeout=600,
 retries=0,max_containers=1,min_containers=0,buffer_containers=0,scaledown_window=2,
 single_use_containers=True,serialized=True,include_source=False,volumes={'/evidence':volume})
def work(binding,release):
 started=time.time()
 import os,threading,uuid,traceback,tempfile
 from concurrent.futures import ThreadPoolExecutor,as_completed
 sys.path.insert(0,'/workspace')
 from experiments.sft_allocation_midpoint.common import read,dump,sha,digest,verify,manifest
 from experiments.sft_allocation_midpoint.guard import RunGuard
 from experiments.sft_allocation_p008.audit_binding import validate,validate_label
 from experiments.sft_allocation_p008.audit_bundle import verify_packed_run
 from experiments.sft_allocation_p008.evidence_bundle import pack
 import torch
 torch.set_num_threads(2)
 spec=read('/workspace/'+SPEC);roster=validate(binding,spec,release);plan=binding['plan'];cfg=binding['config']
 if set(release['source_files'])!=set(SOURCES):raise ValueError('Incomplete code identity')
 for name,value in release['source_files'].items():
  if sha(Path('/workspace')/name)!=value:raise ValueError('Unpublished code')
 claims=modal.Dict.from_name('sft-allocation-midpoint-claims-v1',create_if_missing=False)
 prefix='midpoint/'+plan['campaign_id']+'/'
 for run,item in binding['labels'].items():
  if claims.get(prefix+'terminal/'+run)!=item['terminal']:raise ValueError('Real source terminal differs')
 volume.reload();inputs=Path('/evidence')/plan['campaign_id']/cfg['input_directory']
 if read(inputs/'manifest.json')!=binding['input_manifest']:raise ValueError('Foreign audit inputs')
 verify(inputs,binding['input_manifest']['files'])
 labels={run:validate_label(binding,run,read(inputs/(run+'.json'))) for run in sorted(roster)}
 guard=RunGuard(claims,plan);guard.register(now_epoch=time.time())
 won=guard.admit(dict(run_id='audit',config_sha256=digest(binding),source_sha256=digest(release['source_files']),
  data_sha256=digest(binding['input_manifest'])),attempt_id=uuid.uuid4().hex,now_epoch=time.time(),max_runtime_seconds=3360)
 stop=min(started+3300,plan['deadline_epoch']-30)
 timer=threading.Timer(max(1,stop-time.time()),lambda:os._exit(124));timer.daemon=True;timer.start()
 out=Path('/evidence')/plan['campaign_id']/'audit'
 def check():
  if time.time()>=stop-30:raise TimeoutError('Original finite CPU deadline')
 try:
  out.mkdir(parents=True,exist_ok=False)
  dump(out/'intent.json',dict(binding=binding,release=release,started_epoch=started));dump(out/'admission.json',spec);volume.commit()
  results={}
  def one(run):
   check();item=labels[run]
   # Only container-local duplicates are deleted on exit. Original Volume stays untouched.
   with tempfile.TemporaryDirectory(prefix='p008-audit-') as tmp:
    return verify_packed_run(Path('/evidence')/item['campaign']/run,Path(tmp)/'checked',item,check)
  with ThreadPoolExecutor(max_workers=2) as pool:
   futures={}
   for run in sorted(roster):
    check();unit=dict(label_sha256=digest(labels[run]),original_terminal=binding['labels'][run]['terminal'])
    key=prefix+'audit/unit/'+run
    if not claims.put(key,unit,skip_if_exists=True):raise ValueError('Prior/uncertain audit label; no replay')
    dump(out/'intents'/(run+'.json'),unit)
   volume.commit()
   for run in sorted(roster):futures[pool.submit(one,run)]=run
   for future in as_completed(futures):
    run=futures[future];result=future.result();check()
    guard.check_active(won,now_epoch=time.time(),spent_cents=0,next_cost_cents=500)
    dump(out/'proofs'/(run+'.json'),result);volume.commit()
    done=dict(proof_sha256=sha(out/'proofs'/(run+'.json')),label_sha256=digest(labels[run]))
    if not claims.put(prefix+'audit/done/'+run,done,skip_if_exists=True):raise ValueError('Duplicate audit completion')
    dump(out/'completed'/(run+'.json'),done);volume.commit();results[run]=result
  if set(results)!=roster:raise ValueError('Incomplete final integrity audit')
  result=dict(passed=True,labels=results,wall_seconds=time.time()-started,new_model_calls=0,
    reserved_cost_usd=5,provider_invoice_usd=None,
    scope='Packed original bytes and full states; prior independent raw/dose oracles bound; not fresh model reproduction')
  dump(out/'result.json',result);volume.commit();pack(out);volume.commit()
  files=manifest(out);dump(out/'artifact_manifest.json',files);volume.commit()
  receipt=guard.finish(won,status='completed',evidence_sha256=digest(files),actual_cost_cents=500,finished_epoch=time.time())
  return dict(result=result,artifact_manifest=files,receipt=receipt)
 except BaseException as exc:
  if out.exists():
   dump(out/'failure.json',dict(error_type=type(exc).__name__,error=str(exc),traceback=traceback.format_exc(),
    rule='Keep all partial proofs and original claims; no automatic retry or reset'))
   volume.commit();files=manifest(out);dump(out/'failure_manifest.json',files);volume.commit()
   guard.finish(won,status='failed',evidence_sha256=digest(files),actual_cost_cents=500,finished_epoch=time.time())
  raise
 finally:timer.cancel()


@app.local_entrypoint()
def main(binding_json:str,receipt_dir:str):
 from experiments.sft_allocation_midpoint.common import read,dump,sha,digest
 from experiments.sft_allocation_p008.audit_binding import validate
 binding=read(binding_json);plan=binding['plan'];root=Path(binding_json).parent
 if time.time()+4000>plan['deadline_epoch']:raise ValueError('Full CPU/startup window unavailable; pending')
 commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
 remote=subprocess.check_output(['git','ls-remote','origin','refs/heads/codex/icml-acl-2027'],cwd=ROOT,text=True).split()[0]
 if commit!=remote:raise ValueError('Ordinary publication required')
 for name in SOURCES+[SPEC]:
  if subprocess.check_output(['git','show','HEAD:'+name],cwd=ROOT)!=(ROOT/name).read_bytes():raise ValueError('Unpublished source/spec')
 spec=read(ROOT/SPEC);release=dict(commit=commit,source_files={n:sha(ROOT/n) for n in SOURCES},spec_sha256=digest(spec))
 roster=validate(binding,spec,release)
 cli=str(Path(sys.executable).with_name('modal'))
 containers=json.loads(subprocess.check_output([cli,'container','list','--json'],text=True))
 apps=json.loads(subprocess.check_output([cli,'app','list','--json'],text=True));by_id={a['app_id']:a for a in apps}
 if containers:raise ValueError('All model resources must be released before final CPU')
 for run in roster:
  app_id=binding['labels'][run]['app_id'];a=by_id[app_id]
  if a['state']!='stopped' or str(a['tasks'])!='0':raise ValueError('Source app not stopped')
 claims=modal.Dict.from_name('sft-allocation-midpoint-claims-v1',create_if_missing=False);prefix='midpoint/'+plan['campaign_id']+'/'
 if any(claims.get(prefix+kind+'/audit') is not None for kind in ('claim','intent','terminal')):
  raise ValueError('Existing/uncertain CPU attempt')
 if any(k.startswith(prefix+'audit/') for k in claims.keys()):raise ValueError('Existing CPU units')
 for run,item in binding['labels'].items():
  if claims.get(prefix+'terminal/'+run)!=item['terminal']:raise ValueError('Source terminal changed')
 from modal.exception import NotFoundError
 try:entries=list(volume.iterdir('/'+plan['campaign_id']+'/audit'))
 except NotFoundError:entries=[]
 if entries:raise ValueError('Remote audit evidence exists')
 target=Path(receipt_dir)
 if target.resolve()!=(root/'runs'/'audit').resolve():raise ValueError('Canonical receipt directory required')
 target.mkdir(parents=True,exist_ok=False)
 dump(target/'dispatch_intent.json',dict(binding=binding,release=release,provider_before=apps,containers=containers))
 call=work.spawn(binding,release);dump(target/'submitted.json',dict(call_id=call.object_id))
 try:dump(target/'result.json',call.get())
 except BaseException as exc:
  dump(target/'return_error.json',dict(type=type(exc).__name__,error=str(exc)));raise

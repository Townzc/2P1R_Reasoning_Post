"""Bounded read-only NC3200 failure preservation; no model/remote writes/retry."""
from pathlib import Path, PurePosixPath
from datetime import datetime,timezone
from concurrent.futures import ThreadPoolExecutor,as_completed
import hashlib,json,os,shutil,subprocess,threading,sys
sys.path.insert(0,'.')
from experiments.sft_allocation_midpoint.common import read,dump,sha,digest,verify
from experiments.sft_allocation_p008.evidence_bundle import safe_name
from experiments.sft_allocation_p008.provider_release import read_stopped_apps
from experiments.learning_regime_p009.stage1_nc_binding import CAMPAIGN,dispatch_key,logical_key,marker,intent,validate
R=Path('.local/p009_20261014/r1/stage1_nc_r1'); RUN='nc_s17_n3200'
CLI='.local/midpoint_20261011/venv/bin/modal'; OUT=R/'failed_nc3200_preservation_r1'
def now():return datetime.now(timezone.utc).isoformat()
def main():
 import modal
 from modal.volume import FileEntryType
 spec=read('reports/p009_20261014/stage1_nc_runtime_preflight_v1/ADMISSION.json')
 sent=read(R/'runs'/RUN/'dispatch_intent.json'); submitted=read(R/'runs'/RUN/'submitted.json')
 cap=validate(spec,sent['plan'],RUN,sent['release'])
 for n,h in spec['source_files'].items():
  if sha(n)!=h:raise ValueError('Original NC42 source changed')
 if OUT.exists() or (R/'runs'/RUN/'result.json').exists():raise ValueError('Prior preservation or completed callback; never retry')
 app=sent['provider_app_id']; containers=json.loads(subprocess.check_output([CLI,'container','list','--json'],text=True,timeout=60))
 owned=[c for c in containers if c.get('app_id')==app]; infos=read_stopped_apps(CLI,[app],owned)
 db=modal.Dict.from_name('sft-allocation-midpoint-claims-v1',create_if_missing=False)
 vol=modal.Volume.from_name('sft-allocation-midpoint-v1',create_if_missing=False)
 pre='midpoint/'+CAMPAIGN+'/'
 keys=[pre+k+'/'+RUN for k in ('claim','terminal','intent')]+[dispatch_key(RUN),logical_key(RUN)]
 before={k:db.get(k) for k in keys};claim=before[keys[0]];terminal=before[keys[1]]
 if (terminal['status']!='failed' or terminal['run_id']!=RUN or claim['run_id']!=RUN
   or terminal['claim_sha256']!=digest(claim) or terminal['attempt_id']!=claim['attempt_id']
   or claim['reserved_cents']!=cap['reserved_cents'] or terminal['actual_cost_cents']!=cap['reserved_cents']
   or before[keys[2]]!=intent(spec,RUN) or any(before[k]!=marker(spec,RUN,sent['release']) for k in keys[3:])):
  raise ValueError('Original failed physical/logical identity differs')
 oldledger=R/'closeouts/nc_s17_n400/ledger.json'; old=read(oldledger)
 if any(old.get(k)!=v for k,v in before.items()):raise ValueError('Existing full ledger does not contain exact original failed lineage')
 OUT.mkdir();dump(OUT/'READ_INTENT.json',dict(utc=now(),source_sha256=sha(__file__),run=RUN,app_id=app,
  call_id=submitted['call_id'],model_calls=0,remote_writes=0,readers=2,max_files=4096,max_bytes=256*1024**2,
  reused_full_ledger_sha256=sha(oldledger),new_full_dict_enumerations=0,whole_retry_allowed=False))
 dump(OUT/'PROVIDER.json',dict(app_ids=[app],original_app_info=infos,owned_containers=owned,owned_container_ids=[],state='stopped',read_utc=now()))
 dump(OUT/'RECORDS_BEFORE.json',before);shutil.copyfile(oldledger,OUT/'ledger.json')
 for n in ('dispatch_intent.json','submitted.json','return_error.json'):
  shutil.copyfile(R/'runs'/RUN/n,OUT/n)
 shutil.copyfile(R/'nc_s17_n3200_run_r1.log',OUT/'original_cli.log')
 remote=CAMPAIGN+'/'+RUN
 def listing():
  found={}
  for e in vol.iterdir('/'+remote,recursive=True):
   if e.type!=FileEntryType.FILE:continue
   n=PurePosixPath(e.path.lstrip('/')).relative_to(remote).as_posix();safe_name(n)
   if n in found or e.size>32*1024**2:raise ValueError('Duplicate/oversized original file')
   found[n]=dict(bytes=e.size,mtime=e.mtime)
   if len(found)>4096 or sum(x['bytes'] for x in found.values())>256*1024**2:raise ValueError('Original failed evidence exceeds finite preservation bounds')
  if not found:raise ValueError('Original stopped evidence absent')
  return found
 files=listing();dump(OUT/'LIST_BEFORE.json',files)
 def copy(n):
  p=OUT/'evidence'/n;p.parent.mkdir(parents=True,exist_ok=True);h=hashlib.sha256();size=0
  with p.open('xb') as f:
   for block in vol.read_file('/'+remote+'/'+n):
    size+=len(block)
    if size>files[n]['bytes']:raise ValueError('Original file grew; preserve partial')
    f.write(block);h.update(block)
   f.flush();os.fsync(f.fileno())
  if size!=files[n]['bytes']:raise ValueError('Incomplete original file; preserve partial')
  value=dict(bytes=size,sha256=h.hexdigest());dump(OUT/'transfers'/(n+'.json'),value)
  return n,value
 copied={};errors={}
 with ThreadPoolExecutor(max_workers=2) as pool:
  futures={pool.submit(copy,n):n for n in files}
  for future in as_completed(futures):
   name=futures[future]
   try:n,value=future.result();copied[n]=value
   except Exception as e:errors[name]=dict(type=type(e).__name__,error=str(e))
 dump(OUT/'COPIED.json',copied);dump(OUT/'READ_ERRORS.json',errors)
 if errors:raise ValueError('Preserved partial transfer; reconcile missing files only, never whole helper')
 afterlist=listing();after={k:db.get(k) for k in keys};dump(OUT/'LIST_AFTER.json',afterlist);dump(OUT/'RECORDS_AFTER.json',after)
 if afterlist!=files or after!=before:raise ValueError('Original stopped evidence changed')
 failure=read(OUT/'evidence/failure_manifest.json')
 if digest(failure)!=terminal['evidence_sha256'] or set(failure)|{'failure_manifest.json'}!=set(files):raise ValueError('Original failure manifest/terminal/list differs')
 verify(OUT/'evidence',failure)
 if any(copied[k]!=v for k,v in failure.items()):raise ValueError('Original failure file hash differs')
 states=[n for n in files if n.endswith('.pt') or n.endswith('.safetensors')]
 names=[n for n in files if n.startswith('completed/update_') and n.endswith('.json')]
 updates=sorted(int(Path(n).stem.split('_')[1]) for n in names);continuous=0
 for i in updates:
  if i!=continuous+1:break
  continuous=i
 blocks=sorted(n for n in files if n.startswith('completed/training_block_') and n.endswith('.json'))
 for n in blocks:
  key=pre+RUN+'/done/'+Path(n).stem
  if old.get(key)!=read(OUT/'evidence'/n):raise ValueError('Saved block differs from original full ledger')
 result=dict(passed=True,run_id=RUN,parent_stays_failed=True,original_terminal=terminal,
  files_preserved=len(files),bytes_preserved=sum(x['bytes'] for x in files.values()),
  continuous_saved_updates=continuous,last_saved_block=read(OUT/'evidence'/blocks[-1]) if blocks else None,
  saved_checkpoint_or_weight_files=states,full_restart_is_not_resume=not bool(states),
  output_raw_files=[n for n in files if n.startswith('endpoint/raw/')],
  full_state_oracle_performed=False,partial_scoring_performed=False,model_calls=0,remote_writes=0,
  original_ledger_sha256=sha(oldledger),unknown_transfer_files=0,read_finished_utc=now(),
  operator_resubmission=False,platform_preemption_and_restart_evidence='original_cli.log')
 dump(OUT/'PRESERVED.json',result);print(json.dumps(result))
if __name__=='__main__':
 timer=threading.Timer(1200,lambda:os._exit(124));timer.daemon=True;timer.start()
 try:main()
 finally:timer.cancel()

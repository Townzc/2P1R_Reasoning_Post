"""Bounded operator-only original byte preservation; no scientific transformation.
No cloud function/deployment/model/decoding/scoring or failed-job retry. Existing
successful byte files are never overwritten; partial transfer is preserved.
"""
from pathlib import Path,PurePosixPath
from concurrent.futures import ThreadPoolExecutor
import json,time,hashlib,signal,traceback
import modal
from experiments.p011 import b_current_path
from scripts.p011_b_current_io import expected_records
R=Path('.local/p011_20261020/r1');ROOT=R/'b_generation_failed_preservation_r1';DEST=ROOT/'original_remote_files';PREFIX='p011-20261020/b_runs_r1/B_generation_t10_400x16_r1'
def put(name,value):
 p=ROOT/name;p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x') as f:json.dump(value,f,indent=2,sort_keys=True);f.write('\n')
def alarm(*_):raise TimeoutError('Original bounded600s preservation expired')
signal.signal(signal.SIGALRM,alarm);signal.alarm(600)
provider=json.loads((ROOT/'PROVIDER_OBSERVATION.json').read_text());assert provider['state']=='stopped' and provider['owned_containers']==0;assert not DEST.exists()
put('PRESERVATION_INTENT.json',dict(started_epoch=time.time(),prefix=PREFIX,max_seconds=600,application_retries=0,scientific_transformations=0,previous_whole_helper_attempt=False,original_failed_call_not_retried=True))
volume=modal.Volume.from_name('sft-allocation-midpoint-v1',create_if_missing=False)
def inventory():
 result=[]
 for e in volume.iterdir('/'+PREFIX,recursive=True):
  name=e.path.lstrip('/');p=PurePosixPath(name)
  if '..' in p.parts or not name.startswith(PREFIX+'/') or int(e.type) not in (1,2):raise ValueError('Out-of-prefix/nonregular inventory')
  result.append(dict(path=name,type=int(e.type),mtime=e.mtime,size=e.size))
 return sorted(result,key=lambda x:x['path'])
try:
 before=inventory();put('REMOTE_INVENTORY_BEFORE.json',dict(observed_epoch=time.time(),entries=before));files=[e for e in before if e['type']==1];assert 0<len(files)<=1000 and sum(x['size'] for x in files)<=500_000_000
 def copy(e):
  rel=e['path'][len(PREFIX)+1:];p=DEST/rel;p.parent.mkdir(parents=True,exist_ok=True);h=hashlib.sha256();n=0
  with p.open('xb') as f:
   for b in volume.read_file('/'+e['path']):
    n+=len(b)
    if n>e['size']:raise ValueError('Larger than inventoried size')
    f.write(b);h.update(b)
  if n!=e['size']:raise ValueError('Partial bytes retained')
  v=dict(remote_path=e['path'],relative_path=rel,bytes=n,sha256=h.hexdigest());put('transfer_receipts/'+hashlib.sha256(rel.encode()).hexdigest()+'.json',v);return v
 with ThreadPoolExecutor(max_workers=8) as pool:copied=list(pool.map(copy,files))
 after=inventory();put('REMOTE_INVENTORY_AFTER.json',dict(observed_epoch=time.time(),entries=after));assert after==before,'Prefix changed; not fully preserved'
 spec=json.loads(Path(b_current_path.SPEC_FILES['generation']).read_text());job=spec['jobs']['B_generation_t10_400x16_r1'];keys=expected_records(job);assert len(keys)==54 and len(set(keys))==54;store=modal.Dict.from_name(b_current_path.STORE,create_if_missing=False)
 def get(k):
  v=dict(key=k,value=store.get(k),observed_epoch=time.time());put('named_records/'+hashlib.sha256(k.encode()).hexdigest()+'.json',v);return v
 with ThreadPoolExecutor(max_workers=8) as pool:records=list(pool.map(get,keys))
 proof=dict(completed_epoch=time.time(),files=copied,file_count=len(copied),bytes=sum(x['bytes'] for x in copied),stable_inventory=True,named_key_count=len(records),present_keys=[x['key'] for x in records if x['value'] is not None],absent_key_count=sum(x['value'] is None for x in records),provider=provider,scientific_completion=False,model_calls=0,score_calls=0,decoder_calls=0,original_call_retries=0)
 put('PRESERVATION_COMPLETED.json',proof);print(json.dumps({k:proof[k] for k in ('file_count','bytes','named_key_count','present_keys','absent_key_count','completed_epoch')}),flush=True)
except BaseException as e:
 put('PRESERVATION_FAILED.json',dict(epoch=time.time(),error=repr(e),traceback=traceback.format_exc(),partial_retained=True,automatic_retry=False));raise
finally:signal.alarm(0)

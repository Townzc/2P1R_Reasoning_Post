"""Operator-only bounded missing-byte preservation, never a scientific collector.
Original stock directory get failed before writing files. No cloud function, code
upload, model, scoring, retry, overwrite, old-Dict enumeration, or provider query.
"""
from pathlib import Path,PurePosixPath
from concurrent.futures import ThreadPoolExecutor
import json,time,hashlib,signal,traceback
import modal
from experiments.p011 import c1_outer
ROOT=Path('.local/p011_20261020/r1/c1_failed_preservation_r1')
DEST=ROOT/'original_remote_files'
PREFIX='p011-20261020/c1_original_token_base_forward_r1'
def put(name,value):
 p=ROOT/name;p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x') as f:json.dump(value,f,indent=2,sort_keys=True);f.write('\n')
def alarm(*_):raise TimeoutError('Original bounded600s missing-byte preservation expired')
signal.signal(signal.SIGALRM,alarm);signal.alarm(600)
provider=json.loads((ROOT/'PROVIDER_OBSERVATION.json').read_text())
assert provider['state']=='stopped' and provider['owned_containers']==0
assert (ROOT/'STOCK_VOLUME_GET_INTENT.json').exists()
assert not (ROOT/'STOCK_VOLUME_GET_COMPLETED.json').exists()
existing=[str(p.relative_to(DEST)) for p in DEST.rglob('*') if p.is_file()]
# Existing successful parts would need explicit size/hash reconciliation; original has none.
assert not existing
put('MISSING_BYTES_TRANSFER_INTENT.json',{'started_epoch':time.time(),'stock_get_failed':True,'valid_existing_files':existing,'prefix':PREFIX,'max_seconds':600,'application_retries':0,'new_scientific_calls':0})
volume=modal.Volume.from_name('sft-allocation-midpoint-v1',create_if_missing=False)
def inventory():
 entries=[]
 for e in volume.iterdir('/'+PREFIX,recursive=True):
  path=e.path.lstrip('/');p=PurePosixPath(path)
  if '..' in p.parts or not path.startswith(PREFIX+'/'):raise ValueError('Out-of-prefix inventory')
  if int(e.type) not in (1,2):raise ValueError('Nonregular remote entry')
  entries.append({'path':path,'type':int(e.type),'mtime':e.mtime,'size':e.size})
 return sorted(entries,key=lambda x:x['path'])
try:
 before=inventory();put('REMOTE_INVENTORY_BEFORE.json',{'observed_epoch':time.time(),'entries':before})
 files=[e for e in before if e['type']==1]
 assert 0<len(files)<=2000 and sum(e['size'] for e in files)<=200_000_000
 def copy(e):
  rel=e['path'][len(PREFIX)+1:];p=DEST/rel;p.parent.mkdir(parents=True,exist_ok=True)
  h=hashlib.sha256();n=0
  with p.open('xb') as f:
   for b in volume.read_file('/'+e['path']):
    n+=len(b)
    if n>e['size']:raise ValueError('Transfer larger than inventoried size')
    f.write(b);h.update(b)
  if n!=e['size']:raise ValueError('Partial transfer retained')
  result={'remote_path':e['path'],'relative_path':rel,'bytes':n,'sha256':h.hexdigest()}
  put('transfer_receipts/'+hashlib.sha256(rel.encode()).hexdigest()+'.json',result)
  return result
 with ThreadPoolExecutor(max_workers=8) as pool:copied=list(pool.map(copy,files))
 after=inventory();put('REMOTE_INVENTORY_AFTER.json',{'observed_epoch':time.time(),'entries':after})
 if after!=before:raise ValueError('Remote prefix changed; no complete preservation claim')
 spec=json.loads(Path(c1_outer.SPEC).read_text());keys=c1_outer.complete_record_keys(spec)
 assert len(keys)==603 and len(set(keys))==603
 store=modal.Dict.from_name(c1_outer.STORE,create_if_missing=False)
 def get(key):
  value=store.get(key);result={'key':key,'value':value,'observed_epoch':time.time()}
  put('named_records/'+hashlib.sha256(key.encode()).hexdigest()+'.json',result)
  return result
 with ThreadPoolExecutor(max_workers=8) as pool:records=list(pool.map(get,keys))
 proof={'completed_epoch':time.time(),'files':copied,'file_count':len(copied),'bytes':sum(x['bytes'] for x in copied),'stable_inventory':True,'named_key_count':len(records),'present_keys':[x['key'] for x in records if x['value'] is not None],'absent_key_count':sum(x['value'] is None for x in records),'original_provider':provider,'scientific_completion':False,'model_calls':0,'score_calls':0,'retry_calls':0,'stock_get_failure_retained':True}
 put('PRESERVATION_COMPLETED.json',proof)
 print(json.dumps({k:proof[k] for k in ('file_count','bytes','named_key_count','present_keys','absent_key_count','completed_epoch')}),flush=True)
except BaseException as e:
 put('MISSING_BYTES_TRANSFER_FAILED.json',{'epoch':time.time(),'error':repr(e),'traceback':traceback.format_exc(),'partial_files_retained':True,'automatic_retry':False})
 raise
finally:signal.alarm(0)

"""One bounded original r2 failure preservation; no model/encoding/scoring/retry."""
from pathlib import Path,PurePosixPath
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import json,time,hashlib,signal,traceback,subprocess
import modal
from experiments.p011 import long_lr_r2_path as path,long_lr_r2_evidence as evidence
from experiments.sft_allocation_midpoint.common import sha
R=Path(path.LOCAL);ROOT=R/'long_LR_r2_failures_r1';SPEC=json.loads(Path(path.SPEC).read_text());JOBS=path.INITIAL_JOBS
assert not ROOT.exists();ROOT.mkdir()
def put(p,x):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x') as f:json.dump(x,f,indent=2,sort_keys=True);f.write('\n')
def stop(*_):raise TimeoutError('Bounded600s r2 preservation expired; no automatic retry')
signal.signal(signal.SIGALRM,stop);signal.alarm(600)
put(ROOT/'PRESERVATION_INTENT.json',{'started_epoch':time.time(),'jobs':list(JOBS),'seconds':600,'automatic_retry':False,'model_calls':0,'encode_calls':0,'score_calls':0})
cli='.local/midpoint_20261011/venv/bin/modal'
try:
 subs={j:json.loads((R/'dispatch'/j/'SUBMITTED.json').read_text()) for j in JOBS}
 cmds=[('containers',[cli,'container','list','--json'])]+[(j,[cli,'app','info',subs[j]['app_id'],'--json']) for j in JOBS]
 def observe(pair):
  n,a=pair;p=subprocess.run(a,capture_output=True,timeout=45);(ROOT/(n+'_PROVIDER_RAW.json')).write_bytes(p.stdout);(ROOT/(n+'_PROVIDER_STDERR.txt')).write_bytes(p.stderr);assert p.returncode==0
  return n,json.loads(p.stdout)
 with ThreadPoolExecutor(max_workers=3) as pool:raw=dict(pool.map(observe,cmds))
 providers={}
 for j in JOBS:
  app=subs[j]['app_id'];info=raw[j];assert info['app_id']==app
  state=str(info['lifecycle']['state']).lower();owned=sum(x.get('app_id')==app for x in raw['containers'])
  assert state=='stopped' and owned==0,(j,state,owned)
  providers[j]={'app_id':app,'state':state,'owned_containers':owned,'observed_epoch':time.time()}
  put(ROOT/j/'PROVIDER_OBSERVATION.json',providers[j])
 volume=modal.Volume.from_name('sft-allocation-midpoint-v1',create_if_missing=False);store=modal.Dict.from_name(path.STORE,create_if_missing=False);bindings={};proofs={}
 for j in JOBS:
  dest=ROOT/j;prefix='p011-20261020/long_runs_r1/'+j
  def inventory():
   rows=[]
   for e in volume.iterdir('/'+prefix,recursive=True):
    n=e.path.lstrip('/');assert n.startswith(prefix+'/') and '..' not in PurePosixPath(n).parts and int(e.type) in (1,2)
    rows.append({'path':n,'type':int(e.type),'mtime':e.mtime,'size':e.size})
   return sorted(rows,key=lambda x:x['path'])
  before=inventory();put(dest/'REMOTE_INVENTORY_BEFORE.json',{'observed_epoch':time.time(),'entries':before});files=[x for x in before if x['type']==1]
  assert 0<len(files)<=100 and sum(x['size'] for x in files)<=100_000_000
  def copy(e):
   rel=e['path'][len(prefix)+1:];p=dest/'original_remote_files'/rel;p.parent.mkdir(parents=True,exist_ok=True);h=hashlib.sha256();size=0
   with p.open('xb') as f:
    for b in volume.read_file('/'+e['path']):size+=len(b);assert size<=e['size'];f.write(b);h.update(b)
   assert size==e['size'];item={'remote_path':e['path'],'relative_path':rel,'bytes':size,'sha256':h.hexdigest()};put(dest/'transfer_receipts'/(hashlib.sha256(rel.encode()).hexdigest()+'.json'),item);return item
  with ThreadPoolExecutor(max_workers=8) as pool:copied=list(pool.map(copy,files))
  after=inventory();put(dest/'REMOTE_INVENTORY_AFTER.json',{'observed_epoch':time.time(),'entries':after});assert before==after
  job=SPEC['jobs'][j];k=path.key(job);keys=[k+'/dispatch',*evidence.expected_record_keys(k,job['kind'],job['U'])];assert len(keys)==len(set(keys)) and len(keys)<1500
  def get(key):
   v={'key':key,'value':store.get(key),'observed_epoch':time.time()};put(dest/'named_records'/(hashlib.sha256(key.encode()).hexdigest()+'.json'),v);return v
  with ThreadPoolExecutor(max_workers=12) as pool:records=list(pool.map(get,keys))
  present={x['key']:x['value'] for x in records if x['value'] is not None};terminal=present[k+'/terminal'];assert terminal['status']=='failed' and terminal['app_id']==providers[j]['app_id'] and providers[j]['observed_epoch']>=terminal['finished_epoch']
  proof={'completed_epoch':time.time(),'files':copied,'file_count':len(copied),'bytes':sum(x['bytes'] for x in copied),'stable_inventory':True,'named_key_count':len(records),'present_keys':list(present),'absent_key_count':len(records)-len(present),'provider':providers[j],'scientific_completion':False,'model_calls':0,'encode_calls':0,'score_calls':0,'original_call_retries':0,'no_full_success_archive_or_scoring_inferred':True}
  put(dest/'PRESERVATION_COMPLETED.json',proof);proofs[j]=proof
  dispatch=R/'dispatch'/j
  labels={'intent':dispatch/'INTENT.json','submitted':dispatch/'SUBMITTED.json','failure':dest/'original_remote_files/FAILURE.json','provider':dest/'PROVIDER_OBSERVATION.json','preservation':dest/'PRESERVATION_COMPLETED.json'}
  labels.update({'named_'+n:dest/'named_records'/(hashlib.sha256((k+'/'+n).encode()).hexdigest()+'.json') for n in ('dispatch','claim','terminal')})
  bindings[j]={'key':k,'category':'A','reserved_usd':job['limits']['reserved_usd'],'files':{n:{'path':str(p),'sha256':sha(p)} for n,p in labels.items()}}
  # Exact new evidence is preserved outside the shared dispatch directory until
  # a new reviewed SPEC binds it. Do not create unbound RESULT or STOPPED0 there.
  print(json.dumps({n:proof[n] for n in ('file_count','bytes','named_key_count','present_keys','completed_epoch')}),flush=True)
 put(ROOT/'FAILED_ATTEMPT_BINDINGS.json',bindings);put(ROOT/'PRESERVATION_COMPLETED.json',{'completed_epoch':time.time(),'jobs':proofs,'all_original_failures_retained':True,'automatic_retry':False})
 put(R/'LONG_LR_R2_FAILED_ATTEMPT_BINDINGS.json',bindings)
except BaseException as e:
 put(ROOT/'PRESERVATION_FAILED.json',{'epoch':time.time(),'error':repr(e),'traceback':traceback.format_exc(),'partial_retained':True,'automatic_retry':False});raise
finally:signal.alarm(0)

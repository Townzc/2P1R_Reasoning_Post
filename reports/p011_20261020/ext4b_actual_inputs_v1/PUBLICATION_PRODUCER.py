"""Once-only new constructed inputs; original endpoint bytes are referenced only."""
from pathlib import Path
import gzip,io,json,hashlib,tarfile,datetime
R=Path('.local/p011_20261020/r1');P=Path('reports/p011_20261020');INPUT=R/'ext4b_inputs_r1';ACTUAL=R/'ext4b_runtime_actual_r1'
def read(p):return json.loads(Path(p).read_text())
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(2**20),b''):h.update(b)
 return h.hexdigest()
def create(p,v):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
state=R/'ext4b_actual_input_publication_r1';out=P/'ext4b_actual_inputs_v1'
assert not state.exists() and not out.exists();complete=read(INPUT/'COMPLETED.json');actual_complete=read(ACTUAL/'COMPLETED.json')
assert complete['same_supervised_B_including_EOS']==164926860 and complete['same_optimizer_updates']==2577
state.mkdir();out.mkdir();create(state/'ATTEMPT.json',{'utc':utc(),'science_repeated':False,'models':0})
try:
 inventory=read(INPUT/'MANIFEST.json')['files'];sources={};members={}
 for name,record in inventory.items():
  if name in ('ENDPOINT_GPU.json','ENDPOINT_LOCAL.json'):continue
  member='inputs/'+name;sources[member]=INPUT/name;members[member]=record
 for name,p in [('inputs/MANIFEST.json',INPUT/'MANIFEST.json'),('actual/ACTUAL_JOB_MANIFEST.json',ACTUAL/'ACTUAL_JOB_MANIFEST.json'),('actual/COMPLETED.json',ACTUAL/'COMPLETED.json'),('actual/EFFECTIVE_DOSE_METADATA.json',R/'EXT4B_ACTUAL_DOSE_METADATA.json')]:
  sources[name]=p;members[name]={'bytes':p.stat().st_size,'sha256':sha(p)}
 assert members['actual/ACTUAL_JOB_MANIFEST.json']['sha256']==actual_complete['actual_job_manifest_sha256']
 create(out/'MEMBERS.json',members)
 archive=state/'NEW_INPUT_EVIDENCE.tar.gz'
 with archive.open('xb') as file:
  with gzip.GzipFile(fileobj=file,mode='wb',compresslevel=1,mtime=0,filename='') as gz:
   with tarfile.open(fileobj=gz,mode='w|') as tar:
    for name,p in sorted(sources.items()):
     record=members[name];assert p.stat().st_size==record['bytes'];info=tarfile.TarInfo(name);info.size=record['bytes'];info.mtime=0;info.mode=0o644
     with p.open('rb') as f:tar.addfile(info,f)
     print(utc(),'ARCHIVED',name,record['bytes'],flush=True)
 parts=[];overall=hashlib.sha256();size=0
 with archive.open('rb') as file:
  i=0
  while True:
   b=file.read(40*1024**2)
   if not b:break
   part=out/f'NEW_INPUT_EVIDENCE.tar.gz.part{i:03d}'
   with part.open('xb') as f:f.write(b)
   overall.update(b);size+=len(b);parts.append({'file':part.name,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()});i+=1
 class PartStream(io.RawIOBase):
  def __init__(self,paths):self.paths=iter(paths);self.file=None
  def readable(self):return True
  def read(self,n=-1):
   if n<0:raise ValueError('Unbounded archive read forbidden')
   result=[];remaining=n
   while remaining:
    if self.file is None:
     try:self.file=next(self.paths).open('rb')
     except StopIteration:break
    b=self.file.read(remaining)
    if b:result.append(b);remaining-=len(b)
    else:self.file.close();self.file=None
   return b''.join(result)
  def close(self):
   if self.file:self.file.close()
   super().close()
 seen=set()
 with PartStream([out/x['file'] for x in parts]) as reader:
  with tarfile.open(fileobj=reader,mode='r|gz') as tar:
   for m in tar:
    assert m.isfile() and m.name in members and m.name not in seen
    h=hashlib.sha256();length=0;f=tar.extractfile(m)
    for b in iter(lambda:f.read(2**20),b''):h.update(b);length+=len(b)
    assert {'bytes':length,'sha256':h.hexdigest()}==members[m.name];seen.add(m.name)
    print(utc(),'READBACK',m.name,length,flush=True)
 assert seen==set(members)
 create(out/'ARCHIVE.json',{'compression':'gzip1','parts':parts,'compressed_bytes':size,'concatenated_sha256':overall.hexdigest(),'member_count':len(members),'uncompressed_member_bytes':sum(x['bytes'] for x in members.values()),'complete_new_archive_readback_once':True,'old_endpoint_files_rearchived':False})
 binding={'scope':'p011-ext-4B-actual-input-and-numeric-A2-lite','full_source_target':'10b74e99bb4b544fac7752d82c51b27a7125b9b8','full_spec_sha256':'132b183d52149e2378f4d5f83cf0780f12f89e3e242d63f5f7b61d8c57c5d52f','data_source_target':'583a035a9cd3353f0d71f9ad6d8432d57ef9f4ea','data_CR_report_sha256':'b08252f61e0acdcd13dfc9c6134b0ca55adde030855080da873bf188a125b3d2','input_manifest_sha256':sha(INPUT/'MANIFEST.json'),'actual_job_manifest_sha256':actual_complete['actual_job_manifest_sha256'],'actual_dose':read(R/'EXT4B_ACTUAL_DOSE_METADATA.json'),'reused_endpoints_not_rearchived':{n:inventory[n] for n in ['ENDPOINT_GPU.json','ENDPOINT_LOCAL.json']},'reused_endpoint_source_binding':'reports/p011_20261020/ext4b_relaxed_input_preflight_v2/SPEC.json#endpoint_reuse','original_model_files_source':'reports/p011_20261020/owner150_runtime_v1/SPEC.json#jobs.long_A7_S-F15_s17_owner_r1.model','private_original_model_binary_access_claimed':False,'required_flags':read(P/'ext4b_full_runtime_preflight_v1/SPEC.json')['actual_review_flags'],'GPU_started':False,'full_source_CR_and_actual_A2_still_required':True,'metadata_or_archive_not_scientific_recompute':True}
 create(out/'ACTUAL_INPUT_BINDING.json',binding)
 (out/'README.md').write_text('''# Actual revised 4B input evidence

First constructor completed:12,096 unique selected questions, first3,024 strictsubset, equal164,926,860 supervisedtokens includingEOS and2,577updates. Large exactlyonepass; small3,008answers appear4times and16appear3times (weightedE3.9950464647). This is3.9443719368 times original saved A7B, not an exact4.0 claim. Fixedshuffle/firstoriginaleligibleanswer, no outcome selection.10,490new encodings plus1,606exactoldlinecopies; censusretokenization0/newendpointencoding0.

Only this newly constructed input corpus is archived once. Original completedcensus and nativeendpoints/baseweights are referenced by their priorexacthashes rather than rearchived or re-encoded. MANIFEST,selectedraw,responseidentity,encodingproofs,tokens/masks,rosters,plans/rates,actualjobs andeffectiveE are available. No model hasrun. FullruntimeCR and actualA2 are distinct mandatorygates beforeGPU; neither thispublisher nor byteverification means PASS. Actualprivate model weights are represented by previouslysaved evaluated/pinned assetreceipts, not claimed independentlyread.

Readback verifieseverynewarchive member once, with40MiB compressedparts. Original scientific scorer/seed/bootstrap unchanged; A7differentpool comparison descriptiveonly.90USDpair/45percellincludingresume remainhard;~80cost estimate is not admission orinvoice.
''')
 (out/'PUBLICATION_PRODUCER.py').write_bytes(Path(__file__).read_bytes())
 files={str(p.relative_to(out)):{'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(out.iterdir()) if p.is_file()};create(out/'MANIFEST.json',{'files':files,'manifest_self_excluded':True})
 result={'utc':utc(),'packet':str(out),'manifest_sha256':sha(out/'MANIFEST.json'),'actual_input_binding_sha256':sha(out/'ACTUAL_INPUT_BINDING.json'),'input_manifest_sha256':binding['input_manifest_sha256'],'actual_job_manifest_sha256':binding['actual_job_manifest_sha256'],'member_count':len(members),'uncompressed_member_bytes':sum(x['bytes'] for x in members.values()),'part_count':len(parts),'compressed_bytes':size,'once_complete_readback':True}
 create(state/'COMPLETED.json',result);create(R/'EXT4B_ACTUAL_INPUT_PUBLICATION_DONE.json',result);print(json.dumps(result),flush=True)
except BaseException as exc:create(state/'FAILED.json',{'utc':utc(),'type':type(exc).__name__,'message':str(exc),'automatic_retry':False});raise

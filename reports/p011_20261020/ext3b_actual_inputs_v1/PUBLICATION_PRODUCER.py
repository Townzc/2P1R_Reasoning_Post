"""Publish only newprefix/plans/actualmetadata; reference saved original token corpus."""
from pathlib import Path
import gzip,json,hashlib,tarfile,datetime
R=Path('.local/p011_20261020/r1');P=Path('reports/p011_20261020');INPUT=R/'ext3b_inputs_r1';ACTUAL=R/'ext3b_runtime_actual_r1';SOURCE=P/'ext3b_math_runtime_preflight_v2'
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,v):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x') as f:json.dump(v,f,indent=2,ensure_ascii=False);f.write('\n')
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def run():
 state=R/'ext3b_actual_metadata_publication_r1';out=P/'ext3b_actual_inputs_v1'
 complete=read(INPUT/'COMPLETED.json');inventory=read(INPUT/'MANIFEST.json')['files'];actual=read(ACTUAL/'COMPLETED.json');spec=read(SOURCE/'SPEC.json')
 assert complete['unique_selected_questions']==9072 and complete['strict_subset_questions']==3024 and complete['new_answer_encodings']==0 and complete['GPU_calls']==0
 assert read(ACTUAL/'ACTUAL_JOB_MANIFEST.json')['spec_sha256']==sha(SOURCE/'SPEC.json')
 assert not state.exists() and not out.exists();state.mkdir();out.mkdir();put(state/'ATTEMPT.json',{'utc':utc(),'new_metadata_only':True,'old_scientific_reexecution':False})
 try:
  sources={};members={}
  excluded=('ENCODED.jsonl','ENDPOINT_GPU.json','ENDPOINT_LOCAL.json')
  for name,record in inventory.items():
   if name in excluded:continue
   sources['inputs/'+name]=INPUT/name;members['inputs/'+name]=record
  for name,path in [('inputs/MANIFEST.json',INPUT/'MANIFEST.json'),('actual/ACTUAL_JOB_MANIFEST.json',ACTUAL/'ACTUAL_JOB_MANIFEST.json'),('actual/COMPLETED.json',ACTUAL/'COMPLETED.json')]:
   sources[name]=path;members[name]={'bytes':path.stat().st_size,'sha256':sha(path)}
  assert members['actual/ACTUAL_JOB_MANIFEST.json']['sha256']==actual['actual_job_manifest_sha256']
  put(out/'MEMBERS.json',members);archive=out/'NEW_PREFIX_METADATA.tar.gz'
  with archive.open('xb') as file:
   with gzip.GzipFile(fileobj=file,mode='wb',compresslevel=1,mtime=0,filename='') as gz:
    with tarfile.open(fileobj=gz,mode='w|') as tar:
     for name,path in sorted(sources.items()):
      record=members[name];assert path.stat().st_size==record['bytes'];entry=tarfile.TarInfo(name);entry.size=record['bytes'];entry.mtime=0;entry.mode=0o644
      with path.open('rb') as f:tar.addfile(entry,f)
  assert archive.stat().st_size<40*1024**2
  seen=set()
  with tarfile.open(archive,'r|gz') as tar:
   for member in tar:
    assert member.isfile() and member.name in members and member.name not in seen
    body=tar.extractfile(member).read();assert {'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest()}==members[member.name];seen.add(member.name)
  assert seen==set(members)
  put(out/'ARCHIVE.json',{'file':archive.name,'bytes':archive.stat().st_size,'sha256':sha(archive),'members':len(members),'member_bytes':sum(x['bytes'] for x in members.values()),'complete_new_metadata_archive_readback_once':True,'old_large_encoded_and_endpoints_not_rearchived_or_rehashed':True})
  binding={'scope':spec['actual_review_scope'],'source_target':'c1a73d322e65e1ce5c4545befd366e9f8b6787a2','spec_sha256':sha(SOURCE/'SPEC.json'),'data_source_target':'cf630e860bce1a7bc2892d8cd75b57b805c1c4d4','data_CR_report_sha256':read(R/'EXT3B_PREFIX_DATA_CR_ACCEPTED.json')['report_sha256'],'input_manifest_sha256':sha(INPUT/'MANIFEST.json'),'actual_job_manifest_sha256':actual['actual_job_manifest_sha256'],'actual_completed_dose_and_counts':complete,'original_token_corpus_target':'f679fa5c28f50b011c1d85a3a689c64997cc53d5','original_token_corpus_packet':'reports/p011_20261020/ext4b_actual_inputs_v1','old_encoded_full_roster_prefix_projection':read(INPUT/'PREFIX_SOURCE_BINDING.json'),'not_rearchived_files':{n:inventory[n] for n in excluded},'new_prefix_bytes_verified_once_in_constructor':True,'prior_raw_token_bytes_exact_original_no_reencoding':True,'original_model_files_source':'reports/p011_20261020/owner150_runtime_v1/SPEC.json#jobs.long_A7_S-F15_s17_owner_r1.model','private_model_binary_access_claimed':False,'source_files':spec['source_files'],'required_flags':spec['actual_review_flags'],'GPU_started':False,'full_source_CR_and_actual_A2_still_required':True}
  put(out/'ACTUAL_INPUT_BINDING.json',binding)
  (out/'README.md').write_text('''# Actual owner options2+3 prefix input and numeric evidence

The newly completed9072prefix and first3024subset reuse original12096savedtokenlines and identities byte-for-byte. Prefixhash/selectedindices/newrowmetadata/newq-q+1plans/scaledLR/U/exactB′/effectiveE are bound here. No answerencoding, endpointencoding, census, model oroldscore repeated. Exactdose is inCOMPLETED, not an assumed3.0multiplier. Originalfullyarchivedtokenroster fixedf679fa5c isreferenced; the newprefix bytes are itsfirst9072lines, verifiedonce by constructor andnot rearchived here. Originalendpoints and weights receipts also referenced without recopying oldscientificarchives.

Only newlycreatedmetadata/plans/rates/actualjobs are archived/readbackonce. BothnewsourceCR andactualA2 requiredbeforeGPU. NoPASSclaimed by publication. Per-cell45/pair90costguards/oneproveninfraresume/MATHonly complete500endpointscope unchanged. Originaltraining/native/scalar/pool/bootstrapfunctions unchanged; AIME/AMCNOT_RUN, partialnotzero, four-sampleprimaryrequiresallfourcompleteinbothcells. Privateweights remainrepresented byoriginalreceipts, notindependentexternalbinaryread.
''')
  (out/'PUBLICATION_PRODUCER.py').write_bytes(Path(__file__).read_bytes())
  put(out/'MANIFEST.json',{'files':{x.name:{'bytes':x.stat().st_size,'sha256':sha(x)} for x in out.iterdir() if x.is_file()},'self_excluded':True})
  done={'utc':utc(),'packet':str(out),'manifest_sha256':sha(out/'MANIFEST.json'),'binding_sha256':sha(out/'ACTUAL_INPUT_BINDING.json'),'input_manifest_sha256':sha(INPUT/'MANIFEST.json'),'actual_job_manifest_sha256':actual['actual_job_manifest_sha256'],'members':len(members),'archive_bytes':archive.stat().st_size,'new_metadata_only_readback_done':True,'old_large_science_not_repeated':True}
  put(state/'COMPLETED.json',done);put(R/'EXT3B_ACTUAL_METADATA_PUBLICATION_DONE.json',done);print(json.dumps(done),flush=True)
 except BaseException as exc:put(state/'FAILED.json',{'utc':utc(),'type':type(exc).__name__,'message':str(exc),'automatic_retry':False});raise
if __name__=='__main__':run()

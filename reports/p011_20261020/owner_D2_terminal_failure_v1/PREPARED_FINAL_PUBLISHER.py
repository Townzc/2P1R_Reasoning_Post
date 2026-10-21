"""Prepared only: copy final owner-epoch A/D evidence after every attempted job closes.

Never launches a model, oracle, score or bootstrap. Private state stays private.
"""
from pathlib import Path
from datetime import datetime,timezone
import gzip,hashlib,io,json,tarfile
R=Path('.local/p011_20261020/r1');P=Path('reports/p011_20261020');OUT=P/'owner150_complete_actual_results_v1';SAVE=R/'owner150_final_publication_r1'
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,v):
 with Path(p).open('x') as f:json.dump(v,f,indent=2,ensure_ascii=False);f.write('\n')
def unique(dest,path):
 if dest in members:raise ValueError('Duplicate new archive member')
 members[dest]=path
assert not OUT.exists() and not SAVE.exists()
original=read(P/'owner150_runtime_v1/SPEC.json');retry=read(P/'owner_A1_infra_retry_runtime_v1/SPEC.json')
jobs={**original['jobs'],**retry['jobs']};members={};excluded={};bindings={};success={};failed={};selected={}
for p in sorted((R/'dispatch').glob('long_*_owner_r*/INTENT.json')):
 name=p.parent.name;intent=read(p);job=jobs[name];result=p.parent/'RESULT.json';error=p.parent/'RETURN_ERROR.json'
 if not result.exists():
  assert error.exists(),'Still-active original call: '+name
  if name=='long_A1_S-F15_s17_owner_r1':
   oldgit=read(R/'OWNER_A1_RETRY_NEW_GIT_DONE.json')
   failed[name]=dict(return_error_file=str(error),return_error=read(error),private_original_intent_sha256=sha(p),
       public_failure_packet='reports/p011_20261020/owner_A1_preemption_failure_v1',target_commit=oldgit['head'],
       manifest_sha256=oldgit['new_files']['reports/p011_20261020/owner_A1_preemption_failure_v1/MANIFEST.json']['sha256'],
       scientific_result_unavailable=True,not_scored_as_zero=True)
  elif name=='long_D2_S-F15_s17_owner_r1':
   binding=read(R/'OWNER_D2_FAILURE_PUBLICATION_GIT_DONE.json')
   packet=P/'owner_D2_terminal_failure_v1'
   assert binding['packet']==str(packet) and binding['manifest_sha256']==sha(packet/'MANIFEST.json')
   assert binding['original_return_error_sha256']==sha(error)
   failed[name]=dict(return_error_file=str(error),return_error=read(error),private_original_intent_sha256=sha(p),
       public_failure_packet=str(packet),target_commit=binding['head'],manifest_sha256=binding['manifest_sha256'],
       scientific_result_unavailable=True,not_scored_as_zero=True,partial_endpoints_not_used_as_complete_result=True,
       no_model_restart_after_dispatch_cutoff=True)
  else:
   raise ValueError('New failure must first receive its own complete preservation and publication: '+name)
  continue
 receipt=read(result);assert receipt['status']=='completed'
 base=R/'long_owner_closeout_r1';collect=base/'collect'/name;audit=base/'audit'/name;score=base/'score'/name
 cp=read(collect/'COMPLETED.json');proof=read(audit/'COMPLETE_PROOF.json');scored=read(score/'COMPLETED.json');provider=read(collect/'PROVIDER_STOPPED0.json')
 assert proof['passed'] and scored['read_only_saved_score_proof']['passed']
 assert provider['state']=='stopped' and provider['owned_containers']==0
 assert proof['training_state_verified']==(job['kind']=='student')
 assert proof['source_files']==(retry if name.endswith('_owner_r2') else original)['source_files']
 assert job['cell'] not in selected,'Do not select among multiple successful model attempts'
 selected[job['cell']]=name
 payload=audit/'payload';inv=read(payload/'EVIDENCE_MEMBERS.json')
 for f in sorted(payload.rglob('*')):
  if not f.is_file():continue
  rel=f.relative_to(payload).as_posix();dest=name+'/runtime/'+rel
  if rel=='ADMISSION.json' or rel.startswith('merged/') or f.suffix in ('.pt','.bin','.safetensors'):
   excluded[dest]=dict(saved_original_inventory=inv.get(rel),private_binary_or_accounting_not_reread=True)
  else:unique(dest,f)
 for key in ['ATTEMPT.json','COMPLETE_PROOF.json','DECODED.json','SCORING_ROWS.json']:unique(name+'/audit/'+key,audit/key)
 for key in ['ATTEMPT.json','COMPLETED.json','PROVIDER_STOPPED0.json','ORIGINAL_RESULT.json']:unique(name+'/collect/'+key,collect/key)
 for f in sorted((collect/'records').rglob('*')):
  if f.is_file() and f.name!='dispatch.json':unique(name+'/collect/records/'+f.relative_to(collect/'records').as_posix(),f)
 for f in sorted(score.rglob('*')):
  if f.is_file():unique(name+'/score/'+f.relative_to(score).as_posix(),f)
 unique(name+'/dispatch/SUBMITTED.json',p.parent/'SUBMITTED.json')
 bindings[name]=dict(job_sha256=proof['job_sha256'],actual_worker_source_files=proof['source_files'],
     local_admission_adapter_source_files=intent.get('admission_adapter_source_files'),
     private_original_intent_sha256=sha(p),original_result_sha256=sha(result),oracle_sha256=sha(audit/'COMPLETE_PROOF.json'),
     score_sha256=sha(score/'COMPLETED.json'),provider_sha256=sha(collect/'PROVIDER_STOPPED0.json'),
     original_full_private_artifact=receipt['artifact'],actual_binary_external_access_claimed=False)
 success[name]=dict(cell=job['cell'],arm=job['arm'],seed=job['seed'],B=job['B'],U=job['U'],
     completed_score_proof=scored['read_only_saved_score_proof'],actual_A3_accepted=False)
# All initial scientific cells must be explicitly successful or failed, never silently omitted.
initialcells={original['jobs'][n]['cell'] for n in original['initial_jobs']}
assert initialcells <= (set(selected)|{jobs[n]['cell'] for n in failed})
assert set(selected) <= set(initialcells)|{'A4','A3','A2','A8'}
pairs=[('baseline','A7'),*[( 'A1',cell) for cell in ['A2','A3','A4','A5','A6','A7']],('A5','A7'),('A8','A7'),('D1','D2')];contrasts={};unavailable=[]
for left,right in pairs:
 if left not in selected or right not in selected:
  unavailable.append(dict(left=left,right=right,reason='One or both successful cells absent; not a zero difference'));continue
 name=selected[left]+'__'+selected[right];folder=R/'long_analysis_r1'/name;done=read(folder/'COMPLETED.json')
 for f in sorted(folder.iterdir()):
  if f.is_file():unique('analysis/'+name+'/'+f.name,f)
 contrasts[name]=dict(summary=done,completed_sha256=sha(folder/'COMPLETED.json'))
smoke=None
if {'A7','baseline'}<=set(selected):
 f=R/'owner150_smoke_posthoc_r1/RESULT.json';smoke=read(f);unique('posthoc_smoke/RESULT.json',f)
OUT.mkdir();SAVE.mkdir();archive=SAVE/'original_scientific_bytes.tar.gz';inventory={}
with archive.open('xb') as stream:
 with gzip.GzipFile(filename='',mode='wb',fileobj=stream,mtime=0) as gz:
  with tarfile.open(fileobj=gz,mode='w|') as tar:
   for name,f in sorted(members.items()):
    raw=f.read_bytes();inventory[name]=dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),original_file=str(f));info=tarfile.TarInfo(name);info.size=len(raw);info.mtime=0;info.mode=0o644;tar.addfile(info,io.BytesIO(raw))
seen=set()
with tarfile.open(archive,'r:gz') as tar:
 for item in tar:
  raw=tar.extractfile(item).read();assert len(raw)==inventory[item.name]['bytes'] and hashlib.sha256(raw).hexdigest()==inventory[item.name]['sha256'];seen.add(item.name)
assert seen==set(inventory)
parts=[]
with archive.open('rb') as f:
 while True:
  raw=f.read(40*1024*1024)
  if not raw:break
  name=f'original_scientific_bytes.tar.gz.part{len(parts):03d}';(OUT/name).write_bytes(raw);parts.append(dict(file=name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
put(OUT/'ARCHIVE_INVENTORY.json',inventory);put(OUT/'ARCHIVE_READBACK.json',dict(archive_bytes=archive.stat().st_size,archive_sha256=sha(archive),parts=parts,members=len(inventory),every_new_member_read_back_once=True,private_exclusions=excluded,old_science_or_collectors_repeated=False))
put(OUT/'SAVED_SCORES_AND_CONTRASTS.json',dict(successful_attempts=success,failed_attempts=failed,actual_attempt_for_each_cell=selected,all_available_original_contrasts=contrasts,unavailable_pairs=unavailable,posthoc_smoke=smoke,actual_independent_A3_accepted=False))
put(OUT/'ACTUAL_RESULT_BINDING.json',dict(scope='p011-owner150-A-D-complete-results-and-original-contrasts-actual-A3',actual_evidence=bindings,failed_evidence=failed,
    required_true_flags=['complete_attempt_specific_training_and_all_original_endpoints_accepted','independent_native_decode_and_correctness_scope_disclosed','all_available_original_paired_contrasts_and_missing_cells_disclosed','posthoc_smoke_direct_owner_preselection_and_single_seed_limits_disclosed','private_binary_and_frozen_scorer_access_limits_disclosed'],actual_A3_accepted=False))
(OUT/'README.md').write_text('''# Direct-owner A/D results: actual independent A3 pending

This packet copies all original completed owner-epoch A/D outputs, first full local state/optimizer/RNG/trajectory/native-output proofs, first frozen scores and all available original planned contrasts. Failed attempts remain explicitly failed; absent or failed cells are not scored as zero. Optional cells were conditional on cost/time and not selected by observed performance. The original A1 preemption and D2 exit124/subsequent compound-guard failure are retained by their fixed failure packets; A1's single infrastructure retry is identified separately. D2 partial endpoints do not constitute a completed scientific result or a D1-D2 contrast. No original input encoding, completed model, score or bootstrap was repeated by this publisher.

The direct owner replaced predictive dispatch gates with logging and hard timers, authorized F15 before results, and required the original A7/baseline smoke rule after results. The saved posthoc report retains all outcomes and is not a prospective selection gate. All paired question intervals are conditional on the fixed training seed and do not represent training-seed population uncertainty, causal mechanism or equivalence. The original frozen scorer and its disclosed limitations remain.

Private full checkpoints, merged model weights and admission accounting are excluded using saved inventories, without rereading those binaries. Full local scientific oracles ran once; external private-binary access is not claimed. Independent actual A3 must disclose actual native-decode/correctness coverage and inaccessible state. Course-report interpretation remains with the owner. The two separate fallback controls are published in their own complete packet and are not republished here.
''')
put(OUT/'MANIFEST.json',{p.name:dict(bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(OUT.iterdir())})
put(R/'OWNER150_FINAL_RESULTS_PUBLICATION_DONE.json',dict(finished_utc=datetime.now(timezone.utc).isoformat(),packet=str(OUT),members=len(inventory),archive_bytes=archive.stat().st_size,successful_jobs=list(success),failed_jobs=list(failed),actual_A3_pending=True,never_repeat=True))
print(json.dumps(read(R/'OWNER150_FINAL_RESULTS_PUBLICATION_DONE.json')))

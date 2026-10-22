"""One new metadata/byte-copy publication; no scientific operations."""
import json,gzip,hashlib,io,tarfile
from pathlib import Path
from datetime import datetime,timezone
R=Path('.local/p011_20261020/r1');P=Path('reports/p011_20261020')
OUT=P/'d1_d2_option_a_actual_results_v1';SAVE=R/'d1_d2_option_a_publication_r1'
D1='long_D1_S-F15_s17_owner_r1';D2='long_D2_S-F15_s17_owner_r1'
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,v):
 with Path(p).open('x') as f:json.dump(v,f,indent=2,ensure_ascii=False);f.write('\n')
assert not OUT.exists() and not SAVE.exists()
base=R/'long_owner_closeout_r1';collect=base/'collect'/D1;audit=base/'audit'/D1;score=base/'score'/D1;tail=R/'d2_option_a_r1'
cp=read(collect/'COMPLETED.json');lp=read(audit/'COMPLETE_PROOF.json');ls=read(score/'COMPLETED.json');rp=read(tail/'audit/COMPLETE_PROOF.json');rs=read(tail/'score/COMPLETED.json');contrast=read(tail/'analysis/COMPLETED.json')
assert all(x['passed'] for x in [lp,rp,ls['read_only_saved_score_proof'],rs['read_only_saved_score_proof']])
assert ls['read_only_saved_score_proof']['outputs']==3300 and rs['read_only_saved_score_proof']['outputs']==2980
assert rp['original_worker_completed'] is False and rp['endpoint']['amc23']['scored']==0
assert contrast['contrast']=='D2_minus_D1'
provider=read(collect/'PROVIDER_STOPPED0.json');assert provider['state']=='stopped' and provider['owned_containers']==0
members={};excluded={}
def add(name,p):
 assert name not in members;members[name]=p
payload=audit/'payload';inv=read(payload/'EVIDENCE_MEMBERS.json')
for p in sorted(payload.rglob('*')):
 if not p.is_file():continue
 rel=p.relative_to(payload).as_posix();name=D1+'/runtime/'+rel
 if rel=='ADMISSION.json' or p.suffix in ('.pt','.bin','.safetensors'):
  excluded[name]=dict(saved_original_inventory=inv.get(rel),private_binary_or_accounting_not_reread=True)
 else:add(name,p)
for folder in ['collect','audit']:
 files=['ATTEMPT.json','COMPLETED.json','PROVIDER_STOPPED0.json','ORIGINAL_RESULT.json'] if folder=='collect' else ['ATTEMPT.json','COMPLETE_PROOF.json','DECODED.json','SCORING_ROWS.json']
 for name in files:add(D1+'/'+folder+'/'+name,base/folder/D1/name)
for p in sorted((collect/'records').rglob('*.json')):
 if p.name!='dispatch.json':add(D1+'/collect/records/'+p.relative_to(collect/'records').as_posix(),p)
for p in sorted(score.rglob('*')):
 if p.is_file():add(D1+'/score/'+p.relative_to(score).as_posix(),p)
for name in ['ATTEMPT.json','COMPLETE_PROOF.json','DECODED.json','SCORING_ROWS.json']:
 add(D2+'/option_a/audit/'+name,tail/'audit'/name)
for folder in ['score','analysis']:
 for p in sorted((tail/folder).rglob('*')):
  if p.is_file():add(D2+'/option_a/'+folder+'/'+p.relative_to(tail/folder).as_posix(),p)
for name in ['D2_OPTION_A_FIRST_FULL_ORACLE_CLI_EXIT.json','D2_OPTION_A_FIRST_SCOPED_SCORE_CLI_EXIT.json','D2_OPTION_A_FIRST_MATH_CONTRASTS_CLI_EXIT.json','OWNER_D1_FIRST_CLOSED_COLLECT_CLI_EXIT.json','OWNER_D1_FIRST_CLOSED_ORACLE_CLI_EXIT.json','OWNER_D1_FIRST_CLOSED_SCORE_CLI_EXIT.json']:
 add('local_cli_receipts/'+name,R/name)
OUT.mkdir();SAVE.mkdir();archive=SAVE/'original_D1_and_scoped_D2_results.tar.gz';inventory={}
with archive.open('xb') as stream:
 with gzip.GzipFile(filename='',mode='wb',fileobj=stream,mtime=0) as gz:
  with tarfile.open(fileobj=gz,mode='w|') as tar:
   for name,p in sorted(members.items()):
    raw=p.read_bytes();inventory[name]=dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),original_file=str(p));info=tarfile.TarInfo(name);info.size=len(raw);info.mtime=0;info.mode=0o644;tar.addfile(info,io.BytesIO(raw))
seen=set()
with tarfile.open(archive,'r:gz') as tar:
 for member in tar:
  raw=tar.extractfile(member).read();assert len(raw)==inventory[member.name]['bytes'] and hashlib.sha256(raw).hexdigest()==inventory[member.name]['sha256'];seen.add(member.name)
assert seen==set(inventory)
parts=[]
with archive.open('rb') as f:
 while True:
  raw=f.read(40*1024*1024)
  if not raw:break
  name=f'original_D1_and_scoped_D2_results.tar.gz.part{len(parts):03d}'
  with (OUT/name).open('xb') as g:g.write(raw)
  parts.append(dict(file=name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
put(OUT/'ARCHIVE_INVENTORY.json',inventory)
put(OUT/'ARCHIVE_READBACK.json',dict(archive_sha256=sha(archive),archive_bytes=archive.stat().st_size,members=len(inventory),parts=parts,every_new_member_read_back_once=True,private_exclusions=excluded,old_science_repeated=False))
binding=dict(scope='p011-D1-D2-option-a-complete-MATH-AIME-and-MATH-contrasts-actual-A3',owner_decision_sha256=sha(P/'OWNER_D2_OPTION_A_20261021.json'),D2_source_binding_sha256=sha(P/'d2_option_a_local_scope_v1/SOURCE_BINDING.json'),D2_source_target='942e1dab8bdd6dd9dcd748ca233c2cef6ebd390c',D1_original_result_sha256=sha(R/'dispatch'/D1/'RESULT.json'),D1_oracle_sha256=sha(audit/'COMPLETE_PROOF.json'),D1_score_sha256=sha(score/'COMPLETED.json'),D2_full_training_scoped_oracle_sha256=sha(tail/'audit/COMPLETE_PROOF.json'),D2_scoped_score_sha256=sha(tail/'score/COMPLETED.json'),D2_minus_D1_contrast_sha256=sha(tail/'analysis/COMPLETED.json'),D2_original_failure=dict(packet=str(P/'owner_D2_terminal_failure_v1'),target='0b44606a1133eb0b331e312e433fc09c391c1ba6',manifest_sha256=sha(P/'owner_D2_terminal_failure_v1/MANIFEST.json'),original_worker_failed=True,original_saved_raw_count=3072,raw_and_training_metadata_reused_by_reference=True),required_true_flags=['exact_owner_D2_scope_and_original_failure_retained','original_full_training_state_oracle_and_access_limits_disclosed','independent_native_decode_and_correctness_scope_disclosed','complete_MATH_AIME_AMC_incomplete_excluded_accepted','MATH_only_greedy_and_sample_paired_10000_bootstrap_accepted','missing_endpoint_whole_cycle_array_and_single_seed_limits_disclosed'],actual_A3_accepted=False)
put(OUT/'ACTUAL_RESULT_BINDING.json',binding)
put(OUT/'SAVED_RESULTS.json',dict(D1=ls['read_only_saved_score_proof'],D2=rs['read_only_saved_score_proof'],D2_amc23=rs['amc23'],D2_minus_D1=contrast,original_worker_failure_retained=True,actual_A3_accepted=False))
(OUT/'README.md').write_text('''# D1 and owner-authorized D2 option(a): actual A3 pending

D2 的 worker 在最后一批 AMC 评测时撞上硬计时器（9,000 s）；MATH-500 和 AIME 输出完整，AMC 不完整，未报告。

This packet contains original D1 full3300 results and first complete local state/trajectory/native-output oracle and frozen score, plus D2's first original full training-state oracle and complete2980 MATH/AIME scope. D2's original3072 raw records and training metadata remain in the fixed0b44606a failure archive, referenced by exact manifest; they are not regenerated, recopied from the provider or republished. The92 saved AMC rows are raw only: no decode, score, accuracy, aggregate or contrast;228missing are never zeros. The failed worker remains failed, and the derived training-only view is not a complete worker RESULT.

D2-minus-D1 is MATH500 only. Both sampled mean pass@1 and greedy use original10000 paired-question bootstrap/seed20261021. The greedy adapter repeats one saved bit only at the unchanged four-entry mean interface; no additional model samples exist. AIME24/25 are descriptive only. These are fixed-training-seed conditional question intervals, not training-seed population, mechanism or causal proofs. Original decoder, scalar scorer, symbolic pool and bootstrap functions are unchanged; all saved labels and vectors are preserved.

Original complete endpoint-cycle timings were not saved for failed D2. Saved batch acknowledgments/body times and forecasts are preserved; body times are not claimed to be whole cycles, and exact endpoint-forecast replay is unavailable. Original training/pre-engine checks were executed unchanged. Private checkpoints, exported weights and admission accounting remain excluded using saved inventories; local full-state oracles passed, but external private-binary inspection is not claimed. Independent A3 must disclose actual raw decode/correctness coverage, symbolic-engine limitations and state access. No old science/scoring/bootstrap was repeated by this publisher.
''')
put(OUT/'MANIFEST.json',{p.name:dict(bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(OUT.iterdir())})
put(R/'D1_D2_OPTION_A_ACTUAL_PUBLICATION_DONE.json',dict(finished_utc=datetime.now(timezone.utc).isoformat(),packet=str(OUT),members=len(inventory),archive_bytes=archive.stat().st_size,manifest_sha256=sha(OUT/'MANIFEST.json'),result_binding_sha256=sha(OUT/'ACTUAL_RESULT_BINDING.json'),original_D2_failure_retained=True,actual_A3_pending=True,never_repeat=True))
print(json.dumps(read(R/'D1_D2_OPTION_A_ACTUAL_PUBLICATION_DONE.json')))

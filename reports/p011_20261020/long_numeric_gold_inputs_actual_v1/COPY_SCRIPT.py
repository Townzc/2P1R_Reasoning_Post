from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, tarfile, io, shutil

R=Path('.local/p011_20261020/r1')
S=R/'long_inputs_numeric_gold_r1'
P=Path('reports/p011_20261020/long_numeric_gold_inputs_actual_v1')
assert not P.exists(), 'create once; preserve partial on error'
def h(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def write(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x') as f:f.write(x if isinstance(x,str) else json.dumps(x,ensure_ascii=False,indent=2,sort_keys=True)+'\n')
now=datetime.now(timezone.utc).isoformat()
inventory=read(S/'MANIFEST.json');assert len(inventory)==85 and not (S/'FAILED.json').exists()
complete=read(S/'COMPLETED.json');assert complete['endpoint_prompt_tokenizations']==600 and complete['training_tokenizations']==0
selected={n:v for n,v in inventory.items() if not n.endswith('/encoded.json') and not (n.split('/')[0]!='baseline' and n.endswith(('/ENDPOINT_GPU.json','/ENDPOINT_LOCAL.json')))}
selected['MANIFEST.json']={'bytes':(S/'MANIFEST.json').stat().st_size,'sha256':h(S/'MANIFEST.json')}
P.mkdir()
# This new publication reads only its selected new outputs. Original training
# archives and private multi-GB encoded projections are not rebuilt or rehashed.
archive=P/'new_inputs_and_projection_metadata.tar.gz'
with tarfile.open(archive,'w:gz',compresslevel=6) as tar:
 for name,expected in sorted(selected.items()):
  data=(S/name).read_bytes()
  assert len(data)==expected['bytes'] and hashlib.sha256(data).hexdigest()==expected['sha256'], name
  entry=tarfile.TarInfo(name);entry.size=len(data);entry.mtime=0;entry.mode=0o644
  tar.addfile(entry,io.BytesIO(data))
with tarfile.open(archive,'r:gz') as tar:
 assert sorted(tar.getnames())==sorted(selected)
 for member in tar:
  data=tar.extractfile(member).read();expected=selected[member.name]
  assert len(data)==expected['bytes'] and hashlib.sha256(data).hexdigest()==expected['sha256']
write(P/'ARCHIVE_READBACK.json',{'archive_sha256':h(archive),'archive_bytes':archive.stat().st_size,
 'members':selected,'all_selected_new_original_bytes_equal':True,'whole_private_85file_archive':False})
for name in ['COMPLETED.json','ORIGINAL_GOLD_PROJECTION.json']:
 (P/name).write_bytes((S/name).read_bytes())
(P/'ORIGINAL_INVENTORY.json').write_bytes((S/'MANIFEST.json').read_bytes())
omitted={n:v for n,v in inventory.items() if n not in selected}
reuse={}
for label,packet,target,invpath in [
 ('OT3','reports/p011_20261020/ot3_nfc_inputs_actual_v1','20044d50cee1acbef0b1aa17ed559e8f0311d98a','ARCHIVE_READBACK.json'),
 ('AM','reports/p011_20261020/am_inputs_actual_v1','cf9a12e4f3cfb883b09be603c8aa5d79206c90f3','am/ARCHIVE_READBACK.json')]:
 old=read(Path(packet)/invpath)
 reuse[label]={'fixed_target':target,'packet':packet,'archive_readback_file':invpath,
  'archive_readback_sha256':h(Path(packet)/invpath),'original_members':old.get('original_members',old.get('members',{})),
  'new_archive_or_old_validation_run':False}
write(P/'TRAINING_REUSE_AND_PROJECTION.json',{'original_85file_inventory_sha256':h(S/'MANIFEST.json'),
 'original_private_bytes':sum(v['bytes'] for v in inventory.values()),'omitted_from_this_new_archive':omitted,
 'original_training_sources':reuse,'training_encoding_calls':0,'whole_private_encoded_files_independently_read_by_reviewer':False,
 'reconstruction':'Select the exact original ENCODED.jsonl dictionaries by each original plan row_path_ids, in order. ORIGINAL_ROWS.json binds source file SHA and canonical row-value digest. plan.json is original file-byte copy; encoded.json is lossless JSON list reserialization, not an encoding pass. Public original OT3/AM archives remain the full token source.',
 'duplicate_endpoint_files':'All ten cell ENDPOINT_GPU/LOCAL entries equal the baseline byte hashes in ORIGINAL_INVENTORY. Baseline full originals and ENDPOINT_ROSTER are in the new archive.'})
binding={'source_target':'e6ce0467ded06b4bd09487e7843f5bf2f6f6924e',
 'source_binding_path':'reports/p011_20261020/long_runtime_repair_v1/SOURCE_BINDING.json',
 'source_binding_sha256':h('reports/p011_20261020/long_runtime_repair_v1/SOURCE_BINDING.json'),
 'source_files':complete['source_files'],'original_inventory_sha256':h(S/'MANIFEST.json'),
 'completion_file_sha256':h(S/'COMPLETED.json'),'archive_sha256':h(archive),
 'owner_decision_sha256':h(R/'OWNER_LONG_NUMERIC_GOLD_INPUT.json'),
 'source_CR_report_sha256':'7c67c4d4c5afd2a874f1bd3dfc3e6654f369decca35ccede67d53da65bf3ff40',
 'original_failed_attempt_retained':True,'new_CPU_CLI':61074,'new_CPU_status':'EXIT0CONSUMED',
 'actual_input_A1_accepted':False,'new_paid_calls':0}
write(P/'ACTUAL_INPUT_BINDING.json',binding)
write(P/'README.md',f'''# Actual long input continuation — input A1 pending

Created {now}. The single approved CPU continuation61074 completed at
2026-10-21T07:10:22.630991+00:00. It encoded600 original evaluation prompts once,
saved3300 requests, and losslessly reused the accepted A/D training tokens and
original plan files. There was no training-token encoding, model, generation or
scoring. The original failed37318 and its530 unsaved ephemeral prompts remain
failed; those prompts were not claimed as reused.

The new archive contains every new endpoint/gold roster and compact plan, LR,
ordered-row and completion record needed for actual A1. Its {len(selected)} members
were read back once. The complete private output inventory contains85 members,
{sum(v['bytes'] for v in inventory.values())}bytes. Ten large lossless encoded-list
projections and20 duplicate endpoint files are referenced explicitly, not silently
represented as archived. Full original training rows remain available in the fixed
OT3 and AM archives. TRAINING_REUSE_AND_PROJECTION describes deterministic row
selection and every omitted file/hash. Public hashes alone do not prove an auditor
read a private file. Actual review must state which row reconstruction/checks it
performed, or retain an access limitation.

Original A grid4032parents/B41813212/U654 and D1024parents/B4070922/U64 remain
unchanged. All30 arm/cell validation receipts are in COMPLETED. Native endpoint
context is17243, generation cap16384, full3300 request roster; gold stays local.
ORIGINAL_GOLD_PROJECTION retains530strings,30integers and40integral-floats with
original values and equal-value textual scoring projection. No scientific label
was changed. No runtime or paid numerical A2 admission follows from this packet.

The same long shared request now seeks actual input A1 plus later measured numeric
A2. R1–R3 source CR is genuinely accepted in the adjacent review135a4f53 packet.
Three separate engineering preflights still require their exact subset source/input
and bounded numeric admission. Original input failure and all earlier OT3/AM
limitations remain immutable. P010 formal freeze remains due Oct21 19UTC.

One read-only completion metadata lookup used `proofs[A8]` rather than
`proofs[A8/S-L15]`; it failed before the CLI status update. Only the missing metadata
was corrected; no constructor repeated. Local bounded awake PID was absent on the
cleanup check; no signal was sent and the reason for absence is unknown.
''')
shutil.copyfile(__file__,P/'COPY_SCRIPT.py')
payload={str(p.relative_to(P)):{'bytes':p.stat().st_size,'sha256':h(p)} for p in sorted(P.rglob('*')) if p.is_file()}
write(P/'PUBLIC_MANIFEST.json',payload)
write(R/'LONG_ACTUAL_INPUT_PUBLICATION_COMPLETED.json',{'created_utc':now,'public_packet':str(P),
 'public_manifest_sha256':h(P/'PUBLIC_MANIFEST.json'),'archive_readback_members':len(selected),
 'archive_bytes':archive.stat().st_size,'archive_sha256':h(archive),'old_training_archive_rebuilds':0,
 'public_files':payload,'no_repeat':True})
print(json.dumps({'archive_members':len(selected),'archive_bytes':archive.stat().st_size,'public_members':len(payload)+1}))

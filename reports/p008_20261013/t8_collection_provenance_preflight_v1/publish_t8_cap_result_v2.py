"""PREPARED ONLY: publish one fully closed T8 as an immutable compact G3 packet.

No cloud calls, scoring, checkpoint loading, or overwriting. The archive contains
selected original evidence bytes; private runtime gates are not published.
"""
from pathlib import Path
import datetime, gzip, hashlib, json, shutil, sys, tarfile
from experiments.sft_allocation_midpoint.common import read, dump, sha, digest, manifest
from experiments.sft_allocation_p008.student_t8_cap_binding import verify_supplement, AMENDMENT_KEY, supplement_key

r = Path(__file__).resolve().parent
s = r / 'student_completion_r1'
run = sys.argv[1]
spec_path = Path('reports/p008_20261013/student_t8_cap_9600_v1/ADMISSION.json')
spec = read(spec_path)
assert run in spec['runs']
out = Path('reports/p008_20261013/t8_results_v1') / run
assert not out.exists(), 'Existing immutable packet; reconcile, never rerun publisher'
root = s / 'exports' / run / 'evidence'
oracle = read(root / 'LOCAL_ORACLE_AUDIT.json')
envelope = read(s / 'runs' / run / 'result.json')
provider = read(s / 'closeouts' / run / 'provider.json')
ledger = read(s / 'closeouts' / run / 'ledger.json')
intent = read(root / 'intent.json')
cfg = intent['config']
campaign = 'p008-students-completion-20261013-r1'
prefix = 'midpoint/' + campaign + '/'
assert cfg['run_id'] == run and intent['plan']['campaign_id'] == campaign
assert cfg['max_seconds'] == 9560 and intent['effective_worker_seconds'] == 9600
assert read(root / 'admission.json') == spec
assert digest(spec) == intent['release']['spec_sha256']
assert intent['release']['source_files'] == read(r / 't8_cap_9600_r1/RUNTIME_ACCEPTED.json')['source_files']
assert oracle['passed'] is True and oracle['run_id'] == run
assert oracle['updates_verified'] == 2048 and oracle['targets_verified'] == 4194296
assert oracle['outputs_rescored'] == 1319 and oracle['original_N2_passed'] is False
assert oracle['post_hoc_engineering_deviation'] is True and oracle['effective_worker_seconds'] == 9600
assert oracle['total_reserved_cents'] == 1258 and oracle['supplement_reserved_cents'] == 5
assert oracle['forensic_checkpoints']['1024']['used_for_selection'] is False
assert envelope['receipt'] == ledger[prefix + 'terminal/' + run]
assert envelope['receipt']['status'] == 'completed'
assert envelope['receipt']['run_id'] == run
assert envelope['receipt']['evidence_sha256'] == oracle['artifact_digest'] == digest(envelope['artifact_manifest'])
assert provider['apps'] and not provider['owned_containers']
assert all(x['state'] == 'stopped' for x in provider['apps'])
supplement = verify_supplement(ledger, spec, run)
assert intent['supplement'] == supplement
files = envelope['artifact_manifest']
assert read(root / 'artifact_manifest.json') == files

# L1: carry the actual collection and optional callback-recovery route into
# the public packet. No private intent/gate or full recovery payload is copied.
closeout = s/'closeouts'/run
collection_file = closeout/'COLLECTION.json'
collection = dict(schema='p008_public_collection_provenance_v1', run_id=run, campaign=campaign,
     collection_route='single_run_readonly', original_result_file_sha256=sha(s/'runs'/run/'result.json'),
     source_ledger_file_sha256=sha(closeout/'ledger.json'), provider_file_sha256=sha(closeout/'provider.json'),
     original_timing_metadata_file_sha256=sha(closeout/'TIMING_READ_METADATA.json'),
     provider_released=True, completed_terminal_matches_original_envelope=True,
     new_model_calls=0, new_remote_writes=0, new_raw_scoring=False,
     callback_route='original_envelope_available_without_recovery',
     original_callback_error_retained=(s/'runs'/run/'return_error.json').exists())
if collection_file.exists():
    c = read(collection_file)
    assert c['passed'] is True and c['new_model_calls'] == c['new_remote_writes'] == 0
    assert c['one_ledger_scan'] is True and c['selected_terminal_before_after_equal'] is True
    assert run in c['runs'] and len(c['runs']) == len(set(c['runs']))
    assert c['common_ledger_sha256'] == sha(closeout/'ledger.json')
    wave = Path(c['wave'])
    assert wave.resolve().parent == (s/'t8_collection_waves').resolve()
    wi = read(wave/'READ_INTENT.json'); done = read(wave/'COMPLETED.json')
    assert wi['runs'] == c['runs'] == done['runs'] and done['passed'] is True
    assert done['ledger_sha256'] == c['common_ledger_sha256']
    assert done['new_model_calls'] == done['new_remote_writes'] == 0
    assert wi['envelope_sha256'][run] == collection['original_result_file_sha256']
    collection.update(collection_route='named_wave_single_scan_readonly',named_runs=c['runs'],
       source_collection_file_sha256=sha(collection_file),wave_intent_file_sha256=sha(wave/'READ_INTENT.json'),
       wave_completed_file_sha256=sha(wave/'COMPLETED.json'),
       selected_terminal_before_after_equal=True,unrelated_active_records_snapshot_atomic=False)
else:
    for path in (s/'t8_collection_waves').glob('*/READ_INTENT.json'):
        assert run not in read(path)['runs'], 'Existing wave must finish or reconcile; cannot claim single-run route'
recovery = s/'receipt_recovery_t8_cap'/run
if recovery.exists():
    proof = read(recovery/'READBACK_VERIFIED.json')
    assert proof['passed'] is True and proof['new_model_calls'] == proof['new_remote_writes'] == 0
    assert proof['original_N2_passed'] is False and proof['post_hoc_engineering_deviation'] is True
    assert collection['original_callback_error_retained']
    assert read(s/'runs'/run/'return_error.json')['type'] == 'ConnectionError'
    assert set(proof['files']) == {'intent.json','admission.json','result.json','artifact_manifest.json'}
    for name, record in proof['files'].items():
        assert record['sha256'] == sha(root/name) and record['bytes'] == (root/name).stat().st_size
    collection.update(callback_route='bounded_readonly_original_volume_reconstruction',
       recovery_verified_file_sha256=sha(recovery/'READBACK_VERIFIED.json'),
       original_network_error_file_sha256=sha(s/'runs'/run/'return_error.json'),
       recovered_original_files=proof['files'],recovery_new_model_calls=0,recovery_remote_writes=0)

selected = []
for directory in ('endpoint1319', 'intents', 'completed'):
    selected.extend(str(p.relative_to(root)) for p in (root / directory).rglob('*') if p.is_file())
selected.extend(('result.json', 'recipe.json', 'environment.json', 'guard_read_metrics.json',
                 'block_journal_metrics.json', 'training_journal_policy.json'))
for checkpoint in (root / 'checkpoint_1024', root / 'checkpoint_2048'):
    selected.extend(str(p.relative_to(root)) for p in checkpoint.glob('*.json'))
assert len(selected) == len(set(selected)) and selected
selected = sorted(selected)
selected_manifest = {name: files[name] for name in selected}
for name, record in selected_manifest.items():
    source = root / name
    assert not source.is_symlink() and source.stat().st_size == record['bytes']
    assert sha(source) == record['sha256']
assert 'intent.json' not in selected and not any(name.endswith('.pt') for name in selected)
assert sum(item['bytes'] for item in selected_manifest.values()) < 512 * 1024**2

out.mkdir(parents=True, exist_ok=False)
archive = out / 'original_evidence.tar.gz'
with archive.open('xb') as raw, gzip.GzipFile(fileobj=raw, mode='wb', mtime=0, filename='', compresslevel=6) as gz:
    with tarfile.open(fileobj=gz, mode='w|', format=tarfile.PAX_FORMAT) as tar:
        for name in selected:
            info = tarfile.TarInfo(name)
            info.size = selected_manifest[name]['bytes']
            info.mode = 0o644
            info.mtime = 0
            with (root / name).open('rb') as source:
                tar.addfile(info, source)
assert archive.stat().st_size < 95 * 1024**2, 'Keep partial packet; no automatic split or republish'
seen = set()
with tarfile.open(archive, 'r|gz') as tar:
    for entry in tar:
        assert entry.isfile() and entry.name in selected_manifest and entry.name not in seen
        record = selected_manifest[entry.name]
        assert entry.size == record['bytes']
        h = hashlib.sha256()
        size = 0
        member = tar.extractfile(entry)
        for block in iter(lambda: member.read(2**20), b''):
            size += len(block)
            h.update(block)
        assert size == record['bytes'] and h.hexdigest() == record['sha256']
        seen.add(entry.name)
assert seen == set(selected_manifest)
dump(out / 'ORIGINAL_EVIDENCE_MANIFEST.json', selected_manifest)
dump(out / 'ARCHIVE_READBACK.json', dict(passed=True, files_verified=len(seen), bytes=archive.stat().st_size,
                                       sha256=sha(archive), all_original_bytes=True, new_scoring=False))
for name in ('LOCAL_ORACLE_AUDIT.json', 'artifact_manifest.json'):
    shutil.copyfile(root / name, out / name)
shutil.copyfile(s / 'closeouts' / run / 'TIMING_READ_METADATA.json', out / 'TIMING_READ_METADATA.json')
shutil.copyfile(r / 'student_preparation_r1/inputs/gsm8k_test1319.jsonl', out / 'gsm8k_test1319.jsonl')
dump(out / 'ENVELOPE.json', envelope)
dump(out / 'SOURCE_BINDING.json', dict(plan=intent['plan'], config=cfg,
     source_commit=intent['release']['commit'], source_files=intent['release']['source_files'],
     spec_sha256=intent['release']['spec_sha256'], started_epoch=intent['started_epoch'],
     original_intent_file_sha256=sha(root / 'intent.json'), effective_worker_seconds=9600,
     total_reserved_cents=1258, supplement=supplement, original_N2_passed=False,
     post_hoc_engineering_deviation=True,
     runtime_and_numeric_acceptance='reports/p008_20261013/t8_cap_9600_accepted_v1'))
dump(out / 'RESOURCE_RELEASE.json', dict(utc=provider['utc'], owned_containers=[],
     apps=[dict(app_id=x['app_id'], state=x['state'], stopped_at=x['lifecycle']['stopped_at']) for x in provider['apps']]))
public_keys = {prefix + k + '/' + run for k in ('claim', 'intent', 'terminal')}
public_keys.update((prefix + 'campaign', AMENDMENT_KEY, supplement_key(run)))
dump(out / 'LEDGER.json', {k: v for k, v in ledger.items() if k in public_keys or k.startswith(prefix + run + '/')})
dump(out / 'SUMMARY.json', dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
     run_id=run, correct=oracle['correct'], n=1319,
     length_caps=oracle['endpoint_stop_diagnostics']['length_cap_outputs'], updates=2048, targets=4194296,
     state_sha256=oracle['state_sha256'], forensic_checkpoints=oracle['forensic_checkpoints'],
     technical_unknowns=0, local_oracle_passed=True, external_review='pending', provider_released=True,
     actual_entry_to_terminal_seconds=envelope['receipt']['finished_epoch'] - intent['started_epoch'],
     original_N2_passed=False, post_hoc_engineering_deviation=True, effective_worker_seconds=9600,
     reserved_usd=12.58, provider_invoice_usd=None, final_cpu_integrity_complete=False, new_model_calls=0))
(out / 'REVIEW_REQUEST.md').write_text('''# Completed T8: independent G3 requested

Verify every saved endpoint token and all 2,048 updates / 4,194,296 targets,
including the 1,024-step forensic checkpoint, original scientific claim,
operational cap, and supplemental reservation. original_evidence.tar.gz holds
selected original bytes, with per-member SHA/size and a verified archive
readback. It replaces thousands of public loose files; it is not the original
private worker bundle. Raw outputs, scored records, recipe, local and remote
training journals, and both checkpoint metadata sets are included. Full state
binaries remain private/on Volume; public hashes do not imply external binary
inspection. COLLECTION.json identifies the actual single-run or named-wave collection route and any bounded original-callback recovery, with source hashes and no new model call. Private gate payloads are excluded; their original intent hash and
the fixed public admission/acceptance packets are linked in SOURCE_BINDING.

The original 9,530-second numerical admission criterion failed. The owner and
the independent reviewer subsequently approved the same eight finite slots
with a 9,600-second operational cap and 9,570-second admission line. This is a
post-hoc engineering deviation; scientific inputs, dose and endpoint rules
remain unchanged. Reservations are not invoices. The final CPU integrity audit
is still separate. Publish all outcomes and caps without effect-based gating.
''')
dump(out / 'COLLECTION.json', collection)
dump(out / 'MANIFEST.json', manifest(out))
print(json.dumps(dict(packet=str(out), run_id=run, correct=oracle['correct'], external_review='pending')))

"""New copy-only formal snapshot; never runs an original scientific publisher."""
from pathlib import Path
from datetime import datetime,timezone
import subprocess,json,hashlib
R=Path('.local/p010_20261019/r1');P=Path('reports/p010_20261019')
CUTOFF=datetime(2026,10,21,19,0,0,tzinfo=timezone.utc)
def now():return datetime.now(timezone.utc)
def sha_bytes(b):return hashlib.sha256(b).hexdigest()
def gitbytes(commit,path):return subprocess.check_output(['git','show',commit+':'+str(path)])
def create(p,value):
    with Path(p).open('x') as f:json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')
started=now();assert started>=CUTOFF,'Formal freeze cannot precede actual scheduled cutoff'
out=P/'midpoint_freeze_20261021_1200PDT_v1';assert not out.exists()
attempt=R/'FINAL_FREEZE_20261021_ATTEMPT.json';assert not attempt.exists()
create(attempt,dict(scheduled_cutoff_utc=CUTOFF.isoformat(),actual_write_started_utc=started.isoformat(),copy_only=True,old_publisher_called=False))
out.mkdir();copies={};source_manifests={};exclusions={}
sources=[('9178029d82776b01a759d6376d7309bd7df9681a','z2_number_trace_v1'),('f8c17cf8166cd2a011e66483c0871902cb4edb5f','post_audit_technical_notes_20261020_v1'),('f8c17cf8166cd2a011e66483c0871902cb4edb5f','technical_handoff_20261020_v1'),('f8c17cf8166cd2a011e66483c0871902cb4edb5f','review_f04922a_actual_E3_C6_Z2_accepted_v1')]
for commit,folder in sources:
    source=P/folder;raw_manifest=gitbytes(commit,source/'MANIFEST.json');m=json.loads(raw_manifest);files=m.get('files',m)
    source_manifests[folder]=dict(commit=commit,path=str(source/'MANIFEST.json'),sha256=sha_bytes(raw_manifest))
    for name,meta in sorted(files.items()):
        # The Claude-owned placeholder is outside this Codex freeze. Original
        # mixed Z2 bytes are private; only the already-public non-Z1 projection
        # appears in the accepted metadata packet copied here.
        if name.endswith('.py') or name=='T3_CLAUDE_OWNED_COMPONENT.json':
            exclusions[folder+'/'+name]={'reason':'unused historical builder or Claude-owned placeholder; no content opened','original_manifest_entry':meta};continue
        raw=gitbytes(commit,source/name);assert len(raw)==meta['bytes'] and sha_bytes(raw)==meta['sha256']
        dest=out/folder/name;dest.parent.mkdir(parents=True,exist_ok=True)
        with dest.open('xb') as f:f.write(raw)
        copies[str(dest.relative_to(out))]=dict(source_commit=commit,source_file=str(source/name),bytes=len(raw),sha256=sha_bytes(raw),byte_identical=True)
    dest=out/folder/'MANIFEST.json';dest.write_bytes(raw_manifest)
    copies[str(dest.relative_to(out))]=dict(source_commit=commit,source_file=str(source/'MANIFEST.json'),bytes=len(raw_manifest),sha256=sha_bytes(raw_manifest),byte_identical=True,original_manifest_includes_excluded_historical_files=True)
create(out/'COPY_SOURCE_BINDING.json',dict(source_manifests=source_manifests,files=copies,explicit_copy_exclusions=exclusions,scientific_recomputation=False,old_verifier_or_publisher_repeated=False))
status=dict(scheduled_cutoff_utc=CUTOFF.isoformat(),actual_snapshot_write_started_utc=started.isoformat(),actual_snapshot_write_completed_utc=now().isoformat(),actual_freeze=True,final_frozen_version_A5='PENDING_NOT_SUBSTITUTED_BY_EARLY_A5',original_scientific_calls_complete=True,new_model_encoding_scoring_statistics_rendering=0,old_provider_billing_queries=0,source_cutoff_policy='Only fixed existing Codex-owned technical tables/figures and accepted dated notes',early_A5_scope_limits='38 members/73 of77 trace sources independently verified;4 local-only not verified',Z1_original_material_not_opened_for_freeze=True,prior_mixed_report_exposure_record_retained=True,failed_cancelled_histories_retained=True,private_state_or_local_only_evidence_not_claimed_independently_read=True)
create(out/'FREEZE_STATUS.json',status)
(out/'README.md').write_text('''# P010 formal technical freeze — 2026-10-21 12:00 PDT

This is the actual immutable copy-only freeze at or after **2026-10-21 19:00 UTC**. `FREEZE_STATUS.json` separately records the scheduled cutoff and actual write times. The original T1–T4 tables, F1–F2 figures and number-trace bindings come from fixed 9178029d; dated footnotes, accepted E3/C6 actual A3, early Codex-scoped A5, boundary record and technical handoff come from fixed f8c17cf8. `COPY_SOURCE_BINDING.json` binds each copied original byte sequence and explicit exclusions. Original manifests retain their historical scope and statuses; this root status governs the new snapshot.

No original model, encoding, scoring, statistics, figure rendering, verifier, collector or publisher was rerun. All retained failures and cancellations remain in the original linked evidence. The old cost observation is delayed/incompletely attributed usage, not final expense, invoice or balance; reservations are separate. No fresh provider or billing query was needed for the freeze.

The accepted dated T1 field-definition and GSM parser-sensitivity caveats accompany the unchanged original tables. All contrasts, including unfavorable results, remain available. This is a technical evidence handoff; the owner writes course-report and slide interpretation.

The earlier A5 remains an early review with access limits (73 of77 trace sources verified,4 local-only unverified). It does not accept this final frozen version. A new final A5 is required for the exact snapshot commit and manifest. Claude-owned Z1 material is excluded; the historical accidental mixed-report exposure is retained, and only the existing non-Z1 projection is copied. No complete mixed report was opened for this freeze.

- [Tables, figures and number trace](z2_number_trace_v1/README.md)
- [Accepted dated technical notes](post_audit_technical_notes_20261020_v1/README.md)
- [Original accepted technical handoff](technical_handoff_20261020_v1/README.md)
- [Accepted audit evidence and access limits](review_f04922a_actual_E3_C6_Z2_accepted_v1/README.md)
''')
builder=Path(__file__);(out/'copy_only_freeze_builder.py').write_bytes(builder.read_bytes())
manifest={str(p.relative_to(out)):{'bytes':p.stat().st_size,'sha256':sha_bytes(p.read_bytes())} for p in sorted(out.rglob('*')) if p.is_file()}
create(out/'MANIFEST.json',dict(schema='p010-actual-final-freeze-v1',files=manifest,scheduled_cutoff_utc=CUTOFF.isoformat(),actual_snapshot_write_started_utc=started.isoformat(),scientific_recomputation=False))
create(R/'FINAL_FREEZE_20261021_COMPLETED.json',dict(packet=str(out),manifest_sha256=sha_bytes((out/'MANIFEST.json').read_bytes()),copy_binding_sha256=sha_bytes((out/'COPY_SOURCE_BINDING.json').read_bytes()),copied_original_files=len(copies),new_files=len(manifest)+1,finished_utc=now().isoformat(),final_A5_pending=True,never_repeat=True))
print(json.dumps(dict(packet=str(out),copied_original_files=len(copies),new_files=len(manifest)+1,actual_write_started=started.isoformat(),final_A5='PENDING')))

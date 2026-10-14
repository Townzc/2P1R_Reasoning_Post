"""Publish the one original completed CPU integrity proof; no cloud or science.

PREPARED ONLY. Requires the separately reviewed local finalizer's real PASS.
Copies original compact bytes and receipts into a new immutable dated packet.
"""
from pathlib import Path
import datetime
import json
import shutil

from experiments.sft_allocation_midpoint.common import read, dump, sha, digest, manifest
from experiments.sft_allocation_p008.audit_bundle import CONTAINERS

R = Path(__file__).resolve().parent
ROOT = R.parents[2]
CPU = R / 'student_completion_r1/final_audit_t8_cap_r1'
E = CPU / 'export_r1/evidence'
OUT = ROOT / 'reports/p008_20261013/final_cpu_integrity_v1'
SPEC = ROOT / 'reports/p008_20261013/final_audit_t8_cap_admission_v1/ADMISSION.json'


def publish():
    if OUT.exists():
        raise ValueError('Existing immutable CPU packet; preserve partial files, never republish')
    proof_path = E / 'LOCAL_FINAL_CPU_VERIFICATION.json'
    proof = read(proof_path)
    envelope = read(CPU / 'runs/audit/result.json')
    binding, spec = read(CPU / 'binding.json'), read(SPEC)
    provider = read(CPU / 'closeout_r1/provider.json')
    ledger_path = CPU / 'closeout_r1/ledger.json'
    intent, result = read(E / 'intent.json'), read(E / 'result.json')
    files = envelope['artifact_manifest']
    assert proof['passed'] is True and envelope['receipt']['status'] == 'completed'
    assert proof['logical_runs'] == 21 and proof['physical_sources'] == 24
    assert proof['original_failed_sources'] == 3 and proof['state_binaries_bound'] == 26
    assert proof['original_failures_preserved'] is True
    assert proof['new_model_calls'] == 0 and proof['new_raw_rescoring'] is False
    assert proof['state_binaries_reloaded_locally'] is False
    assert proof['original_N2_passed'] is False and proof['post_hoc_engineering_deviation'] is True
    assert proof['binding_sha256'] == digest(binding) and proof['admission_sha256'] == digest(spec)
    assert proof['artifact_digest'] == digest(files) == envelope['receipt']['evidence_sha256']
    assert proof['original_receipt_sha256'] == sha(CPU / 'runs/audit/result.json')
    assert proof['ledger_file_sha256'] == sha(ledger_path)
    assert proof['provider_evidence_sha256'] == sha(CPU / 'closeout_r1/provider.json')
    assert proof['finalizer_source_sha256'] == sha(ROOT / 'scripts/audit_p008_final_cpu.py')
    assert intent['binding'] == binding and result == envelope['result']
    assert set(result['labels']) == set(binding['labels']) and len(result['labels']) == 24
    assert provider['owned_containers'] == [] and len(provider['apps']) == 1
    assert provider['apps'][0]['app_id'] == proof['provider_app_id']
    assert provider['apps'][0]['lifecycle']['state'] == 'stopped'
    assert all(c['app_id'] != proof['provider_app_id'] for c in provider.get('other_containers', []))
    for name in CONTAINERS:
        f = E / name
        assert not f.is_symlink() and f.stat().st_size == files[name]['bytes']
        assert sha(f) == files[name]['sha256']
    assert sum(files[n]['bytes'] for n in CONTAINERS) < 95 * 1024**2
    camp = binding['plan']['campaign_id']
    ledger = read(ledger_path)
    assert ledger['midpoint/' + camp + '/terminal/audit'] == envelope['receipt']
    actual_wall = envelope['receipt']['finished_epoch'] - intent['started_epoch']
    assert 0 <= result['wall_seconds'] <= actual_wall <= 3300
    # Independent enumeration addresses reviewer ap/N2 without changing the accepted finalizer.
    states = {name: item.get('checkpoint_sha256', {})
              for name, item in result['labels'].items() if item.get('checkpoint_sha256')}
    failed = sorted(name for name, item in result['labels'].items()
                    if item.get('original_status') == 'failed')
    completed = sorted(set(result['labels']) - set(failed))
    observed_counts = dict(state_binaries=sum(len(v) for v in states.values()),
                           physical_sources=len(result['labels']),
                           completed_physical_sources=len(completed),
                           failed_physical_sources=len(failed))
    assert observed_counts == dict(state_binaries=26, physical_sources=24,
        completed_physical_sources=21, failed_physical_sources=3)
    assert observed_counts['state_binaries'] == proof['state_binaries_bound']
    assert observed_counts['completed_physical_sources'] == proof['completed_physical_sources']
    assert observed_counts['failed_physical_sources'] == proof['original_failed_sources']
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    summary = dict(utc=now, passed_local=True, external_G3='pending',
        campaign=camp, run_id='audit', provider_app_id=proof['provider_app_id'],
        physical_sources=24, logical_sources=21, completed_sources=21,
        retained_failed_sources=3, full_state_binaries_checked_by_original_CPU=26,
        source_files=len(intent['release']['source_files']),
        CPU_entry_to_terminal_seconds=actual_wall,
        CPU_reported_seconds_before_final_pack=result['wall_seconds'],
        proxy_forecast_seconds=binding['io_gate']['forecast_seconds'],
        actual_runtime_is_not_a_future_host_bound=True,
        original_N2_passed=False, post_hoc_engineering_deviation=True,
        reservation_usd=5, new_reservation_usd=0, provider_invoice_usd=None,
        new_model_calls=0, new_raw_rescoring=False, original_Volume_retained=True,
        primary_material_freeze_unchanged=True,
        original_receipt_sha256=sha(CPU/'runs/audit/result.json'),
        original_provider_sha256=sha(CPU/'closeout_r1/provider.json'),
        local_verification_sha256=sha(proof_path))
    OUT.mkdir()
    for name in CONTAINERS:
        shutil.copyfile(E/name, OUT/name)
        assert sha(OUT/name) == files[name]['sha256']
    for src, name in [(CPU/'runs/audit/result.json','ENVELOPE.json'),
                      (E/'artifact_manifest.json','ARTIFACT_MANIFEST.json'),
                      (proof_path,'LOCAL_FINAL_CPU_VERIFICATION.json'),
                      (ledger_path,'LEDGER.json'), (SPEC,'ADMISSION.json')]:
        shutil.copyfile(src, OUT/name)
        assert sha(OUT/name) == sha(src)
    # Expose the original selected app rows; unrelated workspace rows stay private.
    public_apps = [{**app, 'lifecycle': {k:v for k,v in app['lifecycle'].items()
                    if k not in ('created_by','deployed_by','stopped_by')}}
                   for app in provider['apps']]
    dump(OUT/'PROVIDER.json',dict(utc=provider['utc'],apps=public_apps,
        owned_containers=[],original_provider_file_sha256=sha(CPU/'closeout_r1/provider.json'),
        unrelated_workspace_rows_omitted=True, actor_identity_fields_omitted=True))
    dump(OUT/'SOURCE_BUNDLE.json',intent['release']['source_files'])
    dump(OUT/'SUMMARY.json',summary)
    dump(OUT/'OBSERVED_PROOF_ROSTER.json',dict(counts=observed_counts, state_identities=states,
        completed_sources=completed, retained_failed_sources=failed,
        original_CPU_result_sha256=sha(CPU/'runs/audit/result.json'),
        derivation='Enumerated already verified proof JSON; no state reload, scoring, or new runtime call'))
    shutil.copyfile(__file__,OUT/'PUBLICATION_SOURCE.py')
    (OUT/'README.md').write_text(
        '# Final original CPU integrity proof — external review pending\n\n'
        'This dated addendum follows the immutable21:00PDT materials snapshot. '
        'The original single500-cent CPU slot completed; its local finalizer passed. '
        'The24physical sources represent21logical outcomes and retain the failed D2 parent '
        'and both failed zero-update T1 attempts. The CPU independently copied and checked '
        'the26complete states; its original proofs are bound to the earlier raw/dose oracles.\n\n'
        'The local finalizer checks exact source/admission/claim/unit/done/proof bytes, state '
        'identities, original app release, failed parents and all9T8 supplement records. '
        'It does not reload those binaries or rescore any answer. External review of these '
        'proofs is not direct external inspection of private binary states. Original N2FAIL '
        'and the post-hoc9600 amendment remain. No model or old oracle was rerun.\n\n'
        'SUMMARY separates actual entry-to-terminal time from the CPU result timestamp '
        'before final packing and from the uncalibrated forecast. One observed CPU host '
        'does not establish a runtime bound. Five dollars is a retained reservation, '
        'not an invoice; originals remain on the Volume.\n\n'
        'The three compact-container files and original envelope/manifest/ledger are copied '
        'without repacking or changing bytes. PROVIDER projects the original selected app rows '
        'and binds the full private file hash; actor identity fields and unrelated workspace rows are omitted. '
        'The primary materials and scientific tables are unchanged.\n')
    dump(OUT/'MANIFEST.json',manifest(OUT))
    print(json.dumps(summary))


if __name__ == '__main__':
    publish()

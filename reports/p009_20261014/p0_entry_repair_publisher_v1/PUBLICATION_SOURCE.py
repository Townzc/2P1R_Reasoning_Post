"""Create-only P0 result publication from complete, independently audited evidence.

No model, cloud, tokenizer, scoring or parity recomputation is performed here.
The original failed parent remains failed. Existing/partial destinations fail.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import tarfile
from datetime import datetime, timezone

from experiments.sft_allocation_midpoint.common import read, dump, sha, digest, manifest, verify
from experiments.learning_regime_p009.p0_entry_repair_binding import validate_repair_release as validate_release

ROOT = Path('.local/p009_20261014/r1/p0_entry_repair_r1')
SPEC = Path('reports/p009_20261014/p0_entry_repair_preflight_v1/ADMISSION.json')
PREFIX = Path('reports/p009_20261014/p0_fast_failed_prefix_v1')
PUB = Path('reports/p009_20261014/p0_entry_repair_complete_v1')
PARENT_TARGET = '5c5222573dece18fe3fe715ecfa3bdbfec1d2d01'
RUN = 'p0_fast_remaining'
ROLES = ('base_638', 'correct_969')


def publish():
    if PUB.exists():
        raise FileExistsError('Immutable destination already exists; preserve partials, no whole-tool retry')
    code = read(ROOT/'PUBLICATION_CODE_ACCEPTED.json')
    if (code['scope'] != 'p009-p0-fast-remainder-result-publication-code'
            or code['decision'] not in ('PASS', 'PASS-WITH-NOTES')
            or code['source_sha256'] != sha(__file__)
            or sha(code['local_report_path']) != code['report_sha256']):
        raise ValueError('Exact new full-P0 publisher code review required')
    spec = read(SPEC)
    evidence = ROOT/'export_r1/evidence'
    close = ROOT/'closeout_r1'
    envelope = read(ROOT/'runs'/RUN/'result.json')
    oracle = read(evidence/'LOCAL_ORACLE_AUDIT.json')
    provider = read(close/'provider.json')
    completed = read(close/'COMPLETED.json')
    intent = read(evidence/'intent.json')
    release = intent['release']
    review = release['runtime_review']
    validate_release(spec, intent['plan'], release)
    if (oracle.get('passed') is not True or oracle.get('spec_sha256') != digest(spec)
            or oracle.get('parent_status') != 'failed' or oracle.get('new_raw_count') != 2382
            or oracle.get('inherited_raw_count') != 256 or oracle.get('old_reference_rescored') is not False
            or oracle.get('old_eager_raw_scored') is not False
            or oracle.get('parent_acknowledgement_fabricated') is not False
            or oracle.get('new_model_calls') != 0 or oracle.get('new_training_updates') != 0
            or set(oracle['summary']) != set(ROLES)):
        raise ValueError('Complete exact parent/suffix local oracle required')
    for role in ROLES:
        row = oracle['summary'][role]
        if (row['total'] != 1319 or row['technical_unknown'] != 0
                or len(oracle['scored'][role]) != 1319 or row['parity']['n'] != 1319):
            raise ValueError('Both full logical endpoints required, including failed parity decisions')
    if (completed.get('passed') is not True or completed['ledger_sha256'] != sha(close/'ledger.json')
            or completed['original_receipt_sha256'] != sha(ROOT/'runs'/RUN/'result.json')
            or envelope['receipt']['status'] != 'completed'
            or digest(envelope['artifact_manifest']) != oracle['artifact_digest']
            or read(evidence/'result.json') != envelope['result']
            or intent['spec'] != spec or release['source_files'] != spec['source_files']
            or review['target_commit'] != release['review_target']
            or sha(review['local_report_path']) != review['report_sha256']):
        raise ValueError('Actual receipt/source/review/collection binding differs')
    if (provider['state'] != 'stopped' or provider['owned_container_ids'] or provider['owned_containers']
            or len(provider['app_ids']) != 3
            or provider['app_ids'][:2] != [spec['parent_spec']['parent_app_id'],spec['parent_app_id']]
            or {x['app_id'] for x in provider['original_app_info']} != set(provider['app_ids'])
            or any(x['lifecycle']['state'] != 'stopped' for x in provider['original_app_info'])):
        raise ValueError('Both exact parent and child must be STOPPED with zero owned containers')
    verify(evidence, envelope['artifact_manifest'])
    verify(PREFIX, read(PREFIX/'MANIFEST.json'))
    inputs = ROOT.parent/'p0_r1/inputs'
    verify(inputs, spec['parent_spec']['inputs'])
    for name, expected in spec['source_files'].items():
        if sha(name) != expected:
            raise ValueError('Reviewed source changed before publication')

    from experiments.sft_allocation_p008.provider_release import validate_stopped_apps
    preclaim = read(close/'PRECLAIM_PROVIDER.json')
    failed_app = spec['preclaim_failure']['zero_work_proof']['original_app_id']
    if preclaim['app_ids'] != [failed_app]:
        raise ValueError('Original pre-claim failure provider missing')
    validate_stopped_apps([failed_app],preclaim['original_app_info'],preclaim['owned_containers'])
    source_manifest = envelope['artifact_manifest']
    exclusions = {'intent.json', 'compact_evidence.tar.gz', 'compact_manifest.json', 'bundle_receipt.json'}
    selected = {n: r for n, r in source_manifest.items() if n not in exclusions and not n.endswith('.pt')}
    omitted = {n: r for n, r in source_manifest.items() if n not in selected}
    PUB.mkdir(parents=True)
    archive = PUB/'original_fast_projection.tar.gz'
    with archive.open('xb') as handle, gzip.GzipFile(fileobj=handle, mode='wb', mtime=0) as zipped:
        with tarfile.open(fileobj=zipped, mode='w') as tar:
            for name in sorted(selected):
                info = tar.gettarinfo(str(evidence/name), arcname=name)
                info.uid = info.gid = 0
                info.uname = info.gname = ''
                info.mtime = 0
                with (evidence/name).open('rb') as member:
                    tar.addfile(info, member)
    with tarfile.open(archive, 'r:gz') as tar:
        observed = {}
        for member in tar.getmembers():
            if not member.isfile() or member.name not in selected or member.name in observed:
                raise ValueError('Unsafe, duplicate or extra projection archive member')
            raw = tar.extractfile(member).read()
            observed[member.name] = dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
        if observed != selected:
            raise ValueError('Original-byte projection readback differs')
    for name in ('LOCAL_ORACLE_AUDIT.json', 'result.json', 'MERGE_PROOF.json',
                 'PARENT_PREFIX_PROOF.json', 'PARENT_CONTINUATION_MARKER.json'):
        shutil.copyfile(evidence/name, PUB/name)
    shutil.copyfile(close/'ledger.json', PUB/'LEDGER.json')
    shutil.copyfile(inputs/'HF_REFERENCE_OUTCOMES.json', PUB/'HF_REFERENCE_OUTCOMES.json')
    shutil.copyfile(__file__, PUB/'PUBLICATION_SOURCE.py')
    dump(PUB/'ORIGINAL_ENVELOPE.json', envelope)
    dump(PUB/'PROJECTION.json', dict(files=selected, omitted=omitted,
        original_manifest_sha256=digest(source_manifest), public_archive_sha256=sha(archive),
        reason='Private runtime intent, wrapping artifacts and any binary checkpoints omitted; all2,382 child raw rows included; original256 inherited raw are in the linked immutable failed-parent packet.'))
    dump(PUB/'PROVIDER.json', dict(app_ids=provider['app_ids'], state='stopped', owned_container_count=0,
        observed_utc=provider['utc'], original_private_file_sha256=sha(close/'provider.json'),
        projection='Account actors and unrelated rows omitted explicitly; full private original retained.',
        apps=[dict(app_id=x['app_id'], lifecycle={k:x['lifecycle'][k]
            for k in ('state','created_at','stopped_at')}) for x in provider['original_app_info']]))
    dump(PUB/'ENTRY_REPAIR_PROVENANCE.json', dict(
        original_zero_work_proof=spec['preclaim_failure']['zero_work_proof'],
        zero_work_file_sha256=spec['preclaim_failure']['zero_work_proof_file_sha256'],
        public_reconciliation_packet='reports/p009_20261014/p0_preclaim_failure_v1',
        original_failed_call_stopped=True, original_private_provider_sha256=sha(close/'PRECLAIM_PROVIDER.json'),
        original_two_failed_reserved_cents=500, prior_preclaim_call_allowance_cents=252,
        prior_envelope_cents=752, current_slot_reserved_cents=252,
        effective_stage0_cap_cents=2000, effective_experiment_cap_cents=11000,
        owner_budget_amendment_sha256=spec['owner_budget_amendment_sha256'],
        failed_terminal_fabricated=False, no_prior_claim_cleared=True,
        limits_are_not_final_invoices=True))
    dump(PUB/'SOURCE_BINDING.json', dict(source_files=spec['source_files'], spec_sha256=digest(spec),
        execution_commit=release['execution_commit'], source_target=review['target_commit'],
        runtime_review_commit=review['report_commit'], runtime_review_sha256=review['report_sha256'],
        original_intent_file_sha256=sha(evidence/'intent.json'),
        earlier_eager_reserved_cents=248, failed_fast_reserved_cents=252, new_claim_reserved_cents=252,
        stage0_cap_cents=2000, whole_experiment_cap_cents=11000,
        reserves_are_not_expense=True, all_failures_retained=True))
    dump(PUB/'PARENT_LINK.json', dict(commit=PARENT_TARGET, packet=str(PREFIX),
        manifest_file_sha256=sha(PREFIX/'MANIFEST.json'), status='failed', reused_raw=256, retained_unscored_eager_raw=128, parent_done_acknowledgement_fabricated=False,
        parent_preservation_sha256=spec['parent_preservation_sha256']))
    dump(PUB/'RESULTS.json', dict(summary=oracle['summary'], local_oracle_sha256=sha(evidence/'LOCAL_ORACLE_AUDIT.json'),
        new_raw=2382, inherited_raw=256, total_logical_raw=2638, new_training_updates=0,
        old_hf_rescored=False, actual_result_external_review='PENDING', created_utc=datetime.now(timezone.utc).isoformat()))
    lines = ['# P009 P0: complete engine comparability evidence', '',
        'Both1,319 endpoints are complete under the same reviewed CUDA-graph/256-sequence setting:256 original saved fast-parent rows plus2,382 new suffix rows, all independently scored once as complete endpoints. The fast parent stays failed and its absent done acknowledgement is never fabricated. The earlier eager128 remain excluded and unscored. All three scientific-lineage apps and the separate pre-claim failed app are STOPPED0. Actual-result A2 review remains pending.', '',
        '|Model|vLLM correct / 1,319|Delta from saved HF (pp)|Discordant pairs|Frozen gate decision|',
        '|---|---:|---:|---:|---|']
    for role in ROLES:
        row = oracle['summary'][role]; paired = row['parity']
        lines.append(f"|{role}|{row['correct']}|{paired['delta_pp']:+.4f}|{paired['discordant_count']}|{paired['decision']}|")
    lines += ['', 'The table copies the complete local oracle, including any stop/internal-only outcome; it does not select passing models or recompute parity. The same frozen HF Boolean maps are supplied for independent comparison. Historical HF outputs were not rescored. Logical caps remain incorrect; backend and logical stop counts are separate in the oracle.', '',
        'All original failures remain. The entry-schema call failed before a claim, model load or new output, as independently reconciled; its registered plan was preserved. The corrected entry uses the same previously unclaimed slot, nested input manifest and permanent dispatch fence. The scientific ancestors are: the original eager timing gate and the new fast native-EOS-at-cap transport check. The suffix only accepts the exact documented vLLM metadata tie, preserving original token/backend bytes and the frozen first_stop/parser; true logical caps remain incorrect. The owner separately authorized a bounded increase to P009$110 and Stage0$20, preserving Stage1$50/Stage2$35/unallocated$5 and project$450/$50 protection. Original$5 claimed-failure ceilings plus the entire$2.52 pre-claim failed-call allowance and new$2.52 slot total$10.04 conservative reservation, within the new Stage0 cap. Settlement at actual gross metering plus a delay allowance remains a separately reviewed future accounting change; it is not a prerequisite for this call and no old cost is erased. Reservations and forecast proxies are not invoices, actual speed guarantees or permission to borrow; all failed/setup/build/storage costs remain.', '',
        'This is an engine-comparability gate on previously seen questions, not a new learning-regime result. No student training occurred. A source/code PASS is not an actual-result PASS, and a stop decision does not by itself prove an implementation error. Downstream admission requires the genuine complete A2 report and remaining scientific, source, numeric and budget gates.', '',
        'The merge proof binds the original correct-969 checkpoint; public metadata is not evidence that the external reviewer loaded its private binary. All public suffix members are original bytes in a disclosed projection with archive readback; inherited256 raw remain at the immutable failed-prefix link. The parent packet is immutable at the linked commit.']
    (PUB/'README.md').write_text('\n'.join(lines)+'\n')
    (PUB/'REVIEW_REQUEST.md').write_text('Scope p009-p0-complete-engine-parity-A2: independently replay both full endpoints from256 saved raw in the linked fast-parent packet plus2,382 new suffix raw; the earlier128 eager rows are excluded and remain unscored, verify exact frozen HF reference maps, integer parity gates, physical lineage, zero unknowns/retraining, merge proof/source binding, all four provider exits, the pre-claim zero-work reconciliation and permanent repair dispatch marker, nested input-bound claim, owner-amended exact caps and all retained original timing failure/costs. Explicitly distinguish comparable, internal-only and blocked outcomes; do not infer later G0 or training admission.\n')
    dump(PUB/'MANIFEST.json', manifest(PUB))
    print(json.dumps({'published':str(PUB), 'actual_A2':'PENDING', 'models_called':0}))


if __name__ == '__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    publish()

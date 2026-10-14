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

ROOT = Path('.local/p009_20261014/r1/p0_r1/suffix_r1')
SPEC = Path('reports/p009_20261014/p0_suffix_preflight_v1/ADMISSION.json')
PREFIX = Path('reports/p009_20261014/p0_interrupted_prefix_v1')
PUB = Path('reports/p009_20261014/p0_complete_parity_v1')
SOURCE_TARGET = '7c9f093cd9f0b866cce65329d0b88c42fe0066b8'
RUN = 'p0_parity_remaining'
ROLES = ('base_638', 'correct_969')


def publish():
    if PUB.exists():
        raise FileExistsError('Immutable destination already exists; preserve partials, no whole-tool retry')
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
    if (oracle.get('passed') is not True or oracle.get('spec_sha256') != digest(spec)
            or oracle.get('parent_status') != 'failed' or oracle.get('new_raw_count') != 2510
            or oracle.get('inherited_raw_count') != 128 or oracle.get('old_reference_rescored') is not False
            or oracle.get('original_timing_gate_failed') is not True
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
            or review['target_commit'] != SOURCE_TARGET
            or sha(review['local_report_path']) != review['report_sha256']):
        raise ValueError('Actual receipt/source/review/collection binding differs')
    if (provider['state'] != 'stopped' or provider['owned_container_ids'] or provider['owned_containers']
            or len(provider['app_ids']) != 2 or provider['app_ids'][0] != spec['parent_app_id']
            or {x['app_id'] for x in provider['original_app_info']} != set(provider['app_ids'])
            or any(x['lifecycle']['state'] != 'stopped' for x in provider['original_app_info'])):
        raise ValueError('Both exact parent and child must be STOPPED with zero owned containers')
    verify(evidence, envelope['artifact_manifest'])
    verify(PREFIX, read(PREFIX/'MANIFEST.json'))
    inputs = ROOT.parent/'inputs'
    verify(inputs, spec['parent_spec']['inputs'])
    for name, expected in spec['source_files'].items():
        if sha(name) != expected:
            raise ValueError('Reviewed source changed before publication')

    source_manifest = envelope['artifact_manifest']
    exclusions = {'intent.json', 'compact_evidence.tar.gz', 'compact_manifest.json', 'bundle_receipt.json'}
    selected = {n: r for n, r in source_manifest.items() if n not in exclusions and not n.endswith('.pt')}
    omitted = {n: r for n, r in source_manifest.items() if n not in selected}
    PUB.mkdir(parents=True)
    archive = PUB/'original_suffix_projection.tar.gz'
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
        reason='Private runtime intent, wrapping artifacts and any binary checkpoints omitted; all raw suffix bytes included.'))
    dump(PUB/'PROVIDER.json', dict(app_ids=provider['app_ids'], state='stopped', owned_container_count=0,
        observed_utc=provider['utc'], original_private_file_sha256=sha(close/'provider.json'),
        projection='Account actors and unrelated rows omitted explicitly; full private original retained.',
        apps=[dict(app_id=x['app_id'], lifecycle={k:x['lifecycle'][k]
            for k in ('state','created_at','stopped_at')}) for x in provider['original_app_info']]))
    dump(PUB/'SOURCE_BINDING.json', dict(source_files=spec['source_files'], spec_sha256=digest(spec),
        execution_commit=release['execution_commit'], source_target=SOURCE_TARGET,
        runtime_review_commit=review['report_commit'], runtime_review_sha256=review['report_sha256'],
        original_intent_file_sha256=sha(evidence/'intent.json'),
        original_claim_reserved_cents=248, new_claim_reserved_cents=326,
        stage0_cap_cents=1000, whole_experiment_cap_cents=10000,
        reserves_are_not_expense=True, all_failures_retained=True))
    dump(PUB/'PARENT_LINK.json', dict(commit=SOURCE_TARGET, packet=str(PREFIX),
        manifest_file_sha256=sha(PREFIX/'MANIFEST.json'), status='failed', reused_raw=128,
        parent_preservation_sha256=spec['parent_preservation_sha256']))
    dump(PUB/'RESULTS.json', dict(summary=oracle['summary'], local_oracle_sha256=sha(evidence/'LOCAL_ORACLE_AUDIT.json'),
        new_raw=2510, inherited_raw=128, total_logical_raw=2638, new_training_updates=0,
        old_hf_rescored=False, actual_result_external_review='PENDING', created_utc=datetime.now(timezone.utc).isoformat()))
    lines = ['# P009 P0: complete engine comparability evidence', '',
        'Both original 1,319-question endpoints are complete and independently scored. The original 128 rows remain bound to the failed parent; only 2,510 never-attempted rows were generated by the suffix. Both apps are stopped with zero owned containers. Actual-result A2 review is pending.', '',
        '|Model|vLLM correct / 1,319|Delta from saved HF (pp)|Discordant pairs|Frozen gate decision|',
        '|---|---:|---:|---:|---|']
    for role in ROLES:
        row = oracle['summary'][role]; paired = row['parity']
        lines.append(f"|{role}|{row['correct']}|{paired['delta_pp']:+.4f}|{paired['discordant_count']}|{paired['decision']}|")
    lines += ['', 'The table copies the complete local oracle, including any stop/internal-only outcome; it does not select passing models or recompute parity. The same frozen HF Boolean maps are supplied for independent comparison. Historical HF outputs were not rescored. Logical caps remain incorrect; backend and logical stop counts are separate in the oracle.', '',
        'The original 1,200-second timing gate failed. The separately reviewed 1,800-second unused suffix is a disclosed engineering amendment, not a retroactive pass. Original failed claim, raw bytes, timing and reservations remain unchanged. $2.48 plus $3.26 are conservative reservations within Stage0 $10 and P009 $100, not actual costs or an invoice; all failed/setup/storage costs remain accounted for.', '',
        'This is an engine-comparability gate on previously seen questions, not a new learning-regime result. No student training occurred. A source/code PASS is not an actual-result PASS, and a stop decision does not by itself prove an implementation error. Downstream admission requires the genuine complete A2 report and remaining scientific, source, numeric and budget gates.', '',
        'The merge proof binds the original correct-969 checkpoint; public metadata is not evidence that the external reviewer loaded its private binary. All public suffix members are original bytes in a disclosed projection, with archive readback. The parent packet is immutable at the linked commit.']
    (PUB/'README.md').write_text('\n'.join(lines)+'\n')
    (PUB/'REVIEW_REQUEST.md').write_text('Scope p009-p0-complete-engine-parity-A2: independently replay both full endpoints from the original128-prefix packet and this2,510-row suffix, verify exact frozen HF reference maps, integer parity gates, physical lineage, zero unknowns/retraining, merge proof/source binding, both provider exits and retained original timing failure/costs. Explicitly distinguish comparable, internal-only and blocked outcomes; do not infer later G0 or training admission.\n')
    dump(PUB/'MANIFEST.json', manifest(PUB))
    print(json.dumps({'published':str(PUB), 'actual_A2':'PENDING', 'models_called':0}))


if __name__ == '__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    publish()

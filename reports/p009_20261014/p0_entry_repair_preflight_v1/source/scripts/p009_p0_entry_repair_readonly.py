"""Bounded local observation/failed preservation. Never dispatch or write remotely."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import threading

from experiments.sft_allocation_midpoint.common import read, dump, sha, digest
from experiments.sft_allocation_p008.evidence_bundle import safe_name
from experiments.sft_allocation_p008.provider_release import validate_stopped_apps
from experiments.learning_regime_p009.p0_fast_remaining_contract import (
    CAMPAIGN, RUN, PARENT_CAMPAIGN, PARENT_RUN, ANCESTOR_CAMPAIGN, ANCESTOR_RUN,
    OFFSETS, RESERVED_CENTS,
)

from experiments.learning_regime_p009.p0_entry_repair_binding import validate_repair_release as validate_release, DISPATCH_KEY

ROOT = Path('.local/p009_20261014/r1/p0_entry_repair_r1')
SPEC = Path('reports/p009_20261014/p0_entry_repair_preflight_v1/ADMISSION.json')
CLI = '.local/midpoint_20261011/venv/bin/modal'
PREFIX = 'midpoint/'+CAMPAIGN+'/'
PARENT_PREFIX = 'midpoint/'+PARENT_CAMPAIGN+'/'
ANCESTOR_PREFIX = 'midpoint/'+ANCESTOR_CAMPAIGN+'/'
MAX_FILES = 512
MAX_FILE_BYTES = 32*1024**2
MAX_TOTAL_BYTES = 256*1024**2
SCOPE = 'p009-p0-fast-remainder-readonly-observation-and-failed-preservation-code'


def now():
    return datetime.now(timezone.utc).isoformat()


def local_basis():
    review = read(ROOT/'READONLY_CODE_ACCEPTED.json')
    if (review['scope'] != SCOPE or review['decision'] not in ('PASS', 'PASS-WITH-NOTES')
            or review['source_sha256'] != sha(__file__)
            or sha(review['local_report_path']) != review['report_sha256']
            or len(review['target_commit']) != 40 or len(review['report_commit']) != 40):
        raise ValueError('Exact real read-only code review required')
    spec = read(SPEC)
    sent = read(ROOT/'runs'/RUN/'dispatch_intent.json')
    submitted = read(ROOT/'runs'/RUN/'submitted.json')
    validate_release(spec, sent['plan'], sent['release'])
    for name, expected in spec['source_files'].items():
        if sha(name) != expected:
            raise ValueError('Exact repair source bytes changed')
    if (sent['run_id'] != RUN or not sent['provider_app_id'].startswith('ap-')
            or not submitted['call_id'].startswith('fc-')):
        raise ValueError('Original exact submitted call required')
    return spec, sent, submitted


def provider(app_ids):
    infos = [json.loads(subprocess.check_output(
        [CLI, 'app', 'info', app, '--json'], text=True, timeout=30)) for app in app_ids]
    if any(info.get('app_id') != app for app, info in zip(app_ids, infos)):
        raise ValueError('Provider identity mismatch')
    containers = json.loads(subprocess.check_output(
        [CLI, 'container', 'list', '--json'], text=True, timeout=30))
    if not isinstance(containers, list) or any('app_id' not in c for c in containers):
        raise ValueError('Unknown provider container schema')
    owned = [c for c in containers if c['app_id'] in app_ids]
    return dict(observed_utc=now(), app_ids=app_ids, original_app_info=infos,
                owned_containers=owned, snapshot_is_atomic=False)


def lineage_keys():
    return [PREFIX+'claim/'+RUN, PREFIX+'terminal/'+RUN,
            PARENT_PREFIX+'claim/'+PARENT_RUN, PARENT_PREFIX+'terminal/'+PARENT_RUN,
            PARENT_PREFIX+'continuation/'+PARENT_RUN,
            ANCESTOR_PREFIX+'claim/'+ANCESTOR_RUN, ANCESTOR_PREFIX+'terminal/'+ANCESTOR_RUN,
            ANCESTOR_PREFIX+'continuation/'+ANCESTOR_RUN]


def status_keys():
    return [DISPATCH_KEY]+lineage_keys()+[PREFIX+RUN+'/'+kind+'/'+role+'_'+f'{offset:04d}'
        for role, start in OFFSETS.items() for offset in range(start, 1319, 256)
        for kind in ('unit', 'done')]


def failed_binding(spec, claim, terminal, parent_claim, parent_terminal, marker,
                   ancestor_claim, ancestor_terminal, ancestor_marker):
    if (not claim or not terminal or terminal.get('status') != 'failed'
            or claim.get('run_id') != RUN or terminal.get('run_id') != RUN
            or claim.get('plan_sha256') != spec['plan_sha256']
            or claim.get('stage') != 'p0_fast_remaining'
            or claim.get('reserved_cents') != RESERVED_CENTS
            or terminal.get('claim_sha256') != digest(claim)
            or terminal.get('attempt_id') != claim.get('attempt_id')
            or parent_claim != spec['parent_claim'] or parent_terminal != spec['parent_terminal']
            or parent_terminal['status'] != 'failed'
            or ancestor_claim != spec['parent_spec']['parent_claim']
            or ancestor_terminal != spec['parent_spec']['parent_terminal']
            or ancestor_terminal['status'] != 'failed'
            or ancestor_marker != spec['ancestor_marker']):
        raise ValueError('Require exact new failed claim and both immutable failed ancestors')
    # A setup failure can precede this child's successor marker. Its absence is
    # evidence only: the existing child claim still permanently prevents replay.
    if marker is not None and marker != dict(child_campaign=CAMPAIGN, child_run=RUN,
            child_claim_sha256=digest(claim), spec_sha256=digest(spec),
            parent_terminal=spec['parent_terminal'], inherited_outputs=256,
            suffix_outputs=2382, parent_stays_failed=True):
        raise ValueError('Different or ambiguous suffix successor marker')


def bounded_listing(items):
    remote = CAMPAIGN+'/'+RUN
    rows = {}
    total = 0
    for item in items:
        name = PurePosixPath(item['path'].lstrip('/')).relative_to(remote).as_posix()
        safe_name(name)
        size = item['size']
        if (name in rows or type(size) is not int or not 0 <= size <= MAX_FILE_BYTES):
            raise ValueError('Duplicate or oversized remote file')
        total += size
        rows[name] = dict(bytes=size, mtime=float(item['mtime']))
        if len(rows) > MAX_FILES or total > MAX_TOTAL_BYTES:
            raise ValueError('Stopped evidence exceeds preservation bounds')
    if not rows:
        raise ValueError('No original stopped evidence')
    return rows


def copy_original(path, blocks, expected_bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    h = hashlib.sha256()
    count = 0
    with path.open('xb') as f:
        for block in blocks:
            count += len(block)
            if count > expected_bytes:
                raise ValueError('Original file grew; preserve partial')
            f.write(block)
            h.update(block)
        f.flush()
        os.fsync(f.fileno())
    if count != expected_bytes:
        raise ValueError('Incomplete original transfer; preserve partial')
    return dict(bytes=count, sha256=h.hexdigest())


def status(spec, sent, submitted, db):
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    out = ROOT/'status'/stamp
    out.mkdir(parents=True, exist_ok=False)
    dump(out/'READ_INTENT.json', dict(started_utc=now(), app_id=sent['provider_app_id'],
        call_id=submitted['call_id'], read_only=True, partial_scores_computed=False))
    keys = status_keys()
    values, errors = {}, {}
    with ThreadPoolExecutor(max_workers=2) as pool:
        pending = {pool.submit(db.get, k): k for k in keys}
        for future in as_completed(pending):
            key = pending[future]
            try:
                values[key] = future.result()
            except Exception as exc:
                errors[key] = dict(type=type(exc).__name__, error=str(exc), status='unknown')
    dump(out/'RECORDS.json', values)
    dump(out/'READ_ERRORS.json', errors)
    try:
        proof = provider([spec['parent_spec']['parent_app_id'], spec['parent_app_id'],
        spec['preclaim_failure']['zero_work_proof']['original_app_id'], sent['provider_app_id']])
        dump(out/'PROVIDER.json', proof)
    except Exception as exc:
        dump(out/'PROVIDER_UNKNOWN.json', dict(type=type(exc).__name__, error=str(exc)))
    dump(out/'LOCAL_CALLBACK_STATE.json', {n: dict(exists=(ROOT/'runs'/RUN/n).exists(),
        sha256=sha(ROOT/'runs'/RUN/n) if (ROOT/'runs'/RUN/n).exists() else None)
        for n in ('result.json', 'return_error.json')})
    dump(out/'READ_FINISHED.json', dict(finished_utc=now(), records=len(values),
        unknown_records=len(errors), scoring_performed=False, runtime_admission=False,
        note='Saved immutable records only; not a full raw oracle or atomic snapshot.'))
    print(str(out))


def preserve_failed(spec, sent, submitted, db, vol):
    from modal.volume import FileEntryType
    out = ROOT/'interrupted_preservation_r1'
    if out.exists() or (ROOT/'runs'/RUN/'result.json').exists():
        raise ValueError('Prior/partial preservation or completed callback; no whole-tool retry')
    app_ids = [spec['parent_spec']['parent_app_id'], spec['parent_app_id'],
        spec['preclaim_failure']['zero_work_proof']['original_app_id'], sent['provider_app_id']]
    proof = provider(app_ids)
    validate_stopped_apps(app_ids, proof['original_app_info'], proof['owned_containers'])
    keys = lineage_keys()
    records = {k: db.get(k) for k in keys}
    failed_binding(spec, *[records[k] for k in keys])
    out.mkdir(exist_ok=False)
    dump(out/'READ_INTENT.json', dict(started_utc=now(), original_app_id=sent['provider_app_id'],
        call_id=submitted['call_id'], source_sha256=sha(__file__), read_only=True,
        scoring_performed=False, new_scientific_calls=0, retry_authorized=False))
    dump(out/'PROVIDER_BEFORE.json', proof)
    dump(out/'ORIGINAL_RECORDS.json', records)
    try:
        shutil.copytree(ROOT/'runs'/RUN, out/'original_callback')
        shutil.copyfile(ROOT/'run_r1.log', out/'original_cli.log')
        def listing():
            return bounded_listing(dict(path=x.path, size=x.size, mtime=x.mtime)
                for x in vol.iterdir('/'+CAMPAIGN+'/'+RUN, recursive=True)
                if x.type == FileEntryType.FILE)
        before = listing()
        dump(out/'REMOTE_LISTING_BEFORE.json', before)
        evidence = out/'evidence'
        evidence.mkdir()
        files = {}
        with (out/'FILE_READBACKS.jsonl').open('x') as journal, ThreadPoolExecutor(max_workers=2) as pool:
            pending = {pool.submit(copy_original, evidence/name,
                vol.read_file('/'+CAMPAIGN+'/'+RUN+'/'+name), rec['bytes']): name
                for name, rec in before.items()}
            for future in as_completed(pending):
                name = pending[future]
                record = future.result()
                files[name] = record
                journal.write(json.dumps(dict(name=name, **record))+'\n')
                journal.flush()
                os.fsync(journal.fileno())
        after = listing()
        dump(out/'REMOTE_LISTING_AFTER.json', after)
        dump(out/'LOCAL_MANIFEST.json', files)
        if before != after:
            raise ValueError('Stopped remote evidence changed')
        original = read(evidence/'failure_manifest.json')
        terminal = records[PREFIX+'terminal/'+RUN]
        if (original != {k:v for k,v in files.items() if k != 'failure_manifest.json'}
                or digest(original) != terminal['evidence_sha256']):
            raise ValueError('Original failed manifest or terminal mismatch')
        ledger = {k:v for k,v in db.items() if k.startswith((PREFIX, PARENT_PREFIX, ANCESTOR_PREFIX))}
        dump(out/'ledger.json', ledger)
        if any(ledger.get(k) != value for k, value in records.items()):
            raise ValueError('Original records changed during collection')
        after_provider = provider(app_ids)
        validate_stopped_apps(app_ids, after_provider['original_app_info'], after_provider['owned_containers'])
        dump(out/'PROVIDER_AFTER.json', after_provider)
        dump(out/'PRESERVED.json', dict(passed=True, finished_utc=now(), files=len(files),
            bytes=sum(v['bytes'] for v in files.values()), ledger_sha256=sha(out/'ledger.json'),
            manifest_sha256=sha(out/'LOCAL_MANIFEST.json'), original_status='failed',
            scoring_performed=False, retry_authorized=False, new_scientific_calls=0))
        print(str(out/'PRESERVED.json'))
    except BaseException as exc:
        dump(out/'READ_FAILURE.json', dict(utc=now(), type=type(exc).__name__, error=str(exc),
            rule='Retain every part; reconcile first. No whole-tool or model retry.'))
        raise


def main():
    p = argparse.ArgumentParser()
    p.add_argument('action', choices=('status', 'preserve-failed'))
    args = p.parse_args()
    spec, sent, submitted = local_basis()
    # A local hard bound also preserves a partial directory on an RPC hang.
    timer = threading.Timer(180 if args.action == 'status' else 1200, lambda: os._exit(124))
    timer.daemon = True
    timer.start()
    try:
        import modal
        db = modal.Dict.from_name('sft-allocation-midpoint-claims-v1', create_if_missing=False)
        if args.action == 'status':
            status(spec, sent, submitted, db)
        else:
            vol = modal.Volume.from_name('sft-allocation-midpoint-v1', create_if_missing=False)
            preserve_failed(spec, sent, submitted, db, vol)
    finally:
        timer.cancel()


if __name__ == '__main__':
    main()

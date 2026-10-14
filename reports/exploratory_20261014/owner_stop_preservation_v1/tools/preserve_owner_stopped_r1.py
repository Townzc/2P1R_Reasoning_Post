"""Once-only local preservation of the three owner-stopped original calls.

Read-only Modal SDK use: no spawn, remote writes, scores or continuation gates.
Keep partial files and per-file receipts on error; never rerun this helper.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
import hashlib
import json
import os
import shutil
import threading
import time

import modal
from modal.volume import FileEntryType
from experiments.sft_allocation_midpoint.common import read, dump, sha, digest
from experiments.sft_allocation_p008.evidence_bundle import safe_name

ROOT = Path('.local/exploratory_20261014/r1')
CAMP = 'exploratory-20261014-r1'
RUNS = ('base_4shot', 'instruct_0shot', 'wrong_teacher_t1')
OUT = ROOT / 'interrupted_preservation_r1'
PREFIX = 'midpoint/' + CAMP + '/'
now = lambda: datetime.now(timezone.utc).isoformat()


def main():
    provider = read(ROOT / 'owner_stop_20261014_r1/PROVIDER_READ.json')
    owner = read(ROOT / 'owner_stop_20261014_r1/OWNER_STOP_INTENT.json')
    if owner['retry_authorized'] or owner['additional_budget_authorized']:
        raise ValueError('Unexpected authorization record')
    if provider['container_count'] != 0:
        raise ValueError('Original provider release not established')
    if {r['run'] for r in provider['apps']} != set(RUNS):
        raise ValueError('Wrong original provider roster')
    for row in provider['apps']:
        sent = read(ROOT / 'runs' / row['run'] / 'dispatch_intent.json')
        if (sent['provider_app_id'] != row['app'] or
                row['lifecycle']['state'] != 'stopped' or
                not row['lifecycle']['stopped_at']):
            raise ValueError('Exact original app not stopped')
        if (ROOT / 'runs' / row['run'] / 'result.json').exists():
            raise ValueError('Completed envelope exists; reconcile before preservation')
        if not (ROOT / 'runs' / row['run'] / 'return_error.json').exists():
            raise ValueError('Retain original interrupted callback first')
    spec = read('reports/exploratory_20261014/admission_v1/ADMISSION.json')
    for name, expected in spec['source_files'].items():
        if sha(name) != expected:
            raise ValueError('Original scientific source changed')
    OUT.mkdir(exist_ok=False)
    dump(OUT / 'READ_INTENT.json', dict(
        started_at_utc=now(), owner_stop_intent_sha256=sha(ROOT / 'owner_stop_20261014_r1/OWNER_STOP_INTENT.json'),
        provider_read_sha256=sha(ROOT / 'owner_stop_20261014_r1/PROVIDER_READ.json'),
        campaign=CAMP, runs=RUNS, operation='readonly_preservation', new_model_calls=0,
        automatic_retry=False, continuation_admitted=False, source_files=spec['source_files']))
    timer = threading.Timer(1200, lambda: os._exit(124))
    timer.daemon = True
    timer.start()
    try:
        db = modal.Dict.from_name('sft-allocation-midpoint-claims-v1', create_if_missing=False)
        vol = modal.Volume.from_name('sft-allocation-midpoint-v1', create_if_missing=False)
        original = {}
        for run in RUNS:
            original[run] = {k: db.get(PREFIX + k + '/' + run) for k in ('claim', 'terminal')}
            if not original[run]['claim']:
                raise ValueError('Missing original claim')
            term = original[run]['terminal']
            if term and term.get('status') == 'completed':
                raise ValueError('Unexpected complete terminal')
            dst = OUT / run
            dst.mkdir()
            shutil.copytree(ROOT / 'runs' / run, dst / 'original_callback')
            shutil.copyfile(ROOT / (run + '_run_r1.log'), dst / 'original_cli.log')
        dump(OUT / 'ORIGINAL_CLAIMS_TERMINALS.json', original)

        def ledger_snapshot():
            start = now()
            rows = {k: v for k, v in db.items() if k.startswith(PREFIX)}
            dump(OUT / 'ledger.json', rows)
            dump(OUT / 'LEDGER_READ.json', dict(started_at_utc=start, finished_at_utc=now(),
                                             records=len(rows), sha256=sha(OUT / 'ledger.json')))
            return rows

        def listing(run):
            remote = CAMP + '/' + run
            entries = {}
            for item in vol.iterdir('/' + remote, recursive=True):
                if item.type != FileEntryType.FILE:
                    continue
                name = PurePosixPath(item.path.lstrip('/')).relative_to(remote).as_posix()
                safe_name(name)
                if name in entries or item.size > 512 * 1024**2:
                    raise ValueError('Unexpected duplicate/large evidence file')
                entries[name] = dict(bytes=item.size, mtime=float(item.mtime))
            if not entries or len(entries) > 3000 or sum(v['bytes'] for v in entries.values()) > 1024**3:
                raise ValueError('Preservation listing bound exceeded')
            return entries

        with ThreadPoolExecutor(max_workers=1) as lp:
            ledger_future = lp.submit(ledger_snapshot)
            for run in RUNS:
                dest = OUT / run
                before = listing(run)
                dump(dest / 'REMOTE_LISTING_BEFORE.json', before)
                evidence = dest / 'evidence'
                evidence.mkdir()
                files = {}

                def copy_one(name):
                    target = evidence / name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    total = 0
                    h = hashlib.sha256()
                    with target.open('xb') as f:
                        for chunk in vol.read_file('/' + CAMP + '/' + run + '/' + name):
                            total += len(chunk)
                            if total > before[name]['bytes']:
                                raise ValueError('Remote evidence grew')
                            f.write(chunk)
                            h.update(chunk)
                        f.flush()
                        os.fsync(f.fileno())
                    if total != before[name]['bytes']:
                        raise ValueError('Partial local file retained')
                    return name, dict(bytes=total, sha256=h.hexdigest())

                with (dest / 'FILE_READBACKS.jsonl').open('x') as journal:
                    with ThreadPoolExecutor(max_workers=2) as pool:
                        futures = [pool.submit(copy_one, name) for name in before]
                        for future in as_completed(futures):
                            name, record = future.result()
                            files[name] = record
                            journal.write(json.dumps(dict(file=name, **record)) + '\n')
                            journal.flush()
                            if len(files) % 100 == 0:
                                print(json.dumps(dict(run=run, preserved_files=len(files), total_files=len(before))), flush=True)
                after = listing(run)
                dump(dest / 'REMOTE_LISTING_AFTER.json', after)
                dump(dest / 'LOCAL_MANIFEST.json', files)
                if before != after:
                    raise ValueError('Stopped evidence listing changed')
                dump(dest / 'PRESERVED.json', dict(preserved=True, utc=now(), files=len(files),
                     bytes=sum(v['bytes'] for v in files.values()), manifest_digest=digest(files),
                     scientific_oracle_passed=False, continuation_admitted=False))
                print(json.dumps(dict(run=run, preserved=True, files=len(files))), flush=True)
            ledger = ledger_future.result()
        for run in RUNS:
            for kind in ('claim', 'terminal'):
                if ledger.get(PREFIX + kind + '/' + run) != original[run][kind]:
                    raise ValueError('Original immutable claim/terminal changed')
        dump(OUT / 'PRESERVED_ALL.json', dict(preserved=True, finished_at_utc=now(),
             runs={run: read(OUT / run / 'PRESERVED.json') for run in RUNS},
             ledger_sha256=sha(OUT / 'ledger.json'), scientific_oracle_passed=False,
             new_model_calls=0, continuation_admitted=False))
        print(json.dumps(read(OUT / 'PRESERVED_ALL.json')), flush=True)
    except BaseException as exc:
        dump(OUT / 'READ_FAILURE.json', dict(type=type(exc).__name__, error=str(exc), utc=now(),
             rule='Preserve every valid/partial file; reconcile and fetch only missing parts. Never rerun wholesale.'))
        raise
    finally:
        timer.cancel()


if __name__ == '__main__':
    main()

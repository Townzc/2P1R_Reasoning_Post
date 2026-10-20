"""One bounded read-only preservation of an actually stopped E4 failure.

No restart, claim edit, scoring, model state load or merged-weight download.
All successfully retrieved parts survive a failure; an existing output blocks replay.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
from pathlib import Path
import subprocess
import threading

from experiments.p010.common import read, dump, sha, manifest, utc
from experiments.sft_allocation_p008.provider_release import read_stopped_apps


def named_keys(run):
    prefix = 'e4/'+run+'/'
    units = [f'training_block_{i:04d}_{i+15:04d}' for i in range(1, 1025, 16)] + ['terminal_merge']
    return ([prefix+'claim', prefix+'terminal']
            + [prefix+k+'/'+u for u in units for k in ('unit', 'done')]
            + [prefix+k+f'/{i:04d}' for i in range(0, 1319, 256) for k in ('eval', 'eval_done')])


def relative_file(path, prefix):
    value = Path('/'+str(path).lstrip('/')).relative_to('/'+str(prefix).lstrip('/'))
    if not value.parts or '..' in value.parts or value.is_absolute():
        raise ValueError('Remote path is not inside the exact failed run')
    return value


def select_files(inventory, prefix):
    files = []
    for entry in inventory:
        rel = relative_file(entry['path'], prefix)
        if ('merged' not in rel.parts and rel.suffix == '.json') or rel.as_posix() == 'checkpoint_1024/state.pt':
            files.append((entry, rel))
    metadata = [entry for entry, rel in files if rel.suffix == '.json']
    states = [entry for entry, rel in files if rel.suffix == '.pt']
    if (len(metadata) > 4096 or sum(x['bytes'] for x in metadata) > 256*1024**2
            or len(states) > 1 or sum(x['bytes'] for x in states) > 2*1024**3):
        raise ValueError('Original bounded metadata/state inventory exceeded')
    return files


def preserve(args):
    import modal
    receipt = Path(args.receipt); sent = read(receipt/'SUBMITTED.json'); local = read(receipt/'INTENT.json')
    error = read(receipt/'ERROR.json'); n = sent['n']; run = 'e4_s17_n'+str(n)
    if n not in (400, 3200) or local['n'] != n or (receipt/'RESULT.json').exists():
        raise ValueError('Only an original failed E4 receipt can be preserved')
    out = Path(args.out); out.mkdir(parents=True, exist_ok=False)
    dump(out/'INTENT.json', dict(utc=utc(), run=run, original_submitted_sha256=sha(receipt/'SUBMITTED.json'),
        original_error_sha256=sha(receipt/'ERROR.json'), original_local_intent_sha256=sha(receipt/'INTENT.json'),
        original_error=error, local_cap_seconds=1200, max_readers=2, read_only=True, automatic_retry=False))
    timer = threading.Timer(1200, lambda: os._exit(124)); timer.daemon = True; timer.start()
    try:
        cli = '.local/midpoint_20261011/venv/bin/modal'
        containers = json.loads(subprocess.check_output([cli, 'container', 'list', '--json'], text=True, timeout=45))
        owned = [x for x in containers if x.get('app_id') == sent['app_id']]
        info = read_stopped_apps(cli, [sent['app_id']], owned)
        dump(out/'PROVIDER_PRIVATE.json', dict(app_id=sent['app_id'], original_info=info, owned=owned, utc=utc()))
        vol = modal.Volume.from_name('sft-allocation-midpoint-v1', create_if_missing=False)
        store = modal.Dict.from_name('p010-once-20261019', create_if_missing=False)
        prefix = '/p010-20261019/e4/'+run
        def inventory():
            return sorted([dict(path=e.path, bytes=e.size) for e in vol.iterdir(prefix, recursive=True)], key=lambda x: x['path'])
        before = inventory(); dump(out/'INVENTORY_BEFORE.json', before)
        selected = select_files(before, prefix); keys = named_keys(run)
        ledger_before = {k: store.get('e4/'+run+'/'+k) for k in ('claim', 'terminal')}
        dump(out/'LEDGER_BEFORE.json', ledger_before)
        if (not isinstance(ledger_before['claim'], dict)
                or ledger_before['terminal'].get('status') != 'failed'):
            raise ValueError('Original claim and actual failed terminal required')
        records = {}
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = {pool.submit(store.get, key): (i, key) for i, key in enumerate(keys)}
            for future in as_completed(futures):
                i, key = futures[future]; value = future.result(); records[key] = value
                dump(out/'ledger_parts'/f'{i:04d}.json', dict(key=key, value=value))
        dump(out/'LEDGER.json', records)
        def download(item):
            entry, rel = item; target = out/'evidence'/rel; target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('xb') as stream:
                for block in vol.read_file(entry['path']):
                    stream.write(block)
            if target.stat().st_size != entry['bytes']:
                raise ValueError('Partial file: '+str(rel))
            dump(out/'file_receipts'/(str(rel)+'.json'), dict(bytes=entry['bytes'], sha256=sha(target)))
        with ThreadPoolExecutor(max_workers=2) as pool:
            for _ in pool.map(download, selected):
                pass
        after = inventory(); dump(out/'INVENTORY_AFTER.json', after)
        ledger_after = {k: store.get('e4/'+run+'/'+k) for k in ('claim', 'terminal')}
        dump(out/'LEDGER_AFTER.json', ledger_after)
        if before != after or ledger_before != ledger_after:
            raise ValueError('Stopped original inventory or claim/terminal changed')
        actual = manifest(out/'evidence'); dump(out/'MANIFEST.json', actual)
        raw = [x for x in before if '/raw/' in x['path']]
        endpoint_records = {k: v for k, v in records.items() if '/eval/' in k or '/eval_done/' in k}
        has_checkpoint = 'checkpoint_1024/state.pt' in actual
        if has_checkpoint:
            saved = read(out/'evidence/checkpoint_1024/manifest.json')
            # Original checkpoint helper records state bytes under a declared
            # field; the independent full-state oracle checks its entire schema.
            dump(out/'CHECKPOINT_PRESERVED.json', dict(state_file=actual['checkpoint_1024/state.pt'],
                original_manifest=saved, binary_loaded=False, full_oracle_pending=True))
        result = dict(utc=utc(), run=run, app_id=sent['app_id'], call_id=sent['call_id'],
            metadata_and_state_files=len(actual), preserved_bytes=sum(v['bytes'] for v in actual.values()),
            complete_checkpoint_file_present=has_checkpoint, original_failed_terminal=ledger_before['terminal'],
            raw_files=len(raw), any_endpoint_intent_or_ack=any(v is not None for v in endpoint_records.values()),
            new_model_calls=0, new_training=0, new_generations=0, remote_writes=0,
            merged_weights_retained_remotely=True, failed_parent_remains_failed=True,
            provider_stopped=True, manifest_sha256=sha(out/'MANIFEST.json'),
            full_state_oracle_pending=True, no_retry_authorization_granted=True)
        dump(out/'COMPLETED.json', result); return result
    except BaseException as exc:
        dump(out/'FAILED.json', dict(type=type(exc).__name__, error=str(exc),
            partial_evidence_preserved=True, automatic_retry=False))
        raise
    finally:
        timer.cancel()


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--receipt', required=True); p.add_argument('--out', required=True)
    print(json.dumps(preserve(p.parse_args())))

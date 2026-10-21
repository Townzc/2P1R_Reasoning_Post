"""One bounded read-only preservation of the two original failed long prefixes."""
from pathlib import Path, PurePosixPath
from concurrent.futures import ThreadPoolExecutor
import json, time, hashlib, signal, traceback
import modal
from experiments.p011 import long_conditional_path as path, long_evidence

ROOT = Path('.local/p011_20261020/r1/long_initial3_validation_failures_r1')
SPEC = json.loads(Path(path.SPEC).read_text())
JOBS = ('long_A7_S-L15_s17_r1', 'long_A7_S-F15_s17_r1')

def put(destination, value):
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('x') as f:
        json.dump(value, f, indent=2, sort_keys=True)
        f.write('\n')

def timeout(*_):
    raise TimeoutError('Original bounded600s failed-byte preservation expired')

signal.signal(signal.SIGALRM, timeout)
signal.alarm(600)
put(ROOT / 'PRESERVATION_INTENT.json', dict(started_epoch=time.time(), seconds=600,
    jobs=list(JOBS), model_calls=0, decoder_calls=0, score_calls=0, automatic_retry=False))
volume = modal.Volume.from_name('sft-allocation-midpoint-v1', create_if_missing=False)
store = modal.Dict.from_name(path.STORE, create_if_missing=False)
proofs = {}
try:
    for job_id in JOBS:
        dest = ROOT / job_id
        provider = json.loads((dest / 'PROVIDER_OBSERVATION.json').read_text())
        assert provider['state'] == 'stopped' and provider['owned_containers'] == 0
        prefix = 'p011-20261020/long_runs_r1/' + job_id
        def inventory():
            entries = []
            for e in volume.iterdir('/' + prefix, recursive=True):
                n = e.path.lstrip('/')
                assert n.startswith(prefix + '/') and '..' not in PurePosixPath(n).parts
                assert int(e.type) in (1, 2)
                entries.append(dict(path=n, type=int(e.type), mtime=e.mtime, size=e.size))
            return sorted(entries, key=lambda e: e['path'])
        before = inventory()
        put(dest / 'REMOTE_INVENTORY_BEFORE.json', dict(observed_epoch=time.time(), entries=before))
        files = [e for e in before if e['type'] == 1]
        assert 0 < len(files) <= 50 and sum(e['size'] for e in files) <= 25_000_000
        def copy(e):
            relative = e['path'][len(prefix) + 1:]
            p = dest / 'original_remote_files' / relative
            p.parent.mkdir(parents=True, exist_ok=True)
            h, size = hashlib.sha256(), 0
            with p.open('xb') as f:
                for b in volume.read_file('/' + e['path']):
                    size += len(b)
                    assert size <= e['size']
                    f.write(b)
                    h.update(b)
            assert size == e['size']
            receipt = dict(remote_path=e['path'], relative_path=relative, bytes=size, sha256=h.hexdigest())
            put(dest / 'transfer_receipts' / (hashlib.sha256(relative.encode()).hexdigest()+'.json'), receipt)
            return receipt
        with ThreadPoolExecutor(max_workers=8) as pool:
            copied = list(pool.map(copy, files))
        after = inventory()
        put(dest / 'REMOTE_INVENTORY_AFTER.json', dict(observed_epoch=time.time(), entries=after))
        assert after == before
        job = SPEC['jobs'][job_id]
        k = path.key(job)
        keys = [k + '/dispatch', *long_evidence.expected_record_keys(k, job['kind'], job['U'])]
        assert len(keys) == len(set(keys)) and len(keys) < 1500
        def get(key):
            v = dict(key=key, value=store.get(key), observed_epoch=time.time())
            put(dest / 'named_records' / (hashlib.sha256(key.encode()).hexdigest()+'.json'), v)
            return v
        with ThreadPoolExecutor(max_workers=12) as pool:
            records = list(pool.map(get, keys))
        present = {e['key']: e['value'] for e in records if e['value'] is not None}
        assert present[k+'/terminal']['status'] == 'failed'
        assert present[k+'/terminal']['app_id'] == provider['app_id']
        proof = dict(completed_epoch=time.time(), files=copied, file_count=len(copied),
            bytes=sum(e['bytes'] for e in copied), stable_inventory=True,
            named_key_count=len(records), present_keys=list(present),
            absent_key_count=len(records)-len(present), provider=provider,
            scientific_completion=False, model_calls=0, score_calls=0, decoder_calls=0,
            original_call_retries=0, no_full_success_archive_or_scoring_inferred=True)
        put(dest / 'PRESERVATION_COMPLETED.json', proof)
        proofs[job_id] = proof
        print(json.dumps({k: proof[k] for k in ('file_count', 'bytes', 'named_key_count', 'present_keys', 'completed_epoch')}), flush=True)
    put(ROOT / 'PRESERVATION_COMPLETED.json', dict(completed_epoch=time.time(), jobs=proofs,
        previous_failures_preserved=True, baseline_not_dispatched=True, automatic_retry=False))
except BaseException as e:
    put(ROOT / 'PRESERVATION_FAILED.json', dict(epoch=time.time(), error=repr(e),
        traceback=traceback.format_exc(), partial_retained=True, automatic_retry=False))
    raise
finally:
    signal.alarm(0)

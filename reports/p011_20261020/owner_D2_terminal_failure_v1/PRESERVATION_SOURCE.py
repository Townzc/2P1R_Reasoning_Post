"""First read-only preservation of D2's exit124 and subsequent guard failure."""
from pathlib import Path, PurePosixPath
from concurrent.futures import ThreadPoolExecutor
import dataclasses, enum, hashlib, json, signal, time, traceback
import modal
from experiments.p011 import long_owner_path as path, long_owner_evidence as evidence

R = Path(path.LOCAL)
OUT = R / 'owner_D2_terminal_failure_preservation_r1'
JOB = 'long_D2_S-F15_s17_owner_r1'
assert not OUT.exists(), 'Permanent preservation fence exists'
OUT.mkdir()

def put(p, value):
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('x') as f:
        json.dump(value, f, indent=2, default=lambda x: x.value if isinstance(x, enum.Enum) else str(x))
        f.write('\n')

def deadline(*_):
    raise TimeoutError('D2 first preservation 1800s cap; retain partial files, no automatic repeat')

signal.signal(signal.SIGALRM, deadline)
signal.alarm(1800)
put(OUT / 'ATTEMPT.json', dict(started_epoch=time.time(), job=JOB, read_only=True,
    model_calls=0, score_calls=0, full_original_binary_stream_copy=True, cap_seconds=1800))
try:
    spec = json.loads(Path(path.SPEC).read_text())
    job = spec['jobs'][JOB]
    dispatch = R / 'dispatch' / JOB
    assert not (dispatch / 'RESULT.json').exists()
    for name in ['INTENT.json', 'SUBMITTED.json', 'RETURN_ERROR.json', 'BUDGET_SOURCE.json', 'ORIGINAL_REPORT.md']:
        with (OUT / name).open('xb') as f:
            f.write((dispatch / name).read_bytes())
    sub = json.loads((OUT / 'SUBMITTED.json').read_text())
    error = json.loads((OUT / 'RETURN_ERROR.json').read_text())
    assert error['message'] == 'Original source/dispatch/report/window differs'
    raw = (R / 'OWNER150_INITIAL6_ORIGINAL_RUN.log').read_bytes()
    with (OUT / 'ORIGINAL_SHARED_CLI_SNAPSHOT.log').open('xb') as f:
        f.write(raw)
    assert b'Runner failed with exit code: 124' in raw and ('FAILED ' + JOB).encode() in raw
    graph = modal.FunctionCall.from_id(sub['call_id']).get_call_graph()
    put(OUT / 'ORIGINAL_D2_CALL_GRAPH.json', [dataclasses.asdict(x) for x in graph])
    put(OUT / 'QUIESCENCE_SCOPE.json', dict(original_call_returned_error=True,
        whole_shared_app_stopped_claimed=False, other_original_workers_must_continue=True,
        observed_epoch=time.time(), exact_rejected_guard_predicate_observed=False,
        log_exit_code=124, provider_preemption_claimed=False,
        no_new_model_after_owner_dispatch_cutoff=True))
    volume = modal.Volume.from_name('sft-allocation-midpoint-v1', create_if_missing=False)
    store = modal.Dict.from_name(path.STORE, create_if_missing=False)
    prefix = (path.BASE + '/' + JOB).removeprefix('/evidence/')
    key = path.key(job)

    def inventory():
        rows = []
        for entry in volume.iterdir('/' + prefix, recursive=True):
            name = entry.path.lstrip('/')
            assert name.startswith(prefix + '/') and '..' not in PurePosixPath(name).parts
            rows.append(dict(path=name, type=int(entry.type), size=entry.size, mtime=entry.mtime))
        return sorted(rows, key=lambda x: x['path'])

    before = inventory()
    put(OUT / 'REMOTE_INVENTORY_BEFORE.json', dict(observed_epoch=time.time(), entries=before))
    files = [x for x in before if x['type'] == 1]
    assert sum(x['size'] for x in files) <= 100 * 1024**3, 'Unexpected size; inspect saved inventory without recopying'
    small = [x for x in files if x['size'] <= 16000000 and Path(x['path']).suffix in ('.json', '.jsonl', '.log', '.txt')]
    large = [x for x in files if x not in small]

    def save(entry):
        rel = entry['path'][len(prefix) + 1:]
        destination = OUT / 'original_remote_payload' / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256()
        size = 0
        with destination.open('xb') as f:
            for block in volume.read_file('/' + entry['path']):
                size += len(block)
                assert size <= entry['size']
                f.write(block)
                digest.update(block)
        assert size == entry['size']
        result = dict(relative_path=rel, bytes=size, sha256=digest.hexdigest())
        put(OUT / 'copy_receipts' / (hashlib.sha256(rel.encode()).hexdigest() + '.json'), result)
        return result

    with ThreadPoolExecutor(max_workers=8) as pool:
        copied = list(pool.map(save, small))
    for entry in large:
        copied.append(save(entry))
    after = inventory()
    put(OUT / 'REMOTE_INVENTORY_AFTER.json', dict(observed_epoch=time.time(), entries=after))
    assert before == after, 'Inventory changed; preserve actual copies without claiming stability'
    keys = [key + '/dispatch', *evidence.expected_record_keys(key, job['kind'], job['U'])]
    assert len(keys) == len(set(keys))

    def get(name):
        result = dict(key=name, value=store.get(name), observed_epoch=time.time())
        put(OUT / 'named_records' / (hashlib.sha256(name.encode()).hexdigest() + '.json'), result)
        return result

    with ThreadPoolExecutor(max_workers=12) as pool:
        records = list(pool.map(get, keys))
    present = {x['key']: x['value'] for x in records if x['value'] is not None}
    claim = present.get(key + '/claim')
    assert claim and claim['logical_id'] == JOB
    proof = dict(job=JOB, finished_epoch=time.time(), claim=claim,
        terminal=present.get(key + '/terminal'), file_count=len(copied),
        copied_bytes=sum(x['bytes'] for x in copied), copied_files=copied,
        excluded_files=[], stable_inventory=True, named_key_count=len(keys),
        present_keys=list(present), absent_count=len(keys)-len(present),
        whole_shared_app_stopped_claimed=False, original_model_or_score_repeated=False,
        original_failure_observed_epoch=error['observed_epoch'],
        failed_duration_upper_bound_seconds=error['observed_epoch']-claim['worker_start_epoch'],
        duration_bound_not_invoice=True, exact_rejected_guard_predicate_observed=False,
        original_scientific_result_unavailable=True, partial_outputs_not_scored_as_zero=True)
    put(OUT / 'PRESERVATION_COMPLETED.json', proof)
    print(json.dumps(dict(preserved=str(OUT), files=len(copied), bytes=proof['copied_bytes'],
        keys=len(keys), present=len(present), terminal_present=key+'/terminal' in present)), flush=True)
except BaseException as exc:
    put(OUT / 'FAILED.json', dict(error=repr(exc), traceback=traceback.format_exc(), partial_retained=True))
    raise
finally:
    signal.alarm(0)

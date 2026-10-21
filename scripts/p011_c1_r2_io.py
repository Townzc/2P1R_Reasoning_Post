"""C1 r2 completed-call collection and full readonly closure; no upload.

All subcommands are create-only and locally bounded. Partial transfers remain;
no whole-command retry, model/tokenizer invocation or recomputed statistics.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import threading
import time

from experiments.p011.c1_r2 import outer, admission as c1_admission, artifacts as c1_artifacts
from experiments.sft_allocation_midpoint.common import dump, read, sha, digest
from experiments.p011.c1_r2.inputs import load_pack

ROOT = Path(__file__).resolve().parents[1]
VOLUME = 'sft-allocation-midpoint-v1'


def remaining_io_seconds(mode, spec, now, receipt=None):
    """Both closeout commands share the original absolute result deadline."""
    from experiments.p011.c1_r2.execution import CUTOFF_EPOCH
    if type(now) not in (int, float) or not math.isfinite(now):
        raise ValueError('Actual finite IO observation time required')
    if mode in ('collect', 'audit'):
        start = receipt['worker_start_epoch']
        if type(start) not in (int, float) or not math.isfinite(start) or start > now:
            raise ValueError('Original real worker start required')
        deadline = min(CUTOFF_EPOCH, start+spec['limits']['worker_seconds']+
            spec['limits']['closeout_seconds'])
    else:
        raise ValueError('Unknown bounded IO mode')
    remaining = min(3600, deadline-now)
    if remaining < 1:
        raise TimeoutError('Original end-to-end result window is exhausted')
    return remaining, deadline


def get_review(root, review_file):
    spec_file = root/outer.SPEC
    spec = read(spec_file)
    outer.published(root, spec)
    review = c1_admission.reviewed_path(spec, spec_file, read(review_file))
    return spec, review


def collect(root, out, spec, review):
    import modal
    run = root/outer.LOCAL/'dispatch'/outer.LOGICAL
    receipt = read(run/'RESULT.json')
    sub = read(run/'SUBMITTED.json')
    if receipt.get('status') != 'completed' or receipt.get('app_id') != sub['app_id']:
        raise ValueError('Original returned complete call required; failed-call preservation is separate')
    cli = str(root/'.local/midpoint_20261011/venv/bin/modal')
    def provider(*args):
        return json.loads(subprocess.check_output([cli, *args, '--json'],
            text=True, stderr=subprocess.PIPE, timeout=45))
    info = provider('app', 'info', sub['app_id'])
    containers = provider('container', 'list')
    observed = outer.closed_provider(sub['app_id'], info, containers, time.time())
    dump(out/'PROVIDER_RAW.json', {'app': info, 'containers': containers})
    dump(out/'PROVIDER_STOPPED0.json', observed)
    store = modal.Dict.from_name(outer.STORE, create_if_missing=False)
    records = {}
    for key in outer.complete_record_keys(spec):
        value = store.get(key)
        if value is None:
            raise ValueError('Required original named C1 record unavailable')
        records[key] = value
        dump(out/'records'/(key.removeprefix(outer.KEY+'/')+'.json'), value)
    c1_artifacts.original_completion(spec, receipt, observed, records, outer.KEY, receipt['claim'])
    dump(out/'RECORDS.json', records)
    dump(out/'ORIGINAL_RESULT.json', receipt)
    volume = modal.Volume.from_name(VOLUME, create_if_missing=False)
    remote = outer.REMOTE.removeprefix('/evidence')+'/payload/evidence.tar.gz'
    target = out/'evidence.tar.gz'
    with target.open('xb') as handle:
        for block in volume.read_file(remote): handle.write(block)
    if sha(target) != receipt['artifact']['tar_sha256'] or target.stat().st_size != receipt['artifact']['tar_bytes']:
        raise ValueError('Original completed archive transfer differs; partial retained')
    dump(out/'COMPLETED.json', {'review': review, 'receipt_file_sha256': sha(out/'ORIGINAL_RESULT.json'),
        'archive_sha256': sha(target), 'named_record_count': len(records),
        'provider': observed, 'completed_epoch': time.time(), 'retries': 0})
    dump(run/'PROVIDER_STOPPED0.json', observed)


def audit(root, out, spec, review):
    saved = root/outer.LOCAL/'c1_io_r2'/'collect'
    read(saved/'COMPLETED.json')
    receipt = read(saved/'ORIGINAL_RESULT.json')
    provider = read(saved/'PROVIDER_STOPPED0.json')
    records = read(saved/'RECORDS.json')
    dispatch = read(root/outer.LOCAL/'dispatch'/outer.LOGICAL/'INTENT.json')
    if (records[outer.KEY+'/dispatch'] != dispatch or dispatch['review'] != review
            or dispatch['spec_file_sha256'] != sha(root/outer.SPEC)
            or receipt['basis']['dispatch_sha256'] != digest(dispatch)
            or receipt['basis']['source_files'] != spec['source_files']
            or receipt['basis']['input_files'] != spec['input_files']
            or receipt['basis']['review'] != review
            or receipt['basis']['spec_file_sha256'] != sha(root/outer.SPEC)):
        raise ValueError('Original outer dispatch/review/source/input binding differs')
    source = root/outer.LOCAL/'dispatch'/outer.LOGICAL/'BUDGET_SOURCE.json'
    if sha(source) != dispatch['budget_source_sha256']:
        raise ValueError('Original full budget source bytes differ')
    b = read(source)
    p = dispatch['provider_observation']
    # Replay the original saved admission snapshot; never query closed providers.
    prior = dispatch['prior_attempt_records']
    if c1_admission.fresh_budget(spec, b, prior, p['containers'], p['states'],
            dispatch['dispatch_epoch'], root) != dispatch['budget']:
        raise ValueError('Original whole-category numeric admission differs')
    tasks, memberships = load_pack(root/outer.LOCAL/'c1_inputs_r1', spec['input_files'], spec['task_inventory'])
    c1_artifacts.extract(saved/'evidence.tar.gz', out/'payload', receipt['artifact'])
    proof = c1_artifacts.check_complete(spec, receipt, provider, records, outer.KEY,
        receipt['claim'], out/'payload', tasks, memberships, receipt['basis'])
    dump(out/'COMPLETE_READONLY_PROOF.json', {**proof,
        'outer_source_review_budget_and_input_binding_still_required': False,
        'full_outer_bindings_verified': True, 'model_calls': 0, 'new_statistics': 0,
        'actual_independent_A3_accepted': False, 'finished_epoch': time.time()})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('collect', 'audit'))
    parser.add_argument('--review', required=True)
    args = parser.parse_args()
    spec, review = get_review(ROOT, args.review)
    receipt = read(
        ROOT/outer.LOCAL/'dispatch'/outer.LOGICAL/'RESULT.json')
    seconds, deadline = remaining_io_seconds(args.mode, spec, time.time(), receipt)
    out = ROOT/outer.LOCAL/'c1_io_r2'/args.mode
    out.mkdir(parents=True, exist_ok=False)
    dump(out/'ATTEMPT.json', {'mode': args.mode, 'spec_file_sha256': sha(ROOT/outer.SPEC),
        'started_epoch': time.time(), 'whole_helper_retry_allowed': False,
        'original_absolute_deadline_epoch': deadline, 'remaining_local_seconds': seconds})
    timer = threading.Timer(seconds, lambda: os._exit(124))
    timer.daemon = True; timer.start()
    try:
        {'collect': collect, 'audit': audit}[args.mode](ROOT, out, spec, review)
    except BaseException as exc:
        dump(out/'FAILED.json', {'type': type(exc).__name__, 'message': str(exc),
            'partial_retained': True, 'whole_helper_retry_allowed': False})
        raise
    finally:
        timer.cancel()


if __name__ == '__main__':
    main()

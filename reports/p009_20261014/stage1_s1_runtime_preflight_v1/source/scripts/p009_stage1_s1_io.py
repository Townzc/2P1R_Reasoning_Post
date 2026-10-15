"""Single S1 upload, per-slot gates, and original completed evidence collection."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import time

from experiments.sft_allocation_midpoint.common import read, dump, sha, digest, verify
from experiments.learning_regime_p009.stage1_s1_funded_binding import (
    CAMPAIGN, RUNS, FIRST_PAIR, validate, dispatch_key, logical_key, marker,
)

SPEC = Path('reports/p009_20261014/stage1_s1_runtime_preflight_v1/ADMISSION.json')
CLI = '.local/midpoint_20261011/venv/bin/modal'


def prospective(root, run, budget_path, readback):
    spec = read(SPEC)
    value = dict(source_files=spec['source_files'], input_readback=readback,
        runtime_review=read(root/'RUNTIME_ACCEPTED.json'),
        core_review=read(root.parent/'STAGE1_SCIENTIFIC_CORE_CODE_ACCEPTED.json'),
        input_review=read(root.parent/'STAGE1_S1_INPUTS_ACCEPTED.json'),
        G0_review=read(root.parent/'P1_COMPLETE_A2_ACCEPTED.json'),
        internal_only_review=read(root.parent/'P0_INTERNAL_ONLY_AMENDMENT_ACCEPTED.json'),
        NC_A4_review=read(root.parent/'NC_GUARD_REPAIR_PAIR_A4_ACCEPTED.json'),
        budget_owner_decision=read(root/'OWNER_BUDGET_PROXY_DECISION.json'), budget=read(budget_path))
    value['review_target'] = value['runtime_review']['target_commit']
    names = ['runtime_review','core_review','input_review','G0_review','internal_only_review','NC_A4_review']
    if run not in FIRST_PAIR:
        value['futility_review'] = read(root/'FIRST_PAIR_FUTILITY_A4_ACCEPTED.json')
        value['futility_target_commit'] = value['futility_review']['target_commit']
        names.append('futility_review')
    for name in names:
        review = value[name]
        if sha(review['local_report_path']) != review['report_sha256']:
            raise ValueError('Actual original complete review file missing')
    owner = value['budget_owner_decision']
    if (sha(owner['raw_comment_local_path']) != owner['raw_comment_file_sha256']
            or read(owner['raw_comment_local_path']) != owner['comment']):
        raise ValueError('Original actual owner proxy comment differs')
    for name, expected in spec['source_files'].items():
        if sha(name) != expected: raise ValueError('Exact source bytes changed')
    if not 0 <= time.time()-value['budget']['observed_epoch'] <= 3600:
        raise ValueError('A necessary current budget snapshot is required')
    validate(spec, read(root/'plan.json'), run, value)
    return value


def upload(root, budget_path):
    import modal
    from modal.exception import NotFoundError
    spec = read(SPEC); plan = read(root/'plan.json')
    if any((root/k).exists() for k in ('UPLOAD_INTENT.json','UPLOAD_VERIFIED.json','upload_receipts','runs')):
        raise ValueError('Prior/partial upload or calls block whole-helper replay')
    for run in FIRST_PAIR: prospective(root, run, budget_path, spec['inputs'])
    if time.time()+max(c['full_window_seconds'] for c in spec['slots'].values()) > plan['deadline_epoch']:
        raise ValueError('Full original window unavailable')
    local = root.parent/'stage1_s1_inputs_r1'; verify(local, spec['inputs'])
    volume = modal.Volume.from_name('sft-allocation-midpoint-v1', create_if_missing=False)
    remote = spec['remote_inputs'].removeprefix('/evidence')
    try: list(volume.iterdir(remote))
    except NotFoundError: pass
    else: raise ValueError('Remote input directory already exists; no overwrite')
    dump(root/'UPLOAD_INTENT.json', dict(utc=datetime.now(timezone.utc).isoformat(),
        spec_sha256=digest(spec), files=spec['inputs'], remote=remote, base_weights_reused=True))
    observed = {}
    for name, expected in spec['inputs'].items():
        with volume.batch_upload(force=False) as batch: batch.put_file(local/name, remote+'/'+name)
        h = hashlib.sha256(); size = 0
        for part in volume.read_file(remote+'/'+name): h.update(part); size += len(part)
        value = dict(bytes=size, sha256=h.hexdigest())
        if value != expected: raise ValueError('Original input readback mismatch')
        observed[name] = value; dump(root/'upload_receipts'/(name+'.json'), value)
    dump(root/'UPLOAD_VERIFIED.json', dict(files=observed, utc=datetime.now(timezone.utc).isoformat(),
                                         new_model_calls=0, new_base_weight_uploads=0))
    print('All original S1 inputs transferred and read back once; zero model calls.')


def gates(root, run, budget_path):
    dest = root/'gates'/run
    if dest.exists() or (root/'runs'/run).exists():
        raise ValueError('Existing/partial slot gate or call blocks repetition')
    readback = read(root/'UPLOAD_VERIFIED.json')['files']
    release = prospective(root, run, budget_path, readback)
    cap = read(SPEC)['slots'][run]
    if time.time()+cap['full_window_seconds'] > read(root/'plan.json')['deadline_epoch']:
        raise ValueError('Full original dispatch window unavailable')
    dump(dest/'INTENT.json', dict(run_id=run, utc=datetime.now(timezone.utc).isoformat(),
        budget_file_sha256=sha(budget_path), automatic_retry=False))
    dump(dest/'gates.json', release)
    print('One source/review-bound gate written for '+run+'; no upload or model call.')


def collect(root, run):
    import modal
    from experiments.sft_allocation_p008.provider_release import read_stopped_apps
    spec = read(SPEC); dest = root/'closeouts'/run
    if dest.exists(): raise ValueError('Prior/partial collection blocks whole-helper retry')
    sent = read(root/'runs'/run/'dispatch_intent.json'); env = read(root/'runs'/run/'result.json')
    validate(spec, sent['plan'], run, sent['release'])
    if env['receipt']['status'] != 'completed': raise ValueError('A real complete original result required')
    first = [] if run in FIRST_PAIR else sent['release']['futility_review']['first_pair_app_ids']
    apps = list(dict.fromkeys(spec['required_stopped_app_ids']+first+[sent['provider_app_id']]))
    containers = json.loads(subprocess.check_output([CLI,'container','list','--json'],text=True,timeout=60))
    owned = [c for c in containers if c.get('app_id') in apps]
    infos = read_stopped_apps(CLI, apps, owned)
    dump(dest/'INTENT.json', dict(run_id=run, app_id=sent['provider_app_id'], utc=datetime.now(timezone.utc).isoformat()))
    store = modal.Dict.from_name('sft-allocation-midpoint-claims-v1', create_if_missing=False)
    extra = set(spec['required_records'])|{logical_key(k) for k in RUNS}; prefix = 'midpoint/'+CAMPAIGN+'/'
    ledger = {k:v for k,v in store.items() if k.startswith(prefix) or k in extra}
    if (ledger.get(prefix+'terminal/'+run) != env['receipt']
            or digest(env['artifact_manifest']) != env['receipt']['evidence_sha256']
            or any(ledger.get(k) != v for k,v in spec['required_records'].items())
            or any(ledger.get(k) != marker(spec,run,sent['release']) for k in (dispatch_key(run),logical_key(run)))):
        raise ValueError('Original complete lineage/receipt/fences differ')
    dump(dest/'ledger.json', ledger)
    dump(dest/'provider.json', dict(app_ids=apps, state='stopped', original_app_info=infos,
        owned_containers=owned, owned_container_ids=[], utc=datetime.now(timezone.utc).isoformat()))
    dump(dest/'COMPLETED.json', dict(passed=True, ledger_sha256=sha(dest/'ledger.json'),
        original_receipt_sha256=sha(root/'runs'/run/'result.json'), scientific_calls=0))
    print('Original complete S1 lineage and provider STOPPED0 collected once.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('action',choices=['upload','gates','collect'])
    parser.add_argument('--root',required=True); parser.add_argument('--run',choices=list(RUNS))
    parser.add_argument('--budget-json'); args = parser.parse_args()
    if args.action != 'upload' and not args.run: parser.error('--run required')
    if args.action != 'collect' and not args.budget_json: parser.error('--budget-json required')
    root = Path(args.root)
    if args.action == 'upload': upload(root,args.budget_json)
    elif args.action == 'gates': gates(root,args.run,args.budget_json)
    else: collect(root,args.run)

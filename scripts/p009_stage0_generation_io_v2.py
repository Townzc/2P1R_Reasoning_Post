"""Exact candidate input transfer and completed-only collection; no dispatch."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import time

from experiments.sft_allocation_midpoint.common import read,dump,sha,digest,verify
from experiments.learning_regime_p009.stage0_generation_binding_v2 import (
    CAMPAIGN,validate_release,dispatch_key,dataset_key,marker)
from experiments.learning_regime_p009.stage0_generation_contract_v2 import SLOTS

SPEC=Path('reports/p009_20261014/stage0_generation_runtime_preflight_v2/ADMISSION.json')
CLI='.local/midpoint_20261011/venv/bin/modal'


def prospective(root,spec):
    release=dict(source_files=spec['source_files'],
        runtime_review=read(root/'RUNTIME_ACCEPTED.json'),
        internal_only_review=read(root.parent/'P0_INTERNAL_ONLY_AMENDMENT_ACCEPTED.json'),
        p0_integrity_review=read(root.parent/'P0_ACTUAL_A2_INTEGRITY_ACCEPTED.json'),
        budget=read(root/'BUDGET_CHECK.json'),input_readback=spec['inputs'],
        olmo_model_readback=spec['models']['olmo']['files'])
    release['review_target']=release['runtime_review']['target_commit']
    for key in ('runtime_review','internal_only_review','p0_integrity_review'):
        rr=release[key]
        if sha(rr['local_report_path'])!=rr['report_sha256']:
            raise ValueError('Full original exact review bytes missing')
    for name,expected in spec['source_files'].items():
        if sha(name)!=expected:raise ValueError('Exact reviewed code differs')
    if not 0<=time.time()-release['budget']['observed_epoch']<=3600:
        raise ValueError('Fresh actual budget evidence required')
    for run in SLOTS:validate_release(spec,read(root/'plan.json'),run,release)
    return release


def upload(root):
    import modal
    from modal.exception import NotFoundError
    spec=read(SPEC);release=prospective(root,spec)
    if (root/'UPLOAD_INTENT.json').exists() or (root/'gates.json').exists():
        raise ValueError('Prior or partial upload: preserve and reconcile, never whole-tool retry')
    plan=read(root/'plan.json')
    if time.time()+max(x['full_window_seconds'] for x in spec['slots'].values())>plan['deadline_epoch']:
        raise ValueError('No complete dispatch window')
    local_inputs=root.parent/'stage0_inputs_r1'
    local_model=root.parent/'stage0_model_assets_r1/olmo'
    verify(local_inputs,spec['inputs']);verify(local_model,spec['models']['olmo']['files'])
    volume=modal.Volume.from_name('sft-allocation-midpoint-v1',create_if_missing=False)
    groups=[('inputs',local_inputs,spec['remote_inputs'],spec['inputs']),
            ('olmo',local_model,spec['models']['olmo']['remote_path'],spec['models']['olmo']['files'])]
    for _,_,remote,_ in groups:
        try:list(volume.iterdir(remote.removeprefix('/evidence')))
        except NotFoundError:pass
        else:raise ValueError('Remote new inputs already exist; independent reconciliation required')
    dump(root/'UPLOAD_INTENT.json',dict(utc=datetime.now(timezone.utc).isoformat(),
        spec_sha256=digest(spec),groups={tag:dict(remote=remote,files=files) for tag,_,remote,files in groups},
        scientific_calls=0,old_base_and_teacher_assets_not_reuploaded=True))
    observed={}
    for tag,local,remote,files in groups:
        remote=remote.removeprefix('/evidence');observed[tag]={}
        for name,expected in files.items():
            # One explicit transfer per original file, serially, followed by
            # independent bytes. Preserve a partial intent on any failure.
            with volume.batch_upload(force=False) as batch:
                batch.put_file(local/name,remote+'/'+name)
            h=hashlib.sha256();size=0
            for block in volume.read_file(remote+'/'+name):h.update(block);size+=len(block)
            value=dict(bytes=size,sha256=h.hexdigest())
            if value!=expected:raise ValueError('Actual Volume readback mismatch')
            observed[tag][name]=value
            dump(root/'upload_receipts'/tag/(name+'.json'),value)
    dump(root/'UPLOAD_VERIFIED.json',dict(files=observed,utc=datetime.now(timezone.utc).isoformat(),
        scientific_calls=0,old_assets_reused=True))
    release['input_readback']=observed['inputs'];release['olmo_model_readback']=observed['olmo']
    for run in SLOTS:validate_release(spec,plan,run,release)
    dump(root/'gates.json',release)
    print('New seven prompt files and original pinned OLMo files transferred/read back; zero calls.')


def collect(root,run):
    import modal
    from experiments.sft_allocation_p008.provider_release import read_stopped_apps
    spec=read(SPEC);dest=root/'closeouts'/run
    if dest.exists():raise ValueError('Original/partial collection exists; no whole helper retry')
    sent=read(root/'runs'/run/'dispatch_intent.json');envelope=read(root/'runs'/run/'result.json')
    validate_release(spec,sent['plan'],run,sent['release'])
    if envelope['receipt']['status']!='completed':raise ValueError('Completed-only collector')
    app_id=sent['provider_app_id'];apps=spec['P0_app_ids']+[app_id]
    containers=json.loads(subprocess.check_output([CLI,'container','list','--json'],text=True))
    owned=[c for c in containers if c.get('app_id') in apps]
    infos=read_stopped_apps(CLI,apps,owned)
    dump(dest/'INTENT.json',dict(run_id=run,app_id=app_id,utc=datetime.now(timezone.utc).isoformat()))
    store=modal.Dict.from_name('sft-allocation-midpoint-claims-v1',create_if_missing=False)
    prefix='midpoint/'+CAMPAIGN+'/'
    extra=set(spec['required_P0_records'])|{dataset_key(n) for n in spec['datasets']}
    ledger={k:v for k,v in store.items() if k.startswith(prefix) or k in extra}
    if (ledger[prefix+'terminal/'+run]!=envelope['receipt']
            or digest(envelope['artifact_manifest'])!=envelope['receipt']['evidence_sha256']
            or ledger[dispatch_key(run)]!=marker(spec,run,sent['release'])):
        raise ValueError('Original envelope/dispatch differs')
    for key,value in spec['required_P0_records'].items():
        if ledger.get(key)!=value:raise ValueError('Original P0 evidence changed')
    dump(dest/'ledger.json',ledger)
    dump(dest/'provider.json',dict(app_ids=apps,state='stopped',original_app_info=infos,
        owned_containers=owned,owned_container_ids=[],utc=datetime.now(timezone.utc).isoformat()))
    dump(dest/'COMPLETED.json',dict(ledger_sha256=sha(dest/'ledger.json'),
        original_receipt_sha256=sha(root/'runs'/run/'result.json'),passed=True))
    print('Original completed lineage/ledger and STOPPED0 saved once.')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['upload','collect'])
    p.add_argument('--root',required=True);p.add_argument('--run',choices=list(SLOTS))
    a=p.parse_args()
    if a.action=='collect' and not a.run:p.error('--run required for collection')
    upload(Path(a.root)) if a.action=='upload' else collect(Path(a.root),a.run)

"""One bound NC input upload/readback and one original completed collection."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import subprocess
import time

from experiments.sft_allocation_midpoint.common import read,dump,sha,digest,verify
from experiments.learning_regime_p009.stage1_nc_binding import (
    CAMPAIGN,RUNS,validate,dispatch_key,logical_key,marker)

SPEC=Path('reports/p009_20261014/stage1_nc_runtime_preflight_v1/ADMISSION.json')
CLI='.local/midpoint_20261011/venv/bin/modal'


def prospective(root,spec):
    release=dict(source_files=spec['source_files'],runtime_review=read(root/'RUNTIME_ACCEPTED.json'),
        core_review=read(root.parent/'STAGE1_SCIENTIFIC_CORE_CODE_ACCEPTED.json'),
        input_review=read(root.parent/'STAGE1_NC_INPUTS_ACCEPTED.json'),
        G0_review=read(root.parent/'STAGE0_COMPLETE_A2_ACCEPTED.json'),
        internal_only_review=read(root.parent/'P0_INTERNAL_ONLY_AMENDMENT_ACCEPTED.json'),
        input_readback=spec['inputs'],budget=read(root/'BUDGET_CHECK.json'))
    release['review_target']=release['runtime_review']['target_commit']
    for key in ('runtime_review','core_review','input_review','G0_review','internal_only_review'):
        item=release[key]
        if sha(item['local_report_path'])!=item['report_sha256']:raise ValueError('Original full fixed report missing')
    for name,h in spec['source_files'].items():
        if sha(name)!=h:raise ValueError('Reviewed source bytes changed')
    if not 0<=time.time()-release['budget']['observed_epoch']<=3600:raise ValueError('Fresh necessary budget required')
    for run in RUNS:validate(spec,read(root/'plan.json'),run,release)
    return release


def upload(root):
    import modal
    from modal.exception import NotFoundError
    spec=read(SPEC);release=prospective(root,spec);plan=read(root/'plan.json')
    if any((root/n).exists() for n in ('UPLOAD_INTENT.json','UPLOAD_VERIFIED.json','gates.json')):
        raise ValueError('Existing/partial upload must be reconciled; no whole helper retry')
    if time.time()+max(x['full_window_seconds'] for x in spec['slots'].values())>plan['deadline_epoch']:
        raise ValueError('Complete original dispatch window missing')
    local=root.parent/'stage1_nc_inputs_r1';verify(local,spec['inputs'])
    volume=modal.Volume.from_name('sft-allocation-midpoint-v1',create_if_missing=False)
    remote=spec['remote_inputs'].removeprefix('/evidence')
    try:list(volume.iterdir(remote))
    except NotFoundError:pass
    else:raise ValueError('Original remote input directory exists; no overwrite/retry')
    dump(root/'UPLOAD_INTENT.json',dict(spec_sha256=digest(spec),files=spec['inputs'],remote=remote,
        utc=datetime.now(timezone.utc).isoformat(),model_files_reused_without_upload=True,scientific_calls=0))
    observed={}
    for name,expected in spec['inputs'].items():
        with volume.batch_upload(force=False) as batch:batch.put_file(local/name,remote+'/'+name)
        h=hashlib.sha256();size=0
        for block in volume.read_file(remote+'/'+name):h.update(block);size+=len(block)
        value=dict(bytes=size,sha256=h.hexdigest())
        if value!=expected:raise ValueError('Original input readback mismatch')
        observed[name]=value;dump(root/'upload_receipts'/(name+'.json'),value)
    dump(root/'UPLOAD_VERIFIED.json',dict(files=observed,utc=datetime.now(timezone.utc).isoformat(),scientific_calls=0))
    release['input_readback']=observed
    for run in RUNS:validate(spec,plan,run,release)
    dump(root/'gates.json',release)
    print('Original nine NC input files transferred and independently read back; zero model calls.')


def collect(root,run):
    import modal
    from experiments.sft_allocation_p008.provider_release import read_stopped_apps
    spec=read(SPEC);dest=root/'closeouts'/run
    if dest.exists():raise ValueError('Original/partial collection exists; never restart whole helper')
    sent=read(root/'runs'/run/'dispatch_intent.json');envelope=read(root/'runs'/run/'result.json')
    validate(spec,sent['plan'],run,sent['release'])
    if envelope['receipt']['status']!='completed':raise ValueError('A real complete original result is required')
    app_id=sent['provider_app_id'];apps=spec['required_stopped_app_ids']+[app_id]
    containers=json.loads(subprocess.check_output([CLI,'container','list','--json'],text=True))
    owned=[x for x in containers if x.get('app_id') in apps];infos=read_stopped_apps(CLI,apps,owned)
    dump(dest/'INTENT.json',dict(run_id=run,app_id=app_id,utc=datetime.now(timezone.utc).isoformat()))
    store=modal.Dict.from_name('sft-allocation-midpoint-claims-v1',create_if_missing=False)
    prefix='midpoint/'+CAMPAIGN+'/'
    extra=set(spec['required_records'])|{logical_key(k) for k in RUNS}
    ledger={k:v for k,v in store.items() if k.startswith(prefix) or k in extra}
    if (ledger[prefix+'terminal/'+run]!=envelope['receipt']
            or digest(envelope['artifact_manifest'])!=envelope['receipt']['evidence_sha256']
            or ledger[dispatch_key(run)]!=marker(spec,run,sent['release'])
            or ledger[logical_key(run)]!=marker(spec,run,sent['release'])):
        raise ValueError('Original complete envelope/dispatch differs')
    for k,v in spec['required_records'].items():
        if ledger.get(k)!=v:raise ValueError('Scientific dependency changed')
    dump(dest/'ledger.json',ledger)
    dump(dest/'provider.json',dict(app_ids=apps,state='stopped',original_app_info=infos,
        owned_containers=owned,owned_container_ids=[],utc=datetime.now(timezone.utc).isoformat()))
    dump(dest/'COMPLETED.json',dict(ledger_sha256=sha(dest/'ledger.json'),passed=True,
        original_receipt_sha256=sha(root/'runs'/run/'result.json')))
    print('Original full NC ledger and provider STOPPED0 collected once.')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['upload','collect'])
    p.add_argument('--root',required=True);p.add_argument('--run',choices=list(RUNS))
    a=p.parse_args()
    if a.action=='collect' and not a.run:p.error('--run is required')
    upload(Path(a.root)) if a.action=='upload' else collect(Path(a.root),a.run)

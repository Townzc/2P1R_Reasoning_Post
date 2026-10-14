"""Reviewed P0 upload/readback and read-only collection; never model dispatch."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import time
from experiments.sft_allocation_midpoint.common import read,dump,sha,digest,verify
from experiments.learning_regime_p009.p0_contract import validate_release,FULL_WINDOW

SPEC=Path('reports/p009_20261014/p0_runtime_preflight_v1/ADMISSION.json')
CLI='.local/midpoint_20261011/venv/bin/modal'


def reviewed_candidate(root,spec):
    design=read(root/'DESIGN_ACCEPTED.json');runtime=read(root/'RUNTIME_ACCEPTED.json')
    for review in (design,runtime):
        if sha(review['local_report_path'])!=review['report_sha256']:
            raise ValueError('Original review bytes not present')
    for name,expected in spec['source_files'].items():
        if sha(name)!=expected:raise ValueError('Exact reviewed source changed')
    budget=read(root/'BUDGET_CHECK.json')
    if not 0<=time.time()-budget['observed_epoch']<=3600:
        raise ValueError('Fresh actual budget evidence required')
    candidate=dict(source_files=spec['source_files'],design_review=design,runtime_review=runtime,
        review_target=runtime['target_commit'],budget=budget,input_readback=spec['inputs'])
    # This is only a prospective schema check. No dispatch gate is persisted
    # before every actual uploaded byte has been independently read back.
    validate_release(spec,read(root/'plan.json'),candidate)
    return candidate


def upload(root):
    import modal
    from modal.exception import NotFoundError
    spec=read(SPEC);candidate=reviewed_candidate(root,spec);plan=read(root/'plan.json')
    if time.time()+FULL_WINDOW>plan['deadline_epoch']:
        raise ValueError('No complete execution window')
    if (root/'UPLOAD_INTENT.json').exists() or (root/'gates.json').exists():
        raise ValueError('Prior/partial upload; reconcile missing bytes, never whole-tool retry')
    verify(root/'inputs',spec['inputs'])
    volume=modal.Volume.from_name('sft-allocation-midpoint-v1',create_if_missing=False)
    remote=spec['remote_inputs'].removeprefix('/evidence')
    try:list(volume.iterdir(remote))
    except NotFoundError:pass
    else:raise ValueError('Existing remote inputs; require explicit reconciliation')
    dump(root/'UPLOAD_INTENT.json',dict(remote=remote,files=spec['inputs'],
        utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),scientific_calls=0))
    # One explicit transfer per file, no worker or model is used for upload.
    for name in spec['inputs']:
        with volume.batch_upload(force=False) as batch:
            batch.put_file(root/'inputs'/name,remote+'/'+name)
    observed={}
    for name,expected in spec['inputs'].items():
        h=hashlib.sha256();size=0
        for block in volume.read_file(remote+'/'+name):h.update(block);size+=len(block)
        record=dict(bytes=size,sha256=h.hexdigest())
        if record!=expected:raise ValueError('Independent Volume readback differs')
        observed[name]=record
    dump(root/'UPLOAD_VERIFIED.json',dict(files=observed,scientific_calls=0,
        utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
    candidate['input_readback']=observed
    dump(root/'gates.json',candidate)
    print('Three exact P0 files uploaded/read back; zero model calls.')


def collect(root):
    import modal
    from experiments.sft_allocation_p008.provider_release import read_stopped_apps
    spec=read(SPEC);run='p0_parity_pair';dest=root/'closeout_r1'
    if dest.exists():raise ValueError('Prior/partial collector; no whole-tool retry')
    sent=read(root/'runs'/run/'dispatch_intent.json');env=read(root/'runs'/run/'result.json')
    if env['receipt']['status']!='completed':raise ValueError('Completed-only collector')
    validate_release(spec,sent['plan'],sent['release'])
    app=sent['provider_app_id']
    containers=json.loads(subprocess.check_output([CLI,'container','list','--json'],text=True))
    owned=[c for c in containers if c['app_id']==app]
    infos=read_stopped_apps(CLI,[app],owned)
    dump(dest/'INTENT.json',dict(app_id=app,run_id=run,utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
    db=modal.Dict.from_name('sft-allocation-midpoint-claims-v1',create_if_missing=False)
    prefix='midpoint/'+sent['plan']['campaign_id']+'/'
    ledger={k:v for k,v in db.items() if k.startswith(prefix)}
    if (ledger[prefix+'terminal/'+run]!=env['receipt'] or
            digest(env['artifact_manifest'])!=env['receipt']['evidence_sha256']):
        raise ValueError('Original completed envelope differs')
    dump(dest/'ledger.json',ledger)
    dump(dest/'provider.json',dict(app_id=app,state='stopped',original_app_info=infos,
        owned_containers=owned,owned_container_ids=[],utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
    dump(dest/'COMPLETED.json',dict(passed=True,ledger_sha256=sha(dest/'ledger.json'),
        original_receipt_sha256=sha(root/'runs'/run/'result.json')))
    print('Original P0 completed ledger and STOPPED0 collected once.')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=('upload','collect'));p.add_argument('--root',required=True)
    a=p.parse_args();(upload if a.action=='upload' else collect)(Path(a.root))

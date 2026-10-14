"""One-time reviewed input transfer and read-only completed-run collection.

No model submission. Partial transfers/collections are evidence, never a reason
to rerun this whole tool. Remote files are never overwritten or deleted.
"""
import argparse
import datetime
import hashlib
import json
import subprocess
from pathlib import Path
from experiments.sft_allocation_midpoint.common import read,dump,sha,digest,manifest,verify

SPEC=Path('reports/exploratory_20261014/admission_v1/ADMISSION.json')


def accepted(root,spec):
    a=read(root/'REVIEW_ACCEPTED.json');report=(root/'REVIEW_REPORT.md').read_text()
    if (a['scope']!='exploratory-20261014-code-and-data' or a['decision'] not in ('PASS','PASS-WITH-NOTES') or
        a['spec_sha256']!=digest(spec) or a['source_files']!=spec['source_files'] or
        a['input_manifest_sha256']!=spec['input_manifest_sha256'] or
        a['report_sha256']!=hashlib.sha256(report.encode()).hexdigest() or
        a['io_source_sha256']!=sha(__file__)):
        raise ValueError('Exact real review and helper hash required')
    for n,h in spec['source_files'].items():
        if sha(n)!=h:raise ValueError('Reviewed source changed')
    return a,report


def upload(root):
    import modal,time
    from modal.exception import NotFoundError
    spec=read(SPEC);a,report=accepted(root,spec);plan=read(root/'plan.json')
    if plan!=spec['plan']:raise ValueError('Exact plan required')
    if time.time()+6701>plan['deadline_epoch']:raise ValueError('Complete worker window required')
    if (root/'UPLOAD_INTENT.json').exists() or (root/'UPLOAD_VERIFIED.json').exists():raise ValueError('Do not repeat input transfer')
    inputs=root/'inputs';verify(inputs,read(inputs/'manifest.json')['files'])
    if sha(inputs/'manifest.json')!=spec['input_manifest_sha256']:raise ValueError('Input manifest differs')
    d=modal.Dict.from_name('sft-allocation-midpoint-claims-v1',create_if_missing=False)
    v=modal.Volume.from_name('sft-allocation-midpoint-v1',create_if_missing=False)
    camp=plan['campaign_id'];prefix='midpoint/'+camp+'/'
    if any(k.startswith(prefix) for k in d.keys()):raise ValueError('Prior campaign attempt or reservation')
    try:list(v.iterdir('/'+camp))
    except NotFoundError:pass
    else:raise ValueError('Remote campaign already exists; reconcile')
    files=manifest(inputs);parts=root/'upload_parts';parts.mkdir(exist_ok=False)
    dump(root/'UPLOAD_INTENT.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),files=files,
        remote='/'+camp+'/inputs',review_sha256=sha(root/'REVIEW_ACCEPTED.json'),automatic_retry=False))
    deadline=time.monotonic()+900;actual={}
    # One small, serialized transport batch per file avoids the old bulk-upload
    # SSL fanout failure. Each is attempted only once and independently read back.
    for i,(n,record) in enumerate(files.items()):
        if time.monotonic()>deadline:raise TimeoutError('Bounded local input upload')
        dump(parts/f'{i:03d}_intent.json',dict(file=n,expected=record))
        with v.batch_upload(force=False) as batch:batch.put_file(inputs/n,'/'+camp+'/inputs/'+n)
        h=hashlib.sha256();size=0
        for chunk in v.read_file('/'+camp+'/inputs/'+n):size+=len(chunk);h.update(chunk)
        observed=dict(bytes=size,sha256=h.hexdigest())
        if observed!=record:raise ValueError('Input readback mismatch')
        actual[n]=observed;dump(parts/f'{i:03d}_verified.json',dict(file=n,observed=observed))
    proof=dict(passed=True,manifest_sha256=sha(inputs/'manifest.json'),files=actual,
        utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),remote='/'+camp+'/inputs')
    dump(root/'UPLOAD_VERIFIED.json',proof)
    for run in spec['configs']:
        dump(root/'gates'/(run+'.json'),dict(acceptance=a,review_report=report,upload_verified=proof))
    print(json.dumps(dict(files=len(actual),bytes=sum(x['bytes'] for x in actual.values()),calls=0)))


def collect(root,run):
    import modal
    from experiments.sft_allocation_p008.provider_release import read_stopped_apps
    spec=read(SPEC);accepted(root,spec)
    if run not in spec['configs']:raise ValueError('Unknown finite slot')
    dest=root/'closeouts'/run
    if dest.exists():raise ValueError('Prior/partial collection; never repeat wholesale')
    envelope=read(root/'runs'/run/'result.json');sent=read(root/'runs'/run/'dispatch_intent.json')
    if envelope['receipt']['status']!='completed':raise ValueError('Completed-only collector')
    app_id=sent['provider_app_id'];cli='.local/midpoint_20261011/venv/bin/modal'
    containers=json.loads(subprocess.check_output([cli,'container','list','--json'],text=True))
    apps=read_stopped_apps(cli,[app_id],[c for c in containers if c['app_id']==app_id])
    dest.mkdir(parents=True,exist_ok=False)
    dump(dest/'COLLECT_INTENT.json',dict(run_id=run,app_id=app_id,utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
    db=modal.Dict.from_name('sft-allocation-midpoint-claims-v1',create_if_missing=False);prefix='midpoint/'+spec['plan']['campaign_id']+'/'
    ledger={k:v for k,v in db.items() if k.startswith(prefix)}
    if ledger[prefix+'terminal/'+run]!=envelope['receipt'] or digest(envelope['artifact_manifest'])!=envelope['receipt']['evidence_sha256']:
        raise ValueError('Original envelope/terminal differs')
    dump(dest/'ledger.json',ledger)
    dump(dest/'provider.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),apps=apps,owned_containers=[]))
    dump(dest/'COMPLETED.json',dict(passed=True,run_id=run,original_receipt_sha256=sha(root/'runs'/run/'result.json'),ledger_sha256=sha(dest/'ledger.json')))
    print('Collected original completed slot '+run)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=('upload','collect'));p.add_argument('--root',required=True);p.add_argument('--run')
    a=p.parse_args();r=Path(a.root)
    if a.action=='upload':upload(r)
    else:collect(r,a.run)

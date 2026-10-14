"""Reviewed gates and once-only read-only collection; no upload or model spawn."""
import argparse,datetime,json,subprocess
from pathlib import Path
from experiments.sft_allocation_midpoint.common import read,dump,sha,digest
from experiments.sft_exploratory_20261014.continuation_binding import validate_release,parent_records,marker

SPEC=Path('reports/exploratory_20261014/continuation_admission_v1/ADMISSION.json')
CLI='.local/midpoint_20261011/venv/bin/modal'


def accepted(root,spec,run):
    a=read(root/'REVIEW_ACCEPTED.json');report=(root/'REVIEW_REPORT.md').read_text()
    gate=dict(acceptance=a,review_report=report,original_input_readback=spec['original_input_readback'])
    validate_release(spec,spec['plan'],spec['configs'][run],dict(source_files=spec['source_files'],**gate))
    for n,h in spec['source_files'].items():
        if sha(n)!=h:raise ValueError('Accepted source changed')
    return gate


def gates(root):
    import modal,time
    from experiments.sft_allocation_p008.provider_release import read_stopped_apps
    from experiments.sft_exploratory_20261014.continuation_binding import FULL_WINDOW
    spec=read(SPEC);runs=list(spec['configs'])
    for run in runs:accepted(root,spec,run)
    if (root/'gates').exists():raise ValueError('Existing/partial gates: reconcile, never repeat')
    if time.time()+FULL_WINDOW>spec['plan']['deadline_epoch']:raise ValueError('Full window unavailable')
    db=modal.Dict.from_name('sft-allocation-midpoint-claims-v1',create_if_missing=False)
    containers=json.loads(subprocess.check_output([CLI,'container','list','--json'],text=True))
    apps=list(spec['parent_apps'].values())
    stopped=read_stopped_apps(CLI,apps,[c for c in containers if c['app_id'] in apps])
    if any(k.startswith('midpoint/'+spec['plan']['campaign_id']+'/') for k in db.keys()):
        raise ValueError('Child campaign already attempted')
    for run,cfg in spec['configs'].items():
        for k,v in parent_records(spec,cfg).items():
            if db.get(k)!=v:raise ValueError('Parent failure changed')
        key,_=marker(spec,cfg)
        if db.get(key) is not None:raise ValueError('Suffix already reserved')
    dump(root/'GATE_READ.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
         parent_apps=stopped,owned_parent_containers=[],calls=0,uploads=0))
    for run in runs:dump(root/'gates'/(run+'.json'),accepted(root,spec,run))
    print('Exact reviewed gates prepared; zero uploads/calls.',flush=True)


def collect(root,run):
    import modal
    from experiments.sft_allocation_p008.provider_release import read_stopped_apps
    spec=read(SPEC);accepted(root,spec,run)
    dest=root/'closeouts'/run
    if dest.exists():raise ValueError('Prior/partial collection; no whole-tool retry')
    env=read(root/'runs'/run/'result.json');sent=read(root/'runs'/run/'dispatch_intent.json')
    if env['receipt']['status']!='completed':raise ValueError('Completed-only collector')
    app_id=sent['provider_app_id'];containers=json.loads(subprocess.check_output([CLI,'container','list','--json'],text=True))
    apps=read_stopped_apps(CLI,[app_id],[c for c in containers if c['app_id']==app_id])
    dump(dest/'INTENT.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),run=run,app=app_id))
    db=modal.Dict.from_name('sft-allocation-midpoint-claims-v1',create_if_missing=False)
    prefixes=['midpoint/'+spec['plan']['campaign_id']+'/', 'midpoint/exploratory-20261014-r1/']
    ledger={k:v for k,v in db.items() if any(k.startswith(p) for p in prefixes)}
    if (ledger[prefixes[0]+'terminal/'+run]!=env['receipt'] or
            digest(env['artifact_manifest'])!=env['receipt']['evidence_sha256']):
        raise ValueError('Original envelope/terminal differs')
    dump(dest/'ledger.json',ledger)
    dump(dest/'provider.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),apps=apps,owned_containers=[]))
    dump(dest/'COMPLETED.json',dict(passed=True,run=run,ledger_sha256=sha(dest/'ledger.json'),
         original_receipt_sha256=sha(root/'runs'/run/'result.json')))
    print('Original completed suffix collected: '+run,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=('gates','collect'));p.add_argument('--root',required=True);p.add_argument('--run')
    a=p.parse_args();r=Path(a.root)
    if a.action=='gates':gates(r)
    else:collect(r,a.run)

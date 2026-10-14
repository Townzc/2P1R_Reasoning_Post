"""Local gate preparation and read-only completed collection; no dispatch/upload."""
import argparse
import datetime
import json
from pathlib import Path
import subprocess
import time
from experiments.sft_allocation_midpoint.common import read, dump, sha, digest, verify
from experiments.learning_regime_p009.p0_suffix_contract import (
    CAMPAIGN, RUN, PARENT_CAMPAIGN, PARENT_RUN, FULL_WINDOW, validate_release, check_parent,
)
SPEC = Path('reports/p009_20261014/p0_suffix_preflight_v1/ADMISSION.json')
CLI = '.local/midpoint_20261011/venv/bin/modal'


def gates(root):
    spec = read(SPEC); plan = read(root/'plan.json')
    review = read(root/'RUNTIME_ACCEPTED.json'); budget = read(root/'BUDGET_CHECK.json')
    parent = root.parent; preserved = parent/'interrupted_preservation_r1'
    if (root/'gates.json').exists() or time.time()+FULL_WINDOW > plan['deadline_epoch']:
        raise ValueError('Prior gate or no complete window')
    if (sha(review['local_report_path']) != review['report_sha256'] or
            sha(preserved/'PRESERVED.json') != spec['parent_preservation_sha256'] or
            not 0 <= time.time()-budget['observed_epoch'] <= 3600):
        raise ValueError('Missing fixed review/preservation/fresh budget')
    for name, expected in spec['source_files'].items():
        if sha(name) != expected:
            raise ValueError('Source changed')
    inputs = parent/'inputs'; verify(inputs, spec['parent_spec']['inputs'])
    proof = check_parent(spec, preserved/'evidence', read(preserved/'ledger.json'), inputs)
    provider = read(preserved/'PROVIDER.json')
    if provider['state'] != 'stopped' or provider['owned_containers']:
        raise ValueError('Original provider not STOPPED0')
    release = dict(source_files=spec['source_files'], runtime_review=review,
        review_target=review['target_commit'], budget=budget,
        input_readback=read(parent/'UPLOAD_VERIFIED.json')['files'], parent_prefix_proof=proof)
    validate_release(spec, plan, release)
    dump(root/'gates.json', release)
    print('Prepared exact local gate, reusing original uploaded inputs; zero transfers/calls.')


def collect(root):
    import modal
    from experiments.sft_allocation_p008.provider_release import read_stopped_apps
    dest = root/'closeout_r1'
    if dest.exists():
        raise ValueError('Prior/partial collector; no whole-tool retry')
    spec = read(SPEC); sent = read(root/'runs'/RUN/'dispatch_intent.json')
    envelope = read(root/'runs'/RUN/'result.json')
    validate_release(spec, sent['plan'], sent['release'])
    if envelope['receipt']['status'] != 'completed':
        raise ValueError('Completed-only collector')
    app = sent['provider_app_id']
    containers = json.loads(subprocess.check_output([CLI,'container','list','--json'],text=True))
    owned = [x for x in containers if x['app_id'] in (app,spec['parent_app_id'])]
    provider = read_stopped_apps(CLI,[spec['parent_app_id'],app],owned)
    dump(dest/'INTENT.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        campaign=CAMPAIGN,run=RUN,app_id=app,read_only=True))
    db = modal.Dict.from_name('sft-allocation-midpoint-claims-v1',create_if_missing=False)
    prefixes = ('midpoint/'+PARENT_CAMPAIGN+'/', 'midpoint/'+CAMPAIGN+'/')
    ledger = {k:v for k,v in db.items() if k.startswith(prefixes)}
    if (ledger[prefixes[1]+'terminal/'+RUN] != envelope['receipt'] or
            ledger[prefixes[0]+'terminal/'+PARENT_RUN] != spec['parent_terminal'] or
            digest(envelope['artifact_manifest']) != envelope['receipt']['evidence_sha256']):
        raise ValueError('Actual two-campaign lineage differs')
    dump(dest/'ledger.json',ledger)
    dump(dest/'provider.json',dict(app_ids=[spec['parent_app_id'],app],state='stopped',
        original_app_info=provider,owned_containers=owned,owned_container_ids=[],
        utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
    dump(dest/'COMPLETED.json',dict(passed=True,ledger_sha256=sha(dest/'ledger.json'),
        original_receipt_sha256=sha(root/'runs'/RUN/'result.json')))
    print('Completed child and failed parent ledger/provider collected once.')


if __name__ == '__main__':
    p = argparse.ArgumentParser();p.add_argument('action',choices=('gates','collect'))
    p.add_argument('--root',required=True);a=p.parse_args()
    (gates if a.action=='gates' else collect)(Path(a.root))

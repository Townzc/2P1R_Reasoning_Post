"""PREPARED ONLY: read-only collect one existing completed CPU, never dispatch."""
import json
import re
import subprocess
from prepare_final_audit_replacements import R,OUT,CLI,utc
from experiments.sft_allocation_midpoint.common import read,dump,digest
from experiments.sft_allocation_p008.provider_release import read_stopped_apps
from experiments.sft_allocation_p008.audit_replacement_binding import REPLACEMENT_CAMPAIGN
from experiments.sft_allocation_p008.pool_lineage import PARENT_CAMPAIGN,CHILD_CAMPAIGN


def collect():
    import modal
    target=OUT/'closeout_r1'
    if target.exists():raise ValueError('Existing collection; reconcile rather than repeat')
    envelope=read(OUT/'runs/audit/result.json');binding=read(OUT/'binding.json')
    if envelope['receipt']['status']!='completed':raise ValueError('Completed-only collector; preserve failures separately')
    ids=set(re.findall(r'\bap-[A-Za-z0-9]+\b',(OUT/'audit_run_r1.log').read_text()))
    if len(ids)!=1:raise ValueError('Exact original audit app identity required')
    containers=json.loads(subprocess.check_output([CLI,'container','list','--json'],text=True))
    apps=read_stopped_apps(CLI,sorted(ids),[c for c in containers if c['app_id'] in ids])
    camp=binding['plan']['campaign_id'];prefix='midpoint/'+camp+'/'
    db=modal.Dict.from_name('sft-allocation-midpoint-claims-v1',create_if_missing=False)
    campaigns={PARENT_CAMPAIGN,CHILD_CAMPAIGN,camp,REPLACEMENT_CAMPAIGN}
    prefixes=tuple('midpoint/'+c+'/' for c in sorted(campaigns))
    target.mkdir()
    dump(target/'READ_INTENT.json',dict(utc=utc(),campaigns=sorted(campaigns),read_only=True,
        rule='Full ledger enumeration may take minutes; no repeat or model call'))
    ledger={k:v for k,v in db.items() if k.startswith(prefixes)}
    if (ledger[prefix+'terminal/audit']!=envelope['receipt']
            or digest(envelope['artifact_manifest'])!=envelope['receipt']['evidence_sha256']):
        raise ValueError('Original CPU terminal/manifest mismatch')
    dump(target/'ledger.json',ledger);dump(target/'provider.json',dict(utc=utc(),apps=apps,owned_containers=[],other_containers=containers))
    print('Collected original completed CPU and all four source ledgers; no export/finalizer rerun')


if __name__=='__main__':collect()

# Prepared preclaim guard-intent repair; original sources retained.
"""Reuse original input readback; collect only a real completed new replacement."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import subprocess
import time
from experiments.sft_allocation_midpoint.common import read,dump,sha,digest,verify
from experiments.learning_regime_p009.stage1_nc_guard_repair_binding import (
    CAMPAIGN,RUN,validate,dispatch_key,logical_key,marker)
from experiments.learning_regime_p009.stage1_nc_replacement_contract import (
    PARENT_CAMPAIGN,OWNER_FILE_SHA)

SPEC=Path('reports/p009_20261014/stage1_nc_guard_repair_preflight_v1/ADMISSION.json')
CLI='.local/midpoint_20261011/venv/bin/modal'


def gates(root):
    if any((root/n).exists() for n in ('gates.json','REUSED_INPUTS.json','GATE_INTENT.json','runs')):
        raise ValueError('Prior/partial gates or invocation exists; never repeat')
    spec=read(SPEC);old=root.parent/'stage1_nc_r1'
    previous=root.parent/'stage1_nc_replacement_r1'
    original=read(previous/'runs'/RUN/'dispatch_intent.json')['release']
    reused=read(old/'UPLOAD_VERIFIED.json')
    if reused['files']!=spec['inputs']:raise ValueError('Original exact input readback differs')
    verify(root.parent/'stage1_nc_inputs_r1',spec['inputs'])
    if sha(root.parent/'OWNER_OVERNIGHT_PROXY_20261014.json')!=spec['overnight_authority_file_sha256']:
        raise ValueError('Original human delegation bytes differ')
    decision=read(root/'OWNER_PROXY_DECISION.json')
    if (sha(decision['raw_comment_local_path'])!=decision['raw_comment_file_sha256']
        or read(decision['raw_comment_local_path'])!=decision['comment']):
        raise ValueError('Actual issue comment bytes must be present')
    value=dict(original_replacement_release=original,original_release=original['original_release'],
        parent_disposition_review=original['parent_disposition_review'],
        source_files=spec['source_files'],input_readback=reused['files'],
        runtime_review=read(root/'RUNTIME_ACCEPTED.json'),owner_proxy_decision=decision,
        budget=read(root/'BUDGET_CHECK.json'))
    value['review_target']=value['runtime_review']['target_commit']
    historical=[original['runtime_review'],original['parent_disposition_review']]+[
        original['original_release'][k] for k in ('runtime_review','core_review','input_review','G0_review','internal_only_review')]
    for item in [value['runtime_review']]+historical:
        if sha(item['local_report_path'])!=item['report_sha256']:
            raise ValueError('Actual complete scoped reports must be present')
    for name,h in spec['source_files'].items():
        if sha(name)!=h:raise ValueError('Reviewed source bytes changed')
    if not 0<=time.time()-value['budget']['observed_epoch']<=3600:
        raise ValueError('Necessary new paid-stage budget snapshot must be current')
    plan=read(root/'plan.json');cap=validate(spec,plan,RUN,value)
    if time.time()+cap['full_window_seconds']>plan['deadline_epoch']:
        raise ValueError('Full original dispatch window is required')
    dump(root/'GATE_INTENT.json',dict(utc=datetime.now(timezone.utc).isoformat(),
        spec_sha256=digest(spec),source_sha256=sha(__file__),scientific_calls=0,uploads=0))
    dump(root/'REUSED_INPUTS.json',dict(files=reused['files'],
        original_readback_sha256=sha(old/'UPLOAD_VERIFIED.json'),new_uploads=0,weights_reused=True))
    dump(root/'gates.json',value)
    print('Exactly one gate saved; original nine inputs/readback and original base reused, zero upload/call.')


def collect(root):
    import modal
    from experiments.sft_allocation_p008.provider_release import read_stopped_apps
    spec=read(SPEC);dest=root/'closeout_r1'
    if dest.exists():raise ValueError('Existing/partial collection cannot be rerun')
    sent=read(root/'runs'/RUN/'dispatch_intent.json');envelope=read(root/'runs'/RUN/'result.json')
    validate(spec,sent['plan'],RUN,sent['release'])
    if envelope['receipt']['status']!='completed':raise ValueError('A true complete replacement is required')
    app=sent['provider_app_id'];apps=spec['required_stopped_app_ids']+[app]
    containers=json.loads(subprocess.check_output([CLI,'container','list','--json'],text=True,timeout=60))
    owned=[x for x in containers if x.get('app_id') in apps];infos=read_stopped_apps(CLI,apps,owned)
    dump(dest/'INTENT.json',dict(run_id=RUN,app_id=app,utc=datetime.now(timezone.utc).isoformat()))
    store=modal.Dict.from_name('sft-allocation-midpoint-claims-v1',create_if_missing=False)
    prefix='midpoint/'+CAMPAIGN+'/';oldprefix='midpoint/'+PARENT_CAMPAIGN+'/'
    extra=set(spec['required_records'])|{logical_key(RUN)}
    ledger={k:v for k,v in store.items() if k.startswith(prefix) or k.startswith(oldprefix) or k in extra}
    if (ledger[prefix+'terminal/'+RUN]!=envelope['receipt']
        or digest(envelope['artifact_manifest'])!=envelope['receipt']['evidence_sha256']
        or ledger.get(dispatch_key(RUN))!=marker(spec,RUN,sent['release'])
        or ledger.get(logical_key(RUN))!=marker(spec,RUN,sent['release'])):
        raise ValueError('Original completed replacement receipt/fences differ')
    if any(ledger.get(k)!=v for k,v in spec['required_records'].items()):
        raise ValueError('Original failed parent/completed sibling/dependency changed')
    dump(dest/'ledger.json',ledger)
    dump(dest/'provider.json',dict(app_ids=apps,state='stopped',original_app_info=infos,
        owned_containers=owned,owned_container_ids=[],utc=datetime.now(timezone.utc).isoformat()))
    dump(dest/'COMPLETED.json',dict(passed=True,ledger_sha256=sha(dest/'ledger.json'),
        original_receipt_sha256=sha(root/'runs'/RUN/'result.json'),
        original_failed_parent_retained=True,source_sha256=sha(__file__)))
    print('One complete replacement and both original NC lineages collected; no model call/replay.')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['gates','collect']);p.add_argument('--root',required=True)
    a=p.parse_args();gates(Path(a.root)) if a.action=='gates' else collect(Path(a.root))

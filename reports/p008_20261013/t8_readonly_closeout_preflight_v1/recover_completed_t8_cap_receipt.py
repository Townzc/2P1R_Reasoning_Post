"""PREPARED: bounded read-only recovery of an original successful T8 callback.

Only after a saved local network error, immutable completed terminal and stopped
provider. Never spawn, clear a claim, write remotely, score, or export the run.
"""
from pathlib import Path
import datetime, hashlib, json, subprocess, sys
import modal
from experiments.sft_allocation_midpoint.common import read, dump, digest
from experiments.sft_allocation_p008.provider_release import read_stopped_apps
from experiments.sft_allocation_p008.student_t8_cap_binding import validate_student_binding, verify_supplement

r=Path(__file__).resolve().parent
root=r/'student_completion_r1';run=sys.argv[1]
spec=read('reports/p008_20261013/student_t8_cap_9600_v1/ADMISSION.json')
assert run in spec['runs']
canonical=root/'runs'/run
assert canonical.exists() and not (canonical/'result.json').exists()
sent=read(canonical/'dispatch_intent.json');submitted=read(canonical/'submitted.json')
failure=read(canonical/'return_error.json')
assert failure['type']=='ConnectionError'
assert any(s in failure['error'].lower() for s in ('nodename nor servname','connection reset','client connection','dns'))
plan=read(root/'plan.json');assert sent['run_id']==run and sent['plan']==plan
validate_student_binding(plan,sent['config'],sent['release'],spec)
cli='.local/midpoint_20261011/venv/bin/modal'
containers=json.loads(subprocess.check_output([cli,'container','list','--json'],text=True))
owned=[x for x in containers if x['app_id']==sent['provider_app_id']]
provider=read_stopped_apps(cli,[sent['provider_app_id']],owned)
d=modal.Dict.from_name('sft-allocation-midpoint-claims-v1',create_if_missing=False)
prefix='midpoint/'+plan['campaign_id']+'/'
before={k:d.get(prefix+k+'/'+run) for k in ('claim','intent','terminal')}
terminal=before['terminal'];claim=before['claim'];binding=before['intent']
assert terminal is not None and terminal['status']=='completed'
assert terminal['run_id']==claim['run_id']==binding['run_id']==run
assert terminal['claim_sha256']==digest(claim) and claim['intent_sha256']==digest(binding)
assert claim['plan_sha256']==digest(plan) and binding['config_sha256']==digest(sent['config'])
assert binding['source_sha256']==digest(sent['release']['source_files'])
assert claim['deadline_epoch']-claim['claimed_epoch']==9630
supplement=verify_supplement(d,spec,run)
out=root/'receipt_recovery_t8_cap'/run;out.mkdir(parents=True,exist_ok=False)
dump(out/'READ_INTENT.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    run_id=run,original_call=submitted,provider=provider,owned_containers=owned,
    ledger_before=before,supplement=supplement,original_network_return_error=failure,
    new_model_calls=0,new_remote_writes=0))
volume=modal.Volume.from_name('sft-allocation-midpoint-v1',create_if_missing=False)
values={};evidence={}
for name in ('intent.json','admission.json','result.json','artifact_manifest.json'):
    chunks=[];size=0
    for chunk in volume.read_file('/'+plan['campaign_id']+'/'+run+'/'+name):
        size+=len(chunk)
        if size>16*1024*1024:raise ValueError('Bounded receipt read exceeded; preserve partial, no whole-helper retry')
        chunks.append(chunk)
    raw=b''.join(chunks)
    with (out/name).open('xb') as f:f.write(raw)
    values[name]=json.loads(raw);evidence[name]=dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
original=values['intent.json'];files=values['artifact_manifest.json'];result=values['result.json']
assert original['plan']==plan and original['config']==sent['config'] and original['release']==sent['release']
assert values['admission.json']==spec and digest(files)==terminal['evidence_sha256']
assert original['effective_worker_seconds']==9600 and original['total_reserved_cents']==1258
assert original['supplement']==supplement
assert result['registered_slot_reserved_usd']==12.53 and result['supplement_reserved_usd']==.05
assert result['reserved_cost_usd']==12.58 and result['provider_invoice_usd'] is None
for name in ('intent.json','admission.json','result.json'):assert files[name]==evidence[name]
assert {k:d.get(prefix+k+'/'+run) for k in before}==before
assert verify_supplement(d,spec,run)==supplement
envelope=dict(result=result,artifact_manifest=files,receipt=terminal)
dump(out/'READBACK_VERIFIED.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    passed=True,files=evidence,new_model_calls=0,new_remote_writes=0,original_call=submitted,
    original_N2_passed=False,post_hoc_engineering_deviation=True,
    provenance='Original Volume bytes plus immutable completed terminal after actual provider STOPPED/0; no new invocation'))
dump(canonical/'result.json',envelope)
print(json.dumps(dict(run_id=run,recovered_original_envelope=True,new_model_calls=0)))

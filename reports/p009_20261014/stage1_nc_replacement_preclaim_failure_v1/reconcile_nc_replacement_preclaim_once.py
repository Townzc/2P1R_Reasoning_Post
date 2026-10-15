"""One bounded read-only reconciliation of the failed replacement entry."""
from pathlib import Path
from datetime import datetime, timezone
import json, shutil, signal, subprocess, sys
import modal
from modal.exception import NotFoundError
sys.path.insert(0, '.')
from experiments.sft_allocation_midpoint.common import read, dump, sha, digest, manifest
from experiments.learning_regime_p009.stage1_nc_replacement_binding import CAMPAIGN, RUN, marker, dispatch_key, logical_key

r=Path('.local/p009_20261014/r1');rr=r/'stage1_nc_replacement_r1'
dest=rr/'preclaim_reconciliation_r1'; cli='.local/midpoint_20261011/venv/bin/modal'
if dest.exists():raise ValueError('Existing or partial reconciliation must not be repeated')
sent=read(rr/'runs'/RUN/'dispatch_intent.json');submitted=read(rr/'runs'/RUN/'submitted.json')
error=read(rr/'runs'/RUN/'return_error.json')
spec=read('reports/p009_20261014/stage1_nc_replacement_preflight_v1/ADMISSION.json')
assert error==dict(type='GuardError',error='invalid intent fields',retry_authorized=False)
assert sent['provider_app_id']=='ap-iCt0KOKWNfNojiIzZv1LoM'
assert submitted['call_id']=='fc-01M4Z33847TMFE5KP93N8B5NXQ'
assert sent['release']['source_files']==spec['source_files']
assert all(sha(n)==h for n,h in spec['source_files'].items())
signal.signal(signal.SIGALRM,lambda *args:(_ for _ in ()).throw(TimeoutError('1200 second local reconciliation cap')))
signal.alarm(1200)
dump(dest/'READ_INTENT.json',dict(utc=datetime.now(timezone.utc).isoformat(),source_sha256=sha(__file__),app_id=sent['provider_app_id'],call_id=submitted['call_id'],remote_mutations=0,model_calls=0))
def provider(label):
    containers=json.loads(subprocess.check_output([cli,'container','list','--json'],text=True,timeout=60))
    info=json.loads(subprocess.check_output([cli,'app','info',sent['provider_app_id'],'--json'],text=True,timeout=60))
    value=dict(utc=datetime.now(timezone.utc).isoformat(),app=info,owned_containers=[x for x in containers if x.get('app_id')==sent['provider_app_id']])
    dump(dest/(label+'.json'),value)
    assert info['app_id']==sent['provider_app_id'] and info['lifecycle']['state']=='stopped' and info['lifecycle']['stopped_at'] and not value['owned_containers']
    return value
provider('PROVIDER_BEFORE')
store=modal.Dict.from_name('sft-allocation-midpoint-claims-v1',create_if_missing=False)
prefix='midpoint/'+CAMPAIGN+'/'
keys=list(store.keys())
selected=[k for k in keys if k.startswith(prefix) or k==logical_key(RUN)]
records={k:store.get(k) for k in selected};dump(dest/'ledger.json',records)
expected={prefix+'campaign':sent['plan'],dispatch_key(RUN):marker(spec,RUN,sent['release']),logical_key(RUN):marker(spec,RUN,sent['release'])}
assert records==expected,'Unexpected claim/intent/terminal/unit/attempt or fence; preserve unknown'
volume=modal.Volume.from_name('sft-allocation-midpoint-v1',create_if_missing=False)
try:
    entries=list(volume.listdir(CAMPAIGN+'/'+RUN,recursive=True))
except NotFoundError:
    dump(dest/'VOLUME_ABSENCE.json',dict(utc=datetime.now(timezone.utc).isoformat(),path=CAMPAIGN+'/'+RUN,not_found=True,exception_type='NotFoundError'))
else:
    dump(dest/'UNEXPECTED_VOLUME.json',[dict(path=x.path,size=x.size,type=str(x.type)) for x in entries])
    raise ValueError('Remote directory exists; no zero-work conclusion')
provider('PROVIDER_AFTER')
for name in ('submitted.json','dispatch_intent.json','return_error.json'):
    target=dest/'original_callback'/name;target.parent.mkdir(exist_ok=True);shutil.copyfile(rr/'runs'/RUN/name,target)
shutil.copyfile(rr/'run_r1.log',dest/'original_cli.log')
for name in ('experiments/learning_regime_p009/modal_stage1_nc_replacement.py','experiments/learning_regime_p009/stage1_nc_replacement_binding.py','experiments/sft_allocation_midpoint/guard.py'):
    shutil.copyfile(name,dest/Path(name).name)
dump(dest/'ZERO_WORK_VERIFIED.json',dict(passed=True,utc=datetime.now(timezone.utc).isoformat(),campaign=CAMPAIGN,run_id=RUN,app_id=sent['provider_app_id'],call_id=submitted['call_id'],registered_plan=True,original_dispatch_and_logical_fence_retained=True,claim=False,intent=False,attempt=False,terminal=False,remote_output_directory=False,training_updates=0,checkpoint=False,endpoint_outputs=0,ledger_sha256=sha(dest/'ledger.json'),entry_error=error,previous_nc3200_training_failure_unchanged=True,reserved_cents_retained=655,zero_work_is_not_zero_bill=True,automatic_retry_authorized=False))
dump(dest/'MANIFEST.json',manifest(dest));signal.alarm(0)
print(json.dumps(dict(passed=True,path=str(dest),manifest_sha256=sha(dest/'MANIFEST.json'),proof_sha256=sha(dest/'ZERO_WORK_VERIFIED.json'))))

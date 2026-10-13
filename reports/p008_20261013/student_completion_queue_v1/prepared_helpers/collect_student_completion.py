"""Prepared read-only one-run closeout, no worker dispatch or retries."""
from pathlib import Path
import sys,json,subprocess,datetime,re
import modal
from experiments.sft_allocation_midpoint.common import read,dump,digest
r=Path(__file__).resolve().parent/'student_completion_r1';plan=read(r/'plan.json');run=sys.argv[1];assert run in plan['slots']
env=read(r/'runs'/run/'result.json');assert env['receipt']['status']=='completed';out=r/'closeouts'/run;assert not out.exists()
cli='.local/midpoint_20261011/venv/bin/modal'
ids=set(re.findall(r'\bap-[A-Za-z0-9]+\b',(r/(run+'_run_r1.log')).read_text()));assert len(ids)==1
from experiments.sft_allocation_p008.provider_release import read_stopped_apps
containers=json.loads(subprocess.check_output([cli,'container','list','--json'],text=True))
infos=read_stopped_apps(cli,sorted(ids),[c for c in containers if c['app_id'] in ids])
owned=[dict(app_id=x['app_id'],state=x['lifecycle']['state'],lifecycle=x['lifecycle']) for x in infos]
d=modal.Dict.from_name('sft-allocation-midpoint-claims-v1',create_if_missing=False);prefix='midpoint/'+plan['campaign_id']+'/'
ledger={k:v for k,v in d.items() if k.startswith(prefix)}
assert env['receipt']==ledger[prefix+'terminal/'+run] and digest(env['artifact_manifest'])==env['receipt']['evidence_sha256']
out.mkdir(parents=True)
if env['result'].get('role') in ('main','bridge','base'):
 volume=modal.Volume.from_name('sft-allocation-midpoint-v1',create_if_missing=False)
 timestamps={}
 for folder in ('completed','intents'):
  for entry in volume.iterdir('/'+plan['campaign_id']+'/'+run+'/'+folder):
   timestamps[folder+'/'+Path(entry.path).name]=dict(mtime=float(entry.mtime),bytes=entry.size)
 dump(out/'TIMING_READ_METADATA.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),scope='Original stopped Volume file mtimes, second precision; compact tar timestamps are intentionally normalized and unusable for timing',files=timestamps))
dump(out/'ledger.json',ledger);dump(out/'provider.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),apps=owned,owned_containers=[],other_containers=containers));print('Collected immutable completed evidence for '+run)

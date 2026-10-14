"""Read-only T8 phase/status snapshot; no scores, generation or ledger writes."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import datetime,json,subprocess
import modal
from experiments.sft_allocation_midpoint.common import read,dump
from experiments.sft_allocation_p008.student_t8_cap_binding import AMENDMENT_KEY,supplement_key
r=Path(__file__).resolve().parent/'student_completion_r1';plan=read(r/'plan.json');camp=plan['campaign_id'];prefix='midpoint/'+camp+'/'
spec=read('reports/p008_20261013/student_t8_cap_9600_v1/ADMISSION.json');d=modal.Dict.from_name('sft-allocation-midpoint-claims-v1',create_if_missing=False);v=modal.Volume.from_name('sft-allocation-midpoint-v1',create_if_missing=False)
containers=json.loads(subprocess.check_output(['.local/midpoint_20261011/venv/bin/modal','container','list','--json'],text=True))
def query(run):
 dest=r/'runs'/run;sent=read(dest/'dispatch_intent.json') if (dest/'dispatch_intent.json').exists() else None
 claim=d.get(prefix+'claim/'+run);terminal=d.get(prefix+'terminal/'+run);progress={}
 if claim is not None and terminal is None:
  try:
   completed=[Path(x.path).stem for x in v.iterdir('/'+camp+'/'+run+'/completed')]
   endpoints=sorted(int(x.rsplit('_',1)[1]) for x in completed if x.startswith('endpoint1319_batch_'))
   if endpoints:
    assert endpoints==list(range(0,endpoints[-1]+1,16))
    ack=d.get(prefix+run+'/done/endpoint1319_batch_%04d'%endpoints[-1])
    if ack is not None:progress.update(saved_endpoint_outputs=endpoints[-1]+ack['count'],last_endpoint_ack=ack)
   blocks=sorted(x for x in completed if x.startswith('training_block_'))
   if blocks:
    ack=d.get(prefix+run+'/done/'+blocks[-1])
    if ack is not None:progress.update(last_training_block_ack=ack,reported_committed_updates=int(blocks[-1].rsplit('_',1)[1]))
   progress['scope']='Saved rosters/immutable acknowledgments only, not full raw/state oracle or score'
  except Exception as exc:progress=dict(read_error_type=type(exc).__name__,read_error=str(exc),unknown_preserved=True)
 app=sent['provider_app_id'] if sent else None
 return run,dict(claim=claim,terminal=terminal,supplement=d.get(supplement_key(run)),app_id=app,
  containers=[c for c in containers if c.get('app_id')==app],dispatch=sent is not None,
  result=(dest/'result.json').exists(),callback_error=(dest/'return_error.json').exists(),saved_progress=progress)
with ThreadPoolExecutor(max_workers=8) as p:records=dict(p.map(query,spec['runs']))
now=datetime.datetime.now(datetime.timezone.utc);out=dict(utc=now.isoformat(),campaign=camp,amendment=d.get(AMENDMENT_KEY),records=records,all_containers=containers)
path=r/'status_t8_cap'/(now.strftime('%Y%m%dT%H%M%SZ')+'.json');dump(path,out)
print(json.dumps(dict(path=str(path),utc=out['utc'],records=records,containers=len(containers))))

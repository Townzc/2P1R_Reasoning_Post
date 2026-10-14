"""Read-only once-per-worker startup evidence; no endpoint accuracy is calculated."""
from pathlib import Path
import sys,json,datetime,subprocess,hashlib
import modal
from modal.exception import NotFoundError
from experiments.sft_allocation_midpoint.common import read,dump,sha,digest
from experiments.sft_allocation_p008.student_t8_cap_binding import validate_student_binding,require_timing_terminals,verify_supplement
from experiments.sft_allocation_midpoint.runtime import VERSIONS
r=Path(__file__).resolve().parent;root=r/'student_completion_r1';run=sys.argv[1];dest=root/'runs'/run;out=dest/'startup_verified'
assert not out.exists(), 'Existing startup evidence: do not repeat'
local=read(dest/'dispatch_intent.json');cfg=local['config'];assert cfg['training_multiple']==8 and cfg['updates']==2048 and cfg['targets']==4194296;camp=local['plan']['campaign_id'];prefix='midpoint/'+camp+'/'
d=modal.Dict.from_name('sft-allocation-midpoint-claims-v1',create_if_missing=False);v=modal.Volume.from_name('sft-allocation-midpoint-v1',create_if_missing=False)
unit='endpoint1319_batch_0000' if cfg['role']=='base' else 'training_block_0001_0016'
ack=d.get(prefix+run+'/done/'+unit)
if ack is None:print(json.dumps(dict(run_id=run,pending='first saved completed unit not present')));sys.exit(0)
cli='.local/midpoint_20261011/venv/bin/modal';containers=json.loads(subprocess.check_output([cli,'container','list','--json'],text=True))
owned=[c for c in containers if c.get('app_id')==local['provider_app_id']];assert len(owned)==1
saved={}
def fetch(name,parse=True):
 raw=b''.join(v.read_file('/'+camp+'/'+run+'/'+name));assert len(raw)<5_000_000;saved[name]=raw
 return json.loads(raw) if parse else raw
try:
 intent=fetch('intent.json');spec=fetch('admission.json');env=fetch('environment.json');recipe=fetch('recipe.json');u=fetch('intents/'+unit+'.json');done=fetch('completed/'+unit+'.json')
 if cfg['role']=='base':
  raw=fetch('endpoint1319/batch_0000_raw.json');scored=fetch('endpoint1319/batch_0000_scored.jsonl',False)
 else:
  first_intents=[fetch('intents/update_%04d.json'%i) for i in range(1,17)]
  first_done=[fetch('completed/update_%04d.json'%i) for i in range(1,17)]
except (NotFoundError,FileNotFoundError):
 print(json.dumps(dict(run_id=run,pending='unit acknowledged but original files not yet visible; no proof directory created')));sys.exit(0)
assert intent['plan']==local['plan'] and intent['config']==cfg and intent['release']==local['release']
validate_student_binding(intent['plan'],cfg,intent['release'],spec)
require_timing_terminals(d,intent['release']['gates'])
assert verify_supplement(d,spec,run)==intent['supplement']
assert intent['effective_worker_seconds']==9600 and intent['total_reserved_cents']==1258 and cfg['max_seconds']==9560
assert intent['release']['source_files']==read(r/'t8_cap_9600_r1/RUNTIME_ACCEPTED.json')['source_files']
claim=d.get(prefix+'claim/'+run);bound=d.get(prefix+'intent/'+run)
assert claim['intent_sha256']==digest(bound) and claim['plan_sha256']==digest(intent['plan'])
assert bound['source_sha256']==digest(intent['release']['source_files']) and bound['config_sha256']==digest(cfg) and bound['data_sha256']==cfg['input_sha256']
assert env['versions']==VERSIONS and 'H100' in env['gpu'] and env['cuda']=='12.8' and env['gpu_total_memory']>=75*1024**3 and env['deterministic_algorithms'] is True
assert recipe['identity']['config']==cfg and recipe['identity']['source_commit']==intent['release']['commit']
assert u==d.get(prefix+run+'/unit/'+unit) and done==ack
if cfg['role']=='base':
 assert done['count']==16 and len(raw['problem_ids'])==16
 assert hashlib.sha256(saved['endpoint1319/batch_0000_raw.json']).hexdigest()==done['raw_sha256']
 assert hashlib.sha256(scored).hexdigest()==done['scored_sha256'];dose=dict(committed_updates=0,initial_endpoint_outputs=16)
else:
 plan=read(r/'student_preparation_r1/inputs'/cfg['plan_file']);rows=[json.loads(x) for x in (r/'student_preparation_r1/inputs'/cfg['rows_file']).read_text().split('\n') if x.strip()]
 assert recipe['schedule']==plan['updates'] and recipe['lrs']==plan['lrs']
 wanted=[];targets=processed=0
 for step in range(1,17):
  ids=plan['updates'][step-1];a=dict(step=step,indices=ids,lr=plan['lrs'][step-1],supervised_tokens=sum(rows[i]['source']['n_supervised'] for i in ids),processed_tokens=sum(rows[i]['source']['n_processed'] for i in ids))
  assert first_intents[step-1]==a and all(first_done[step-1][k]==x for k,x in a.items());wanted.append(a)
  targets+=a['supervised_tokens'];processed+=a['processed_tokens']
  assert first_done[step-1]['cumulative_targets']==targets and first_done[step-1]['cumulative_processed']==processed
 assert u['updates']==wanted and u['updates_sha256']==digest(wanted)
 assert done['count']==16 and done['intent_sha256']==digest(u) and done['completions_sha256']==digest(first_done)
 assert done['cumulative_targets']==targets and done['cumulative_processed']==processed;dose=dict(committed_updates=16,supervised_targets=targets,processed_tokens=processed)
proof=dict(passed=True,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),run_id=run,scope='Actual provider/source/spec/claim/environment and first completed unit only; not final raw/state/dose oracle',source_commit=intent['release']['commit'],source_files=intent['release']['source_files'],claim=claim,binding=bound,environment=env,containers=owned,initial_evidence=dose,new_model_calls=0,timing_proposal_digest=digest(intent['release']['gates']['t8_timing_proposal']),numeric_review=intent['release']['gates']['t8_numeric_review'],physical_timing_dependencies_verified=13)
out.mkdir(exist_ok=False)
for name,raw in saved.items():
 p=out/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
dump(out/'VERIFIED.json',proof);print(json.dumps(dict(passed=True,run_id=run,source_commit=proof['source_commit'],initial_evidence=dose)))

"""Prepared one-time upload only AFTER accepted exact numerical student review."""
from pathlib import Path
import json,datetime,hashlib
import modal
from modal.exception import NotFoundError
from experiments.sft_allocation_midpoint.common import read,dump,sha,verify,manifest,digest
from experiments.sft_allocation_p008.main_binding import accepted
r=Path(__file__).resolve().parent;prep=r/'student_preparation_r1';spec=read('reports/p008_20261013/student_admission_v1/ADMISSION.json')
review=read(r/'STUDENT_RUNTIME_ACCEPTED.json');source=read('reports/p008_20261013/student_admission_v1/SOURCE_BUNDLE.json');accepted(review,'main-runtime',source,digest(spec))
for n,h in source.items():assert sha(n)==h
assert not (prep/'UPLOAD_INTENT.json').exists() and not (prep/'UPLOAD_VERIFIED.json').exists()
p=prep/'inputs';verify(p,read(p/'manifest.json')['files']);h=sha(p/'manifest.json');assert all(c['input_sha256']==h for c in spec['configs'].values())
plan=read(r/'student_completion_r1/plan.json');camp=plan['campaign_id'];assert digest(plan)==spec['plan_sha256']
d=modal.Dict.from_name('sft-allocation-midpoint-claims-v1',create_if_missing=False);v=modal.Volume.from_name('sft-allocation-midpoint-v1',create_if_missing=False)
from experiments.sft_allocation_p008.pool_lineage import validate_pool_lineages
for record in validate_pool_lineages(spec['pool_lineages'],spec['draw_local_oracle_sha256']):
 assert d.get('midpoint/'+record['campaign']+'/terminal/'+record['run_id'])==record['terminal']
for run in spec['configs']:
 for kind in ('claim','intent','terminal'):assert d.get(f'midpoint/{camp}/{kind}/{run}') is None
from experiments.sft_allocation_p008.completion_queue import assert_original_absent,transfer_record,TRANSFER_KEY,ORIGINAL_CAMPAIGN
original=read(r/'plan.json');owner=read(r/'OWNER_STUDENT_COMPLETION.json');transfer=transfer_record(plan,original,owner)
original_records={k:value for k,value in d.items() if k.startswith('midpoint/'+ORIGINAL_CAMPAIGN+'/')}
assert_original_absent(original_records)
assert d.get(TRANSFER_KEY) is None,'Existing transfer intent: reconcile rather than rerun uploader'
for name in plan['slots']:
 try:list(v.iterdir('/'+ORIGINAL_CAMPAIGN+'/'+name));raise RuntimeError('Original slot directory exists: reconcile')
 except NotFoundError:pass
remote='/'+camp+'/student_inputs'
try:list(v.iterdir(remote));raise RuntimeError('Existing input path; reconcile, never overwrite')
except NotFoundError:pass
files=manifest(p);dump(prep/'UPLOAD_INTENT.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),files=files,remote=remote,review_sha256=sha(r/'STUDENT_RUNTIME_ACCEPTED.json')))
assert d.put(TRANSFER_KEY,transfer,skip_if_exists=True),'Uncertain transfer: stop, never overwrite'
assert d.get(TRANSFER_KEY)==transfer
dump(r/'student_completion_r1/TRANSFER_COMMITTED.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),record=transfer,original_unattempted_ledger_sha256=digest(original_records)))
with v.batch_upload(force=False) as upload:
 for n in files:upload.put_file(p/n,remote+'/'+n)
actual={}
for n,record in files.items():
 raw=b''.join(v.read_file(remote+'/'+n));actual[n]=dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest());assert actual[n]==record
proof=dict(passed=True,input_sha256=h,files=actual,remote=remote,utc=datetime.datetime.now(datetime.timezone.utc).isoformat());dump(prep/'UPLOAD_VERIFIED.json',proof)
print(json.dumps(dict(passed=True,files=len(actual),bytes=sum(x['bytes'] for x in actual.values()))))

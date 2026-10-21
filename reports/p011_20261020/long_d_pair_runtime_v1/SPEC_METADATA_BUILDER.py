from pathlib import Path
from copy import deepcopy
from decimal import Decimal, ROUND_CEILING
import json,hashlib,datetime
ROOT=Path.cwd();P=ROOT/'reports/p011_20261020';R=ROOT/'.local/p011_20261020/r1';O=P/'long_d_pair_runtime_v1'
if O.exists():raise RuntimeError('New D metadata directory exists; never overwrite/rebuild')
O.mkdir()
def read(p):return json.loads(p.read_text())
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,v):
 with (O/n).open('x') as f:json.dump(v,f,sort_keys=True,indent=2);f.write('\n')
old=read(P/'long_current_runtime_v1/SPEC.json');basis=read(P/'long_lr_r2_runtime_v1/SPEC.json');b=read(P/'b_students_post_long_failure_runtime_v1/SPEC.json')
new=['experiments/p011/long_d_pair_numeric.py','experiments/p011/long_d_pair_execution.py','experiments/p011/long_d_pair_evidence.py','experiments/p011/long_d_pair_path.py','experiments/p011/modal_long_d_pair.py','scripts/p011_long_d_pair_io.py','scripts/analyze_p011_long_d_pair.py']
spec=deepcopy(basis)
for name in ('prior_input_receipts','initial_allowed_jobs','original_numeric_decision'):
 spec.pop(name,None)
spec.update(delegated_D_decision_sha256='bba65b440106c9272d453f61fe719a3c0b878e497576423434ff5ec3ab819820',D_both_or_neither=True,D_F15_without_A_smoke_selection_disclosed=True,original_numeric_SPEC_file='reports/p011_20261020/long_current_runtime_v1/SPEC.json',original_numeric_SPEC_sha256='f0e9274459b17b25a9754b863ce88d4ecee5c35fe9804e3ffdd86f8ce92c522b',fullparameter_local_oracle_pending_when_prepared=False,fullparameter_original_complete_proof_sha256='b2b639c150a67a0d51be574df8e5b029083abc133b672e28d2ad4f2b0e273898',failed_attempt_bindings=deepcopy(b['failed_attempt_bindings']),prior_failed_C1=deepcopy(b['prior_failed_C1']))
spec['source_files'].update({n:sha(ROOT/n) for n in new});spec['jobs']={}
for name in ('long_D1_S-F15_s17_r1','long_D2_S-F15_s17_r1'):
 j=deepcopy(old['jobs'][name]);t=j['timing'];l=j['limits'];t['endpoint_batch_seconds']=t['endpoint_batch_seconds']+[600]
 t['D_forecast_decision_sha256']=spec['delegated_D_decision_sha256'];t['added600_endpoint_proxy_is_uncalibrated_reviewer_estimate']=True
 initial=1.2*(j['U']*max(t['training_unit_seconds'])+7*max(t['endpoint_batch_seconds'])+t['future_allowance_seconds'])
 worker=int((Decimal(str(initial))*Decimal('1.10')/100).to_integral_value(rounding=ROUND_CEILING)*100)
 l['worker_seconds']=worker;l['platform_seconds']=worker+60;l['full_result_window_seconds']=l['startup_seconds']+l['platform_seconds']+l['closeout_seconds']
 l['reserved_usd']=str(((Decimal(l['startup_seconds']+l['platform_seconds']))*Decimal(l['hourly_rate_usd'])/3600).quantize(Decimal('.01'),rounding=ROUND_CEILING))
 spec['jobs'][name]=j
save('SPEC.json',spec)
save('PREPARATION_PROVENANCE.json',dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),original_D_job_source_commit='99508f316768237185479fbfa660850ea4ed5c0f',original_SPEC_sha256=spec['original_numeric_SPEC_sha256'],old55source_map_reused_without_reverification=True,new_source_count=7,complete_source_count=len(spec['source_files']),new_model_calls=0,new_input_encoding=0,new_input_build=0,new_paid_measurement=0,original_scientific_fields_unchanged=True,original_future_allowance963_preserved=True,rough_reviewer_W7400_not_used=True,fullreserve80_gate_retained_pending_explicit_disposition=True,local_raw_training_or_endpoints_read=False))
print(json.dumps({n:j['limits'] for n,j in spec['jobs'].items()},indent=2))

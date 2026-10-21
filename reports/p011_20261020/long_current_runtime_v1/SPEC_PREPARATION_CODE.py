from pathlib import Path
from datetime import datetime,timezone
from decimal import Decimal,ROUND_CEILING
import json,copy,math,hashlib
from experiments.p011 import long_current_path as path,long_protocol,long_numeric
from experiments.sft_allocation_midpoint.common import digest
R=Path('.local/p011_20261020/r1');P=Path('reports/p011_20261020');OUT=P/'long_current_runtime_v1';assert not OUT.exists()
def rd(p):return json.loads(Path(p).read_text())
def h(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,b):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb') as f:f.write(b)
def dump(p,x):put(p,(json.dumps(x,ensure_ascii=False,indent=2,sort_keys=True)+'\n').encode())
num=rd(R/'LONG_FORMAL_ACTUAL_NUMERIC_PROJECTION.json');eng=rd(P/'long_preflight_failed_ledger_runtime_v1/SPEC.json');src=rd(P/'long_current_source_addendum_v1/SOURCE_BINDING.json');req=rd(P/'long_current_source_addendum_v1/REVIEW_REQUIREMENTS.json');manifest=rd(R/'long_inputs_numeric_gold_r1/MANIFEST.json')
readback={}
for arm in ('S-L15','S-F15','S-L3'):
 model=next(x['model'] for x in eng['jobs'].values() if x['arm']==arm);p=R/'long_preflight_io_r1/model_uploads'/model['revision']/'COMPLETED.json'
 readback[arm]=dict(path=str(p),sha256=h(p))
source_evidence={str(P/'long_preflight_measured_evidence_v1/MEASURED_SUMMARY.json'):h(P/'long_preflight_measured_evidence_v1/MEASURED_SUMMARY.json'),str(R/'LONG_FORMAL_ACTUAL_NUMERIC_PROJECTION.json'):h(R/'LONG_FORMAL_ACTUAL_NUMERIC_PROJECTION.json')}
score_old=rd(R/'B_C2_NEW_NUMERIC_PROJECTION.json')['E3_scoring_window'];scoreW=score_old['conservative_stage_to_next_dependent_stage_seconds']
assert scoreW>0
jobs={};summary={};now=datetime.now(timezone.utc)
for cell in ['baseline']+[f'A{i}' for i in range(1,9)]+['D1','D2']:
 for arm in ('S-L15','S-F15','S-L3'):
  if cell=='baseline' and arm=='S-F15':continue
  original=next(x for x in eng['jobs'].values() if x['arm']==arm);model=copy.deepcopy(original['model']);observed=num['arms'][arm]
  model['preflight_asset_readback']=readback[arm]
  model['local_audit_asset_files']={k:v for k,v in model['files'].items() if k in path.AUDIT_METADATA_NAMES}
  kind='baseline' if cell=='baseline' else 'student';category='A' if cell=='baseline' else cell[0]
  profile=num['profiles'].get(cell);U=0 if profile is None else profile['U'];B=0 if profile is None else profile['B']
  training=[] if profile is None else [v*profile['processed_ratio_to_original_preflight_update'] for v in observed['original_whole_update_seconds']]
  endpoint=[observed['linear512_request_proxy_seconds']]
  # For untrained1.5B use both same-size engineering observations and retain
  # their maximum. This remains a disclosed distribution-transfer proxy.
  if cell=='baseline' and arm=='S-L15':endpoint=[num['arms'][a]['linear512_request_proxy_seconds'] for a in ('S-L15','S-F15')]
  future=observed['uncalibrated_future_seconds']
  if cell=='baseline' and arm=='S-L15':future=max(num['arms'][a]['uncalibrated_future_seconds'] for a in ('S-L15','S-F15'))
  scenario=1.2*(U*max(training,default=0)+7*max(endpoint)+future)
  worker=math.ceil((scenario+30)/300)*300;platform=worker+60;startup=600;score=7200;closeout=3600+3600+score+5;full=startup+platform+closeout
  resources=long_protocol.resources(kind,arm);rates=copy.deepcopy(original['resource_rates_usd_per_hour'])
  hourly=Decimal(str(rates['H100']))+4*Decimal(str(rates['cpu_core']))+Decimal(resources['memory_mib'])/1024*Decimal(str(rates['GiB']))
  reserve=(hourly*Decimal(startup+platform)/3600).quantize(Decimal('.01'),rounding=ROUND_CEILING)
  local={n.removeprefix(cell+'/'):v for n,v in manifest.items() if n.startswith(cell+'/')}
  inputs={n:v for n,v in local.items() if n!='ENDPOINT_LOCAL.json'}
  job=dict(kind=kind,cell=cell,arm=arm,category=category,seed=17,B=B,U=U,context=original['context'],endpoint_count=3300,eos_token_ids=[151645,151643],input_directory=cell,model=model,input_files=inputs,local_input_files=local,resources=resources,resource_rates_usd_per_hour=rates,
   limits=dict(worker_seconds=worker,platform_seconds=platform,startup_seconds=startup,closeout_seconds=closeout,score_seconds=score,full_result_window_seconds=full,artifact_max_bytes=50_000_000_000,hourly_rate_usd=str(hourly),reserved_usd=str(reserve)),
   timing=dict(training_unit_seconds=training,endpoint_batch_seconds=endpoint,future_allowance_seconds=future,source_evidence_files=source_evidence,whole_iteration_scope_accepted=True,scope_acceptance_is_candidate_pending_independent_review=True,formal512_throughput_measured=False,no_speed_or_cost_guarantee=True,training_processed_token_ratio=None if profile is None else profile['processed_ratio_to_original_preflight_update']))
  if kind=='student':job['input_plan_sha256']=digest(rd(R/'long_inputs_numeric_gold_r1'/cell/'plan.json'))
  name=path.logical(job);jobs[name]=job
  summary[name]=dict(initial_worker_scenario_seconds=scenario,reserved_usd=str(reserve),worker_seconds=worker,full_result_window_seconds=full,latest_dispatch_utc=datetime.fromtimestamp(path.CUTOFF-full,timezone.utc).isoformat(),category=category,score_hard_seconds_candidate=score,whole_score_proxy_seconds=1.2*scoreW*(3300/3200)*10,score_proxy_not_a_bound=True)
spec=dict(original_plan_commit=eng['original_plan_commit'],source_files=req['source_files'],jobs=jobs,measurement_exceptions=0,budget_owner_decision_sha256=path.BUDGET_OWNER_SHA,prior_failed_C1=eng['prior_failed_C1'],failed_attempt_bindings=eng['failed_attempt_bindings'],actual_input_directory=path.LOCAL_INPUT_DIRECTORY,actual_input_binding_sha256=rd(P/'long_current_source_addendum_v1/SOURCE_BINDING.json')['actual_input_binding_sha256'],result_cutoff_epoch=path.CUTOFF,
 formal_source_CR_accepted_report_sha256='83d5d8c9a4ad6e63afb9b15a51be2261843c242978ae88b0f9e112782b6830e5',engineering_actual_packet_target='fdf8bd86c5113c1f716ab749d24f4f2a9faaf8ac',fullparameter_local_oracle_pending_when_prepared=True,full_three_arm_measurement_review_accepted=False,operational_score_window_candidate_requires_exact_numeric_acceptance=True,original_scientific_smoke_selection_rule_unchanged=True)
path.validate(spec)
initial=['long_A7_S-L3_s17_r1','long_A7_S-L15_s17_r1','long_A7_S-F15_s17_r1','long_baseline_S-L3_s17_r1','long_baseline_S-L15_s17_r1'];prior=Decimal('5.95');initialproof=[]
for name in initial:
 job=jobs[name];p=path.policy(job,1,str(prior));result=long_numeric.forecast(p,job['U'],7,[],[],1);initialproof.append(dict(job=name,prior_A_reserved_usd=str(prior),forecast=result));prior+=Decimal(job['limits']['reserved_usd'])
mandatory={}
for arm in ('S-L15','S-F15','S-L3'):
 names=['long_'+c+'_'+arm+'_s17_r1' for c in ('A1','A5','A6')]
 total=prior+sum(Decimal(jobs[n]['limits']['reserved_usd']) for n in names)
 mandatory[arm]=dict(mandatory_remaining_cells=names,prospective_total_A_reservations_usd=str(total),remaining_after_initial5_usd=str(115-prior),whole_mandatory_campaign_fit_under_current_unreleased_reservations=total<=115)
OUT.mkdir();dump(OUT/'SPEC.json',spec)
dump(OUT/'NUMERIC_PROJECTION.json',dict(created_utc=now.isoformat(),per_job=summary,initial5_sequential_forecast=initialproof,initial_A_after5_reserved_usd=str(prior),mandatory_remainder=mandatory,all_failed_reservations_retained=True,completed_reserves_not_released=True,plan7_4_trigger=True,delegated_disposition_required_before_initial_paid_stage=True,uncalibrated_proxy_not_guarantee=True,score_interval_source=score_old,score_window7200_is_new_A_D_candidate_not_B_permission=True))
put(OUT/'ORIGINAL_INPUT_UPDATE_PROFILE.json',(R/'LONG_FORMAL_ACTUAL_NUMERIC_PROJECTION.json').read_bytes())
dump(R/'LONG_CURRENT_SPEC_VALIDATION_DONE.json',dict(created_utc=now.isoformat(),spec_sha256=h(OUT/'SPEC.json'),new_concrete32_job_configuration_validation_pass=True,new_model_calls=0,new_scoring_calls=0,original_input_reconstruction=False,full_A2_accepted=False,mandatory_budget_disposition_pending=True))
print(json.dumps({'jobs':len(jobs),'initial5_reserved_A':str(prior),'mandatory_remainder':mandatory,'initial5':{n:summary[n] for n in initial}}))

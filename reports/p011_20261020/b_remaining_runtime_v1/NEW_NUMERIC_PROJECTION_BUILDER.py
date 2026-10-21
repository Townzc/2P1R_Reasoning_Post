"""New prospective budget/timing projection; never runs old science or scoring."""
from pathlib import Path
from datetime import datetime, timezone
from decimal import Decimal, ROUND_CEILING
import hashlib,json

R=Path('.local/p011_20261020/r1'); O=Path('.local/p010_20261019/r1')
OUT=R/'B_C2_NEW_NUMERIC_PROJECTION.json'
assert not OUT.exists()
sources={}
def load(p):
    p=Path(p); raw=p.read_bytes(); sources[str(p)]=hashlib.sha256(raw).hexdigest()
    return json.loads(raw)
def cent(x):return Decimal(x).quantize(Decimal('.01'),rounding=ROUND_CEILING)
billing=Path(load(R/'LATEST_LONG_PREFLIGHT_BILLING_DIRECTORY.json')['directory'])
rates=load(billing/'rates.json')
rate=Decimal(rates['gpu_hour_cost_h100'])+4*Decimal(rates['cpu_hour_cost'])+32*Decimal(rates['mem_gib_hour_cost'])
old=load('reports/p010_20261019/e9_runtime_v1/SPEC.json')
trainmax=max(old['timing']['training_seconds']);old_ep_max=max(old['timing']['endpoint_seconds'])
training=[];cycles=[];missing=[]
for root in sorted((O/'student_exports').glob('*/evidence')):
    p=root/'TRAINING_PROCESS_RESULT.json'
    if p.exists():
        tr=load(p); assert len(tr['block_seconds'])==64
        training.append(dict(run=root.parent.name,count=64,max_seconds=max(tr['block_seconds'])))
        trainmax=max(trainmax,max(tr['block_seconds']))
    for a in sorted((root/'eval_intents').glob('*/0000.json')):
        b=a.with_name('0256.json'); x,y=load(a),load(b)
        assert len(x['rows'])==256 and len(y['rows'])==244
        assert x['evaluation']==y['evaluation']
        duration=y['epoch']-x['epoch'];assert duration>0
        cycles.append(dict(source=str(a),next_intent=str(b),run=root.parent.name,evaluation=x['evaluation'],
            first_epoch=x['epoch'],next_epoch=y['epoch'],full256_intent_to_next_intent_seconds=duration))
for root in sorted((O/'existing_s1_sample_exports').glob('*/evidence')):
    for a in sorted((root/'eval_intents').glob('*/0000.json')):
        b=a.with_name('0256.json'); x,y=load(a),load(b)
        assert len(x['rows'])==256 and len(y['rows'])==244
        duration=y['epoch']-x['epoch'];assert duration>0
        cycles.append(dict(source=str(a),next_intent=str(b),run=root.parent.name,evaluation=x.get('evaluation'),
            first_epoch=x['epoch'],next_epoch=y['epoch'],full256_intent_to_next_intent_seconds=duration))
assert len(training)==11 and len(cycles)>=55
cyclemax=max(v['full256_intent_to_next_intent_seconds'] for v in cycles)
epmax=max(cyclemax,old_ep_max)
forecast=1.2*(64*trainmax+10*epmax+600)
old_reserve=cent(Decimal(5160)*rate/3600)
c2= dict(delegated_decision_sha256=load(R/'C2_FAILED_INPUT_DELEGATED_DECISION.json')['report_sha256'],
    C_cap_usd='12',retained_C1_both_attempts_usd='6.38',remaining_usd='5.62',
    existing_supported_student_worker_seconds=4500,platform_seconds=4560,startup_seconds=600,
    one_student_reserve_usd=str(old_reserve),even_zero_generation_first_student_80percent_usd=str(Decimal('.8')*Decimal('5.62')),
    existing_supported_limits_feasible=False,decision='CLOSE_C2_NO_GENERATION_OR_STUDENTS',
    scope='Existing supported and audited limits; not a mathematical impossibility under arbitrary future runtimes.',
    original_8_null_scores_preserved=True,new_repair_or_scoring_or_model_calls=0)
e3intent=load(O/'e3_scores_r1/INTENT.json')
e3next=load(O/'e3_metrics_r1/INTENT.json')
e3complete=load(O/'e3_scores_r1/job/COMPLETED.json')
e3payload=load(O/'e3_scores_r1/job/payload/COMPLETED.json')
w=(datetime.fromisoformat(e3next['utc'])-datetime.fromisoformat(e3intent['utc'])).total_seconds()
assert w>0 and e3payload['outputs']==3200
feasible=[]
for hard in range(1,4501):
    reserve=cent(Decimal(hard+60+600)*rate/3600)
    remaining=Decimal('20')-Decimal('3.01')-Decimal('3.01')
    first=reserve<=Decimal('.8')*remaining
    second=reserve<=Decimal('.8')*(remaining-reserve)
    if forecast<=hard-30 and first and second:feasible.append(dict(worker_seconds=hard,platform_seconds=hard+60,reserve_usd=str(reserve)))
value=dict(created_utc=datetime.now(timezone.utc).isoformat(),hourly_rate_usd=str(rate),source_files=sources,
    no_old_models_encoding_scoring_statistics_rerun=True,C2=c2,
    B=dict(delegated_decision_sha256=load(R/'B_FAILED_GENERATION_DELEGATED_DECISION.json')['report_sha256'],
        historical_training_max_retained_seconds=trainmax,historical_endpoint_body_or_cycle_max_retained_seconds=old_ep_max,
        added_original_training_receipt_summaries=training,new_full256_intent_intervals=cycles,
        full256_interval_count=len(cycles),full256_max_seconds=cyclemax,selected_endpoint_proxy_seconds=epmax,
        initial_complete_worker_scenario_seconds=forecast,setup_allowance_uncalibrated_seconds=600,margin=1.2,
        original_worker_reserve_usd=str(old_reserve),old_B_failed_reserve_usd='3.01',candidate_continuation_reserve_usd='3.01',
        feasible_integer_worker_limits_for_two_students=feasible,
        actual_new_SPEC_selected=False,actual_new_A2_accepted=False,calibrated_upper_bound=False,
        caveats=['UTC intent-to-next-intent intervals include the previous first256 batch commits and next-loop work; final244 intervals are not measured by this projection.',
        'The full256 proxy is used for both256 and244 batches, without claiming a bound on future prompts/hosts.',
        'New remote acknowledgment/store and code-transfer overhead have not been separately calibrated.',
        'Original slow/failed-host maximum proxies are retained; original training timings are not new measurements.']),
    E3_scoring_window=dict(original_declared_intent_utc=e3intent['utc'],next_dependent_metrics_intent_utc=e3next['utc'],
        conservative_stage_to_next_dependent_stage_seconds=w,criterion_seconds=360,criterion_met=w<=360,
        two_times_W_times10_seconds=2*w*10,new_candidate_scoring_seconds=7200,
        child_lifetime_with_startup_seconds=e3complete['child_lifetime_with_startup_seconds'],
        elapsed_before_final_proof_seconds=e3payload['elapsed_before_final_proof_seconds'],
        includes_gap_before_next_stage=True,wall_clock_interval_not_monotonic_measurement=True,
        no_old_scoring_rerun=True,new_6400_runtime_not_guaranteed=True))
with OUT.open('x') as f:json.dump(value,f,indent=2,sort_keys=True);f.write('\n')
print(json.dumps(dict(path=str(OUT),C2=c2['decision'],B_full_cycle_max=cyclemax,B_scenario=forecast,
    feasible_student_limit_count=len(feasible),feasible_min=feasible[0] if feasible else None,
    feasible_max=feasible[-1] if feasible else None,E3_W=w)))

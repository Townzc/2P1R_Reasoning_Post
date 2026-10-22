"""New technical T5/T6 metadata tables from saved aggregates only; no science."""
from pathlib import Path
import csv,hashlib,json,datetime,io
R=Path('.local/p011_20261020/r1');ROOT=Path('reports/p011_20261020');OUT=ROOT/'technical_numeric_handoff_v1';assert not OUT.exists()
read=lambda p:json.loads(Path(p).read_text())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
sources={};tables={};bindings={}
def source(name):
 p=ROOT/name;v=read(p);sources[str(p)]={'sha256':sha(p),'bytes':p.stat().st_size};return v
def table(name,rows):
 assert rows;fields=list(rows[0]);assert all(list(r)==fields for r in rows)
 b=io.StringIO(newline='');w=csv.DictWriter(b,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(rows);tables[name]=b.getvalue()
 # A new table's own readback, not a repeated scientific calculation.
 assert len(list(csv.DictReader(io.StringIO(tables[name]))))==len(rows)
owner=source('owner150_complete_actual_results_v1/SAVED_SCORES_AND_CONTRASTS.json');stops=source('owner150_complete_actual_results_v1/ENDPOINT_STOP_COUNTS.json');b=source('b_students_complete_results_v1/SAVED_RESULTS.json');c=source('c1_r2_complete_results_v1/DESCRIPTIVE_SUMMARY.json');clean=source('fallback_clean_complete_results_v1/SAVED_RESULTS.json');clean_contrasts=source('fallback_clean_complete_results_v1/RESULTS.json')
rows=[]
for name,v in owner['successful_attempts'].items():
 for endpoint,z in v['completed_score_proof']['endpoints'].items():
  rows.append(dict(attempt=name,cell=v['cell'],endpoint=endpoint,correct=z['correct'],total=z['total'],saved_rate=z['mean_pass_at_one'],completion='complete_original_worker',source_file='owner150_complete_actual_results_v1/SAVED_SCORES_AND_CONTRASTS.json',source_pointer=f'/successful_attempts/{name}/completed_score_proof/endpoints/{endpoint}'))
for name,v in owner['owner_authorized_scoped_results'].items():
 for endpoint,z in v['completed_score_proof']['endpoints'].items():
  rows.append(dict(attempt=name,cell='D2',endpoint=endpoint,correct=z['correct'],total=z['total'],saved_rate=z['mean_pass_at_one'],completion='failed_worker_complete_owner_authorized_MATH_AIME_scope',source_file='owner150_complete_actual_results_v1/SAVED_SCORES_AND_CONTRASTS.json',source_pointer=f'/owner_authorized_scoped_results/{name}/completed_score_proof/endpoints/{endpoint}'))
 rows.append(dict(attempt=name,cell='D2',endpoint='amc23_sample',correct='',total='',saved_rate='',completion='incomplete_92_raw_228_missing_no_decode_score_or_accuracy',source_file='owner150_complete_actual_results_v1/SAVED_SCORES_AND_CONTRASTS.json',source_pointer=f'/owner_authorized_scoped_results/{name}/amc23'))
table('T5_A_D_saved_endpoint_scores.csv',rows)
rows=[]
for name,v in owner['all_available_original_contrasts'].items():
 z=v['summary']
 if v.get('scope')=='MATH500_only_owner_option_a':
  # Separate saved D2 scoped contrasts are copied below, without touching the bootstrap function.
  continue
 z=z['primary'];rows.append(dict(contrast=name,metric='math500_sample',difference_pp=z['difference_pp'],ci_low_pp=z['ci95_pp'][0],ci_high_pp=z['ci95_pp'][1],draws=z['resamples'],bootstrap_seed=z['seed'],training_seed_population=False,source_file='owner150_complete_actual_results_v1/SAVED_SCORES_AND_CONTRASTS.json',source_pointer=f'/all_available_original_contrasts/{name}/summary/primary'))
table('T5_A_saved_paired_contrasts.csv',rows)
# Preserve the complete already-published D2 sampled/greedy summary as JSON rather than assuming a new schema.
for name,v in owner['owner_authorized_scoped_results'].items():tables['T5_D1_D2_saved_MATH_contrasts.json']=json.dumps(v['math_only_comparison'],indent=2,ensure_ascii=False)+'\n'
rows=[]
for name,v in stops['jobs'].items():
 for endpoint,z in v['endpoints'].items():rows.append(dict(attempt=name,endpoint=endpoint,**z,source_file='owner150_complete_actual_results_v1/ENDPOINT_STOP_COUNTS.json',source_pointer=f'/jobs/{name}/endpoints/{endpoint}'))
table('T5_A_saved_endpoint_stops.csv',rows)
rows=[]
for group,saved in [('B',b),('fallback_clean',clean)]:
 for name,z in saved['original_score_summaries'].items():
  rows.append(dict(group=group,attempt=name,metric='greedy',correct=z['endpoints']['greedy']['correct'],total=z['endpoints']['greedy']['total'],saved_rate=z['greedy_accuracy'],source_file=('b_students_complete_results_v1' if group=='B' else 'fallback_clean_complete_results_v1')+'/SAVED_RESULTS.json',source_pointer=f'/original_score_summaries/{name}'))
  rows.append(dict(group=group,attempt=name,metric='sampled_mean_pass_at_1',correct=z['sampled_correct'],total=z['sampled_outputs'],saved_rate=z['sampled_mean_pass_at_1'],source_file=('b_students_complete_results_v1' if group=='B' else 'fallback_clean_complete_results_v1')+'/SAVED_RESULTS.json',source_pointer=f'/original_score_summaries/{name}'))
table('T6_B_and_clean_saved_scores.csv',rows)
rows=[]
for name in ['greedy_CONTRASTS.json','sampled_mean_pass_at_1_CONTRASTS.json']:
 z=source('b_students_complete_results_v1/'+name)
 for i,v in enumerate(z['contrasts']):rows.append(dict(metric=z['metric'],contrast=v['name'],difference_pp=v['difference_pp'],ci_low_pp=v['pointwise95_ci_pp'][0],ci_high_pp=v['pointwise95_ci_pp'][1],draws=z['draws'],bootstrap_seed=z['seed'],source_file='b_students_complete_results_v1/'+name,source_pointer=f'/contrasts/{i}'))
table('T6_B_saved_paired_contrasts.csv',rows)
rows=[]
for i,z in enumerate(clean_contrasts):
 for j,v in enumerate(z['new_contrasts']):rows.append(dict(nominal_P=z['nominal_P'],actual_P_cov=z['actual_P_cov'],metric=z['metric'],contrast=v['name'],difference_pp=v['difference_pp'],ci_low_pp=v['question_paired95_ci_pp'][0],ci_high_pp=v['question_paired95_ci_pp'][1],draws=z['draws'],bootstrap_seed=z['seed_bootstrap'],training_seed=z['seed'],source_file='fallback_clean_complete_results_v1/RESULTS.json',source_pointer=f'/{i}/new_contrasts/{j}'))
table('T6_clean_saved_paired_contrasts.csv',rows)
rows=[]
for group,v in c['groups'].items():
 for role,z in v.items():
  q=z.get('answer_mean_nll_quantiles');rows.append(dict(group=group,role=role,answers=z['answers'],supervised_tokens=z['supervised_tokens'],token_weighted_nll=z['token_weighted_nll'],perplexity=z['perplexity'],answer_median_nll=q['0.5'] if q else None,answer_max_nll=q['1.0'] if q else None,descriptive_only=True,source_file='c1_r2_complete_results_v1/DESCRIPTIVE_SUMMARY.json',source_pointer=f'/groups/{group}/{role}'))
table('T6_C1_saved_descriptive_NLL.csv',rows)
tables['SAVED_POSTHOC_SMOKE.json']=json.dumps(owner['posthoc_smoke'],indent=2)+'\n'
tables['MISSING_AND_FAILED_CELLS.json']=json.dumps({'failed_attempts':owner['failed_attempts'],'unavailable_pairs':owner['unavailable_pairs'],'optional_not_run':['A4','A3','A2','A8'],'B2':'NOT_RUN_BUDGET_CUT','C2':'CLOSED_BY_DELEGATED_BUDGET_DECISION_NO_REPAIR_GENERATION_OR_STUDENT','D2_original_worker_failed_but_owner_scoped_MATH_AIME_complete':True},indent=2,ensure_ascii=False)+'\n'
tables['REVIEW_AND_USE_LIMITS.json']=json.dumps({'recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'owner_A_actual_A3':'pending_exact_fe82972a_request','D1_D2_numerical_A3':'PASS_c999e0d8_explicit_access_timing_single_seed_clarification_pending','B_actual_A3':'PASS_WITH_NOTES_9e7c2444_original1031_retained_separate1029_sensitivity','C1_actual_A3':'PASS_47e80292_report78aa1aa8','fallback_actual_A3':'PASS_WITH_NOTES_c420555f_original1009_retained_separate1008_sensitivity','P010_final_A5':'CLOSED_NOT_REOPENED','this_is_final_05UTC_freeze':False,'this_is_final_P011_A5':False,'interpretation_written':False,'no_new_statistics_or_decode_or_score':True,'original_missing_D2_endpoint_cycle_array':True,'private_binary_external_access_claimed':False,'single_training_seed_population_claim':False,'conditional_termination_causal_mediation_claim':False,'future_freeze_must_copy_later_exact_review_acceptances_as_separate_records':True},indent=2)+'\n'
OUT.mkdir()
for name,text in tables.items():
 with (OUT/name).open('x') as f:f.write(text)
(OUT/'README.md').write_text('''# P011 technical numeric handoff — pre-freeze, not course prose

T5 and T6 copy saved aggregate scores, contrasts and descriptive NLL fields. Every CSV row includes a source JSON path/pointer; SOURCE_BINDINGS contains the exact input hashes. The original fixed source commit for these files is91b65ec11e5a3729078790fb76c2836243dbe0f0 (owner result packet targetfe82972a952a151d14d63dd052f00502560ff9c9). No model, decoder, scorer, bootstrap, original statistics, old archive or renderer was rerun.

D2 remains a failed worker with owner-authorized complete MATH/AIME scope; AMC92raw/228missing has blank metrics and no accuracy, comparison or zero-fill. Missing optional cells remain NOT_RUN. A7's original posthoc smoke failed; all outcomes are retained. Conditional question intervals do not estimate training-seed population uncertainty. Frozen-scorer sensitivities are separate notes, not rewritten original labels or intervals. Course interpretation belongs to the owner.

This is an early technical handoff, not the05UTC formal freeze or finalA5. At the real cutoff, copy these original bytes together with later exact review acceptance/disclosure records; do not rebuild these tables. A3 and finalA5 statuses are represented separately.
''')
with (OUT/'SOURCE_BINDINGS.json').open('x') as f:json.dump({'source_commit':'91b65ec11e5a3729078790fb76c2836243dbe0f0','files':sources,'table_creation_no_science_recompute':True},f,indent=2);f.write('\n')
with (OUT/'MANIFEST.json').open('x') as f:json.dump({p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(OUT.iterdir())},f,indent=2);f.write('\n')
with (R/'P011_TECHNICAL_HANDOFF_BUILD_DONE.json').open('x') as f:json.dump({'finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'packet':str(OUT),'files':len(list(OUT.iterdir())),'table_readback_once':True,'no_science_repeated':True,'not_formal_freeze_or_A5':True},f,indent=2)
print((R/'P011_TECHNICAL_HANDOFF_BUILD_DONE.json').read_text())

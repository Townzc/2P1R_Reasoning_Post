from pathlib import Path
from datetime import datetime,timezone
import ast,hashlib,json,shutil,tarfile,io,subprocess
R=Path('.local/p011_20261020/r1');P=Path('reports/p011_20261020/b_generation_runtime_v1')
assert not P.exists(),'create once; preserve partial'
def h(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def write(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x') as f:f.write(x if isinstance(x,str) else json.dumps(x,ensure_ascii=False,indent=2,sort_keys=True)+'\n')
now=datetime.now(timezone.utc).isoformat();P.mkdir()
obs=read(R/'B_ORIGINAL_COMPLETE_CYCLE_TIMING_OBSERVED.json')
original=Path('.local/p010_20261019/r1/teacher_t15_export_r1/evidence')
oldsource='experiments/p010/teacher_runtime.py'
assert subprocess.check_output(['git','show',obs['original_execution']+':'+oldsource])==Path(oldsource).read_bytes()
members=sorted([*('intents/'+p.name for p in (original/'intents').glob('*.json')),
                *('acks/'+p.name for p in (original/'acks').glob('*.json')),'RESULT.json'])
archive=P/'original_t15_complete_cycle_metadata.tar.gz';inventory={}
with tarfile.open(archive,'w:gz') as tar:
 for n in members:
  data=(original/n).read_bytes();inventory[n]={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
  t=tarfile.TarInfo(n);t.size=len(data);t.mode=0o644;t.mtime=0;tar.addfile(t,io.BytesIO(data))
with tarfile.open(archive,'r:gz') as tar:
 assert sorted(tar.getnames())==members
 for t in tar:
  data=tar.extractfile(t).read();assert hashlib.sha256(data).hexdigest()==inventory[t.name]['sha256']
write(P/'TIMING_ARCHIVE_READBACK.json',{'original_members':inventory,'archive_bytes':archive.stat().st_size,'archive_sha256':h(archive),'all_original_member_bytes_equal':True,'old_raw_outputs_or_scores_copied':False})
(P/'TIMING_OBSERVATION.json').write_bytes((R/'B_ORIGINAL_COMPLETE_CYCLE_TIMING_OBSERVED.json').read_bytes())
owner=read(R/'OWNER_BUDGET_GPU_PREFLIGHT_REPORTED_DECISION.json')
write(P/'OWNER_ACCOUNTING_BINDING.json',{k:owner[k] for k in ('report_commit','report_git_path','report_sha256','git_event_utc','full_read_confirmed_utc','authorization_source')})
entries=['experiments/p011/modal_b_current.py','scripts/p011_b_current_io.py','scripts/prepare_p011_b_runtime_inputs.py','scripts/analyze_p011_b.py']
queue=list(entries);sources={}
while queue:
 name=queue.pop()
 if name in sources:continue
 p=Path(name);sources[name]=h(p);package=list(p.parent.parts)
 for ancestor in p.parents:
  q=ancestor/'__init__.py'
  if str(ancestor)!='.' and q.is_file() and str(q) not in sources:queue.append(str(q))
 for node in ast.walk(ast.parse(p.read_text())):
  modules=[]
  if isinstance(node,ast.Import):modules=[a.name.split('.') for a in node.names]
  elif isinstance(node,ast.ImportFrom):
   stem=package[:len(package)-node.level+1] if node.level else []
   stem=stem+(node.module.split('.') if node.module else [])
   modules=[stem]+[stem+[a.name] for a in node.names if a.name!='*']
  for parts in modules:
   if not parts or parts[0] not in ('experiments','scripts','src','analyses'):continue
   q=Path(*parts)
   for f in (q.with_suffix('.py'),q/'__init__.py'):
    if f.is_file() and str(f) not in sources:queue.append(str(f))
owner_B16='reports/p011_20261020/review_d3f66ec3_B_rule_and_prereview_v1/OWNER_DECISION_B_K1_RULE.md'
for n in [owner_B16,'experiments/learning_regime_p009/requirements_p0.txt',str(P/'OWNER_ACCOUNTING_BINDING.json')]:sources[n]=h(n)
model=read('.local/p010_20261019/r1/T15_ASSETS.json')
model['local_path']='.local/midpoint_20261011/teacher_pilot_preparation/tokenizer'
model['remote_path_producer']='experiments/sft_allocation_midpoint/modal_assets.py::fetch -> /evidence/{campaign_id}/assets/model; original verified campaign mp-teacher-cost-20261012-r1'
model['producer_binding_files']={n:h(n) for n in ['experiments/sft_allocation_midpoint/modal_assets.py','.local/midpoint_20261011/teacher_pilot_r1/ASSETS_VERIFIED.json','.local/p010_20261019/r1/T15_ASSETS.json']}
# Existing small local tokenizer/config files serve the NEW oracle binding. The
# old weights are neither downloaded nor rehashed; remote transfer is readback reuse.
local_model={}
for n,v in model['files'].items():
 p=Path(model['local_path'])/n
 if p.is_file():
  assert p.stat().st_size==v['bytes'] and h(p)==v['sha256'],n
  local_model[n]=v
assert 'config.json' in local_model and 'tokenizer.json' in local_model
write(P/'MODEL_PRODUCER_BINDING.json',{'model':model,'existing_local_small_files_for_new_oracle':local_model,'old_weights_rehashed_or_downloaded':False,'remote_closed_provider_queried':False})
inv=read(R/'b_generation_inputs_r1/MANIFEST.json');inv=inv.get('files',inv)
timing={'source_evidence_files':{str(P/n):h(P/n) for n in ['TIMING_OBSERVATION.json','TIMING_ARCHIVE_READBACK.json']},
 'whole_iteration_scope_accepted':True,'training_cycle_seconds':[],
 'batch_cycle_seconds':[v['seconds'] for v in obs['all_complete_full_batch_intervals']],
 'future_allowance_seconds':600,'candidate_flag_requires_exact_A2':'whole_iteration_scope_accepted is proposed scope, not a claimed existing review',
 'basis_kind':'all23 original full256 intent-to-next-intent epoch intervals; includes all original commits/store/symbolic scoring; not new_B measurement',
 'temperature_change':'.8 to1.0; same native cap1024/context2048/engine256','guarantee_or_upper_bound':False}
job={'kind':'generation','run_id':'generation','category':'B','owner_B16_sha256':h(owner_B16),'input_directory':'generation',
 'input_files':{'GPU_PACK.json':inv['GPU_PACK.json']},'local_input_files':{n:inv[n] for n in ('GPU_PACK.json','PACK.json')},
 'config':None,'model':model,'timing':timing,'resources':{'gpu':'H100','cpu':4,'memory_mib':32768},
 'resource_rates_usd_per_hour':{'H100':'3.95','cpu_core':'.04730','GiB':'.008'},
 'limits':{'worker_seconds':1800,'platform_seconds':1860,'startup_seconds':600,'score_seconds':62000,
  'closeout_seconds':69205,'full_result_window_seconds':71665,'artifact_max_bytes':10_000_000_000,
  'hourly_rate_usd':'4.39520','reserved_usd':'3.01'}}
spec={'phase':'generation','original_plan_commit':'e0dee182972f9910b707fac68800dcb5a3aff2d3','source_files':dict(sorted(sources.items())),
 'budget_owner_decision_sha256':owner['report_sha256'],'measurement_exceptions':0,'result_cutoff_epoch':1792645200,
 'prior_failed_C1':read('reports/p011_20261020/c1_r2_runtime_v1/SPEC.json')['prior_failed_C1'],
 'jobs':{'B_generation_t10_400x16_r1':job}}
write(P/'SPEC.json',spec)
from experiments.p011 import b_current_path as path,b_numeric
path.validate(spec)
forecast=b_numeric.forecast(path.policy(job,1,'0'),0,25,[],[],1)
write(P/'NUMERIC_SCENARIO.json',{'initial_forecast':forecast,'actual_new_reserved_usd':'0','historical_rate_observed_utc':'2026-10-21T04:46:44Z',
 'fresh_rate_and_D1_required':True,'max_observed_complete_batch_seconds':obs['max_complete_full_batch_seconds'],
 'old_setup_through_first_intent_seconds':obs['setup_through_first_intent_seconds'],
 'score_scenario_seconds':61800,'score_scenario_definition':'1.2*(6400*8+300), unchanged2worker/8souter pairs; scenario not guarantee',
 'collect_and_audit_allowance_each_seconds':3600,'whole_score_cleanup_seconds':5,
 'latest_dispatch_utc':'2026-10-21T09:05:35Z','remaining_B_students_not_admitted':True})
write(P/'SOURCE_BINDING.json',{'source_files':spec['source_files'],'spec_sha256':h(P/'SPEC.json'),
 'original_B_source_target':'bca90236c7be2c2b37f3a207eb23d1f518027290',
 'original_B_source_files_unchanged':True,'entry_files':entries,'narrow_new_source':['experiments/p011/b_current_path.py','experiments/p011/modal_b_current.py','scripts/p011_b_current_io.py'],
 'actual_generation_input_target':'1d0d1d6d1ede001949c64d3675b214ecf2feb5f7','actual_input_A1_report_sha256':'c994da9ca61385a8b55d0e95c202e6cae62ad3a9d4acbbffc73ab7bd5b6be9d4',
 'owner_B16_sha256':h(owner_B16),'budget_owner_decision_sha256':owner['report_sha256']})
shutil.copyfile(R/'b_current_admission_new_checks_r1.log',P/'NEW_CHECKS.log')
write(P/'REVIEW_REQUIREMENTS.json',{'request_id':'p011-B-generation-student-complete-path-CR-A1-A2-lite-r1',
 'scope':path.SCOPE,'spec_sha256':h(P/'SPEC.json'),'source_files':spec['source_files'],
 'jobs_sha256':__import__('experiments.sft_allocation_midpoint.common',fromlist=['digest']).digest(spec['jobs']),
 'original_plan_commit':spec['original_plan_commit'],'owner_B16_sha256':h(owner_B16),
 'budget_owner_decision_sha256':owner['report_sha256'],'measurement_exceptions':0,
 'true_flags':['complete_source_closure_accepted','complete_actual_input_A1_accepted','original_P010_tokens_seeds_dose_and_endpoint_rules_unchanged',
 'all_original_complete_timing_sources_accepted','full_state_raw_scoring_window_and_budget_accepted','remote_paths_traced_to_producers',
 'owner_B16_selection_and_actual_Pcov_accepted','current_owner_accounting_and_saved_failed_parent_accepted','original_complete_cycle_interval_proxy_accepted'],
 'source_only_PASS_does_not_authorize_paid_entry':True,'generation_only_SPEC_not_student_permission':True})
write(P/'FUTURE_COMMANDS.md','''# Conditional generation-only commands — NOT RUN

Only after true exact source/current-owner/actual A1/numeric A2-lite and fresh full
rates plus D1 permit the original full71665-second result window, no later than
Oct21 09:05:35UTC:

```sh
P011_B_PHASE=generation PYTHONPATH=. .local/midpoint_20261011/venv/bin/python scripts/p011_b_current_io.py upload --job B_generation_t10_400x16_r1 --review REVIEW
P011_B_PHASE=generation PYTHONPATH=. .local/midpoint_20261011/venv/bin/modal run -m experiments.p011.modal_b_current --job-id B_generation_t10_400x16_r1 --review-json REVIEW --budget-json BUDGET
```

Original complete result plus actual STOPPED0: once `collect`, then `audit` using
data_pipeline Python, then `score` using math_verify_env Python, same job/review
arguments and original absolute workerstart+1800+69205 closeout. The scorer child
is bounded62000+5 with the frozen two-worker8-second outer pair contract. No old
teacher output is decoded/scored again. Unknown/partial/failure is preserved;
never repeat the model or whole helper. Subsequent B1–B3 input/actual A1/numeric
SPECs remain required; generation admission alone never allows student training.
''')
write(P/'README.md',f'''# B generation concrete numeric candidate and narrow accounting revision

Prepared {now}. Exact{len(sources)}source entries; originalB71sources unchanged.
Three new wrapper files adopt currentownerprotected0/full resource rates and saved
C1r1 failed-parent STOPPED0. Original model/generation/student/scoring bodies remain
unchanged (AST parity checked). Six new checks passed once; old tests not rerun.
OriginalB400parent/6400request input A1 genuinely PASS in Claude135a4f53 reportc994.
No actual B model, upload or reservation has occurred.

Original teacher execution6a04af4e saved24 batch intents. The23 full256 batches
have a following intent epoch: their complete intervals include original batch
marker,3Volumecommits, generation/transport/symbolic CPU scoring, completion marker
and the next precheck/forecast. All23 are retained; maximum22.100826501846313s.
These epoch intervals differ from both oldbody13.942883893 and new Bmonotonic
wholecycles. Final52row partial is excluded from full256 basis. The first batch's
pre-intent checks are outside its interval. Original setup through first intent
was72.2804582118988s. The original fullsource byte identity at6a04af4e is checked
for this new numerical provenance, not a repeated old scientific verification.

Candidate1.2*(25*22.1008265+600)=1383.024795s fits1770worker forecast threshold.
600 is an uncalibrated allowance covering new setup/final work;20percent is a
scenario margin, not a bound. Temperature changes.8 to1.0; identical nativecap1024
andengine/context do not guarantee output lengths, host or decoding time. Removing
old in-worker symbolic scoring does not justify subtracting its time. Exact A2
must explicitly accept or reject this complete-interval proxy, including wall-clock
versus monotonic limitations. Every actual new wholecycle updates the guard.

H100+4CPU+32GiB historical rate4.3952/hour gives full2460 billed-window reserve3.01
and initialpredicted2.43. These are candidates, not fresh rates/costs/reservations.
All failed/P011 reserves remain, including C1r1 3.74. Current owner balance stays
private, is not refreshed by restating it, and is not a platform balance query.
Fresh meter/rates and accepted D1 derive availability from current owner baseline
minus retained P011 commitments and conservative meter growth, without old P010
double subtraction. Original180/categorycaps and80percent remain.

The full result window71665s includes600startup/1860platform and69205closeout:
3600collect+3600audit+62000score+5cleanup. Latestdispatch Oct21 09:05:35UTC; no
deadline reset or shortening to force admission. Scoring1.2*(6400*8+300)=61800 is
only an engineering scenario; frozen timeouts/failures are preserved. B1–B3 student
work still requires its own actual selected data and shared-path numeric appendix;
this generation SPEC cannot authorize it. The original all16 failure/Pcov rule and
fallback>10percent hold remain unchanged. No B4 or paid measurement exception.

New timing evidence archive copies49 original metadata members only; no rawoutput
or score was read, re-decoded or re-scored. Original datasets/archives and completed
input constructor are not rebuilt. Read-only guessed input-binding/producer paths
and an unmatched shell glob failed during metadata navigation; no side effects.
''')
shutil.copyfile(__file__,P/'BUILD_SCRIPT.py')
payload={str(p.relative_to(P)):{'bytes':p.stat().st_size,'sha256':h(p)} for p in sorted(P.rglob('*')) if p.is_file()}
write(P/'MANIFEST.json',payload)
write(R/'B_GENERATION_NUMERIC_CANDIDATE_PREPARED.json',{'created_utc':now,'source_count':len(sources),'spec_sha256':h(P/'SPEC.json'),'new_checks':6,'actual_SPEC_validation_done':True,'old_checks_repeated':0,'actual_new_reserved_usd':'0','timing_archive_members':len(members),'files':payload})
print(json.dumps({'source_count':len(sources),'newchecks':6,'reserve':'3.01','forecast':forecast['forecast_total_seconds'],'archive_members':len(members)}))

from pathlib import Path
from datetime import datetime,timezone
import ast,hashlib,json,shutil

R=Path('.local/p011_20261020/r1')
P=Path('reports/p011_20261020/long_preflight_source_v1')
assert not P.exists(),'create once; preserve partial'
def h(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def write(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x') as f:f.write(x if isinstance(x,str) else json.dumps(x,ensure_ascii=False,indent=2,sort_keys=True)+'\n')
now=datetime.now(timezone.utc).isoformat();P.mkdir()
owner=read(R/'OWNER_BUDGET_GPU_PREFLIGHT_REPORTED_DECISION.json')
owner_projection='reports/p011_20261020/review_3f314dac_B_CR_C1_failure_owner_records_v1/OWNER_DECISION_BUDGET_AND_GPU_PREFLIGHT_PUBLIC_PROJECTION.md'
write(P/'OWNER_BINDING.json',{**{k:owner[k] for k in ('report_commit','report_git_path','report_sha256','git_event_utc','full_read_confirmed_utc','authorization_source')},
 'public_projection':owner_projection,'public_projection_sha256':h(owner_projection),
 'preflight_jobs':3,'one_per_arm':['S-L15','S-F15','S-L3'],'maximum_total_reserved_usd':'6',
 'category':'A','formal_measurement_exceptions':0,'protected_usd':'0','balance_not_public':True,
 'original_caps_unchanged':True,'no_automatic_retry':True,
 'interpretation_limit':'Codex has not seen the underlying claude.ai conversation. Original chronology inconsistency retained; direct overnight delegation also saved separately.'})
roots=['experiments/p011/long_preflight/modal_entry.py','scripts/prepare_p011_long_preflight_inputs.py','scripts/p011_long_preflight_io.py']
files=set();queue=list(roots)
def module_files(name):
 stem=Path(*name.split('.'))
 return [str(p) for p in (stem.with_suffix('.py'),stem/'__init__.py') if p.is_file()]
while queue:
 name=queue.pop()
 if name in files:continue
 files.add(name);p=Path(name)
 for par in p.parents:
  init=par/'__init__.py'
  if str(par)!='.' and init.is_file() and str(init) not in files:queue.append(str(init))
 for n in ast.walk(ast.parse(p.read_text())):
  modules=[]
  if isinstance(n,ast.Import):modules=[v.name for v in n.names]
  elif isinstance(n,ast.ImportFrom):
   assert n.level==0,'Relative import needs explicit resolution'
   if n.module:modules=[n.module]+[n.module+'.'+v.name for v in n.names if v.name!='*']
  for m in modules:
   for q in module_files(m):
    if q not in files:queue.append(q)
files.update(['experiments/learning_regime_p009/requirements_p0.txt',str(P/'OWNER_BINDING.json')])
source={n:h(n) for n in sorted(files)}
origin=R/'long_inputs_numeric_gold_r1';inv=read(origin/'MANIFEST.json')
basis={str(origin/n):inv[n]['sha256'] for n in ['A8/encoded.json','baseline/ENDPOINT_GPU.json','baseline/ENDPOINT_LOCAL.json','COMPLETED.json']}
basis.update({str(origin/'MANIFEST.json'):h(origin/'MANIFEST.json'),
 str(R/'LONG_RUNTIME_REPAIR_SOURCE_CR_ACCEPTED.json'):h(R/'LONG_RUNTIME_REPAIR_SOURCE_CR_ACCEPTED.json'),
 str(R/'OWNER_BUDGET_GPU_PREFLIGHT_REPORTED_DECISION.json'):h(R/'OWNER_BUDGET_GPU_PREFLIGHT_REPORTED_DECISION.json')})
binding={'source_files':source,'input_basis_files':basis,'original_plan_commit':'e0dee182972f9910b707fac68800dcb5a3aff2d3',
 'owner_decision_sha256':owner['report_sha256'],
 'actual_long_input_packet':'reports/p011_20261020/long_numeric_gold_inputs_actual_v1',
 'actual_long_input_public_manifest_sha256':h('reports/p011_20261020/long_numeric_gold_inputs_actual_v1/PUBLIC_MANIFEST.json'),
 'formal_R1_R3_report_sha256':'7c67c4d4c5afd2a874f1bd3dfc3e6654f369decca35ccede67d53da65bf3ff40',
 'original_failed_C1_parent_binding':'reports/p011_20261020/c1_r2_runtime_v1/SPEC.json',
 'original_failed_C1_parent_binding_sha256':h('reports/p011_20261020/c1_r2_runtime_v1/SPEC.json')}
write(P/'SOURCE_BINDING.json',binding)
write(P/'SOURCE_CLOSURE_STATIC.json',{'roots':roots,'transitive_local_imports_and_package_initializers_included':True,
 'source_count':len(source),'source_files':source,'no_runtime_import_or_model_execution':True})
tests=['tests/test_p011_long_preflight.py','tests/test_p011_long_preflight_execution.py','tests/test_p011_long_preflight_engine_proof.py']
logs=['long_preflight_new_checks_r1.log','long_preflight_new_execution_checks_r1.log','long_preflight_new_engine_proof_r1.log']
for n in logs:shutil.copyfile(R/n,P/n)
write(P/'NEW_CHECKS.json',{'distinct_new_checks':13,'results':[{'count':9,'seconds':.325},{'count':3,'seconds':.134},{'count':1,'seconds':0.0}],
 'test_files':{p:h(p) for p in tests},'old_tests_repeated':0,'original_training_body_and_join_AST_parity_checked':True,
 'mocks_are_not_actual_GPU_timings_or_memory_proof':True})
requirements={'request_id':'p011-long-three-arm-engineering-preflight-CR-A1-A2-lite-r1',
 'initial_scope':'p011-long-three-arm-engineering-preflight-source-CR',
 'source_files':source,'input_basis_files':basis,'owner_decision_sha256':owner['report_sha256'],
 'initial_true_flags':['input_preparation_authorized','original_completed_long_inputs_accepted','engineering_subset_only'],
 'actual_long_input_A1_scope':'p011-long-A-D-complete-runtime-input-A1',
 'final_scope':'p011-long-three-arm-engineering-preflight-CR-A1-A2-lite',
 'final_true_flags':['complete_source_closure_accepted','actual_input_A1_accepted','formal_R1_R3_source_CR_accepted',
 'engineering_subset_of_formal_path_accepted','all_three_reserves_at_most6_accepted',
 'full_state_export_join_and_original_engine_accepted','original_failed_parent_retained',
 'current_owner_budget_scope_and_full_window_accepted','no_scientific_result_or_A3_A5_claim'],
 'final_binding_fields':['original_plan_commit','spec_sha256','source_files','jobs_sha256','owner_decision_sha256','measurement_exceptions','formal_repair_review_sha256'],
 'source_only_pass_cannot_upload_or_dispatch':True,'actual_SPEC_and_subset_input_A1_still_required':True}
write(P/'REVIEW_REQUIREMENTS.json',requirements)
write(P/'PROTOCOL.json',{'kind':'owner_authorized_engineering_only','arms':['S-L15','S-F15','S-L3'],
 'selection':'Two longest original A8 sequences by descending n_processed then path_id; both at least15000 and at most16384.',
 'training':{'updates':2,'schedule':[[0,1],[0,1]],'microbatch':1,'seed':17,'LR':'original arm function evaluated atU2','state_and_export':'same full state serialization/mmap verification/BF16 export; joined child exits0 before vLLM'},
 'evaluation':{'original_subset_requests':32,'per_benchmark':8,'choice':'sample0 prompt-length quantiles, one original MATHgreedy replaces shortest MATHsample','maximum_new_tokens':16384,'context':17243,'max_num_seqs':256,'max_num_batched_tokens':8192,'graph_sizes':[1,2,4,8,16,32,64,128,256],'scoring':False},
 'per_job_limits':{'worker_seconds':900,'platform_seconds':960,'startup_seconds':600,'closeout_seconds':7200,'full_result_window_seconds':8760,'latest_dispatch_utc':'2026-10-22T02:34:00Z'},
 'resources':{'S-L15':{'H100':1,'CPU':4,'GiB':32},'S-F15':{'H100':1,'CPU':4,'GiB':96},'S-L3':{'H100':1,'CPU':4,'GiB':32}},
 'historical_rate_candidate_reserves_usd':{'S-L15':'1.91','S-F15':'2.13','S-L3':'1.91','total':'5.95'},
 'historical_rate_observed_utc':'2026-10-21T04:46:44Z','fresh_rates_and_D1_required':True,
 'initial_scientific_forecast':False,'owner_measurement_exception_each':1,'formal_A_D_measurement_exceptions':0,
 'preserved_failed_reservations':{'C1r1':'3.74'},'actual_new_reserve':'0',
 'no_full512request_batch_measurement':True,'no_throughput_upper_bound_or_guarantee':True})
write(P/'FUTURE_COMMANDS.md','''# Conditional commands — PREPARED NOT RUN

Only after a real fixed initial source report with SOURCE_BINDING and all three
initial flags, including actual completed long input acceptance:

```sh
PYTHONPATH=. .local/midpoint_20261011/data_pipeline/venv/bin/python scripts/prepare_p011_long_preflight_inputs.py --review .local/p011_20261020/r1/LONG_PREFLIGHT_SOURCE_CR_ACCEPTED.json
```

The input consumer is permanent once-only; it selects saved tokens/requests without
encoding or loading a model. Its actual outputs and the concrete three-job SPEC
must then be attached to the SAME request for actual A1 and numeric A2-lite.
Fresh full resource rates and D1 accounting are required before entry. For each
original job preflight_S-L15_s17_r1, preflight_S-F15_s17_r1, preflight_S-L3_s17_r1,
only after final exact admission and sufficient original full window:

```sh
PYTHONPATH=. .local/midpoint_20261011/venv/bin/python scripts/p011_long_preflight_io.py upload --job JOB --review REVIEW
PYTHONPATH=. .local/midpoint_20261011/venv/bin/modal run -m experiments.p011.long_preflight.modal_entry --job-id JOB --review-json REVIEW --budget-json BUDGET
```

Use actual argparse names from the fixed IO file; no production CLI was invoked
to print help. After that job's original completed result and actual STOPPED0,
collect once, then audit once with data_pipeline Python in the original shared
worker-start+900+7200 absolute closeout window. The IO commands accept `collect`
and `audit`; no scoring command exists. Preserve unknown/partial/failed jobs,
never use a completed-only collector on a failure, and never whole-job retry.
''')
write(P/'README.md',f'''# Three-arm engineering preflight — complete source candidate

Prepared {now}; {len(source)} exact transitive source entries,13 distinct new checks
passed once. No subset constructor, model, forward, upload or paid call ran.
The real owner record SHA364aaf6c authorizes one bounded engineering preflight per
original arm, total reserve<=6 from A, only after exact source CR/A2-lite. Formal
R1–R3 source CR is genuinely PASS in report7c67c4d4. The original long source37
remains unchanged; new engineering code lives in its own namespace.

The actual training computation and child-join bodies are AST-identical to the
formal path, with only a separately validated2-update subset and distinct identity.
Use two longest saved A8 sequences near16k, original model/precision/optimizer/LR
function, full terminal-state serialization and mmap validation, BF16 export, then
confirmed childexit0 before the original V1engine. Full-parameter host memory is
96GiB. One32-request original representative subset spans all four benchmarks,
prompt lengths and both sample/greedy modes. The corrected engine256 geometry,
cap16384 and original17243context remain exact.

Measured records cover both complete update cycles, state/export phase commits,
model load, parent child interval, vLLM startup plus commit and the complete raw
evaluation cycle. Read-only closeout verifies all original trainable tensors,
AdamW/RNG/order/dose, export lineage, actualenginefields and every32native raw
output. No scientific correctness score or A3/A5 result is produced. A32-request
measurement does not measure formal512-request batch throughput or prove a runtime
upper bound; formal A/D numerical admission must explicitly accept or reject the
later measured extrapolation. The exception is not permission for formal A/D.

Each900worker/960platform/600startup job has a retained1560-second billed-window
reservation. Historical full rates give1.91+2.13+1.91=5.95, not a fresh quote or
actual cost. Current owner accounting/protected0 and all categorycaps/80percent
remain. All prior failed/pending/unknown/unmatched slots and reservations stay;
saved C1r1 STOPPED0 is reused through the exact parent adapter. No closed C1 call
is queried. Sharedmax4 and immutable upload/dispatch/claim/unit fences block replay.
The same original absolute full closeout window is enforced, never reset per tool.

Source-only CR first authorizes a single saved-token subset consumer. Its actual
input A1 and concrete SPEC/numeric review are subsequent evidence for this same
three-arm request, not separate per-arm gates. The new actual long input packet
contains complete new endpoint bytes plus explicit old training archive reuse;
the auditor must record any private-input access limitation. Owner underlying
claude.ai conversation was not seen by Codex, and original chronology caveats
remain. Original CPUfailure37318 and failed C1r1/3.74 are never erased.
''')
shutil.copyfile(__file__,P/'BUILD_SCRIPT.py')
payload={str(p.relative_to(P)):{'bytes':p.stat().st_size,'sha256':h(p)} for p in sorted(P.rglob('*')) if p.is_file()}
write(P/'MANIFEST.json',payload)
write(R/'LONG_PREFLIGHT_SOURCE_PREPARED.json',{'created_utc':now,'source_count':len(source),'source_files':source,
 'input_basis_files':basis,'manifest_sha256':h(P/'MANIFEST.json'),'builder_done':True,'new_tests_done':13,
 'source_files_prepared':sorted(str(p) for p in Path('experiments/p011/long_preflight').glob('*.py'))+roots[1:]+tests,
 'new_paid_calls':0,'actual_subset_constructor_run':False})
print(json.dumps({'source_count':len(source),'packet_members':len(payload)+1,'actual_production_calls':0}))

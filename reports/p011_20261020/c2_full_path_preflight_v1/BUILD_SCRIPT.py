from pathlib import Path
import ast,hashlib,json,shutil
from datetime import datetime,timezone
from experiments.p011.c2_input_path import FILES,EVIDENCE
from scripts.prepare_p011_c2_students import PAIRS,ENDPOINT,GOLD
root=Path.cwd();out=root/'reports/p011_20261020/c2_full_path_preflight_v1';assert not out.exists();out.mkdir()
r=root/'.local/p011_20261020/r1'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2,sort_keys=True)+'\n')
entries=['experiments/p011/modal_c2.py','scripts/p011_c2_io.py','scripts/prepare_p011_c2_runtime_inputs.py','scripts/prepare_p011_c2_students.py','scripts/analyze_p011_c2.py',
'experiments/p011/c2_student_process.py','experiments/p011/c2_score_process.py','experiments/p010/student_score_process.py']
seen=set();todo=list(entries)
def add_module(module):
 for name in (module.replace('.','/')+'.py',module.replace('.','/')+'/__init__.py'):
  if (root/name).is_file() and name not in seen:todo.append(name)
 for i in range(1,len(module.split('.'))):
  name='/'.join(module.split('.')[:i])+'/__init__.py'
  if (root/name).is_file() and name not in seen:todo.append(name)
while todo:
 name=todo.pop()
 if name in seen:continue
 seen.add(name);text=(root/name).read_text();tree=ast.parse(text)
 package=name[:-3].split('/')[:-1]
 for node in ast.walk(tree):
  if isinstance(node,ast.Import):
   for alias in node.names:add_module(alias.name)
  elif isinstance(node,ast.ImportFrom):
   module=node.module or ''
   if node.level:module='.'.join(package[:len(package)-node.level+1]+([module] if module else []))
   add_module(module)
   for alias in node.names:
    if alias.name!='*':add_module(module+'.'+alias.name)
seen.add('experiments/learning_regime_p009/requirements_p0.txt')
sources={name:sha(root/name) for name in sorted(seen)}
old=json.loads((root/'reports/p011_20261020/b_full_path_preflight_v1/SOURCE_BINDING.json').read_text())
model=json.loads((root/'reports/p011_20261020/c1_runtime_v1/MODEL_ASSET_BINDING.json').read_text())
pairs={};manifest_refs={}
for label,folder in PAIRS.items():
 base='.local/p011_20261020/r1/c1_inputs_r1' if '/c1_inputs_r1/' in folder else '.local/p010_20261019/r1/'+('t15_datasets_r1' if '/t15_' in folder else 't72_datasets_r1')
 mp=root/base/'MANIFEST.json';saved=json.loads(mp.read_text());manifest_refs[str(mp.relative_to(root))]=sha(mp)
 for name in ('rows.json','encoded.json'):
  rel=str((Path(folder)/name).relative_to(base));pairs[folder+'/'+name]=saved[rel]['sha256']
tok=old['base_tokenizer_local_path'];tokenizers={tok+'/'+n:model['files'][n]['sha256'] for n in ('tokenizer.json','tokenizer_config.json','vocab.json','merges.txt','config.json')}
binding={'original_plan_commit':'e0dee182972f9910b707fac68800dcb5a3aff2d3',
 'source_files':sources,'source_count':len(sources),'entry_files':entries,
 'original_reuse_files':{p:sha(root/p) for p in FILES.values()},
 'original_acceptance_files':{p:sha(root/p) for p in EVIDENCE},
 'original_encoded_pair_files':pairs,'original_encoded_inventory_files':manifest_refs,
 'student_endpoint_files':old['student_endpoint_files'],'base_tokenizer_local_path':tok,
 'tokenizer_files':tokenizers,'window_size':700,
 'budget_owner_decision_sha256':'364aaf6cd70fa9cf1a89902af6dedb33a1b64d7c47e73a12b37b6b97dfb69a2f',
 'production_input_consumer_executed':False,'actual_SPEC_present':False,'paid_calls':0,
 'source_CR_accepted':False,'reservations_usd':0,'measurement_exceptions':0,
 'prior_attempted_C_reservations_usd':'6.38','prior_C_reservations_not_actual_expense':True,
 'private_original_hash_not_external_private_file_access':True,
 'current_new_checks':25,'historical_superseded_AST_check':1,'old_successful_tests_repeated':0}
write(out/'SOURCE_BINDING.json',binding)
write(out/'REVIEW_REQUIREMENTS.json',{'request_id':'p011-C2-generation-student-complete-path-CR-A1-A2-lite-r1',
 'first_source_scope':'p011-C2-generation-student-complete-path-CR',
 'full_numeric_scope':'p011-C2-generation-student-complete-path-CR-A1-A2-lite',
 'source_stage_bindings':['source_files','original_plan_commit','original_reuse_files','original_acceptance_files','original_encoded_pair_files','student_endpoint_files','window_size'],
 'source_flags':['input_preparation_authorized','read_only_original_Boolean_and_prompt_reuse_accepted','missing_T15_only_first_four_and_original_E1d_order_accepted','old_selected_encoding_reuse_accepted'],
 'actual_input_A1_after_first_consumer':True,'separate_numeric_SPEC_before_any_upload_or_paid_call':True,
 'numeric_flags':['complete_source_closure_accepted','complete_actual_input_A1_accepted','original_P010_tokens_seeds_dose_and_endpoint_rules_unchanged','all_original_complete_timing_sources_accepted','full_state_raw_scoring_window_and_budget_accepted','remote_paths_traced_to_producers','original_E1d_first_common400_and_saved_output_reuse_accepted','current_owner_accounting_and_saved_failed_parent_accepted','original_complete_cycle_interval_proxy_accepted'],
 'no_C1_self_calibration_exception':True,'original_failed_and_completed_C1_reservations_retained':True})
for src,dest in [('c2_student_numeric_new_checks_r1.log','INITIAL_STUDENT_NUMERIC_CHECKS.log'),('c2_student_inputs_new_checks_r1.log','INPUT_REUSE_CHECKS.log'),('c2_full_path_new_checks_r1.log','INITIAL_IMPORT_FAILURE.log'),('c2_full_path_new_checks_after_import_fix.log','FULL_PATH_CHECKS.log'),('c2_two_changed_boundaries_checks_r1.log','NEW_BOUNDARY_CHECKS.log')]:
 (out/dest).write_bytes((r/src).read_bytes())
(out/'README.md').write_text('''# C2 complete generation and two-student path: source-review candidate

Prepared only. One shared CR request covers input projection, missing T1.5 outputs, full raw proof and frozen new-only scoring, common-support selection, student inputs, both full training/endpoint paths, and the final paired contrasts. Source CR first authorizes one bounded CPU projection; actual A1 and concrete per-phase numeric SPEC follow in the same request. No production input, upload, model, scoring or reservation has occurred.

The original E1d order and T72 saved first-four verdicts are reused. T1.5 only generates absent attempts 1–4 at temperature .8 and original seeds; known output/score evidence is never decoded or scored again. Candidate window 700 is a CPU projection cap requiring explicit source review, not authorization for 2800 outputs. Every generated extra is preserved and charged; fewer than 400 common usable parents requires a disposition, never silent replacement. S1 overlap remains reported.

Both C2a/T1.5 and C2b/T72 use the first complete common400 in the same order, one first usable response each, no fallback. Original saved encoding catalogs are matched by question/path/prompt/response. Only unseen selected answers are encoded once. The new worker retains the entire original P010 model/update/state/merge body except replacing its redundant rt.encode call with fixed row/token structural verification; original input A1 and exact hashes remain required. This is a new C2 source revision, not a change to any completed B/P010 source. Current dedicated boundary test verifies every other training AST statement against original B body. Original 1024 updates/2097148 targets/seed17/LR and five500-question endpoints remain.

Full source-bound dispatch/claim/batch fences, saved failed C1 parent and all-category ledger, actual provider slots, current owner accounting, C12 and 80% remaining-category forecast are enforced. Retained C1 attempts total6.38 is a reservation, not expense/release; no paid C2 feasibility has yet been demonstrated. No C1 self-calibration exception is transferred. Full collect/audit/score share the original worker absolute window and Oct22 05UTC cutoff. Partial or unknown results block repeats.

25 current distinct new synthetic checks passed across the prepared components. One earlier training AST assertion passed on its initial unpublished body and was superseded by the explicit no-reencoding boundary check; its original log/snapshot is retained. An initial full-path test import failed before any test executed; only that import was repaired, then eight new cases ran once. No successful prior test, corpus, model or statistic was rerun. Source-only endpoint format inspection caught the list-versus-dict adaptation before its new test ran. A JSONL reader now preserves U+2028/U+2029 within physical lines; only its new boundary test ran.

Remote paths for the original T1.5 and base model remain the exact producers already bound in b_generation_runtime_v1/MODEL_PRODUCER_BINDING.json and c1_runtime_v1/MODEL_ASSET_BINDING.json; the eventual SPEC must bind those original files and full billed resources. No fresh rates or invented timing guarantee are supplied here. Large private input hashes and copied original inventory descriptors are not independent reviewer access.
''')
(out/'FUTURE_COMMANDS.md').write_text('''# Future commands, NOT RUN

Only after real exact shared-source CR and saved matching acceptance:

```sh
.local/midpoint_20261011/data_pipeline/venv/bin/python -m scripts.prepare_p011_c2_runtime_inputs --review .local/p011_20261020/r1/C2_FULL_SOURCE_CR_ACCEPTED.json
```

Then publish actual first input A1; construct an exact generation SPEC from the actual finite queue, complete original timing evidence, full result window and retained C budget. Its actual CR/A1/A2 plus fresh D1 must precede one `p011_c2_io upload` and one `P011_C2_PHASE=generation modal run -m experiments.p011.modal_c2 --job-id C2_generation_t08_missing_r1 ...`. No paid timing exception or candidate numerical admission is implied.

Only original completed RESULT plus actual STOPPED0 permits one collect, one full audit and one new-only score. Commands use `scripts.p011_c2_io` modes `collect`, `audit`, `score`, exact job ID and accepted review. Retain original directories and process receipts; partial transmission must be reconciled, never whole-helper retry.

After complete original saved verdicts and 400 common support, once:

```sh
.local/midpoint_20261011/data_pipeline/venv/bin/python -m scripts.prepare_p011_c2_students --review .local/p011_20261020/r1/C2_FULL_SOURCE_CR_ACCEPTED.json
```

Actual student input A1/concrete two-cell numeric SPEC and full budget/window acceptance are still required before either original C2a/C2b call. New analysis only after both completed states/full500×5 raw/scores/STOPPED0: `python -m scripts.analyze_p011_c2 --review <actual_student_review>`. Original P010 statistics are not recomputed. Every path is permanent once-only and no automatic retry is allowed.
''')
write(out/'BUILD_RECORD.json',{'written_utc':datetime.now(timezone.utc).isoformat(),'builder_sha256':sha(__file__),'new_source_files':sorted(p.as_posix() for p in Path('experiments/p011').glob('c2*.py')),'new_runtime_not_executed':True,'original_encoded_pair_hashes_from_existing_inventory':True})
(out/'BUILD_SCRIPT.py').write_bytes(Path(__file__).read_bytes())
write(out/'MANIFEST.json',{p.relative_to(out).as_posix():{'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(out.rglob('*')) if p.is_file()})
write(r/'C2_FULL_PREFLIGHT_BUILDER_DONE.json',{'source_count':len(sources),'directory':str(out.relative_to(root)),'manifest_sha256':sha(out/'MANIFEST.json'),'source_CR_pending':True,'production_calls':0})
print({'source_count':len(sources),'packet':str(out.relative_to(root)),'done':True})

from pathlib import Path
import json,hashlib,difflib,datetime
R=Path('.local/p011_20261020/r1');OUT=Path('reports/p011_20261020/long_current_source_addendum_v1')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def put(n,v):
 p=OUT/n;p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x') as f:f.write(json.dumps(v,indent=2,sort_keys=True)+'\n' if not isinstance(v,str) else v)
old=read('reports/p011_20261020/long_numeric_gold_owner_approved_v1/SOURCE_BINDING.json')['source_files']
prior=read('reports/p011_20261020/long_preflight_failed_ledger_runtime_v1/SOURCE_BINDING.json')['source_files']
new=['experiments/p011/long_current_path.py','experiments/p011/modal_long_current.py','scripts/p011_long_current_io.py','scripts/analyze_p011_long_current_pair.py']
source={**old,**{n:prior[n] for n in ('experiments/p011/c1_r2/__init__.py','experiments/p011/c1_r2/parent.py','experiments/p011/failed_attempt_ledger.py')},**{n:sha(n) for n in new}}
actual='reports/p011_20261020/long_numeric_gold_inputs_actual_v1/ACTUAL_INPUT_BINDING.json'
accepted=read(R/'LONG_RUNTIME_INPUT_A1_ACCEPTED.json')
owner='reports/p011_20261020/long_preflight_source_v1/OWNER_BINDING.json'
assert len(source)==44
OUT.mkdir(exist_ok=False)
binding=dict(source_files=source,new_files={n:source[n] for n in new},original37_source_map=old,
 current_owner_raw_sha256='364aaf6cd70fa9cf1a89902af6dedb33a1b64d7c47e73a12b37b6b97dfb69a2f',
 current_owner_binding_file=owner,current_owner_binding_file_sha256=sha(owner),
 actual_input_binding_file=actual,actual_input_binding_sha256=sha(actual),
 actual_input_directory='long_inputs_numeric_gold_r1',
 actual_input_A1_report_sha256=accepted['report_sha256'],actual_input_A1_target=accepted['target_commit'],
 ledger_candidate_target='38942d3a9380030d3ad885dfe46b6cfb377aad00',
 ledger_candidate_source_sha256=source['experiments/p011/failed_attempt_ledger.py'],
 original_input_construction_repeated=False,actual_SPEC_exists=False,measurement_exceptions=0)
put('SOURCE_BINDING.json',binding)
put('REVIEW_REQUIREMENTS.json',dict(shared_request_id='p011-long-A-D-complete-path-CR-A1-A2-lite-r1',
 source_scope='p011-long-A-D-complete-path-CR',full_numeric_scope='p011-long-A-D-complete-path-CR-A1-A2-lite',
 source_files=source,source_binding_sha256=sha(OUT/'SOURCE_BINDING.json'),
 required_source_flags=['complete_source_closure_accepted','science_functions_unchanged','current_owner_accounting_only_no_scientific_measurement_exception',
 'failed_B_and_C1_reservations_and_permanent_fences_retained','completed_input_locator_and_asset_receipt_reuse_accepted','local_audit_uses_pinned_metadata_not_absent_weights'],
 future_numeric_flags=['complete_source_closure_accepted','OT3_actual_A1_accepted','AM_actual_A1_accepted','endpoint_native_inputs_A1_accepted',
 'all_original_complete_timing_sources_accepted','full_state_raw_scoring_window_and_budget_accepted','remote_paths_traced_to_producers',
 'current_owner_budget_and_failed_reservations_accepted','completed_numeric_gold_inputs_and_prior_asset_reuse_accepted'],
 future_numeric_exact_fields=['source_files','spec_sha256','jobs_sha256','budget_owner_decision_sha256','prior_failed_C1_sha256','failed_attempt_bindings_sha256','actual_input_directory','actual_input_binding_sha256','measurement_exceptions'],
 actual_numeric_pending=True,no_input_construction_authorized=True,no_paid_call_authorized=True))
put('NEW_CHECKS.json',dict(new_distinct_methods=7,elapsed_seconds=.016,all_pass=True,
 test_path='tests/test_p011_long_current_path.py',test_sha256=sha('tests/test_p011_long_current_path.py'),old_successful_tests_repeated=0,
 production_ledger_or_model_invocations=0,fixture_values_are_not_actual_numeric_admission=True))
(OUT/'NEW_LONG_CURRENT_CHECKS.log').write_bytes((R/'NEW_LONG_CURRENT_CHECKS.log').read_bytes())
(OUT/'OWNER_BINDING.json').write_bytes(Path(owner).read_bytes())
put('ARTIFACT_REUSE_BINDING.json',dict(actual_input_directory=str(R/'long_inputs_numeric_gold_r1'),actual_input_binding_file=actual,
 actual_input_binding_sha256=sha(actual),original_failed_directory=str(R/'long_inputs_r1'),
 original_completed_cpu_cli=61074,original_failed_cli=37318,
 future_preflight_model_receipt='r/long_preflight_io_r1/model_uploads/REVISION/COMPLETED.json',
 future_receipt_not_yet_created=True,formal_upload_requires_exact_file_sha_and_model_file_map=True,
 local_audit_metadata_minimum=['config.json','generation_config.json','tokenizer.json','tokenizer_config.json'],
 local_audit_metadata_must_equal_subset_of_pinned_model_files=True,full_worker_model_verification_unchanged=True,
 new_weight_downloads=0,new_actual_artifact_reads=0))
pairs=[('experiments/p011/long_path.py',new[0]),('experiments/p011/modal_long.py',new[1]),('scripts/p011_long_io.py',new[2]),('scripts/analyze_p011_long_pair.py',new[3])]
diff=''.join(''.join(difflib.unified_diff(Path(a).read_text().splitlines(True),Path(b).read_text().splitlines(True),fromfile=a,tofile=b,n=0)) for a,b in pairs)
put('NARROW_FORMAL_ADAPTER_DIFF.patch',diff)
put('README.md','''# Formal A/D current-owner and artifact-reuse adapter

Prepared, not run. This is a narrow source appendix to the existing shared long-path request. It does not authorize a formal model call or create an actual timing specification.

Four new adapters preserve the original training, endpoint, timing policy, selection rules, logical IDs, remote fences, result window, complete-state oracle, scorer and analysis. Original 37 sources stay unchanged. The closure includes the previously proposed failed-attempt ledger and original C1 parent binding, for 44 sources total.

The admission adapter adopts the recorded current-owner accounting scope (protected0, retained P011 reservations and positive delayed-meter growth; no repeated P010 subtraction). Failed B3.01 and both C1 reservations6.38 remain obligations. Failed calls never acquire a fabricated completed RESULT. Unknown, pending and unmatched providers still count toward the shared four-slot limit. Formal measurement exceptions remain zero.

The local input locator now points to the completed numeric-gold inputs from CPU61074, rather than the failed original CPU37318 directory. Nothing is rebuilt or re-encoded. Formal upload requires the exact complete engineering model-upload receipt and reuses it without downloading, uploading or rereading model weights. The worker still verifies its complete pinned remote model bytes. Local output audit checks pinned configuration/tokenizer metadata, which it needs for full-state and raw-token proofs; it does not require absent local1.5B weights or reload a model.

The original actual input A1 remains accepted at63e8710f/reportdccd0876. The immutable input packet's historical pending label is not rewritten. Seven new synthetic checks passed once in0.016s; these are code checks, not measurements. No old tests, inputs, scientific calls, scoring or statistics were repeated.

Before any formal A/D call: real exact source review of this44-source appendix, actual three-arm engineering results and timing/memory evidence, a concrete SPEC with exact original complete input and asset receipt hashes, independent numeric admission, fresh accounting/provider/whole-window checks, and the original Claude smoke selection for later cells are still required. Three engineering exceptions do not transfer to formal A/D. No new arm, dose, reserve release, category transfer or automatic retry is introduced.
''')
put('FUTURE_COMMANDS.md','''# Future commands only after exact full admission

No actual formal SPEC exists. Do not invoke these commands now. Retain original logical job IDs and all once-only markers. Do not rerun either input constructor or preflight subset constructor.

```sh
PYTHONPATH=. .local/midpoint_20261011/venv/bin/python scripts/p011_long_current_io.py upload --job JOB --review .local/p011_20261020/r1/LONG_CURRENT_PATH_A1_A2_ACCEPTED.json
PYTHONPATH=. .local/midpoint_20261011/venv/bin/modal run -m experiments.p011.modal_long_current --job-id JOB --review-json .local/p011_20261020/r1/LONG_CURRENT_PATH_A1_A2_ACCEPTED.json --budget-json EXACT_FRESH_BUDGET --selection-json ACTUAL_SELECTION_IF_REQUIRED
```

For a truly completed original call and actual STOPPED/owned0, use the same p011_long_current_io.py collect, then audit, then score, once per original job. All share the original absolute result window. Analysis uses scripts/analyze_p011_long_current_pair.py, original allowed pair only, after both full results. Unknown or failed calls cannot use completed-only collection or retry.
''')
(OUT/'BUILD_SCRIPT.py').write_bytes(Path(__file__).read_bytes())
put('PUBLIC_MANIFEST.json',{str(p.relative_to(OUT)):{'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(OUT.rglob('*')) if p.is_file()})
with (R/'LONG_CURRENT_SOURCE_PUBLICATION_DONE.json').open('x') as f:json.dump(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),packet=str(OUT),source_count=44,new_checks=7,no_production_invoked=True),f,indent=2)
print(str(OUT),len(source),'source files; new packet only')

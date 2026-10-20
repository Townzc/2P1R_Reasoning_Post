"""Freeze original four C6 benchmarks with one bounded shared GPU lifetime."""
import ast,hashlib,json,shutil,tarfile
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from experiments.p010.common import read,dump,sha,manifest,utc
from experiments.p010.cue_benchmark_group import forecast,check_rosters,RESERVE,HARD_SECONDS,FULL_WINDOW
from experiments.p010.cue_benchmark_roster import RUNS
r=Path('.local/p010_20261019/r1');p=Path('reports/p010_20261019');inputs=r/'cue_benchmark_inputs_r1';out=p/'c6_benchmark_runtime_v1'
assert not out.exists() and not (r/'cue_benchmark_runs').exists() and not (r/'cue_benchmark_input_upload_r1').exists()
assert read(inputs/'COMPLETED.json')['new_outputs']==21371
check_rosters({n:read(inputs/(n+'.json')) for n in RUNS})
node=next(x for x in ast.parse(Path('scripts/prepare_p010_runtime_packets.py').read_text()).body if isinstance(x,ast.FunctionDef) and x.name=='closure');ns=dict(ast=ast,Path=Path,sha=sha)
exec(compile(ast.Module(body=[node],type_ignores=[]),'<closure helper only>','exec'),ns)
sources=ns['closure'](['experiments/p010/modal_cue_benchmark.py']);sources['experiments/learning_regime_p009/requirements_p0.txt']=sha('experiments/learning_regime_p009/requirements_p0.txt')
verifiers=ns['closure'](['scripts/prepare_p010_cue_benchmark_inputs.py','scripts/p010_cue_benchmark_io.py','scripts/p010_transfer.py','scripts/audit_p010_cue_benchmark.py','scripts/score_p010_cue_benchmark.py'])
old=read(p/'c6_search_runtime_v1/SPEC.json');prior=read(p/'seed29_runtime_v1/SPEC.json')
observed=list(prior['timing']['endpoint_seconds']);additional=[]
for f in sorted((r/'cue_search_export_r1/evidence/screen_acks').glob('*.json')):
 item=read(f);additional.append(dict(file=str(f),sha256=sha(f),seconds=item['seconds']));observed.append(item['seconds'])
assert len(additional)==40
scenario=forecast(0,0,[],observed,'5.78')
all_input=read(inputs/'MANIFEST.json')
worker_names=[n+'.json' for n in RUNS]+['MODEL_BINDINGS.json','SELECTION.json']
worker_files={n:all_input[n] for n in worker_names}
spec=dict(schema='p010_original_c6_four_cell_single_lifetime_v1',created_utc=utc(),plan_commit=old['plan_commit'],
 source_files=sources,verification_source_files=verifiers,input_files=worker_files,
 basis_sha256=sha(inputs/'BASIS.json'),existing_tables_sha256=sha(inputs/'EXISTING_NO_CUE_TABLES.json'),
 selection_sha256=sha(inputs/'SELECTION.json'),selection_binding=dict(target_commit='e0000fb3c438f2f68e42cee6501c086e6ca8be59',manifest_sha256='fecc92bee1f519aacc13b3d226da66a0e9955b1c3b62ee35e5059e96167acc54',scope='p010-C6-complete-search-selection-A3'),
 model_bindings=read(inputs/'MODEL_BINDINGS.json'),local_tokenizer_files=old['local_tokenizer_files'],
 math_gold_sha256=sha('.local/p009_20261014/r1/stage0_inputs_r1/math500.jsonl'),gsm_gold_sha256=sha('.local/p009_20261014/r1/stage0_inputs_r1/gsm8k_test1319.jsonl'),
 new_outputs=read(inputs/'COMPLETED.json').get('new_outputs_by_cell',read(inputs/'BASIS.json')['new_outputs']),
 new_outputs_total=21371,new_batches=85,new_training_updates=0,new_optimizer_checkpoint_loads=0,new_merge_operations=0,
 observed_batch_seconds=observed,timing_source=dict(previous_full_timing_spec_sha256=sha(p/'seed29_runtime_v1/SPEC.json'),additional_C6_original_batches=additional),
 scenario=scenario,hard_seconds=HARD_SECONDS,platform_seconds=5460,startup_seconds=600,full_window_seconds=FULL_WINDOW,
 new_I_reserved_usd=RESERVE,prior_I_after_E9_scenario_usd='5.78',I_total_after_search_E9_and_benchmark_usd='14.43',
 total_after_seed29_E9_benchmark_usd='166.76',category='I',cap_usd='15',no_reservation_release=True,
 first_paid_measurement_exceptions=0,maximum_shared_containers=4,no_automatic_retry=True,
 one_physical_call_contains_original_four_cells=True,each_model_in_fresh_joined_child=True,
 original_setup_allowance_seconds_per_cell=600,all_four_allowances_retained_throughout=True,
 runtime_review_scope='p010-C6-complete-benchmark-input-runtime-and-numeric-A2',
 math_local_cap_per_new500_endpoint_seconds=5200,math_single_endpoint_scenario_seconds=5160,
 max_math_cell_local_seconds=46920,gsm_cell_local_seconds=1200,raw_audit_local_seconds=7200,
 projected_scorer_row_id_is_schema_only=True,original_no_cue_tables_reused_without_rescoring=True,
 actual_model_calls=0,actual_A3_required_after_results=True)
# Each original named condition remains separate scientifically; only GPU lifetime is shared.
archive_node=next(x for x in ast.parse((r/'publish_k1_completed_once.py').read_text()).body if isinstance(x,ast.FunctionDef) and x.name=='archive');an=dict(hashlib=hashlib,tarfile=tarfile,sha=sha)
exec(compile(ast.Module(body=[archive_node],type_ignores=[]),'<original archive helper>','exec'),an)
out.mkdir()
for name,value in [('SPEC.json',spec),('SOURCE_BINDING.json',sources),('VERIFICATION_SOURCE_BINDING.json',verifiers),('WORKER_INPUT_MEMBERS.json',worker_files),('BASIS.json',read(inputs/'BASIS.json')),('MODEL_BINDINGS.json',spec['model_bindings']),('EXISTING_NO_CUE_TABLES.json',read(inputs/'EXISTING_NO_CUE_TABLES.json'))]:dump(out/name,value)
shutil.copyfile(inputs/'SELECTION.json',out/'SELECTION.json')
dump(out/'INPUT_ARCHIVE.json',an['archive'](out/'inputs.tar.gz',{f.relative_to(inputs).as_posix():f for f in inputs.rglob('*') if f.is_file()}))
for folder,mapping in [('source',sources),('verification_source',verifiers)]:
 for name,h in mapping.items():
  dst=out/folder/name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(name,dst);assert sha(dst)==h
shutil.copyfile('tests/test_p010_cue_benchmark_group.py',out/'NEW_GROUP_CHECKS.py')
shutil.copyfile(r/'test_cue_benchmark_group_fixture_r1.py',out/'ORIGINAL_TEST_FIXTURE.py')
for n in ('r1','r2'):
 f=r/f'cue_benchmark_group_new_checks_{n}.log';text=f.read_text().replace(str(Path.cwd()),'<workspace>');(out/f'NEW_GROUP_CHECKS_{n}.log').write_text(text)
dump(out/'TEST_LOG_PROJECTION.json',dict(original_private_sha256={n:sha(r/f'cue_benchmark_group_new_checks_{n}.log') for n in ('r1','r2')},only_absolute_workspace_prefix_redacted=True,original_logs_retained=True))
shutil.copyfile(Path(__file__),out/'candidate_builder.py')
(out/'README.md').write_text('''# Original C6 benchmark — complete input/runtime A2 candidate

The frozen development-only selection chose token [1249]. The original four scientific cells remain base-MATH, base-GSM8K, original T1.5/S1-n400-MATH and T72-n400-MATH. Each has no-cue/cue × greedy/four fixed samples. All saved original no-cue conditions are reused without generation, decode or scoring. Only 4,500/11,871/2,500/2,500 original missing outputs are generated, 21,371 total. Input preparation copied original full token arrays and saved Boolean tables, with exact prior raw/score/review hashes. It did not encode tokens, score, reselect the cue or load any old training state. MATH500 and GSM1319 original orders and 2048 context/1024-or512 continuation caps stay fixed. Cue plus generated continuation is passed through the unchanged logical stopping rule; genuine caps remain wrong.

One physical call executes the four cells in fixed order. Each model lifetime owns a new process that must exit0 and join before the next starts. Both student models reuse their already persisted, hash-verified evaluated merged weights; no optimizer-checkpoint reload, merge or training. All four cell markers and every batch are immutable under a single original group claim. A failure preserves completed parts and blocks automatic group/cell replay. One H100, min0, retries0, shared all-category max4 including pending/unknown/unmatched. This groups infrastructure only and does not merge scientific arms or change sample seeds.

The proposed entry cap is5,400s, platform5,460, startup600, full dispatch window6,100; new I reservation$8.65. All old failed/completed reservations remain. Search$3.26 + prospective E9baseline$2.52 + this group$8.65 = I$14.43, below the unchanged$15 cap. No release, category transfer or new funding is assumed. Timing retains all pooled endpoint intervals and adds all40 original C6 batches. It uses the full maximum, four separate600s uncalibrated setup/closing allowances and20% margin, and rechecks every new batch against actual elapsed time. No bootstrap exception, speed guarantee, calibrated bound or probability claim is made.

Eight new checks now pass: full actual outer worker and actual cell generation bodies under synthetic provider/model/process substitutes preserve all21,371 output identities and85 acknowledgments; child failure stops later cells; prior claim prevents generation; numeric/all-history/persisted-parent checks; score projection and no-cue reuse. The first three worker fixtures failed because the isolated AST omitted the module-global read function. Only those three were rerun after fixing the fixture, with no runtime change. Original failure logs and source are preserved. Existing pure roster/payload tests were not rerun; only the payload ledger-prefix interface was adapted.

The complete verifier checks source/input/review/claim/provider/parent bindings, every raw token and all85 forecasts; no old raw or binary is reloaded. MATH scoring uses the unchanged frozen single500-row scorer in owned processes, max5,200s per new condition (5,160s uncalibrated scenario), preserving original condition/ID through an explicit schema-only projection. GSM uses unchanged marked_answer_v1/task-boundary scoring,1,200s local bound. Saved original no-cue Booleans are copied only. Actual fixed samples/limitations and independent actual result A3 remain required. This packet is not permission to run: exact complete A2, actual C6 selection A3, already-issued original A4, fresh budget/readback/source/unused/full-window gates must all hold.
''')
(out/'FUTURE_COMMANDS.md').write_text('''# Future only after actual selection A3 and exact full A2

Use the Modal environment once: `scripts/p010_cue_benchmark_io.py --root .local/p010_20261019/r1 --spec reports/p010_20261019/c6_benchmark_runtime_v1/SPEC.json`. Only six gold-free worker files transfer; saved no-cue Boolean tables and private old scores are not sent to the GPU. Existing matching files may be read back; partial state prohibits a whole-helper retry.

One `modal run --detach -m experiments.p010.modal_cue_benchmark::main --receipt-dir .local/p010_20261019/r1/cue_benchmark_runs/benchmark_group_r1 --runtime-review-json ACTUAL_A2 --selection-review-json ACTUAL_SELECTION_A3 --actual-results-review-json K1_E1D_S1_SAMPLES_C9_A3_ACCEPTED --a4-report-json A4_SCIENTIFIC_SIGNAL_REPORT --budget-json FRESH_I_BUDGET`. Use actual JSON paths. One group only, not four resubmissions; save original CLI/app/call. No training or repeated old outputs.

Only original complete result plus STOPPED0: `scripts/p010_transfer.py collect --receipt RECEIPT --remote /p010-20261019/cue/benchmark_group_r1 --out NEW_EXPORT`, then `scripts/audit_p010_cue_benchmark.py records --spec SPEC --receipt RECEIPT --export EXPORT --out NEW_RECORDS`. Full `audit` uses spec/receipt/export/records/inputs/tokenizer/math-gold/gsm-gold/runtime-review/selection-review/actual-results-review/a4-report/out; inspect exact parser first. Once complete, each original cell uses `scripts/score_p010_cue_benchmark.py --spec SPEC --oracle COMPLETE_ORACLE --inputs ORIGINAL_INPUTS --run RUN --out NEW_SCORE` in math_verify_env. No old scorer/decoder/state rerun. Preserve partial data and failures; no whole-tool retries. Actual result A3 follows publication.
''')
dump(out/'MANIFEST.json',manifest(out))
rid='p010-C6-complete-benchmark-A2-r1';request=p/'C6_COMPLETE_BENCHMARK_A2_REQUEST.md'
request.write_text(f'''# Original C6 complete benchmark input/runtime A2\n\nRequest {rid}, scope `{spec['runtime_review_scope']}`. SPEC `{sha(out/'SPEC.json')}`, exact runtime{len(sources)}/verification{len(verifiers)}source. Review four original scientific cells,21371 new outputs/85 batches, all existing no-cue provenance/Boolean reuse and no regeneration, native EOS/cue-prefix cap semantics, actual selected-cue A3 binding, persisted student models without retraining/remerge, all-category budget and one group claim with per-cell/batch fences. Original A4 is already issued.\n\nConfirm source/spec/basis, complete four-cell roster, original no-cue outputs reused, original persisted models only, each child exit-before-next, single physical call only, new I reserve865c, no release, full5400/5460/600/6100 windows, all original timing observations plus4×600 uncalibrated allowance/20percent scenario, and complete local raw/provider/source and frozen-score verification. Scorer row-name projection is schema-only and must preserve original condition/id. No actual new benchmark call or scoring has occurred. Actual complete result A3 remains required.\n''')
x=read('reports/p007_audit/INDEX.json');assert not any(z['request_id']==rid for z in x['review_requests'])
x['review_requests'].append(dict(request_id=rid,scope=spec['runtime_review_scope'],status='pending',request=str(request),packet=str(out),manifest_sha256=sha(out/'MANIFEST.json'),spec_sha256=sha(out/'SPEC.json'),source_count=len(sources),verification_count=len(verifiers),created_utc=utc()))
x['p010'].update(C6_status='Actual selection complete; actual selection A3 and full original benchmark input/runtime A2 pending; no benchmark calls',C6_benchmark_candidate=str(out))
Path('reports/p007_audit/INDEX.json').write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
dump(r/'C6_BENCHMARK_CANDIDATE_CREATED.json',dict(utc=utc(),packet=str(out),spec_sha256=sha(out/'SPEC.json'),source_count=len(sources),verification_count=len(verifiers),new_model_calls=0))
pt=datetime.now(ZoneInfo('America/Los_Angeles')).strftime('%Y-%m-%d %H:%M:%S PDT')
note=f'\n### {pt} — Original C6 complete benchmark candidate\n\nInput preparation onceDONE without old encoding/decode/score; original saved no-cue conditions reused. Four original cells share one bounded GPU lifetime with separate joined child processes,5400s/8.65I, all old and E9baseline reserves retained: I14.43<15. Eight new checks pass; first3 ASTfixtures lacked importedglobalread, corrected fixture only and reran onlyfailed3. Original failure source/logs retained,0runtimefix/actualGPU. All original scientifique endpoints/seeds/caps unchanged. True selectionA3 and exactfullA2 pending; no extra code-only approval gate. Review poll09:08:37 stillc37f/109; initial0908guard blockedbeforeanyAPI, preserved, nextnormal09:38:38. Two guessed read-only filenames were absent with no writes or science effects.\n'
for f in ('docs/WORKBOARD.md','reports/sft_allocation_midpoint_20261011/RUN_LOG.md','AI_USE_LOG.md'):
 with Path(f).open('a') as h:h.write(note)
print(json.dumps(dict(source_count=len(sources),verification_count=len(verifiers),scenario_seconds=scenario['total_seconds'],forecast_usd=scenario['budget']['forecast_usd'],members=len(read(out/'MANIFEST.json')),archive_bytes=(out/'inputs.tar.gz').stat().st_size)))

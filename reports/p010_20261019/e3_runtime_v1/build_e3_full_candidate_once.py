"""Freeze the complete original E3 candidate once; no scientific execution."""
import ast,hashlib,json,shutil,tarfile
from pathlib import Path
from experiments.p010.common import read,dump,sha,manifest,utc
from experiments.p010.e3_contract import forecast,check_rosters
from experiments.p010.e3_settlement_binding import validate_settlement
from experiments.p010.e3_metrics import DEFINITION

r=Path('.local/p010_20261019/r1');p=Path('reports/p010_20261019');out=p/'e3_runtime_v1';inputs=r/'e3_inputs_r1'
assert not out.exists()
tree=ast.parse(Path('scripts/prepare_p010_runtime_packets.py').read_text());node=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='closure');ns=dict(ast=ast,Path=Path,sha=sha)
exec(compile(ast.Module(body=[node],type_ignores=[]),'<existing pure closure>','exec'),ns)
source=ns['closure'](['experiments/p010/modal_e3.py'])
source['experiments/learning_regime_p009/requirements_p0.txt']=sha('experiments/learning_regime_p009/requirements_p0.txt')
verification=ns['closure'](['scripts/p010_e3_io.py','scripts/audit_p010_e3.py','scripts/score_p010_e3.py','scripts/summarize_p010_e3.py'])
verification['experiments/learning_regime_p009/requirements_math_verify.txt']=sha('experiments/learning_regime_p009/requirements_math_verify.txt') if Path('experiments/learning_regime_p009/requirements_math_verify.txt').exists() else None
verification={k:v for k,v in verification.items() if v is not None}
asset=read(r/'teacher_t72_export_r1/evidence/INTENT.json')['asset'];asset=dict(asset,vocab_size=read(r/'model_metadata_1120_r1/COMPLETED.json')['original_T72_vocab_size'])
assert asset['vocab_size']==152064 and sha(r/'model_metadata_1120_r1/ORIGINAL_T72_CONFIG.json')==asset['files']['config.json']['sha256']
basis=read(inputs/'BASIS.json');timeref=read(p/'e3_budget_reallocation_proposal_v2/PROPOSAL.json')
original_result=r/'teacher_t72_export_r1/evidence/RESULT.json';times=read(original_result)['full_batch_seconds']
assert len(times)==36 and sha(original_result)==timeref['timing_source_sha256']
for n,h in timeref['pre_first_batch_sources'].items():assert sha(r/'teacher_t72_export_r1/evidence'/n)==h
timing=dict(original_full_batch_seconds=times,observed_pre_first_batch_seconds=float(timeref['observed_original_pre_first_batch_seconds']),
    original_result_sha256=sha(original_result),original_setup_source_files=timeref['pre_first_batch_sources'],
    future_host_upper_bound=False,uncalibrated_closing_seconds=300,margin=1.2)
settlement=p/'e3_d1_settlement_candidate_v1';proposal=read(settlement/'PROPOSAL.json')
scenario=forecast(0,0,[],times,timing['observed_pre_first_batch_seconds'],model_loaded=False,charged_G=proposal['proposed_charged_G_usd'])
check_rosters(read(inputs/'ROSTER.json'),{label:read(inputs/(label+'_requests.json')) for label in ('t06','t10')})
prior=[f'student_runs/{teacher}_s29_n{n}_k1' for teacher in ('t72','t15') for n in (400,3200)]
prior += ['e9_runs/'+run for run in ('e9_s17_n400','e9_s17_n3200','e9_base_math')]+['cue_benchmark_runs/benchmark_group_r1']
for relative in prior:assert (r/relative/'SUBMITTED.json').exists()
spec=dict(schema='p010_original_E3_complete_v1',created_utc=utc(),plan_commit='4287537f7733f5c3568ddb11695d47b566ef75fa',
    runtime_A2_scope='p010-E3-complete-input-runtime-and-numeric-A2',source_files=source,verification_source_files=verification,
    model=asset,actual_T72_config_sha256=sha(r/'model_metadata_1120_r1/ORIGINAL_T72_CONFIG.json'),
    original_input_basis_sha256=sha(inputs/'BASIS.json'),input_files=basis['worker_files'],
    gold_source_sha256=sha(inputs/'GOLD_SOURCE.json'),original_T08_rows_sha256=sha(inputs/'ORIGINAL_T08_ROWS.json'),
    original_T08_metadata_proof_sha256=sha(r/'e3_t08_metadata_r1/COMPLETED.json'),
    local_tokenizer_files=read(p/'c6_benchmark_runtime_v1/SPEC.json')['local_tokenizer_files'],
    original_actual_teacher_A1=basis['original_actual_A1'],new_outputs=3200,reused_T08_outputs=1600,
    old_T08_regenerated_or_rescored=False,new_training_updates=0,original_matched_questions=200,
    temperatures=[.6,.8,1.],new_attempts_per_question_per_temperature=8,cap_new_tokens=1024,context=2048,
    teacher_native_chat=True,original_seed_function_unchanged=True,gpu='H100!:4',tensor_parallel=4,
    worker_seconds=1800,platform_seconds=1860,startup_seconds=600,full_cloud_window_seconds=2500,
    full_result_window_seconds=51105,local_window_components_seconds=dict(collection=3600,records=1200,raw_oracle=7200,symbolic_with_cleanup=32405,metrics=3600,publication=600),
    no_automatic_retry=True,first_paid_measurement_exceptions=0,maximum_shared_active_predecessors=0,
    required_prior_receipt_directories=prior,owner_D4_file_sha256=sha(r/'OWNER_E3_D4_DECISION.json'),
    owner_D4_original_evidence_sha256=read(r/'OWNER_E3_D4_DECISION.json')['evidence_sha256'],
    owner_delegation_sha256=sha(r/'OWNER_P010_OVERNIGHT_DELEGATION.json'),
    settlement_packet=str(settlement),settlement_files=read(settlement/'MANIFEST.json'),
    settlement_proposal_sha256=sha(settlement/'PROPOSAL.json'),settlement_manifest_sha256=sha(settlement/'MANIFEST.json'),
    prior_original_G_reserve_usd='44',proposed_charged_G_usd=proposal['proposed_charged_G_usd'],
    new_G_reserved_usd='11.13',caps_usd=dict(G=50,T=150,I=15,C=25),overall_cap_usd=240,protected_usd=43,
    actual_settlement_release_applied=False,timing=timing,scenario=scenario,
    descriptive_metric_definitions=DEFINITION,new_confidence_intervals=False,independent_actual_A3_required=True)
assert validate_settlement(spec)['E3_D4_numeric_condition']
assert sum(spec['local_window_components_seconds'].values())+2500==51105
out.mkdir(exist_ok=False);dump(out/'SPEC.json',spec)
archive_node=next(x for x in ast.parse((r/'publish_e9_completed_once.py').read_text()).body if isinstance(x,ast.FunctionDef) and x.name=='archive')
ans=dict(hashlib=hashlib,tarfile=tarfile,sha=sha);exec(compile(ast.Module(body=[archive_node],type_ignores=[]),'<existing archive/readback>','exec'),ans)
files={str(f.relative_to(inputs)):f for f in inputs.iterdir() if f.is_file()}
dump(out/'INPUT_ARCHIVE.json',ans['archive'](out/'frozen_inputs.tar.gz',files))
for f in (r/'e3_t08_metadata_r1').iterdir():
    if f.is_file():target=out/'original_T08_metadata'/f.name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(f,target)
for name in sorted(set(source)|set(verification)):
    dest=out/'source'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(name,dest)
dump(out/'SOURCE_BINDING.json',dict(runtime=source,verification=verification))
for old in [r/'test_e3_full_new_r1.py',r/'test_e3_full_new_r1.log',r/'test_settlement_d1_new.py',r/'test_settlement_d1_new_r1.log',r/'e3_execution_draft_r1/test_e3_contract.py',r/'e3_execution_draft_r1/test_e3_worker_body.py',r/'e3_execution_draft_r1/test_e3_metrics.py',r/'e3_execution_draft_r1/new_contract_checks_r1.log',r/'e3_execution_draft_r1/new_worker_body_checks_r1.log',r/'e3_execution_draft_r1/new_metrics_checks_r1.log',Path('tests/test_p010_student_scoring.py')]:
    dest=out/'recorded_checks'/old.relative_to(r) if old.is_relative_to(r) else out/'recorded_checks'/old
    dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(old,dest)
for old in [r/'prepare_e3_inputs_once.py',r/'prepare_e3_t08_lengths_once.py',Path(__file__)]:shutil.copyfile(old,out/old.name)
dump(out/'PREPARED_NOT_RUN.json',dict(utc=utc(),runtime_sources=len(source),verification_sources=len(verification),new_scientific_calls=0,new_uploads=0,new_symbolic_scores=0,old_output_decodes=0,actual_settlement_release=0,
    completed_new_tests=dict(original_contract=11,original_worker_mocks=6,metrics=10,D1=9,full_D4_score_and_worker=11),
    test_scope='Synthetic only. Existing completed checks copied, not rerun; no real vLLM/TP4/symbolic execution. Entry full-result-window/verification-source check and bounded collector wrapper added after recorded11 checks, AST inspected; review their exact new source.'))
(out/'README.md').write_text('# Original E3: complete candidate, no call or settlement applied\n\n'
    'P010 v3 exploratory E3 only: the original hash200 questions from n400, eight attempts each at new temperatures0.6 and1.0, original per-question/attempt seeds and teacher native chat. '
    'Exactly3,200 new responses. The original first-eight0.8 responses for the same200 questions are copied with original Boolean verdicts and physical token-length provenance:1,600 reused, zero rescoring/regeneration. '
    'No training, new arm, paid calibration or input re-encoding. Frozen context2048/new-token1024/nativeEOS and original cap-wrong scoring remain.\n\n'
    'Full A1/A2 includes exact input archive, TP4 H100 runtime, source closure, original real36batch/setup timing, once-only fences, shared zero-active admission, raw/source/stop oracle, durable3,200-row local scoring, and original descriptive supply/diversity metrics. '
    'Local scores preserve failures/timeouts/unknowns and fixed audit samples. Lexical equation Jaccard and whitespace-token ROUGE-L are surface measures, not semantic equivalence. No new CI or scientific interpretation is produced.\n\n'
    'D4 rejected category transfer/cap increase. Original G50/T150/I15/C25,total240,protected43 remain. The D1 candidate has G24.03 charged versus original44 reservations, with full0.50 held for the app lacking exact owned-zero proof; failures stay included. '
    'E3 full11.13 reserve≤80% of remaining G20.776. Returned complete hourly intervals establish coverage, not final invoice/latency watermarks; exact A2 must accept this evidence scope. No release yet. '
    'Initial scenario1548.8585 seconds/9.9597USD includes original pre-first457.334 seconds and uncalibrated300 closing/20% margin, not a host upper bound.1800 worker/1860 platform/600 startup/full2500, zero retries. '
    'Dispatch also reserves the explicit51,105-second full verification/publication window before Oct21 19UTC, and obeys original Oct21 10UTC dispatch cutoff.\n\n'
    'Original seed29/E9 actual A3 now passed. Original C6 was dispatched before E3 and is closed failed with18,871 outputs preserved; no new C6 continuation is admitted. '
    'This E3 entry requires the original raw G44/I14.43 reservation state; do not dispatch a C6 continuation first and then bypass its ledger guard. Future C6 entry must bind any actually applied E3 D1 proof. '
    'Review request combines exact data/runtime/numeric A1/A2 in one round; no extra code-only gate. Actual results A3 follows completion.\n')
(out/'FUTURE_COMMANDS.md').write_text('''# Conditional commands — none executed

Use repository root; R=.local/p010_20261019/r1. Read actual CLI arguments first. Only after real fixed full A1/A2 with exact fields, save R/E3_RUNTIME_A1_A2_ACCEPTED.json and a fresh budget report / R/e3_budget_r1.json. Verify original D4 and covered D1 candidate; ordinary commit/push/remote verification precede dispatch. No acceptance is fabricated by this packet.

```sh
PYTHONPATH=. .local/midpoint_20261011/venv/bin/python scripts/p010_e3_io.py upload --root .local/p010_20261019/r1 --spec reports/p010_20261019/e3_runtime_v1/SPEC.json
PYTHONPATH=. .local/midpoint_20261011/venv/bin/modal run --detach -m experiments.p010.modal_e3::main --receipt-dir .local/p010_20261019/r1/e3_runs/temperature_supply_r1 --runtime-review-json .local/p010_20261019/r1/E3_RUNTIME_A1_A2_ACCEPTED.json --owner-d4-json .local/p010_20261019/r1/OWNER_E3_D4_DECISION.json --a4-report-json .local/p010_20261019/r1/A4_SCIENTIFIC_SIGNAL_REPORT.json --actual-results-review-json .local/p010_20261019/r1/K1_E1D_S1_SAMPLES_C9_A3_ACCEPTED.json --budget-json .local/p010_20261019/r1/e3_budget_r1.json
```

Only original result plus actual STOPPED0: `p010_e3_io.py collect --receipt R/e3_runs/temperature_supply_r1 --remote /p010-20261019/e3/temperature_supply_r1 --out NEW R/e3_export_r1`; then `audit_p010_e3.py records --receipt ... --export R/e3_export_r1 --out NEW R/e3_records_r1`. Data env full `audit_p010_e3.py audit --spec ... --receipt ... --export ... --records ... --inputs R/e3_inputs_r1 --tokenizer .local/midpoint_20261011/data_pipeline/reconstruction_r1/tokenizer --runtime-review R/E3_RUNTIME_A1_A2_ACCEPTED.json --owner-d4 R/OWNER_E3_D4_DECISION.json --out NEW R/e3_oracle_r1`. Math env `score_p010_e3.py --generation-oracle R/e3_oracle_r1 --receipt ... --spec ... --runtime-review ... --out NEW R/e3_scores_r1`. Then `summarize_p010_e3.py --spec ... --inputs R/e3_inputs_r1 --generation-oracle R/e3_oracle_r1 --scores R/e3_scores_r1 --old-metadata R/e3_t08_metadata_r1 --out NEW R/e3_metrics_r1` once. Every path is create-only. Partial/failed results are preserved; no whole-tool or scientific replay. Future publication copies original receipts/raw/journal/metrics and requests actual A3; it cannot change results.
''')
dump(out/'MANIFEST.json',manifest(out))
request=p/'E3_COMPLETE_A1_A2_REVIEW_REQUEST.md';request.write_text('# Original E3 full A1/A2 request\n\n'
    'Request `p010-E3-complete-input-runtime-numeric-A2-r1`, scope `p010-E3-complete-input-runtime-and-numeric-A2`. Review this fixed commit and `e3_runtime_v1/SPEC.json`, full input archive/source closure and `e3_d1_settlement_candidate_v1`. '
    'Bind exact source_files, verification_source_files, spec_sha256, input_basis/archive hashes, owner_D4_evidence_sha256, settlement_proposal_sha256; require input_A1_accepted=true, D1_hourly_coverage_scope_accepted=true, all_old_T08_outputs_reused_without_rescoring=true, first_paid_measurement_exceptions=0. '
    'Accept/reject the explicit saved STOPPED0 plus returned complete-hour coverage limitation; no invoice finality is claimed. Original raw G44 is unchanged, proposed charge24.03, reserve11.13, original category caps. '
    'Review new-output-only full oracle/scoring/metrics and full result-window accounting. Original6h/9h/etc timings are not inferred from new results. No source test, scoring, upload, model call or old-output replay is requested by reading this packet. '
    'Original seed29/E9 A3 accepted; C6 original failure/remaining proposal is separate, cannot waive either once-only exception or exact audit.\n')
f=Path('reports/p007_audit/INDEX.json');idx=read(f);assert not any(x.get('request_id')=='p010-E3-complete-input-runtime-numeric-A2-r1' for x in idx['review_requests'])
idx['review_requests'].append(dict(request_id='p010-E3-complete-input-runtime-numeric-A2-r1',scope=spec['runtime_A2_scope'],status='pending_real_exact_combined_A1_A2_D1_scope',packet=str(out),request=str(request),spec_sha256=sha(out/'SPEC.json'),settlement_proposal_sha256=sha(settlement/'PROPOSAL.json')))
idx['as_of_utc']=utc();idx['p010']['E3_status']='full_candidate_prepared_not_admitted_or_called_original_scope_D1_pending';f.write_text(json.dumps(idx,ensure_ascii=False,indent=2)+'\n')
dump(r/'E3_FULL_CANDIDATE_PREPARED.json',dict(utc=utc(),spec_sha256=sha(out/'SPEC.json'),manifest_sha256=sha(out/'MANIFEST.json'),runtime_sources=len(source),verification_sources=len(verification),actual_release=0,new_models=0))
print(json.dumps(dict(runtime_sources=len(source),verification_sources=len(verification),members=len(read(out/'MANIFEST.json')),spec_sha256=sha(out/'SPEC.json'),input_archive_bytes=(out/'frozen_inputs.tar.gz').stat().st_size)))

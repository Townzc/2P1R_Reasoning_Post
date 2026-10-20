"""One metadata/source freeze for the proposed, not-yet-approved C6 remainder."""
import ast,copy,json,shutil
from pathlib import Path
from experiments.p010.common import read,dump,sha,manifest,utc
from experiments.p010.cue_remaining import PARENT,RUN,forecast
from experiments.p010.cue_benchmark_roster import RUNS

r=Path('.local/p010_20261019/r1');p=Path('reports/p010_20261019')
out=p/'c6_remaining_runtime_v1';assert not out.exists()
oldfile=p/'c6_benchmark_runtime_v1/SPEC.json';old=read(oldfile)
preserved=r/'cue_benchmark_failure_preservation_r1';ledger=read(preserved/'LEDGER.json')
completed=read(preserved/'COMPLETED.json');proposal=p/'c6_remaining_owner_proposal_v1'
pathproof=read(r/'model_metadata_1120_r1/C6_PATH_PROOF.json')
assert completed['total_saved_raw_rows']==18871 and completed['provider_stopped'] and completed['owned_count']==0
assert completed['cells'][RUN]['saved_raw_rows']==completed['cells'][RUN]['confirmed_batch_acks']==0
binding=copy.deepcopy(old['model_bindings'][RUN]);assert binding['remote_path']==pathproof['wrong_path']
binding['remote_path']=pathproof['actual_original_path']
assert binding['files']['added_tokens.json']['sha256']==pathproof['small_original_file_sha256']
times=[];timingfiles={}
for run in RUNS[:-1]:
    cell=preserved/'evidence/cells'/run
    for f in sorted((cell/'batch_acks').glob('*.json')):
        ack=read(f);times.append(ack['seconds']);timingfiles[str(f)]=sha(f)
assert len(times)==75
for first in range(0,2500,256):
    for kind in ('batch','batch_done'):
        assert ledger[PARENT+'/'+RUN+'/'+kind+f'/{first:05d}'] is None
tree=ast.parse(Path('scripts/prepare_p010_runtime_packets.py').read_text())
node=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='closure')
ns=dict(ast=ast,Path=Path,sha=sha);exec(compile(ast.Module(body=[node],type_ignores=[]),'<existing source closure>','exec'),ns)
source=ns['closure'](['experiments/p010/modal_cue_remaining.py'])
source['experiments/learning_regime_p009/requirements_p0.txt']=sha('experiments/learning_regime_p009/requirements_p0.txt')
verification=ns['closure'](['scripts/audit_p010_cue_remaining.py','scripts/score_p010_cue_remaining.py','scripts/p010_e3_io.py'])
for key in ('source_files','verification_source_files'):
    for name,h in old[key].items():
        assert sha(name)==h, name
        verification[name]=h
observed=old['observed_batch_seconds']+times
settled=read(proposal/'I_SEARCH_D1_PROPOSAL.json')
scenario=forecast(0,0,[],observed,settled['proposed_prior_I_charged_usd'])
spec=dict(schema='p010_C6_remaining_only_full_v1',utc=utc(),plan_commit=old['plan_commit'],
    runtime_review_scope='p010-C6-unattempted-T72-remaining-input-runtime-and-numeric-A2',
    source_files=source,verification_source_files=verification,
    original_spec_file=str(oldfile),original_spec_sha256=sha(oldfile),
    original_input_archive_file=str(p/'c6_benchmark_runtime_v1/INPUT_ARCHIVE.json'),
    original_input_archive_metadata_sha256=sha(p/'c6_benchmark_runtime_v1/INPUT_ARCHIVE.json'),
    original_input_archive_sha256=read(p/'c6_benchmark_runtime_v1/INPUT_ARCHIVE.json')['sha256'],
    original_input_basis_sha256=old['basis_sha256'],input_files=old['input_files'],
    original_model_bindings=old['model_bindings'],corrected_model_binding=binding,
    exact_path_proof_sha256=sha(r/'model_metadata_1120_r1/C6_PATH_PROOF.json'),
    existing_tables_sha256=old['existing_tables_sha256'],selection_sha256=old['selection_sha256'],selection_binding=old['selection_binding'],
    math_gold_sha256=old['math_gold_sha256'],gsm_gold_sha256=old['gsm_gold_sha256'],local_tokenizer_files=old['local_tokenizer_files'],
    failed_parent={s:ledger[PARENT+('/'+RUN if s=='cell' else '')+'/'+s] for s in ('claim','terminal','cell')},
    failed_parent_manifest_sha256=sha(preserved/'MANIFEST.json'),failed_parent_ledger_sha256=sha(preserved/'LEDGER.json'),
    preservation_completed_sha256=sha(preserved/'COMPLETED.json'),
    original_parent_status='failed',reused_saved_outputs=18871,new_outputs=2500,new_batches=10,
    new_training_updates=0,new_checkpoint_loads=0,new_merge_operations=0,old_outputs_regenerated=0,
    new_physical_calls=1,new_permanent_marker='cue/t72_remaining_r1',old_markers_retained=True,
    original_cue=[1249],original_input_and_sampling_unchanged=True,no_automatic_retry=True,
    gpu='H100!',cpu=4,memory_gib=32,worker_seconds=1200,platform_seconds=1260,startup_seconds=600,
    full_cloud_window_seconds=1900,full_result_window_seconds=61425,
    local_window_components_seconds=dict(collection=3600,records=1200,raw_oracle=7200,
        concurrent_cell_scoring_with_cleanup=46925,publication=600),
    local_scoring_concurrency=dict(independent_cell_jobs=4,concurrent_math_jobs=3,workers_per_math_job=2,
        base_math_max_seconds=46920,student_math_max_seconds_each=26120,gsm_max_seconds=1200,
        same_original_per_endpoint_scoring=True,concurrent_execution_required_for_this_full_window=True,
        no_new_throughput_or_completion_guarantee=True),
    observed_batch_seconds=observed,all75_saved_batch_time_sources=timingfiles,
    original_timing_source=old['timing_source'],scenario=scenario,first_paid_measurement_exceptions=0,
    future_host_bound=False,uncalibrated_setup_closeout_seconds=600,
    I_settlement_packet=str(proposal),I_settlement_files=read(proposal/'MANIFEST.json'),
    I_settlement_proposal_sha256=sha(proposal/'I_SEARCH_D1_PROPOSAL.json'),
    owner_proposal_sha256=sha(proposal/'PROPOSAL.json'),owner_delegation_sha256=sha(r/'OWNER_P010_OVERNIGHT_DELEGATION.json'),
    E3_spec_file=str(p/'e3_runtime_v1/SPEC.json'),E3_spec_sha256=sha(p/'e3_runtime_v1/SPEC.json'),
    original_prior_I_reserve_usd='14.43',proposed_prior_I_charged_usd='12.16',new_I_reserved_usd='2.52',
    proposed_I_after_usd='14.68',caps_usd=dict(G=50,T=150,I=15,C=25),overall_cap_usd=240,protected_usd=43,
    category_transfer=False,actual_settlement_release_applied=False,owner_exception_received=False,
    runtime_A2_received=False,actual_model_calls=0,actual_symbolic_scores=0,actual_full_raw_oracles=0,
    independent_actual_A3_required=True)
assert 1900+sum(spec['local_window_components_seconds'].values())==61425
out.mkdir(exist_ok=False);dump(out/'SPEC.json',spec)
for name in sorted(set(source)|set(verification)):
    dest=out/'source'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(name,dest)
dump(out/'SOURCE_BINDING.json',dict(runtime=source,verification=verification))
for oldpath in [Path('tests/test_p010_cue_remaining.py'),Path('tests/test_p010_cue_benchmark_group.py'),r/'test_cue_remaining_new_r1.log']:
    dest=out/'recorded_checks'/oldpath.name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(oldpath,dest)
shutil.copyfile(Path(__file__),out/Path(__file__).name)
dump(out/'INPUT_REFERENCE.json',dict(fixed_original_target='a998d25251422707f65bfc836ad0fcfe69d56a43',
    archive_metadata=str(p/'c6_benchmark_runtime_v1/INPUT_ARCHIVE.json'),
    archive_metadata_sha256=spec['original_input_archive_metadata_sha256'],archive_sha256=spec['original_input_archive_sha256'],
    no_rebuilt_inputs=True,no_new_upload=True,only_binding_remote_path_corrected=True))
dump(out/'PREPARED_NOT_RUN.json',dict(utc=utc(),new_synthetic_checks=11,elapsed_seconds=.410,
    mocked_actual_generation_body=True,actual_GPU_calls=0,actual_symbolic_scores=0,new_raw_decodes=0,
    old_tests_repeated=0,actual_owner_approval=False,actual_exact_A2=False,actual_release=0,
    test_limitations='No real GPU, remote model hash read, tokenizer decode, full journal or symbolic execution. Original fixture definitions imported; their test methods not rerun.'))
(out/'README.md').write_text('''# C6: only the original unattempted T72 cell

This complete candidate needs the reasoned delegated owner exception and an independent exact A1/A2. It is not authorized by a code-only PASS. The original benchmark remains failed. Its three complete cells contain18,871 saved outputs/75 acknowledgments; the fourth T72 cell has its original reserved marker but zero generation attempts. The original failure was a singular `student/` path where the original persisted merged model is under `students/`. Correct only that binding; verify the original complete model-file hashes in the new worker. No training, optimizer checkpoint load, merge, old output regeneration or original no-cue rescoring.

One new physical call generates only the original2,500 T72 requests with cue token1249, unchanged seeds, input bytes, context/greedy/sampled settings and original model. One H100,1200 worker/1260 platform/600 startup/full1900,2.52USD I reservation, zero automatic retries. The failed parent claim/terminal/cell and all its costs stay intact. A new permanent dispatch/claim/batch namespace permits no replay. All75 preserved completed batch times plus all older admitted observations inform every new forecast, including the first; maximum20.412141323s yields964.945695877s initially with600 uncalibrated allowance and20% margin, not a future-host bound.

The proposed same-I D1 settlement covers only the completed search app: original3.26 reservation becomes0.99 from the greatest saved delayed gross0.82151854 with20% and cent-ceiling, supported by actual STOPPED0 and complete returned-hour coverage. Original failed benchmark8.65 and E9 baseline2.52 stay fully held. I14.43−3.26+0.99+2.52=14.68≤15. Coverage is not final invoice or a meter-finality watermark; a higher fresh charge blocks this fixed candidate. G50/T150/I15/C25,total240/protected43 remain. No release has occurred.

E3 must dispatch first if both candidates are accepted: its immutable entry expects the original raw ledger. This C6 candidate accepts either original G44 or actual E3 rawG55.13 only with the separately real E3 A2 and recorded D1 proof; it waits until every original app is STOPPED0. No hidden transfer or rewriting old reservations.

After the new original result and STOPPED0, the complete48-key receipt/lineage oracle replays21,371 raw rows once:18,871 from the failed parent's stable preserved files and2,500 from the new call. It never fabricates a completed original group or reloads an old binary. Frozen scoring then runs each of the four independent complete cells once, reusing all earlier no-cue Boolean tables. Three independent MATH jobs may run concurrently, each retaining its original two scoring workers, per-endpoint5200-second bounds, failures/timeouts and create-only journals; GSM runs independently with1200 seconds. This explicit concurrency is required for the61,425-second whole-result window before Oct21 19UTC. It is a bound on scheduled work, not a CPU-speed guarantee. No post-result selection, altered labels or new statistics.

Recorded11 new offline checks passed once, including the actual new generation body with mocked vLLM, raw preservation before rejected acknowledgment, parent/new-fence replay refusal, exact settlement arithmetic, and real entry/source checks. They do not establish real GPU/symbolic behavior. All old tests, models, collectors, scores and publishers remain DONE and are not repeated. Independent actual A3 follows complete results; the owner exception does not waive it.
''')
(out/'FUTURE_COMMANDS.md').write_text('''# Conditional one-call workflow — no command below has run

Use repository root. R=.local/p010_20261019/r1, S=reports/p010_20261019/c6_remaining_runtime_v1/SPEC.json. First save real OWNER_C6_REMAINING_DECISION.json with explicit reasoned delegated decision and C6_REMAINING_A1_A2_ACCEPTED.json with fixed full report bytes/hash/scope/target and exact source/input/numeric bindings. Fresh billing<=1hour must preserve original-cap and greatest historical D1 floors. No input/model upload. Publish the actual acceptance and independently verify ordinary remote HEAD before dispatch.

```sh
PYTHONPATH=. .local/midpoint_20261011/venv/bin/modal run --detach -m experiments.p010.modal_cue_remaining::main --receipt-dir .local/p010_20261019/r1/cue_remaining_runs/t72_remaining_r1 --runtime-review-json .local/p010_20261019/r1/C6_REMAINING_A1_A2_ACCEPTED.json --owner-decision-json .local/p010_20261019/r1/OWNER_C6_REMAINING_DECISION.json --budget-json .local/p010_20261019/r1/cue_remaining_budget_r1.json
```

Only original completed result and actualSTOPPED0: `scripts/p010_e3_io.py collect --receipt R/cue_remaining_runs/t72_remaining_r1 --remote /p010-20261019/cue/t72_remaining_r1 --out NEW R/cue_remaining_export_r1` (bounded collector only, not its E3 upload action). Then `scripts/audit_p010_cue_remaining.py records --spec S --receipt R/cue_remaining_runs/t72_remaining_r1 --export R/cue_remaining_export_r1 --out NEW R/cue_remaining_records_r1` once.

Full data-env oracle: `scripts/audit_p010_cue_remaining.py audit --spec S --receipt R/cue_remaining_runs/t72_remaining_r1 --parent-receipt R/cue_benchmark_runs/benchmark_group_r1 --preservation R/cue_benchmark_failure_preservation_r1 --export R/cue_remaining_export_r1 --records R/cue_remaining_records_r1 --inputs R/cue_benchmark_inputs_r1 --tokenizer .local/midpoint_20261011/data_pipeline/reconstruction_r1/tokenizer --math-gold .local/p009_20261014/r1/stage0_inputs_r1/math500.jsonl --gsm-gold .local/p009_20261014/r1/stage0_inputs_r1/gsm8k_test1319.jsonl --runtime-review R/C6_REMAINING_A1_A2_ACCEPTED.json --owner-decision R/OWNER_C6_REMAINING_DECISION.json --original-runtime-review R/C6_BENCHMARK_A2_ACCEPTED.json --out NEW R/cue_remaining_oracle_r1`. The original gold paths above were SHA-bound to S before freezing this candidate.

Only after full combined proof: math-env `scripts/score_p010_cue_remaining.py --spec S --oracle R/cue_remaining_oracle_r1 --inputs R/cue_benchmark_inputs_r1 --run RUN --out NEW R/cue_remaining_scores/RUN` once per base_math,base_gsm,s1_n400_math,t72_n400_math. Run those independent cells concurrently, at most three MATH jobs/two workers each. Keep original fixed samples/failures/unknowns and original no-cue Boolean tables. No new checkpoint loads or old score calls. Unknown/partial data stay preserved; reconcile valid parts before any bounded missing-only recovery, never repeat a whole tool or model. Future publication must retain split failed/new provenance and request actual A3.
''')
dump(out/'MANIFEST.json',manifest(out))
request=p/'C6_REMAINING_COMPLETE_A1_A2_REVIEW_REQUEST.md'
request.write_text('''# C6 original unattempted T72 cell: complete A1/A2 request

Request `p010-C6-unattempted-T72-remaining-A2-r1`, scope `p010-C6-unattempted-T72-remaining-input-runtime-and-numeric-A2`. Review this exact fixed SPEC, full runtime and verification closure, original input/archive hash, corrected-only model path, original failed-parent evidence, once-only fences, all75 additional timing observations and proposed same-I D1. Original owner request `p010-C6-only-unattempted-T72-cell-owner-exception-r1` remains separate: an explicit reasoned delegated decision is required and cannot waive independent audit.

The actual acceptance must bind exact source_files,verification_source_files,spec_sha256,owner_decision_evidence_sha256,failed_parent_manifest_sha256 and the original input archive/BASIS; require same_I_D1_coverage_scope_accepted=true,reuse18871_generate2500_only=true,first_paid_measurement_exceptions=0. Review the fixed0.99 charge and fresh-meter-increase rejection, original failed8.65/E9base2.52 held, Iafter14.68, unchanged hard category/overall caps; no final billing watermark claim. Check actual E3 settlement compatibility and E3-first dispatch ordering. No release or new call has occurred.

The full new raw oracle preserves the failed original status and independently binds all21,371 logical outputs; no previous full raw oracle/scorer has run for these C6 benchmark outputs. Frozen per-cell scoring includes independent concurrent jobs and explicit61,425-second end-to-end window. Review original no-cue Boolean reuse, original50/fallback/timeout evidence and later actualA3. Existing output scores are not a permission to change the selected cue or sampling. Recorded11 new checks are entirely offline and were not repeated.
''')
f=Path('reports/p007_audit/INDEX.json');idx=read(f)
assert not any(x.get('request_id')=='p010-C6-unattempted-T72-remaining-A2-r1' for x in idx['review_requests'])
idx['review_requests'].append(dict(request_id='p010-C6-unattempted-T72-remaining-A2-r1',scope=spec['runtime_review_scope'],
    status='pending_real_owner_exception_and_full_exact_A1_A2',packet=str(out),request=str(request),
    spec_sha256=sha(out/'SPEC.json'),owner_proposal_sha256=spec['owner_proposal_sha256']))
idx['as_of_utc']=utc();idx['p010']['C6_remaining_status']='full_candidate_only2500_pending_owner_and_A2_original18871_preserved'
f.write_text(json.dumps(idx,ensure_ascii=False,indent=2)+'\n')
dump(r/'C6_REMAINING_FULL_CANDIDATE_PREPARED.json',dict(utc=utc(),spec_sha256=sha(out/'SPEC.json'),manifest_sha256=sha(out/'MANIFEST.json'),
    runtime_sources=len(source),verification_sources=len(verification),actual_release=0,new_models=0))
print(json.dumps(dict(runtime_sources=len(source),verification_sources=len(verification),members=len(read(out/'MANIFEST.json')),spec_sha256=sha(out/'SPEC.json'))))

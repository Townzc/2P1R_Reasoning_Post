"""Create-only source-review metadata; no census/tokenizer/model/scorer execution."""
import ast
from pathlib import Path
import shutil
from experiments.p011.owner_0205_common import OWNER_SHA, create, read, sha, utc

R=Path('.local/p011_20261020/r1')
P=Path('reports/p011_20261020')


def binding(path):
    return {'path':str(path),'sha256':sha(path)}


def source_closure(roots):
    result={};pending=list(roots)
    while pending:
        name=pending.pop()
        if name in result:continue
        path=Path(name);result[name]=sha(path)
        for node in ast.walk(ast.parse(path.read_text(),filename=name)):
            modules=[]
            if isinstance(node,ast.Import):modules=[n.name for n in node.names]
            elif isinstance(node,ast.ImportFrom) and node.module:
                modules=[node.module]+[node.module+'.'+n.name for n in node.names]
            for mod in modules:
                if not mod.startswith(('experiments.','scripts.')):continue
                candidate=Path(mod.replace('.','/')).with_suffix('.py')
                if candidate.is_file():pending.append(str(candidate))
                components=mod.split('.')
                for i in range(1,len(components)+1):
                    init=Path(*components[:i])/'__init__.py'
                    if init.is_file() and str(init) not in result:result[str(init)]=sha(init)
    return dict(sorted(result.items()))


def finish(folder,spec,readme,commands):
    folder.mkdir(exist_ok=False)
    create(folder/'SPEC.json',spec)
    create(folder/'SOURCE_BINDING.json',{'spec_sha256':sha(folder/'SPEC.json'),
        'owner_report_sha256':OWNER_SHA,'source_files':spec['source_files'],
        'distinct_source_count':len(spec['source_files']),'scientific_execution_started':False})
    (folder/'README.md').write_text(readme)
    (folder/'FUTURE_COMMANDS.md').write_text(commands)
    shutil.copyfile(R/'OWNER0205_NEW_TESTS_FIRST.log',folder/'NEW_SYNTHETIC_TESTS.log')
    create(folder/'MANIFEST.json',{'schema':'p011_owner0205_preflight_manifest_v1',
        'created_utc':utc(),'files':{str(p.relative_to(folder)):{'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(folder.iterdir()) if p.is_file()}})


def main():
    fence=R/'OWNER0205_REVIEW_PACKETS_BUILD_ATTEMPT.json'
    create(fence,{'utc':utc(),'production':False,'automatic_retry':False})
    original=read(P/'owner150_runtime_v1/SPEC.json');retry=read(P/'owner_A1_infra_retry_runtime_v1/SPEC.json')
    jobs={**original['jobs'],**retry['jobs']};base=next(iter(jobs.values()))['model']
    tokenizer_files={k:v['sha256'] for k,v in base['files'].items() if k in ['tokenizer.json','tokenizer_config.json','vocab.json','merges.txt','config.json']}
    census_sources=source_closure(['scripts/count_p011_ot3_math_pool.py'])
    census={'schema':'p011_OT3_full_math_pool_census_v1','owner_report_sha256':OWNER_SHA,
        'source_files':census_sources,'required_source_review_flags':[
            'exact_pinned_math_pool_and_original_A_grouping_accepted','original_eligibility_and_new_literal_normalized_counts_distinguished',
            'answer_only_lengths_and_seeded_K1_token_mass_not_training_dose_accepted','no_new_model_or_reencoded_training_inputs'],
        'raw_index':str(R/'ot3_inputs_r1/RAW_INDEX.sqlite'),'raw_index_bytes':(R/'ot3_inputs_r1/RAW_INDEX.sqlite').stat().st_size,
        'expected_ingested_math_rows':850000,'original_metadata_bindings':[binding(R/'ot3_inputs_r1/INGESTED.json'),binding(R/'ot3_inputs_r1/INTENT.json'),binding(P/'long_data_preflight_v1/SOURCE_LOCK.json')],
        'dataset_revision':'61bcf9d4eb38b30295efc2021227a63cc5bb34c8','dataset':'open-thoughts/OpenThoughts3-1.2M',
        'benchmark_binding':binding(R/'ot3_inputs_r1/BENCHMARKS.json'),
        'tokenizer_path':base['local_path'],'tokenizer_files':tokenizer_files,
        'output':str(R/'ot3_full_math_census_r1'),'new_training_inputs':False,'automatic_retry':False,
        'deadline':'New owner analysis exemption; aim05UTC, do not falsify completion if later.'}
    finish(P/'ot3_full_math_census_preflight_v1',census,
        '# New full-pool OT3 math census\n\nSource is the original read-only43.1GB raw SQLite index of all120 pinned local parquet shards, with the original source-lock and ingestion receipts. It scans all850000 math rows; it does not repeat parquet download/ingestion or old training encodings. Full-pool answer-length tokenization is a newly authorized CPU analysis, once only.\n\nA grouping remains NFKC(question).strip(). Raw exact and whitespace-removed casefold counts are separately reported. Eligibility uses original boxed-completeness, exact/13-gram contamination and native prompt+response+EOS+newline<=16384; completeness does not establish correctness. Report≥1 and≥16 eligible responses, and the original stricter exactly16/all16 eligible pool separately.\n\nLength mean/median/p90 excludes EOS; population CV/max:min are per original A group. Zero-length exclusions are explicit. P8192/16384/32768 K1 totals use a new deterministic diagnostic prefix: sorted eligible parent keys shuffled20261020, original per-parent shuffled rows, first eligible response, one-pass supervised tokens including EOS. This is neither a retraining dataset nor a fixed training-token dose. Insufficient pools yield null totals, never zero. Benchmark exact/normalized overlap is reported separately from original13-gram exclusion.\n\nNo production run before this exact quick Claude CR. New tests are synthetic; all prior science stays DONE.\n',
        '# Future once-only CPU command, only after actual source CR\n\n```sh\nPYTHONPATH=. .local/midpoint_20261011/data_pipeline/venv/bin/python scripts/count_p011_ot3_math_pool.py --spec reports/p011_20261020/ot3_full_math_census_preflight_v1/SPEC.json --review .local/p011_20261020/r1/OT3_FULL_MATH_CENSUS_CR_ACCEPTED.json\n```\n')
    roots=['experiments/p011/modal_forced_answer.py','experiments/p011/forced_answer_worker.py',
        'experiments/p011/forced_answer_score_process.py','scripts/prepare_p011_forced_answer_inputs.py',
        'scripts/p011_forced_answer_io.py','scripts/analyze_p011_forced_answer.py','scripts/record_p011_forced_answer_budget.py']
    cells={}
    for cell in ['baseline','A1r2','A5','A6','A7','D1','D2']:
        jobid='long_baseline_S-L15_s17_owner_r1' if cell=='baseline' else ('long_A1_S-F15_s17_owner_r2' if cell=='A1r2' else f'long_{cell}_S-F15_s17_owner_r1')
        job=jobs[jobid]
        audit=R/'d2_option_a_r1/audit' if cell=='D2' else R/'long_owner_closeout_r1/audit'/jobid
        payload=R/'owner_D2_terminal_failure_preservation_r1/original_remote_payload' if cell=='D2' else audit/'payload'
        score=R/'d2_option_a_r1/score' if cell=='D2' else R/'long_owner_closeout_r1/score'/jobid
        metadata=[audit/'COMPLETE_PROOF.json',audit/'DECODED.json',audit/'SCORING_ROWS.json',score/'COMPLETED.json',score/'owned_score/payload/ALL_SCORED_ROWS.json',payload/'ENGINE.json']
        if cell=='baseline':
            model_files=base['files'];remote=base['remote_path'];metadata.append(Path(base['preflight_asset_readback']['path']))
        else:
            export=read(payload/'MODEL_EXPORT.json');model_files=export['files']
            remote='/evidence/p011-20261020/long_owner150_runs_r1/'+jobid+'/'+export['relative_path'];metadata.append(payload/'MODEL_EXPORT.json')
        cells[cell]={'original_job_id':jobid,'payload_path':str(payload),'decoded_path':str(audit/'DECODED.json'),
            'scoring_rows_path':str(audit/'SCORING_ROWS.json'),'saved_scored_rows_path':str(score/'owned_score/payload/ALL_SCORED_ROWS.json'),
            'metadata_bindings':[binding(p) for p in metadata], 'remote_model_path':remote,'model_files':model_files,
            'eos_token_ids':job['eos_token_ids'],'old_primary_result_or_training_changed':False}
    forced={'schema':'p011_fixed_forced_answer_diagnostic_v1','owner_report_sha256':OWNER_SHA,
        'source_files':source_closure(roots),'required_source_review_flags':[
            'exact_seven_cells_original_checkpoint_and_length_only_tokens_accepted','fixed_suffix_once_greedy64_no_prompt_or_old_output_reencoding',
            'natural_labels_reused_no_original_rescore','native_stop_and_frozen_P1_scalar_pool_including_64cap_policy_accepted',
            'posthoc_loop_utf8_ratio_and_five_new_contrasts_single_seed_limits_disclosed',
            'one_shared_attempt_partial_cell_preservation_no_retry_and_hard_cost_timer_accepted'],
        'required_A2_flags':['actual_selected_ids_prompt_generated_suffix_and_total_context_verified',
            'actual_checkpoint_export_weight_binding_and_remote_reuse_verified','no_natural_rows_or_gold_in_GPU_requests',
            'actual_prefill_rows_runtime_cost_and_at_most_12_dollar_reserve_accepted'],
        'cells':cells,'student_tokenizer_path':base['local_path'],'student_tokenizer_files':tokenizer_files,
        'model_vocab_size':151936,'input_output':str(R/'forced_answer_inputs_r1'),'local_root':str(R/'forced_answer_r1'),
        'terminal_cost_binding':binding(R/'owner150_terminal_cost_reconciliation_r1/COMPLETED.json'),
        'resources':{'gpu':'H100','cpu':4,'memory_mib':32768,'max_worker_seconds':10800,'startup_seconds':600,'platform_grace_seconds':60},
        'new_reserve_ceiling_usd':'12','prior_unattributed_allowance_usd':'20.02','new_noncompute_allowance_usd':'1.50',
        'historical_rate_not_admission_usd_per_hour':'4.39520','new_fresh_rate_and_actual_meter_required':True,
        'runtime_note':'min10800, floor((12-1.50)*3600/fresh_hourly_rate)-660; cap platform at worker+60. Single attempt, seven sequential model loads; no performance guarantee.',
        'scoring_cap_per_cell_seconds':7200,'original_symbolic_pair_timeout_seconds':8,
        'new_analysis_deadline':'Owner exemption applies only these analyses; aim05UTC and keep formal05UTC original freeze honest.',
        'independent_actual_A2_and_A3_required':True,'automatic_retry':False,'training_authorized':False}
    finish(P/'forced_answer_preflight_v1',forced,
        '# Fixed-suffix forced-answer posthoc diagnostic\n\nSeven cells: baseline,A1r2,A5,A6,A7,D1,D2. Only saved MATH sample+greedy outputs whose original backend finish_reason is length and whose native stream is exactly16384 tokens are selected. Each new prompt is the exact saved prompt IDs plus generated IDs plus one fixed suffix encoding. There is no question/output retokenization or new training. Original evaluated exported weights (or baseline Instruct) are bound by saved MODEL_EXPORT/full-state oracle metadata and verified by remote byte hashes at the new load. No old weights are uploaded.\n\nSuffix is exactly `\\n</think>\\n\\nFinal answer: \\boxed{`. Encode once with the pinned tokenizer. One greedy64-token continuation, original EOS IDs and unchanged engine settings function. New native oracle preserves original EOS/special/length semantics at the explicit64 cap. Scoring text is `\\boxed{` plus decoded continuation, using the unchanged P1 last_box/scalar/two-process symbolic pool. A64-token cap remains length_cap and is incorrect under the frozen scorer even if a box appears closed; CR must explicitly acknowledge this. Only forced rows are scored; every natural-end label is reused from its original immutable scored row.\n\nTruncated loop split uses zlib(defaultlevel) compressed UTF8 bytes of the last6000 original decoded answer characters divided by their UTF8 bytes, threshold<0.12. Review must explicitly confirm this matches the stated heuristic; it is descriptive. Five new label contrasts use the original paired-question10000bootstrap/seed20261021. For greedy, the same saved bit repeats four times only to use the original interface; no new observations. Original contrasts and labels are never recomputed/replaced.\n\nOne H100 worker runs seven cell subprocesses sequentially. Permanent input/upload/dispatch/claim/cell/score/analysis fences, no automatic retry. Each completed cell is durable before starting the next. If the global attempt fails, completed cells may be collected and analyzed, partial cells remain unavailable rather than zero. Full requests contain no gold or original labels.\n\nReserve≤12USD, including a1.50newnoncompute allowance. Budget computes a worker timer from the fresh authenticated rate,600sstartup+60splatformgrace, maximum10800s; at the historical4.39520/h it is about2.2h, not a3h guarantee. Prior100.02287004taggedcost is historical, not a fresh invoice. Fresh admission retains20.02for prior unattributed/delayed costs, includes all original ten attempts/failed actuals/two controls, and counts unknown/pending slots. No transfer from other categories.\n\nSource CR before new CPU inputs; actual input A2-lite before paid dispatch; actual A3 after results. The new owner exemption does not rewrite the original05UTC freeze. Scientific limitations: posthoc intervention, fixed suffix, singletrainingseed, frozen scorer known leniency, no unique mechanism claim. All previous science is DONE.\n',
        '# Future commands: no execution before exact source CR\n\n`R=.local/p011_20261020/r1`; all commands from repository root with PYTHONPATH=.\n\n1. Data environment: `scripts/prepare_p011_forced_answer_inputs.py --spec reports/p011_20261020/forced_answer_preflight_v1/SPEC.json --review $R/FORCED_ANSWER_SOURCE_CR_ACCEPTED.json`. Exactly once; publish actual manifest/roster/prefill/context/weight bindings for real A2-lite before paid work.\n2. Modal environment: `scripts/record_p011_forced_answer_budget.py --review $R/FORCED_ANSWER_SOURCE_CR_ACCEPTED.json --runtime-review $R/FORCED_ANSWER_ACTUAL_A2_ACCEPTED.json --directory $R/forced_answer_r1/budget_DATED`. Necessary fresh once; abort if insufficient.\n3. Modal environment: `scripts/p011_forced_answer_io.py upload --review $R/FORCED_ANSWER_SOURCE_CR_ACCEPTED.json`. New requests only; no labels/weights.\n4. Verify ordinary execution HEAD published; then `.local/midpoint_20261011/venv/bin/modal run experiments/p011/modal_forced_answer.py --source-review $R/FORCED_ANSWER_SOURCE_CR_ACCEPTED.json --runtime-review $R/FORCED_ANSWER_ACTUAL_A2_ACCEPTED.json --budget-json $R/forced_answer_r1/budget_DATED/BUDGET.json`. One attempt. No commit/push between entry and SUBMITTED.\n5. After original CLI terminal and app stopped: same IO `collect` once inModalenv. Per complete cell, `audit --cell CELL` once indata_pipelineenv, `score --cell CELL` once inmath_verify_env, with the same source review. Never score partial cells.\n6. Analysis environment: `scripts/analyze_p011_forced_answer.py --review $R/FORCED_ANSWER_SOURCE_CR_ACCEPTED.json` once. Publish all available cells/contrasts, unavailable statuses and original references, then real actualA3.\n\nEnvironment python paths: `.local/midpoint_20261011/venv/bin/python`, `.local/midpoint_20261011/data_pipeline/venv/bin/python`, `.local/p009_20261014/r1/math_verify_env/bin/python`, `.local/p009_20261014/r1/analysis_env/bin/python`.\n')
    create(R/'OWNER0205_REVIEW_PACKETS_BUILD_DONE.json',{'utc':utc(),'census_sources':len(census_sources),
        'forced_sources':len(forced['source_files']),'new_production':False,
        'packets':[str(P/'ot3_full_math_census_preflight_v1'),str(P/'forced_answer_preflight_v1')]})
    print('Created source-review metadata only; no production.',flush=True)


if __name__=='__main__':main()

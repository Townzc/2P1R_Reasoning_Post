"""Prepare a new metadata-only review packet; no scientific entry is called."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import shutil

R = Path('.local/p011_20261020/r1')
P = Path('reports/p011_20261020/ext3b_local_endpoint_links_preflight_v1')


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def put(name, value):
    with (P / name).open('x') as f:
        if isinstance(value, str):
            f.write(value)
        else:
            json.dump(value, f, ensure_ascii=False, indent=2)
            f.write('\n')


P.mkdir(exist_ok=False)
original = json.loads(Path('reports/p011_20261020/ext3b_preentry_schema_runtime_v3/SPEC.json').read_text())
diagnosis = json.loads((R / 'EXT3B_LOCAL_ENDPOINT_SYMLINK_FAILURE_DIAGNOSIS.json').read_text())
sources = dict(original['source_files'])
new_sources = ['experiments/p011/local_endpoint_link_verify.py', 'scripts/p011_ext3b_local_link_closeout.py']
for name in new_sources:
    if name in sources:
        raise ValueError('Only genuinely new local wrapper/helper sources')
    sources[name] = sha(name)
flags = [
    'exact89_source_bindings_and_original87_unchanged_accepted',
    'only_two_declared_endpoint_links_to_fixed_prior_targets_and_exact_bytes_accepted',
    'exact_pre_science_large_failure_preserved_and_completed_prefix_reused_without_reexecution',
    'small_first_full_oracle_and_unchanged_actual_inputs_jobs_source_A2_carry_accepted',
    'original_full_state_optimizer_RNG_trajectory_native_decoder_functions_unchanged',
    'original_scalar_pool_and_two_original10000_question_bootstrap_seed20261021_unchanged',
    'original_absolute_closeout_clock_score7200_and_local_oracle_concurrency1_retained',
    'separate_once_only_local_output_fences_no_new_model_upload_encoding_budget_or_retry',
    'actual_results_A3_still_required_private_binary_and_single_seed_limits_retained',
]
spec = {
    'scope': 'p011-ext-3B-local-endpoint-links-closeout-CR',
    'request_id': 'p011-ext-3B-local-endpoint-links-closeout-CR-r1',
    'source_files': sources, 'source_count': len(sources), 'original_source_count': len(original['source_files']),
    'original_target': '63523da98cb0325c6a5956d05c251fda6cb0500b',
    'original_spec_sha256': '055bcdb79bd28a376175b93b748864165fda5b70bcef8e84349f5549d1a9d094',
    'actual_target': '5f1003c5f459ed3f4f1780decae49e2141a37d1a',
    'actual_job_manifest_sha256': 'bf556ba4e18ab52b6613d6e86eec207ec6dedab9937accb2b754f94368453a24',
    'input_manifest_sha256': 'afd5fe1bd7e13d28353d28fe4e7b6e2e296babcbc7752dc5cec843bdb7d17bfc',
    'large_original_result_sha256': '472e60e6beb985ae94dc326f14262af976491620edb3ab709cb713c53600ef94',
    'failed_prefix_bindings': diagnosis['bindings'],
    'required_flags': flags, 'production': False,
    'direct_authority': 'Owner delegated overnight dispositions to Claude; this is local closeout of the same two completed jobs.',
    'old_failed_audit_immutable': True, 'new_output_root': '.local/p011_20261020/r1/ext3b_runs_r1/local_endpoint_links_r1',
    'no_new_GPU_or_transfer_or_reencoding': True,
}
if len(sources) != 89 or len(original['source_files']) != 87:
    raise ValueError('Exact original87 plus two local sources expected')
put('SPEC.json', spec)
put('SOURCE_BINDINGS.json', {'original87_referenced_not_rehashed_or_republished': True,
                           'new_source_files': {k: sources[k] for k in new_sources}, 'all_source_files': sources})
put('FAILURE_DIAGNOSIS.json', {
    'observed_utc': diagnosis['observed_utc'], 'failure': diagnosis['failure'],
    'original_oracle_CLI39311': 'EXIT1_CONSUMED',
    'cause': diagnosis['cause'],
    'endpoint_links': {k: {'declared': v['declared_manifest'],
                          'observed': v['observed_bytes_sha256'],
                          'target': '.local/p011_20261020/r1/ext4b_inputs_r1/' + k}
                       for k, v in diagnosis['links'].items()},
    'successful_prefix_reused_next': diagnosis['successful_prefix_reused_next'],
    'scientific_stages_not_started': diagnosis['not_started'],
    'large_extracted_payload_and_failure_kept_in_place': True,
    'private_full_binary_independently_reviewed': False,
})
for source, target in [
    (R / 'ext3b_runs_r1/audit/long_R9072x1_S-F15_s17_attempt1/FAILED.json', 'ORIGINAL_FAILED.json'),
    (R / 'EXT3B_R9072_FIRST_FULL_ORACLE_CLI_EXIT.json', 'ORIGINAL_ORACLE_CLI_EXIT.json'),
    (R / 'EXT3B_LOCAL_LINK_NEW_CHECKS_CLI_EXIT.json', 'NEW_CHECKS.json'),
    (R / 'EXT3B_LOCAL_LINK_NEW_CHECKS.log', 'NEW_CHECKS.log'),
]:
    shutil.copyfile(source, P / target)
trace = (R / 'EXT3B_R9072_FIRST_FULL_ORACLE.log').read_text()
put('ORIGINAL_ORACLE_TRACE_REDACTED.txt', trace.replace(str(Path.cwd()), '<WORKSPACE>'))
put('TRACE_PROJECTION.json', {'original_sha256': diagnosis['bindings'][str(R / 'EXT3B_R9072_FIRST_FULL_ORACLE.log')]['sha256'],
                            'only_workspace_absolute_prefix_redacted': True, 'original_raw_log_private_and_unchanged': True})
small = json.loads((R / 'EXT3B_R3024_ORIGINAL_RESULT_1457.json').read_text())
put('SMALL_ORIGINAL_RESULT_PROJECTION.json', small)
put('README.md', '''# Exact local endpoint-link correction — production NOT RUN

Both original workers returned completed 1,935 updates and 2,500 MATH outputs. The first large-cell local audit failed before training-state verification or native decoding: the original immutable-artifact verifier rejects all symlinks, whereas the approved 3B prefix constructor explicitly retained two endpoint symlinks. Both targets' bytes still match the admitted manifests. No model/data/scorer change is proposed.

Review only the two new source files and their use of the unchanged 87 dependencies. The helper accepts precisely the two endpoint links to the original `ext4b_inputs_r1` files with the original size/SHA. Other links are rejected. The large continuation reuses its already completed archive extraction, identity/ledger/journal checks and first three regular input checks; its original FAILED record and payload stay immutable. Its first state/optimizer/RNG/trajectory oracle, first 2,500-output native decode, first frozen score, and the small cell's first oracle/score remain NOT RUN. The small collector is independently active and will never be restarted by this adapter.

Separate local output fences preserve the failed prefix and prevent any duplicate successful science. Score/analysis paths point to the new oracle locations; scientific functions, 10,000 question bootstrap/seed 20261021, original deadlines and score cap remain unchanged. Analysis is deliberately limited to the two full, completed MATH results and LARGE-minus-SMALL. There is no new GPU, upload, tokenization, budget admission, timer reset or automatic retry. The old model/preentry failures and all original caps remain historical facts.

Only five new synthetic helper methods were executed; the production continuation and original scientific tests were not run. Private checkpoint/export bytes and ADMISSION are not in this packet, and no independent reviewer access is claimed. Actual-results A3 still follows the first successful local closeout.
''')
put('FUTURE_COMMANDS.md', '''# Only after a real exact local CR/disposition PASS

1. Save the fixed non-Z1 Claude report and all nine flags to R/EXT3B_LOCAL_ENDPOINT_LINKS_CR_ACCEPTED.json, bound to this SPEC/source map and original failure. Do not infer acceptance from the earlier87-source report.
2. Inspect original collector78096 and its COMPLETED/FAILED first. Never repeat either collector, original model, upload or data constructor. Original large failed oracle39311 remains EXIT1_CONSUMED.
3. Use PYTHONPATH=. and scripts/p011_ext3b_local_link_closeout.py audit --attempt-name long_R9072x1_S-F15_s17_attempt1 (then small), with --source-review R/EXT3B_PREENTRY_SCHEMA_RUNTIME_CR_ACCEPTED.json --actual-review R/EXT3B_PREENTRY_SCHEMA_A2_CARRY_ACCEPTED.json --local-review R/EXT3B_LOCAL_ENDPOINT_LINKS_CR_ACCEPTED.json. Use .local/midpoint_20261011/data_pipeline/venv/bin/python; fullstate concurrency at most1. Never call the old failing audit again.
4. After each real first oracle success, the same script score/exact attempt/reviews with .local/p009_20261014/r1/math_verify_env/bin/python once. Original 7200/absolute result window remains enforced.
5. After both first score successes, same script analysis/reviews once using .local/p009_20261014/r1/analysis_env/bin/python. It invokes the two original question-bootstrap functions; no old contrasts are repeated.
6. First new results publication and genuine actual A3 independent original-token decoding/correctness; private binary/single-seed/scorer limitations and this failed local prefix disclosed. No output is success before its real receipt.
''')
shutil.copyfile(__file__, P / 'PREPARE_PACKET.py')
members = {p.name: {'bytes': p.stat().st_size, 'sha256': sha(p)} for p in sorted(P.iterdir()) if p.is_file()}
put('MANIFEST.json', {'files': members, 'manifest_self_excluded': True, 'old_scientific_archives_not_read_or_rebuilt': True})
receipt = {'utc': datetime.now(timezone.utc).isoformat(), 'packet': str(P), 'source_count': len(sources),
           'spec_sha256': sha(P / 'SPEC.json'), 'manifest_sha256': sha(P / 'MANIFEST.json'),
           'production': 'NOT_RUN', 'metadata_only': True, 'old_science_tests_repeated': False}
with (R / 'EXT3B_LOCAL_ENDPOINT_LINKS_PACKET_BUILD_DONE.json').open('x') as f:
    json.dump(receipt, f, indent=2)
    f.write('\n')
print(json.dumps(receipt))

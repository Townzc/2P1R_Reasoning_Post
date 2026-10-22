"""Once-only metadata acceptance; no scientific computation or old artifact checks."""
from pathlib import Path
from datetime import datetime, timezone
import copy
import hashlib
import json

R = Path('.local/p011_20261020/r1')
P = Path('reports/p011_20261020/review_7873c88d_owner_actual_A3_accepted_v1')
REQUEST = Path('reports/p011_20261020/OWNER150_COMPLETE_RESULTS_ACTUAL_A3_REQUEST.md')
now = datetime.now(timezone.utc).isoformat()
poll = json.loads((R / 'LATEST_REVIEW_POLL.json').read_text())
assert poll['head'] == '7873c88d5713e2328204e54ad0bd6c8ed92cbd43'
source = Path(poll['directory'])
fetch = json.loads((source / 'OWNER_A3_REPORT_FETCH_RECEIPT.json').read_text())
display = json.loads((source / 'OWNER_A3_REPORT_FULLTEXT_DISPLAY.json').read_text())
support = json.loads((source / 'OWNER_A3_NEW_SUPPORT_FETCH.json').read_text())
assert not P.exists()
assert not (R / 'OWNER150_COMPLETE_RESULTS_ACTUAL_A3_ACCEPTED.json').exists()
P.mkdir()

def put(path, obj):
    with path.open('x') as stream:
        json.dump(obj, stream, indent=2, ensure_ascii=False)
        stream.write('\n')

def put_text(path, text):
    with path.open('x') as stream:
        stream.write(text)

def copy_bytes(src, dest):
    with dest.open('xb') as stream:
        stream.write(src.read_bytes())

flags = [
    'complete_attempt_specific_training_and_declared_endpoint_scopes_accepted',
    'D2_owner_option_a_math_aime_complete_AMC_incomplete_math_only_contrast_accepted',
    'independent_native_decode_and_correctness_scope_disclosed',
    'all_available_original_paired_contrasts_and_missing_cells_disclosed',
    'posthoc_smoke_direct_owner_preselection_and_single_seed_limits_disclosed',
    'private_binary_and_frozen_scorer_access_limits_disclosed',
]
acceptance = {
    'schema': 'p011.actual_review_acceptance.v1',
    'request_id': 'p011-owner150-A-D-complete-results-and-original-contrasts-actual-A3-r1',
    'scope': 'p011-owner150-A-D-complete-results-and-original-contrasts-actual-A3',
    'target_commit': 'fe82972a952a151d14d63dd052f00502560ff9c9',
    'packet': 'reports/p011_20261020/owner150_complete_actual_results_v1',
    'manifest_sha256': '6ddb9969db8ec03962a0c187c19f5b080190081a6bca515114aca5e8c796c9b2',
    'actual_result_binding_sha256': 'b9311fbe8e2b4c1ea31af8d13b18ce69c1bf6e409e66f26fa8a21436365242b7',
    'report': fetch,
    'reviewer': 'Claude',
    'report_verdict_verbatim': 'numbers ACCEPTED (A3 PASS)',
    'acceptance_status': 'PASS_WITH_EXPLICIT_ACCESS_AND_FROZEN_SCORER_NOTES',
    'flags': {key: True for key in flags},
    'flag_evidence_verbatim': 'All six required flags are true as scoped above, with the access limits stated.',
    'cost_projection_reconciliation_scope_disclosed': True,
    'cost_projection_independently_reconciled': False,
    'cost_scope': 'Exact-new-app projection only; reviewer cannot access billing; not an invoice.',
    'abbreviated_binding_resolution': 'Report names target fe82972a, request 91b65ec1, exact packet, MANIFEST 6ddb9969 and ACTUAL_RESULT_BINDING b9311fbe; expanded against the unchanged fixed request, not by editing the report.',
    'git_event_utc': fetch['file_commit']['committer']['date'],
    'report_self_time_verbatim': '2026-10-22 ~01:45 UTC',
    'self_time_differs_from_git_event': True,
    'discovered_utc': poll['observed_utc'],
    'full_text_display': display,
    'full_read_confirmed_utc': now,
    'independent_review_scope': {
        'native_token_rows_decoded': 16500,
        'jobs': ['baseline', 'A1r2', 'A5', 'A6', 'A7'],
        'raw_text_region_stop_mismatches': 0,
        'non_string_positive_rows': 356,
        'unique_manual_positive_equivalence_pairs': 65,
        'primary_paired_contrasts_independently_recomputed': 5,
        'full_symbolic_engine_rerun': False,
        'full_symbolic_engine_limit': 'math-verify not rerunnable; PyPI blocked',
        'private_checkpoints_exports_ADMISSION_read': False,
        'saved_state_optimizer_RNG_oracles_read': False,
        'collect_records_read': False,
        'local_oracles_independently_reexecuted': False,
    },
    'D2_separate_disclosure_contract_closed': False,
    'D2_scope_note': 'The six owner-packet flags do not close the separate D2 source/actual metadata-only disclosure clarification. c97efacb source PASS and c999e0d8 numerical A3 remain retained with those explicit fields pending.',
    'posthoc_smoke': 'FAIL; 22.6% A7 EOS and 35.85pp below baseline; no prospective pass.',
    'single_training_seed': 17,
    'question_intervals_not_training_seed_population': True,
    'causal_claim_adopted': False,
    'reviewer_loop_heuristic': 'zlib ratio on final 6000 characters <0.12; descriptive reviewer analysis, not rerun or adopted as a causal finding',
    'reviewer_secondary_greedy_intervals': 'Retained in original report; not substituted for saved primary contrasts or added to frozen T5/T6.',
    'Codex_model_decode_score_bootstrap_or_test_reexecution': False,
    'reviewer_scripts_executed_by_Codex': False,
    'P011_final_A5': False,
    'recorded_utc': now,
}
assert fetch['sha256'] == '66d7b3e54bd1a0aa658befb8d301b9ebffd0a8aebda6c2186b2189273fd1f180'
put(R / 'OWNER150_COMPLETE_RESULTS_ACTUAL_A3_ACCEPTED.json', acceptance)
put(P / 'ACCEPTED.json', acceptance)
copy_bytes(source / 'REPORT_OWNER150_COMPLETE_ACTUAL_A3.md', P / 'REPORT_OWNER150_COMPLETE_ACTUAL_A3.md')
for name in ['OWNER_A3_REPORT_FETCH_RECEIPT.json', 'OWNER_A3_REPORT_FULLTEXT_DISPLAY.json', 'OWNER_A3_NEW_SUPPORT_FETCH.json', 'HEAD_RECEIPT.json']:
    copy_bytes(source / name, P / name)
(P / 'reviewer_support').mkdir()
for row in support['files']:
    copy_bytes(Path(row['local_path']), P / 'reviewer_support' / Path(row['local_path']).name)

sensitivity = {
    'source_report_sha256': fetch['sha256'],
    'original_frozen_scores_labels_vectors_and_intervals_unchanged': True,
    'reviewer_known_normalization_violations': [
        {'job': 'baseline', 'question_id': 'math500/179', 'endpoint': 'sample1'},
        {'job': 'baseline', 'question_id': 'math500/179', 'endpoint': 'greedy'},
    ],
    'reviewer_reason': 'Plane equation scaled or sign-flipped; violates specified A>0 and gcd=1 normalization.',
    'baseline_saved_sample': {'correct': 1007, 'total': 2000},
    'baseline_saved_greedy': {'correct': 269, 'total': 500},
    'descriptive_one_row_sample_sensitivity_only': {'correct': 1006, 'total': 2000, 'accuracy': 0.503, 'change_pp': -0.05},
    'descriptive_one_row_greedy_sensitivity_only': {'correct': 268, 'total': 500, 'accuracy': 0.536, 'change_pp': -0.2},
    'other_reviewed_leniencies': 'Base subscripts dropped in A1/A5/A6 and one unsimplified 8/18 in A6; reviewer accepts them as lenient-equivalent and requests no original label changes.',
    'new_scoring_or_bootstrap': False,
    'replacement_result': False,
    'new_sensitivity_confidence_intervals_computed': False,
}
put(P / 'FROZEN_SCORER_SENSITIVITY_NOTE.json', sensitivity)
put(P / 'READ_SCOPE_NOTE.json', {
    'recorded_utc': now,
    'read_only_manifest_display': 'A broad ACTUAL_RESULT_BINDING display was truncated; a guessed separate REVIEW_REQUIREMENTS path was absent. The unchanged request and required_true_flags were used; no data, model, scoring, verification or artifact was rerun.',
    'current_old_scientific_artifacts_reverified': False,
    'new_review_files_only': True,
})
put_text(P / 'README.md', f'''# Owner complete-result actual A3 accepted

Claude report 7873c88d / {fetch['sha256']} explicitly accepts the numerical results at fe82972a, with all six required flags scoped to the report's access limits. The cost flag discloses a public projection, not independent billing reconciliation. Git event 01:33:37 UTC, report self-time approximately 01:45 UTC, discovery {poll['observed_utc']} and actual full-read confirmation {now} are distinct.

The reviewer independently decoded all 16,500 new native-token rows, manually checked 65 unique non-string positive pairs (356 rows), and reproduced the five primary paired-question contrasts. The full symbolic engine, private checkpoints/exports/ADMISSION, saved state/optimizer/RNG oracle records and collect records were not independently accessed or executed. The original local full oracles remain first-execution records, not external binary verification.

The original posthoc A7 smoke remains FAIL. Frozen scores, vectors, confidence intervals, T5/T6 bytes and original scientific evidence remain unchanged. Two baseline normalization violations and other scorer leniencies are disclosed separately. The arithmetic sensitivity note is not a rescore or replacement result. The reviewer's loop heuristic and secondary greedy intervals remain reviewer-only descriptive support; no causal mechanism or training-seed population claim is adopted, and no reviewer script is run.

The separate D2 metadata-only disclosure clarification is still pending. Its previously accepted numerical A3 and source PASS are not reopened. This owner actual A3 is not P011's formal 05:00 UTC freeze or final A5. Those remain required; P010 final A5 is already closed. Course interpretation remains owner-written.
''')
copy_bytes(Path(__file__), P / 'PRODUCER.py')

index_path = Path('reports/p007_audit/INDEX.json')
index = json.loads(index_path.read_text())
prior = copy.deepcopy(index)
current = index['p011_owner150_current']
current.update({
    'recorded_utc': now,
    'owner_complete_actual_A3_accepted': True,
    'future_owner_actual_A3': 'ACCEPTED_NUMERICAL_PASS_WITH_EXPLICIT_LIMITS',
    'owner_complete_actual_A3_report_sha256': fetch['sha256'],
    'owner_complete_actual_A3_review_commit': poll['head'],
    'owner_complete_actual_A3_acceptance_packet': str(P),
    'owner_complete_actual_A3_cost_projection_independently_reconciled': False,
    'owner_complete_actual_A3_private_binary_read': False,
    'owner_frozen_scorer_sensitivity_note': str(P / 'FROZEN_SCORER_SENSITIVITY_NOTE.json'),
    'last_shared_audit_poll_utc': poll['observed_utc'],
    'next_normal_D2_disclosure_review_utc': poll['next_normal_utc'],
    'owner_actual_A3_normal_review_utc': None,
    'D2_clarification_normal_review_utc': poll['next_normal_utc'],
})
for key in ['A1_retry', 'A5', 'A6']:
    current[key] = 'COMPLETE_ACTUAL_A3_ACCEPTED_WITH_ACCESS_AND_SCORER_NOTES'
current['A7'] = 'COMPLETE_ACTUAL_A3_ACCEPTED_POSTHOC_SMOKE_FAIL'
current['baseline_actual_A3'] = 'ACCEPTED_WITH_TWO_NORMALIZATION_VIOLATIONS_DISCLOSED_ORIGINAL_SCORES_UNCHANGED'
index['p011'].update({
    'status': 'ALL_LOCAL_SCIENCE_DONE_OWNER_ACTUAL_A3_ACCEPTED_D2_DISCLOSURE_AND_P011_FINAL_FREEZE_A5_PENDING',
    'last_review_head': poll['head'],
    'last_review_observed_utc': poll['observed_utc'],
    'last_full_review_read_utc': now,
    'latest_acceptance_packet': str(P),
})
request_id = acceptance['request_id']
existing = [x for x in index['review_requests'] if x.get('request_id') == request_id]
record = existing[0] if existing else {}
record.update({'request_id': request_id, 'scope': acceptance['scope'], 'target_commit': acceptance['target_commit'], 'status': 'ACTUAL_A3_ACCEPTED_WITH_ACCESS_AND_SCORER_NOTES', 'request_file': str(REQUEST), 'report_sha256': fetch['sha256'], 'review_commit': poll['head'], 'acceptance_packet': str(P)})
if not existing:
    index['review_requests'].append(record)
for record in index['review_requests']:
    if record.get('request_id') == 'p011-D2-option-a-local-scope-asynchronous-CR-r1':
        record['status'] = 'SOURCE_PASS_NO_STOP_EXPLICIT_DISCLOSURE_CLARIFICATION_PENDING'
    elif record.get('request_id') == 'p011-D1-D2-option-a-complete-MATH-AIME-and-MATH-contrasts-actual-A3-r1':
        record['status'] = 'NUMERICAL_ACTUAL_A3_ACCEPTED_EXPLICIT_DISCLOSURE_CLARIFICATION_PENDING'
index['last_updated_utc'] = now
changes = []
def changed(a, b, path=''):
    if isinstance(a, dict) and isinstance(b, dict):
        for key in sorted(set(a) | set(b)):
            changed(a.get(key), b.get(key), path + '/' + key)
    elif a != b:
        changes.append({'path': path, 'prior': a, 'new': b})
changed(prior, index)
put(P / 'INDEX_CURRENT_STATE_CHANGES.json', {'recorded_utc': now, 'changes': changes})
index_path.write_text(json.dumps(index, indent=2, ensure_ascii=False) + '\n')

entry = f'''### {now} — Owner A/baseline actual A3 accepted; D2 disclosures and final freeze remain

Claude7873c88d/reportSHA{fetch['sha256']} accepts the fixed owner-result targetfe82972a with all six required flags and disclosed cost-projection scope. Independent native BPE decode covered16500/16500 rows with zero text/region/stop mismatch,65 unique non-string positive equivalence pairs covered356 rows, and all five primary paired-question contrasts were reproduced. Full symbolic engine/private state/exports/ADMISSION/saved oracles/collect records and billing reconciliation were not independently accessed or rerun. The original report's approximately01:45 self-time is retained separately from Git01:33:37, discovery02:01:41.898111 and full-read confirmation{now}. Reviewer scripts were preserved but never executed by Codex.

Two baseline math500/179 normalization violations are separately disclosed: one sampled and one greedy row. Original1007/2000 and269/500, all labels/vectors/CI and technical T5/T6 bytes stay unchanged; descriptive one-row sensitivities are1006/2000 and268/500 only, with no rescore/bootstrap. Other base-subscript/unsimplified-answer leniencies remain explicit. A7 posthoc smoke FAIL, single-seed and noncausal limits remain. Reviewer-only loop diagnostics/secondary greedy intervals are not new registered results.

D2 source/numerical PASS is retained, but its same-request explicit private-state/missing-wholecycle/single-seed/cap/fence clarification is still pending; the new A report does not close that separate contract. Only this pending clarification warrants the next normal shared HEAD at{poll['next_normal_utc']}. P011 real05UTC freeze and truefinalA5 are still NOTRUN/required; P010 is closed. All science and technical builders remain DONE, zero active compute, no new billing or models. New acceptance packet {P} contains the exact report/support and access/sensitivity notes.

'''
for path in [Path('docs/WORKBOARD.md'), Path('reports/sft_allocation_midpoint_20261011/RUN_LOG.md'), Path('AI_USE_LOG.md')]:
    path.write_text(entry + path.read_text())
REQUEST.write_text(f'''## Closed actual A3 — {now}

Claude7873c88d/report66d7b3e54bd1a0aa658befb8d301b9ebffd0a8aebda6c2186b2189273fd1f180 explicitly accepts the six required flags with the stated access limits and cost-projection disclosure. Exact report, support, event/read records and scorer-sensitivity note: {P}. This request is CLOSED; no repeated scientific review is requested. Saved scores, vectors, CI and T5/T6 original bytes are unchanged. The separate D2 metadata-only clarification remains pending on its existing requests. P011 real05UTCfreeze and finalA5 remain required; this A3 does not replace them.

''' + REQUEST.read_text())
for name in ['ACTIVE_HANDOFF.md', 'LIVE_P011_INITIAL_DATA_CR_HANDOFF.md']:
    path = R / name
    path.write_text(entry + path.read_text())
freeze = R / 'LIVE_P011_FINAL_FREEZE_HANDOFF.md'
freeze.write_text(f'''## Owner actual A3 accepted; retain separate D2 pending disclosure — {now}

New owner acceptance: {P}, report66d7b3e54bd1a0aa658befb8d301b9ebffd0a8aebda6c2186b2189273fd1f180/Claude7873c88d. Six flags and cost-projection disclosure explicitly accepted with private/oracle/billing access limits. Frozen T5/T6 bytes stay unchanged; copy the later acceptance and scorer-sensitivity note separately at the real05UTCfreeze. D2 explicit metadata-only disclosure clarification remains pending. No formalfreeze/finalA5 has run. Existing old report/publisher/science must not be repeated.

''' + freeze.read_text())
files = {}
for path in sorted(P.rglob('*')):
    if path.is_file():
        data = path.read_bytes()
        files[path.relative_to(P).as_posix()] = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
put(P / 'MANIFEST.json', {'schema': 'p011.review_acceptance_packet.v1', 'recorded_utc': now, 'files': files, 'old_scientific_artifacts_reverified': False})
all_changed = [str(p) for p in P.rglob('*') if p.is_file()] + [str(index_path), str(REQUEST), 'docs/WORKBOARD.md', 'reports/sft_allocation_midpoint_20261011/RUN_LOG.md', 'AI_USE_LOG.md']
put(R / 'OWNER_A3_7873_NEW_FILES_TO_PUBLISH.json', {'recorded_utc': now, 'files': sorted(all_changed)})
put(R / 'OWNER_A3_7873_METADATA_DONE.json', {'completed_utc': datetime.now(timezone.utc).isoformat(), 'packet': str(P), 'new_packet_files': len(files) + 1, 'changed_git_files': len(all_changed), 'scientific_computation': False, 'old_builder_rerun': False})
registry_path = R / 'CLI_SESSIONS.json'
registry = json.loads(registry_path.read_text())
registry['owner_A3_7873_support_fetch'] = {'session_id': 36475, 'state': 'EXIT0_CONSUMED', 'recorded_utc': now, 'receipt': str(source / 'OWNER_A3_NEW_SUPPORT_FETCH.json')}
registry['owner_A3_7873_metadata_acceptance'] = {'state': 'EXIT0_DIRECT_CONSUMED', 'recorded_utc': now, 'receipt': str(R / 'OWNER_A3_7873_METADATA_DONE.json')}
registry_path.write_text(json.dumps(registry, indent=2) + '\n')
print(json.dumps({'packet': str(P), 'new_packet_files': len(files) + 1, 'changed_git_files': len(all_changed), 'accepted': True, 'D2_disclosure_pending': True}, indent=2))

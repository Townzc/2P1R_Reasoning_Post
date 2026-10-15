"""Six registered S1 slots; actual outcome, budget and exact reviews required.

This candidate has no approval writer or fallback. Old reservations, failed NC
identities and the original NC/futility gates remain part of every release.
"""
from datetime import datetime, timezone
import hashlib
import json

from experiments.sft_allocation_midpoint.common import digest
from experiments.learning_regime_p009.high_throughput_v1 import engine_kwargs
from experiments.learning_regime_p009.stage1_s1_funded_contract import (
    RUNS, recipe, limits_checked, checked_slot_budget, forecast,
    STAGE1_CAP_CENTS, NC_RESERVED_CENTS,
)

CAMPAIGN = 'p009-stage1-s1-20261015-r1'
SCOPE = 'p009-stage1-S1-exact-runtime-input-and-numeric'
BUDGET_REQUEST = 'p009-stage1-registered-S1-budget-r1'
NC_SCOPE = 'p009-stage1-NC-guard-repair-complete-pair-A4'
FUTILITY_SCOPE = 'p009-stage1-S1-first-pair-complete-and-futility-A4'
G0_SHA = 'a6479f674f52bbf5dd1fd4d66362a4651a1ad18ecfc37c03807c24249f274477'
INPUT_SHA = '8e27ab943cb903655f30882bbf5b4210e78c8aec3aa01040e4ae0336dc1ba665'
INPUT_BASIS = '47c5c5e88877d50056a76b7595f20e6aff6abfc6aa54593f41d421854b29ebdb'
INPUT_ARCHIVE = 'ba1fbefbe441f0871a0c1285168bd8128ddf67de34dd451199fc8185adfdcde4'
INTERNAL_AMENDMENT = '4f2a56f3e794fd4182e1d9e36c30af0c09c0d6751dea157a3abd34918abf2872'
FIRST_PAIR = tuple(RUNS)[:2]
LIMITS = dict(worker_seconds=4500, platform_seconds=4560, startup_seconds=600,
              full_window_seconds=5200, reserved_cents=655)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def hash_checked(value, size=64):
    return (isinstance(value, str) and len(value) == size
            and all(c in '0123456789abcdef' for c in value))


def dispatch_key(run):
    recipe(run)
    return 'midpoint/'+CAMPAIGN+'/dispatch/'+run


def logical_key(run):
    recipe(run)
    return 'midpoint/p009-stage1-logical/'+run+'/dispatch'


def intent(spec, run):
    recipe(run)
    return dict(run_id=run, config_sha256=digest(spec['configs'][run]),
                source_sha256=digest(spec['source_files']), data_sha256=digest(spec['inputs']))


def marker(spec, run, release):
    recipe(run)
    return dict(campaign=CAMPAIGN, run_id=run, spec_sha256=digest(spec),
        source_sha256=digest(spec['source_files']), input_manifest_sha256=digest(spec['inputs']),
        provider_app_id=release['dispatch_app_id'], execution_commit=release['execution_commit'],
        NC_A4_report_sha256=release['NC_A4_review']['report_sha256'],
        budget_proxy_comment_sha256=release['budget_owner_decision']['comment_sha256'],
        futility_A4_report_sha256=(release['futility_review']['report_sha256']
                                  if run not in FIRST_PAIR else None), automatic_retry=False)


def exact_review(item, scope, target, report_sha=None):
    require(isinstance(item, dict) and item.get('scope') == scope
        and item.get('target_commit') == target and hash_checked(target, 40)
        and hash_checked(item.get('report_commit'), 40) and hash_checked(item.get('report_sha256'))
        and (report_sha is None or item['report_sha256'] == report_sha),
        'Actual complete fixed scoped report is required')


def budget_proxy_checked(value, spec):
    c = value.get('comment', {})
    require(c.get('user', {}).get('login') == 'Townzc' and c.get('author_association') == 'OWNER'
        and c.get('performed_via_github_app', {}).get('slug') == 'claude'
        and type(c.get('id')) is int and c['id'] > 0
        and c.get('html_url') == 'https://github.com/Townzc/2P1R_Reasoning_Post/issues/13#issuecomment-'+str(c['id'])
        and c.get('body', '').startswith('【Owner 代理决定】') and BUDGET_REQUEST in c['body'],
        'Established original auditor proxy comment with the exact budget request is required')
    created = datetime.fromisoformat(c['created_at'].replace('Z', '+00:00'))
    expiry = datetime(2026, 10, 15, 14, tzinfo=timezone.utc)
    require(created.tzinfo is not None and created < expiry
        and created >= datetime(2026, 10, 15, 5, tzinfo=timezone.utc)
        # The original proxy receipt explicitly used UTF-8 Chinese characters;
        # common.digest uses escaped ASCII. Preserve that original convention.
        and value.get('comment_sha256') == hashlib.sha256(json.dumps(c,
            sort_keys=True, separators=(',', ':'), ensure_ascii=False,
            allow_nan=False).encode()).hexdigest()
        and hash_checked(value.get('raw_comment_file_sha256'))
        and value.get('decision') == 'APPROVE_REGISTERED_S1_BUDGET_ALLOCATION'
        and value.get('stage1_cap_cents') == 7000 and value.get('experiment_cap_cents') == 15000
        and value.get('additional_overnight_authority_used_cents') == 2000
        and value.get('prior_stage1_reserved_cents') == NC_RESERVED_CENTS
        and value.get('scientific_rules_unchanged') is True
        and value.get('independent_exact_audit_required') is True
        and value.get('reason') and value['reason'] in c['body']
        and value['comment_sha256'] == spec['budget_proxy_comment_sha256'],
        'Actual bounded proxy allocation, preserved reserves and independent audit must match')


def validate(spec, plan, run, release):
    expected = recipe(run); cap = limits_checked(spec['slots'][run])
    wanted = dict(scope=SCOPE, campaign=CAMPAIGN, slots={k:LIMITS for k in RUNS},
        engine_kwargs=engine_kwargs(), stage1_cap_cents=7000, experiment_cap_cents=15000,
        prior_stage1_reserved_cents=2620, new_reserved_cents=3930,
        project_cap_cents=45000, protected_original_cents=5000,
        maximum_concurrent_workers=4, first_paid_measurement_exceptions=0,
        G0_report_sha256=G0_SHA, input_report_sha256=INPUT_SHA,
        input_basis_file_sha256=INPUT_BASIS, input_archive_file_sha256=INPUT_ARCHIVE,
        internal_only_amendment_sha256=INTERNAL_AMENDMENT,
        deterministic_cublas_workspace=':4096:8', torch_threads=4,
        training_process_exit_before_vllm=True, historical_HF_effect_comparison=False,
        local_scoring_seconds=6000, local_scoring_pair_outer_seconds=8,
        local_scoring_max_distinct_pairs=500, local_scoring_scenario_seconds=5160.0,
        local_scoring_versions={'math-verify':'0.9.0','latex2sympy2_extended':'1.11.0',
            'antlr4-python3-runtime':'4.13.2','sympy':'1.14.0','mpmath':'1.3.0'},
        gold_file_sha256='132582ca829ff11820b9d739a14c6e3ce383aacb51dba50e406acd2d27d1b95d')
    require(all(spec.get(k) == v for k,v in wanted.items()), 'Exact registered S1 scope/caps changed')
    require(plan['campaign_id'] == CAMPAIGN and digest(plan) == spec['plan_sha256']
        and plan['slots'] == {k:dict(stage='stage1_s1', reserved_cents=655) for k in RUNS}
        and plan['stage_caps_cents'] == {'stage1_s1':3930} and plan['total_cap_cents'] == 3930
        and release['source_files'] == spec['source_files'] and release['input_readback'] == spec['inputs']
        and spec['remote_inputs'] == '/evidence/'+CAMPAIGN+'/inputs/r1'
        and spec['base']['files'] and spec['base']['remote_path'].startswith('/evidence/')
        and spec['base']['remote_path'] == spec['base']['tokenizer_remote_path'],
        'Original six-slot plan, source/input readback and base/tokenizer binding differ')
    for key in RUNS:
        require(all(spec['configs'][key].get(k) == recipe(key)[k]
                    for k in ('setting','seed','n','updates','targets')), 'Frozen scientific dose changed')
    before = checked_slot_budget(spec['slots'])
    require(spec['stage_remaining_before_cents'] == before, 'All2620 prior reserve and six655 slots must remain')
    budget_proxy_checked(release['budget_owner_decision'], spec)
    review = release['runtime_review']
    exact_review(review, SCOPE, release['review_target'])
    require(review.get('decision') in ('PASS','PASS-WITH-NOTES')
        and review.get('source_files') == spec['source_files'] and review.get('spec_sha256') == digest(spec)
        and review.get('timing_sha256') == digest(spec['timing'])
        and review.get('budget_proxy_comment_sha256') == spec['budget_proxy_comment_sha256']
        and review.get('NC_packet_manifest_sha256') == spec['NC_packet_manifest_sha256']
        and review.get('input_basis_file_sha256') == INPUT_BASIS
        and review.get('input_archive_file_sha256') == INPUT_ARCHIVE
        and review.get('all_21_training_hosts_included') is True
        and review.get('all_MATH_base_endpoint_batches_included') is True
        and review.get('uncalibrated_timing_proxy_scope_accepted') is True
        and review.get('training_process_exit_before_vllm') is True
        and review.get('local_scoring_worst_pair_scenario_accepted') is True
        and review.get('registered_NC_and_futility_gates_retained') is True
        and review.get('prior_stage1_reserved_cents') == 2620
        and review.get('new_reserved_cents') == 3930
        and review.get('first_paid_measurement_exceptions') == 0,
        'Actual exact full runtime and numeric review does not bind this release')
    nc = release['NC_A4_review']
    exact_review(nc, NC_SCOPE, spec['NC_packet_target_commit'])
    require(nc.get('decision') in ('PASS','PASS-WITH-NOTES')
        and nc.get('manifest_file_sha256') == spec['NC_packet_manifest_sha256']
        and nc.get('registered_decision_file_sha256') == spec['NC_decision_file_sha256']
        and nc.get('paired_NC_gate_passed') is True and nc.get('stop_all_positive_regimes') is False
        and nc.get('complete_logical_cells') == 2 and nc.get('failed_parent_retained') is True,
        'Actual complete paired NC A4 and unchanged stop gate required')
    g0 = release['G0_review']; inp = release['input_review']; core = release['core_review']
    exact_review(g0, 'p009-math-p1-complete-scoring-and-independent-adjudication-A2',
                 'ae8b8c3c2f1ad75bac25678d49f85f6a7c1b6694', G0_SHA)
    require(g0.get('decision') == 'PASS_WITH_SEPARATE_ELIGIBILITY_AND_G0_DISPOSITIONS'
        and g0.get('teacher_labels_eligible_for_frozen_roster') is True
        and g0.get('G0',{}).get('S1') == dict(caps=[36,68],passed=True,student_zero_correct=136,
                                             teacher_correct=359,technical_unknown=0,total=500),
        'Actual unchanged MATH eligibility and S1 G0 required')
    exact_review(inp, 'p009-stage1-S1-exact-input-and-plan',
                 '3d4c5974f195ad73bc47eec847404efff7eddeaf', INPUT_SHA)
    require(inp.get('decision') in ('PASS','PASS-WITH-NOTES')
        and inp.get('basis_file_sha256') == INPUT_BASIS and inp.get('archive_file_sha256') == INPUT_ARCHIVE
        and inp.get('P1_report_sha256') == G0_SHA, 'Actual six-cell S1 input review required')
    exact_review(core, 'p009-stage1-scientific-training-and-endpoint-core-code',
                 '919ab478f4301333e79946d2e7427a457d165108',
                 'c9b44a8090c1cde9ec4e64361cc0ae47ad06a1798925c38aaf87ad9a6fbe58e8')
    require(core.get('decision') in ('PASS','PASS-WITH-NOTES'), 'Original training scientific core review required')
    for item in (core, inp):
        require(all(spec['source_files'].get(k) == v for k,v in item['source_files'].items()),
                'Original accepted transitive sources changed')
    internal = release['internal_only_review']
    exact_review(internal, 'p009-p0-vllm-internal-only-owner-amendment',
                 '2d3e1dd13277d556b18a3569cd80c252b112d54b',
                 '9f13c52becf997815399a494bf78dede442de7939a47b4e5f091c9d589508a74')
    require(internal.get('decision') == 'PASS' and internal.get('amendment_sha256') == INTERNAL_AMENDMENT
        and internal.get('comparison_scope') == 'P009_within_vllm_only'
        and internal.get('original_scientific_comparability_passed') is False,
        'Original P0 failure and owner internal-only scope remain')
    budget = release['budget']
    require(budget.get('stage1_prior_reserved_cents') == 2620 and budget.get('new_reserved_cents') == 3930
        and budget.get('stage1_cap_cents') == 7000 and budget.get('experiment_cap_cents') == 15000
        and type(budget.get('project_prior_upper_cents')) is int
        and 0 <= budget['project_prior_upper_cents'] <= 30000,
        'Current necessary project budget, retained reservations and full S1 allocation required')
    f = forecast(0.,64,2,spec['timing']['training_block_seconds'],
                 spec['timing']['endpoint_batch_seconds'],before[run],cap)
    require(f['admitted'] and spec['timing']['total_training_hosts'] == 21
        and spec['timing']['MATH_base_endpoint_batches'] == 4
        and spec['required_records'] and len(spec['required_stopped_app_ids']) == 11,
        'All-host timing, actual complete NC dependencies and full numeric window required')
    if run not in FIRST_PAIR:
        fut = release['futility_review']
        exact_review(fut, FUTILITY_SCOPE, release['futility_target_commit'])
        require(fut.get('decision') in ('PASS','PASS-WITH-NOTES')
            and fut.get('NC_A4_report_sha256') == nc['report_sha256']
            and fut.get('S1_G0_report_sha256') == G0_SHA
            and fut.get('futility_stopped') is False and fut.get('remaining_S1_allowed') is True
            and fut.get('first_pair_run_ids') == list(FIRST_PAIR)
            and isinstance(fut.get('first_pair_app_ids'), list)
            and len(set(fut['first_pair_app_ids'])) == 2
            and all(isinstance(x,str) and x.startswith('ap-') for x in fut['first_pair_app_ids'])
            and set(fut.get('required_terminal_records',{})) ==
                {'midpoint/'+CAMPAIGN+'/terminal/'+k for k in FIRST_PAIR}
            and all(v.get('status') == 'completed' for v in fut['required_terminal_records'].values()),
            'Actual complete first S1 pair and unchanged registered futility A4 required')
    return dict(cap, **expected)


def require_unused(records, logical, run, plan):
    recipe(run); prefix = 'midpoint/'+CAMPAIGN+'/'
    require(prefix+'campaign' not in records or records[prefix+'campaign'] == plan,
            'Original immutable campaign plan changed')
    require(logical.get(logical_key(run)) is None, 'Logical slot already dispatched or unknown')
    for key in records:
        require(key.startswith(prefix), 'Foreign campaign record')
        s = key[len(prefix):]; p = s.split('/')
        allowed = (s == 'campaign'
            or (len(p) == 2 and p[0] in ('claim','intent','terminal','dispatch') and p[1] in RUNS)
            or (len(p) == 3 and p[0] == 'attempt' and p[1] in RUNS and bool(p[2]))
            or (len(p) == 3 and p[0] in RUNS and p[1] in ('unit','done') and bool(p[2])))
        require(allowed, 'Unknown campaign record blocks dispatch')
        require(s not in {k+'/'+run for k in ('claim','intent','terminal','dispatch')}
            and not s.startswith('attempt/'+run+'/') and not s.startswith(run+'/'),
            'Any prior intent, claim or partial work permanently blocks resubmission')
    order = list(RUNS); at = order.index(run)
    for previous in order[:at]:
        require(isinstance(records.get(dispatch_key(previous)),dict)
            and records[dispatch_key(previous)].get('provider_app_id'), 'Frozen dispatch order changed')
        terminal = records.get(prefix+'terminal/'+previous)
        require(terminal is None or terminal.get('status') == 'completed',
                'An earlier failure requires a concrete separate disposition')
    require(not any(dispatch_key(k) in records for k in order[at+1:]), 'Later dispatch already exists')

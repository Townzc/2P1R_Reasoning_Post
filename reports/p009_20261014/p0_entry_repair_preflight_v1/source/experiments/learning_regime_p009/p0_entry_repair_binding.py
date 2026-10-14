"""Exact pre-claim schema repair; no scoring, dispatch or remote mutation here."""
import math
from experiments.sft_allocation_midpoint.common import digest
from experiments.learning_regime_p009.p0_fast_remaining_contract import (
    CAMPAIGN, RUN, RESERVED_CENTS, SCOPE, OFFSETS, BATCH_SIZE, WORKER_SECONDS,
    PLATFORM_SECONDS, STARTUP_SECONDS, FULL_WINDOW, engine_kwargs, cost_cents,
)

PARENT_RESERVED_CENTS = 752
STAGE0_CAP_CENTS = 2000
EXPERIMENT_CAP_CENTS = 11000

REPAIR_SCOPE = 'p009-p0-fast-preclaim-entry-schema-repair'
DISPATCH_KEY = 'midpoint/'+CAMPAIGN+'/entry_schema_repair_dispatch/'+RUN


def admission_intent(spec, release):
    """Use the actual nested immutable schema before registration or admission."""
    inputs = spec['parent_spec']['inputs']
    if (not isinstance(inputs, dict) or not inputs or
            inputs != release['input_readback']):
        raise ValueError('Exact original input manifest and readback required')
    for name, record in inputs.items():
        if (not isinstance(name, str) or not name or not isinstance(record, dict)
                or set(record) != {'bytes', 'sha256'}
                or type(record['bytes']) is not int or record['bytes'] < 0
                or not isinstance(record['sha256'], str) or len(record['sha256']) != 64
                or any(c not in '0123456789abcdef' for c in record['sha256'])):
            raise ValueError('Malformed input manifest')
    if 'inputs' in spec and spec['inputs'] != inputs:
        raise ValueError('Conflicting top-level alias is forbidden')
    return dict(run_id=RUN, source_sha256=digest(spec['source_files']),
        config_sha256=digest(spec), data_sha256=digest(inputs))


def registration_only(records, plan):
    expected = {'midpoint/'+CAMPAIGN+'/campaign': plan}
    if records != expected:
        raise ValueError('Only the original identical campaign registration may remain')


def validate_repair_release(spec, plan, release):
    validate_amended_release(spec, plan, release)
    admission_intent(spec, release)
    proof = spec['preclaim_failure']['zero_work_proof']
    for key, expected in dict(claims=0, terminals=0, unit_intents=0, new_outputs=0,
            unknown_generation=0, model_loaded=False, volume_absent=True,
            all_original_apps_stopped=True, original_256_untouched=True,
            failed_terminal_fabricated=False, original_call_failed=True).items():
        if key not in proof or type(proof[key]) is not type(expected) or proof[key] != expected:
            raise ValueError('Original zero-work reconciliation incomplete')
    registration_only(proof['actual_campaign_records'], plan)
    repair = spec['preclaim_failure']
    if (repair['repair_scope'] != REPAIR_SCOPE or
            repair['prior_failed_call_reserved_cents'] != RESERVED_CENTS or
            proof['original_error'] != dict(type='KeyError', error="'inputs'", retry_authorized=False)):
        raise ValueError('Different original failure or unaccounted failed call')
    review = release['runtime_review']
    if (review.get('preclaim_entry_schema_repair_accepted') is not True or
            review.get('preclaim_proof_sha256') != repair['zero_work_proof_file_sha256']):
        raise ValueError('New exact entry-repair review required; old suffix PASS is insufficient')
    if (review.get('stage0_cap_cents') != STAGE0_CAP_CENTS or
            review.get('experiment_cap_cents') != EXPERIMENT_CAP_CENTS or
            review.get('owner_budget_amendment_sha256') != spec['owner_budget_amendment_sha256']):
        raise ValueError('Exact owner-amended caps require numeric review')
    if (release['budget']['effective_stage0_cap_cents'] != STAGE0_CAP_CENTS or
            spec['original_two_failed_reserved_cents'] != 500 or
            spec['preclaim_failure']['prior_failed_call_reserved_cents'] != 252 or
            PARENT_RESERVED_CENTS+RESERVED_CENTS > STAGE0_CAP_CENTS):
        raise ValueError('Retain every failed allowance and the full new slot')


def dispatch_marker(spec, release):
    app = release.get('dispatch_app_id')
    if not isinstance(app, str) or not app.startswith('ap-'):
        raise ValueError('Original provider app identity required')
    return dict(repair_scope=REPAIR_SCOPE, provider_app_id=app,
        spec_sha256=digest(spec), source_sha256=digest(spec['source_files']),
        prior_failed_call_id=spec['preclaim_failure']['zero_work_proof']['original_call_id'],
        zero_work_proof_sha256=spec['preclaim_failure']['zero_work_proof_file_sha256'],
        permitted_new_outputs=2382, inherited_outputs=256, retries=0)


def remaining_forecast(elapsed, observations, remaining_batches):
    if (not math.isfinite(elapsed) or elapsed < 0 or not observations
            or any(not math.isfinite(x) or x <= 0 for x in observations)
            or type(remaining_batches) is not int or not 0 <= remaining_batches <= 11):
        raise ValueError('Finite parent proxy plus all new complete timings required')
    remaining = 1.2*(max(observations)*remaining_batches+300)
    total = elapsed+remaining
    cents = cost_cents(total+STARTUP_SECONDS+100)+20
    return dict(elapsed_worker_seconds=elapsed, observed_intervals=len(observations),
        parent_failed_batch_proxy_seconds=observations[0], max_interval_seconds=max(observations),
        future_batches=remaining_batches, remaining_seconds=remaining,
        predicted_worker_seconds=total, predicted_cents=cents,
        admitted=(total <= WORKER_SECONDS-30 and cents <= .8*(STAGE0_CAP_CENTS-PARENT_RESERVED_CENTS)
                  and RESERVED_CENTS+PARENT_RESERVED_CENTS <= STAGE0_CAP_CENTS),
        parent_proxy_is_completed_batch=False, calibrated_bound=False,
        bootstrap_exception=False, old_eager_timings_used=False)


def validate_amended_release(spec, plan, release):
    exact = dict(scope=SCOPE, campaign=CAMPAIGN, run_id=RUN, offsets=OFFSETS,
        worker_seconds=WORKER_SECONDS, platform_seconds=PLATFORM_SECONDS,
        startup_seconds=STARTUP_SECONDS, full_window_seconds=FULL_WINDOW,
        reserved_cents=RESERVED_CENTS, parent_reserved_cents=PARENT_RESERVED_CENTS,
        new_training_updates=0, suffix_outputs=2382, inherited_outputs=256,
        batch_size=BATCH_SIZE, suffix_batches=11, bootstrap_batches_total=0,
        engine_kwargs=engine_kwargs(), stage0_cap_cents=STAGE0_CAP_CENTS, experiment_cap_cents=EXPERIMENT_CAP_CENTS,
        project_cap_cents=45000, protected_original_cents=5000)
    if any(spec.get(k) != v for k, v in exact.items()):
        raise ValueError('Exact suffix scope/dose/configuration/cap changed')
    if (digest(plan) != spec['plan_sha256'] or plan['campaign_id'] != CAMPAIGN
            or plan['slots'] != {RUN: dict(stage='p0_fast_remaining', reserved_cents=RESERVED_CENTS)}
            or plan['stage_caps_cents'] != {'p0_fast_remaining': RESERVED_CENTS}
            or plan['total_cap_cents'] != RESERVED_CENTS
            or release['source_files'] != spec['source_files']
            or digest(spec['parent_spec']) != spec['parent_spec_sha256']
            or spec['parent_terminal']['status'] != 'failed'
            or spec['parent_terminal']['claim_sha256'] != digest(spec['parent_claim'])):
        raise ValueError('Plan/source or original failed lineage changed')
    review = release['runtime_review']
    if (review['scope'] != SCOPE or review['decision'] not in ('PASS', 'PASS-WITH-NOTES')
            or review['target_commit'] != release['review_target']
            or len(review['report_commit']) != 40 or len(review['report_sha256']) != 64
            or review['source_files'] != spec['source_files'] or review['spec_sha256'] != digest(spec)
            or review['parent_preservation_sha256'] != spec['parent_preservation_sha256']
            or review['bounded_suffix_only'] is not True
            or review['native_eos_cap_metadata_accepted'] is not True
            or review['same_frozen_logical_stop'] is not True):
        raise ValueError('Real exact suffix/source/prefix/numeric/EOS review required')
    budget = release['budget']
    if (budget['p009_stage0_used_and_pending_cents'] != PARENT_RESERVED_CENTS
            or budget['slot_reserved_cents'] != RESERVED_CENTS
            or budget['new_experiment_cap_cents'] != EXPERIMENT_CAP_CENTS
            or type(budget['project_prior_upper_cents']) is not int
            or budget['project_prior_upper_cents'] < 0
            or budget['project_prior_upper_cents']+EXPERIMENT_CAP_CENTS > 45000
            or release['input_readback'] != spec['parent_spec']['inputs']):
        raise ValueError('Failed reserves, Stage0/project cap or existing input readback changed')


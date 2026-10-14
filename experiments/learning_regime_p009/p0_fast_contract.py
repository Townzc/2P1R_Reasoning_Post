"""Exact fresh Plan-A P0; the failed eager prefix is historical, never inherited."""
import math
from experiments.sft_allocation_midpoint.common import digest
from experiments.learning_regime_p009.p0_contract import (
    cost_cents, ROLES, REFERENCE_STATE, REFERENCE_IDENTITY, prompts_checked, raw_checked,
)
from experiments.learning_regime_p009.high_throughput_v1 import BATCH_SIZE, engine_kwargs

CAMPAIGN = 'p009-p0-fast-20261014-r1'
RUN = 'p0_fast_pair'
PARENT_CAMPAIGN = 'p009-p0-parity-20261014-r1'
PARENT_RUN = 'p0_parity_pair'
RETIRED_CAMPAIGN = 'p009-p0-suffix-20261014-r1'
SCOPE = 'p009-p0-high-throughput-full-runtime-and-bootstrap-numeric'
WORKER_SECONDS = 1200
PLATFORM_SECONDS = 1260
STARTUP_SECONDS = 600
FULL_WINDOW = 1900
RESERVED_CENTS = 252  # ceil(1900*.00122044*100)+20, not an invoice.
PARENT_RESERVED_CENTS = 248


def remaining_forecast(elapsed, durations, remaining_batches):
    if (not math.isfinite(elapsed) or elapsed < 0 or not durations
            or any(not math.isfinite(x) or x <= 0 for x in durations)
            or type(remaining_batches) is not int or not 0 <= remaining_batches <= 11):
        raise ValueError('Actual full new-configuration batch timings required')
    remaining = 1.2*(max(durations)*remaining_batches+300)
    total = elapsed+remaining
    cents = cost_cents(total+STARTUP_SECONDS+100)+20
    return dict(elapsed_worker_seconds=elapsed, observed_batches=len(durations), full_batch_max_seconds=max(durations),
        future_batches=remaining_batches, remaining_seconds=remaining,
        predicted_worker_seconds=total, predicted_cents=cents,
        admitted=(total <= WORKER_SECONDS-30 and cents <= .8*(1000-PARENT_RESERVED_CENTS)
                  and RESERVED_CENTS+PARENT_RESERVED_CENTS <= 1000),
        calibrated_bound=False, old_eager_timings_used=False)


def validate_release(spec, plan, release):
    exact = dict(scope=SCOPE, campaign=CAMPAIGN, run_id=RUN,
        roles=list(ROLES), worker_seconds=WORKER_SECONDS, platform_seconds=PLATFORM_SECONDS,
        startup_seconds=STARTUP_SECONDS, full_window_seconds=FULL_WINDOW,
        reserved_cents=RESERVED_CENTS, parent_reserved_cents=PARENT_RESERVED_CENTS,
        new_training_updates=0, fresh_outputs=2638, inherited_outputs=0,
        batch_size=BATCH_SIZE, bootstrap_batches_total=1,
        engine_kwargs=engine_kwargs(), reference_state_sha256=REFERENCE_STATE,
        reference_identity_sha256=REFERENCE_IDENTITY, stage0_cap_cents=1000,
        experiment_cap_cents=10000, project_cap_cents=45000, protected_original_cents=5000)
    if any(spec.get(k) != v for k, v in exact.items()):
        raise ValueError('Exact Plan-A source/configuration/dose/cap changed')
    if (digest(plan) != spec['plan_sha256'] or plan['campaign_id'] != CAMPAIGN
            or plan['slots'] != {RUN: dict(stage='p0_fast', reserved_cents=RESERVED_CENTS)}
            or plan['stage_caps_cents'] != {'p0_fast': RESERVED_CENTS}
            or plan['total_cap_cents'] != RESERVED_CENTS
            or release['source_files'] != spec['source_files']
            or spec['parent_terminal']['status'] != 'failed'
            or spec['parent_terminal']['claim_sha256'] != digest(spec['parent_claim'])):
        raise ValueError('Plan/source/failed-parent identity changed')
    owner = spec['owner_plan_A']
    if (owner['scope'] != 'p009-owner-plan-A-high-throughput-full-P0'
            or owner['old_128_not_in_new_endpoint'] is not True
            or owner['new_experiment_cap_cents'] != 10000
            or owner['teacher_context'] != 2048 or owner['seven_math_rows_unsupported'] is not True):
        raise ValueError('Direct owner Plan-A authority missing')
    review = release['runtime_review']
    if (review['scope'] != SCOPE or review['decision'] not in ('PASS', 'PASS-WITH-NOTES')
            or review['target_commit'] != release['review_target']
            or len(review['report_commit']) != 40 or len(review['report_sha256']) != 64
            or review['spec_sha256'] != digest(spec) or review['source_files'] != spec['source_files']
            or review['owner_plan_A_sha256'] != digest(owner)
            or review['fresh_full_P0_accepted'] is not True
            or review['first_one_batch_bootstrap_accepted'] is not True):
        raise ValueError('Real exact new-engine/full-P0/bootstrap numeric review required')
    design = release['design_review']
    if (design['scope'] != 'p009-design-and-stage0-inputs'
            or design['target_commit'] != spec['design_target']
            or design['decision'] not in ('PASS', 'PASS-WITH-NOTES')
            or len(design['report_commit']) != 40 or len(design['report_sha256']) != 64):
        raise ValueError('Original scoped Stage0 design/input acceptance required')
    budget = release['budget']
    if (type(budget['project_prior_upper_cents']) is not int
            or budget['project_prior_upper_cents'] < 0
            or budget['new_experiment_cap_cents'] != 10000
            or budget['p009_stage0_used_and_pending_cents'] != PARENT_RESERVED_CENTS
            or budget['slot_reserved_cents'] != RESERVED_CENTS
            or budget['project_prior_upper_cents']+10000 > 45000
            or release['input_readback'] != spec['inputs']):
        raise ValueError('Original sunk reserve, project cap or exact input readback changed')


def fence_original(store, spec, claim):
    """The new setting wins the same parent successor marker as the retired suffix."""
    pre = 'midpoint/'+PARENT_CAMPAIGN+'/'
    if (store.get(pre+'claim/'+PARENT_RUN) != spec['parent_claim']
            or store.get(pre+'terminal/'+PARENT_RUN) != spec['parent_terminal']):
        raise ValueError('Original failed parent lineage differs')
    marker = dict(kind='owner_plan_A_fresh_configuration', campaign=CAMPAIGN, run_id=RUN,
        claim_sha256=claim.claim_sha256, owner_plan_A_sha256=digest(spec['owner_plan_A']),
        fresh_outputs=2638, inherited_outputs=0, parent_stays_failed=True)
    if not store.put(pre+'continuation/'+PARENT_RUN, marker, skip_if_exists=True):
        raise ValueError('Existing or ambiguous successor marker; no retry')
    return marker

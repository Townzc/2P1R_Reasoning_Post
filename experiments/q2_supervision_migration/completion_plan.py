"""Frozen execution envelope for the owner's one missing-control completion.

The scientific plan, schedules and seeds remain byte-for-byte separate from this
new operational attempt. Earlier failed doses remain overhead, never resumed.
"""
from __future__ import annotations

import math

from . import screen_plan as screen
from .contracts import identity_hash
from .gpu_profile import ProfileError

ATTEMPT = 'controls_completion_2'
PHASES = ('C_prefix', 'C_future', 'R_future', 'eval_C_prefix', 'eval_C_future', 'eval_R_future')
POWERED_CAP_SECONDS = 10800
SHUTDOWN_RESERVE_SECONDS = 600
DOSE = {'optimizer_updates': 384, 'training_completions': 6144,
        'evaluation_completions': 3072, 'total_completions': 9216,
        'final_checkpoints': 3}
PRIOR_DOSE = {
    'committed_optimizer_updates': 386, 'saved_training_completions': 6224,
    'saved_evaluation_completions': 3072,
    'completed_training': {'W_prefix': {'updates': 128, 'outputs': 2048},
                           'W_future': {'updates': 128, 'outputs': 2048}},
    'failed_attempts': {'initial_attempt': {'updates': 5, 'outputs': 96},
                       'C_prefix': {'updates': 100, 'outputs': 1616},
                       'R_future': {'updates': 25, 'outputs': 416}},
    'old_failures_relabelled_or_resumed': False,
}


def make_completion_plan(scientific_plan):
    screen.validate_plan(scientific_plan, {'train_ids': scientific_plan['train_ids'],
                                          'eval_ids': scientific_plan['eval_ids']})
    if scientific_plan.get('scoring_policy') != 'first_failure_per_suite':
        raise ProfileError('completion requires the frozen first-failure scientific plan')
    return {'schema': 1, 'execution_attempt': ATTEMPT,
            'scientific_plan_sha256': identity_hash(scientific_plan),
            'scientific_run_id': scientific_plan['run_id'],
            'execution_run_id': scientific_plan['run_id'] + '__' + ATTEMPT,
            'phases': list(PHASES), 'dose': dict(DOSE),
            'fresh_start_phases': ['C_prefix', 'R_future'],
            'fresh_continuation_source': {'C_future': 'C_prefix'},
            'reuse_model_states_for_final_analysis_only': ['W_prefix', 'W_future'],
            'reuse_evaluations_without_regeneration': ['R', 'W_prefix', 'W_future'],
            'limits': {'powered_seconds': POWERED_CAP_SECONDS,
                       'shutdown_reserve_seconds': SHUTDOWN_RESERVE_SECONDS,
                       'training_phase_seconds': 2700, 'evaluation_phase_seconds': 1800},
            'automatic_retry': False, 'cross_process_resume': False,
            'new_training_seed_or_scientific_arm': False}


def fixed_deadlines(power_on_epoch, provider_deadline_epoch, now, model_deadline_epoch=None):
    values = (power_on_epoch, provider_deadline_epoch, now)
    if any(type(x) not in (int, float) or not math.isfinite(x) for x in values):
        raise ProfileError('power-on/provider/current times must be finite')
    if power_on_epoch > now or power_on_epoch <= 0:
        raise ProfileError('conservative power-on time cannot be future or nonpositive')
    if provider_deadline_epoch != power_on_epoch + POWERED_CAP_SECONDS:
        raise ProfileError('provider deadline must equal original power-on plus three hours')
    latest = provider_deadline_epoch - SHUTDOWN_RESERVE_SECONDS
    model = latest if model_deadline_epoch is None else model_deadline_epoch
    if type(model) not in (int, float) or not math.isfinite(model) or not now < model <= latest:
        raise ProfileError('model window is closed or lacks the fixed shutdown reserve')
    return {'power_on_epoch': power_on_epoch, 'provider_deadline_epoch': provider_deadline_epoch,
            'worker_deadline_epoch': model, 'shutdown_reserve_seconds': provider_deadline_epoch - model,
            'powered_cap_seconds': POWERED_CAP_SECONDS}


def phase_deadline(name, now, shared_deadline):
    if name not in PHASES:
        raise ProfileError('phase is outside the authorized completion queue')
    if not now < shared_deadline:
        raise ProfileError('shared completion work deadline reached')
    return min(shared_deadline, now + (1800 if name.startswith('eval_') else 2700))

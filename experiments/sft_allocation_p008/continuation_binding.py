"""Exact, finite, separately reviewed D2 continuation admission; no cloud calls."""
import math
from experiments.sft_allocation_midpoint.common import digest
from experiments.sft_allocation_midpoint.guard import RunGuard
from .main_binding import accepted, RATE_USD_PER_HOUR
from .contract import DEADLINE_EPOCH

CAMPAIGN = 'p008-d2-continuation-20261013-r1'
RUN = 'pool_d2_remaining'
PARENT = 'p008-main-20261013-r1'
CHILD_DEADLINE = 1791921600  # 2026-10-13 20:00 UTC / 13:00 PDT
PROBE = dict(samples=3, read_timeout_seconds=15, readers=8,
             remaining_rounds_proxy=136, baseline_round_seconds=41.11433974999545,
             baseline_guard_seconds=1.41530, guard_calls_per_round=4,
             startup_closing_allowance_seconds=300, safety_factor=1.2,
             no_favourable_host_resampling=True, measured_runtime_upper_bound=False)


def validate_continuation_binding(plan, cfg, release, spec):
    RunGuard({}, plan)
    if (plan['campaign_id'] != CAMPAIGN or plan['deadline_epoch'] != CHILD_DEADLINE
            or plan['total_cap_cents'] != 1200 or plan['stage_caps_cents'] != {'continuation': 1200}
            or plan['slots'] != {RUN: {'stage': 'continuation', 'reserved_cents': 1200}}
            or cfg['run_id'] != RUN or cfg['role'] != 'pool_continuation'
            or cfg['draw'] != 2 or cfg['high_multiple'] != 8
            or cfg['max_seconds'] != 7200 or cfg['max_physical_attempts'] != 16384
            or cfg['input_directory'] != 'pool_inputs' or cfg['prefix_directory'] != 'parent_prefix'):
        raise ValueError('Frozen child scope, budget or deadline differs')
    if (digest(plan) != spec['plan_sha256'] or digest(cfg) != spec['config_sha256']
            or digest(spec) != release['spec_sha256'] or release['source_files'] != spec['source_files']
            or spec['stage_reserved_cents'] != 24968 or spec['prior_reserved_cents'] != 23768
            or spec['stage_cap_cents'] != 25000 or spec['project_ceiling_cents'] != 45000
            or spec['protected_cents'] != 5000 or spec['global_deadline_epoch'] != DEADLINE_EPOCH
            or spec['probe_policy'] != PROBE):
        raise ValueError('Exact source/spec or accounting binding differs')
    owner = spec['owner_authorization']
    if not (owner['draws_retained'] == 2 and owner['remaining_only'] is True
            and owner['child_deadline_utc'] == '2026-10-13T20:00:00Z'
            and owner['worker_cap_seconds'] == 7200 and owner['additional_reserved_usd'] == 12
            and owner['P008_total_reserved_usd'] == 249.68
            and owner['code_and_data_review_required_before_run'] is True):
        raise ValueError('Actual owner authorization differs')
    if math.ceil((7200+700)*RATE_USD_PER_HOUR/36) > 1200:
        raise ValueError('Child runtime under-reserved')
    gates = release['gates']
    accepted(gates['runtime_review'], 'pool-continuation-runtime', release['source_files'], digest(spec))
    if not (gates['upload']['passed'] is True
            and gates['upload']['input_sha256'] == cfg['input_sha256']
            and gates['upload']['prefix_manifest_sha256'] == cfg['prefix_manifest_sha256']
            and gates['parent_provider_released'] is True):
        raise ValueError('Exact readback or original provider release missing')
    rec = spec['reconciliation']
    if not (rec['physical_attempts'] == 3992 and rec['physical_batches'] == 146
            and rec['returned_tokens'] == 1190193 and rec['physical_raw_unknown'] == 0
            and rec['parent_terminal']['status'] == 'failed'
            and rec['pending_wallets'] == [] and rec['unattempted_pending_candidate_ids'] == []
            and rec['passed'] is True):
        raise ValueError('Different or ambiguous failed prefix')
    dependencies = spec['parent_records']
    prefix = 'midpoint/'+PARENT+'/'
    claim = rec['parent_claim']
    expected = {prefix+'campaign', prefix+'claim/pool_d2', prefix+'intent/pool_d2',
                prefix+'attempt/pool_d2/'+claim['attempt_id'], prefix+'terminal/pool_d2',
                prefix+'terminal/pool_d1'}
    if (set(dependencies) != expected or dependencies[prefix+'terminal/pool_d2'] != rec['parent_terminal']
            or dependencies[prefix+'claim/pool_d2'] != claim
            or dependencies[prefix+'attempt/pool_d2/'+claim['attempt_id']] != claim
            or digest(dependencies[prefix+'campaign']) != claim['plan_sha256']
            or digest(dependencies[prefix+'intent/pool_d2']) != claim['intent_sha256']
            or dependencies[prefix+'terminal/pool_d1']['status'] != 'completed'):
        raise ValueError('Cross-campaign failed-parent/D1 provenance differs')
    return True


def probe_forecast(samples, remaining_seconds):
    """Only a conservative engineering proxy, never a throughput guarantee."""
    if (len(samples) != PROBE['samples'] or not math.isfinite(remaining_seconds)
            or any(not math.isfinite(x) or x < 0 or x >= 15 for x in samples)):
        raise ValueError('Invalid complete-read-set probe')
    worst = max(samples)
    per_round = PROBE['baseline_round_seconds'] + PROBE['guard_calls_per_round'] * max(
        0., worst-PROBE['baseline_guard_seconds'])
    prediction = PROBE['safety_factor']*(PROBE['remaining_rounds_proxy']*per_round
                                       + PROBE['startup_closing_allowance_seconds'])
    return dict(passed=prediction <= remaining_seconds, predicted_seconds=prediction,
                remaining_seconds=remaining_seconds, read_samples_seconds=samples,
                proxy_not_upper_bound=True, policy=PROBE)

"""Pure checks for the finite, two-model P0 engine-comparability job."""
from decimal import Decimal, ROUND_CEILING
import math
from experiments.sft_allocation_midpoint.common import digest

ROLES = ('base_638', 'correct_969')
WORKER_SECONDS = 1200
PLATFORM_SECONDS = 1260
STARTUP_SECONDS = 600
FULL_WINDOW = 1900
RESERVED_CENTS = 248
RATE_USD_SECOND = Decimal('0.00122044')  # H100 + 4 physical CPU + 32GiB
REFERENCE_STATE = 'c3e6de44d072defadee03d552c98874c9937ad14614454540a8f2812999cc341'
REFERENCE_IDENTITY = '0b51d053e1b55ac2826a9b4808ef7dfd198a6afb6530a484cb5308c6e17aa592'


def cost_cents(seconds):
    if not math.isfinite(seconds) or seconds < 0:
        raise ValueError('Finite nonnegative time required')
    return int((Decimal(str(seconds))*RATE_USD_SECOND*100).to_integral_value(rounding=ROUND_CEILING))


def prompts_checked(value):
    if (value['n'] != 1319 or value['eos_token_id'] != 151643
            or value['max_context'] != 2048 or value['max_new_tokens'] != 512):
        raise ValueError('P0 endpoint changed')
    rows = value['prompts']
    expected = [f'gsm8k/test/{i:05d}' for i in range(1319)]
    if [x['problem_id'] for x in rows] != expected:
        raise ValueError('Missing, duplicate or reordered endpoint')
    for row in rows:
        ids = row['input_ids']
        if (not ids or len(ids)+512 > 2048 or
                any(type(x) is not int or not 0 <= x < 151936 for x in ids)):
            raise ValueError('Invalid full prompt')
    return rows


def raw_checked(rows, output):
    if len(rows) != len(output):
        raise ValueError('Missing generation')
    for row, raw in zip(rows, output):
        ids = raw['token_ids']
        if (raw['problem_id'] != row['problem_id'] or
                raw['prompt_token_ids'] != row['input_ids'] or not ids or len(ids) > 512
                or any(type(x) is not int or not 0 <= x < 151936 for x in ids)):
            raise ValueError('Raw identity/token contract differs')
        if 151643 in ids:
            if ids[-1] != 151643 or ids.count(151643) != 1 or raw['finish_reason'] != 'stop':
                raise ValueError('Native EOS must be original terminal token')
        elif len(ids) != 512 or raw['finish_reason'] != 'length':
            raise ValueError('Incomplete output; do not append fabricated EOS')
    return output


def remaining_forecast(elapsed, durations, remaining_batches, stage_used_cents=0):
    """All full batches, including guard/journal/commits; no fast-sample choice."""
    if (not durations or any(not math.isfinite(x) or x <= 0 for x in durations)
            or type(remaining_batches) is not int or remaining_batches < 0):
        raise ValueError('Actual complete batch timing required')
    # 300s is an explicit uncalibrated future setup/merge/pack allowance. The
    # separate worker timer remains authoritative if a later host operation stalls.
    remaining = 1.2*(max(durations)*remaining_batches+300)
    total = elapsed+remaining
    forecast_cents = cost_cents(total+STARTUP_SECONDS)+20
    available = 1000-stage_used_cents
    admitted = (total <= WORKER_SECONDS-30 and forecast_cents <= .8*available
                and RESERVED_CENTS <= available)
    return dict(full_batch_max_seconds=max(durations), observed_batches=len(durations),
                future_batches=remaining_batches, remaining_seconds=remaining,
                predicted_total_worker_seconds=total, predicted_cents=forecast_cents,
                admitted=admitted, calibrated_bound=False)


def validate_release(spec, plan, release):
    if (spec['scope'] != 'p009-p0-parity-runtime-and-bootstrap-numeric'
            or spec['worker_seconds'] != WORKER_SECONDS
            or spec['platform_seconds'] != PLATFORM_SECONDS
            or spec['startup_seconds'] != STARTUP_SECONDS
            or spec['full_window_seconds'] != FULL_WINDOW
            or spec['reserved_cents'] != RESERVED_CENTS
            or spec['reference_state_sha256'] != REFERENCE_STATE
            or spec['roles'] != list(ROLES) or spec['new_training_updates'] != 0
            or spec['bootstrap_batches_per_role'] != 4):
        raise ValueError('Frozen P0 specification differs')
    if digest(plan) != spec['plan_sha256'] or release['source_files'] != spec['source_files']:
        raise ValueError('Exact plan/source binding differs')
    for key, scope, target in (
        ('design_review', 'p009-design-and-stage0-inputs', spec['design_target']),
        ('runtime_review', spec['scope'], release['review_target']),
    ):
        review = release[key]
        if (review['scope'] != scope or review['target_commit'] != target
                or review['decision'] not in ('PASS', 'PASS-WITH-NOTES')
                or len(review['report_sha256']) != 64 or len(review['report_commit']) != 40):
            raise ValueError('Real fixed scoped review required')
    if (release['runtime_review']['spec_sha256'] != digest(spec)
            or release['runtime_review']['source_files'] != spec['source_files']
            or release['runtime_review']['bootstrap_exception_accepted'] is not True):
        raise ValueError('Exact source/numeric/first-measurement review missing')
    if release['input_readback'] != spec['inputs']:
        raise ValueError('Exact uploaded-input readback required')
    budget = release['budget']
    if (budget['p009_stage0_used_and_pending_cents'] != 0
            or budget['project_prior_upper_cents']+10000 > 45000
            or budget['new_experiment_cap_cents'] != 10000
            or budget['slot_reserved_cents'] != RESERVED_CENTS):
        raise ValueError('Initial P0 finite budget gate differs')

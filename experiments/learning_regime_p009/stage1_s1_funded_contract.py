# Candidate funded adaptation. Requires actual owner proxy and independent exact admission.
"""Prepared S1 execution policy, without numerical or dispatch admission.

The future exact binding must supply reviewed caps and actual timing evidence.
There are no default caps, paid bootstrap exceptions, new recipes or retries.
NC A4 and the first S1 pair's futility decision belong to that future binding.
"""
import math

from experiments.learning_regime_p009.stage1_nc_contract import cents, checked_observations
from experiments.learning_regime_p009.stage1_endpoint_engine import checked_endpoint
from experiments.learning_regime_p009.stage0_generation_contract_v2 import ids_checked

RUNS = {
    's1_s17_n400': (17, 400), 's1_s17_n3200': (17, 3200),
    's1_s17_n100': (17, 100), 's1_s17_n1600': (17, 1600),
    's1_s29_n400': (29, 400), 's1_s29_n3200': (29, 3200),
}
STAGE1_CAP_CENTS = 7000
NC_RESERVED_CENTS = 2620
FUTURE_ALLOWANCE_SECONDS = 600


def recipe(run):
    if run not in RUNS:
        raise ValueError('Only the six original S1 recipes are supported')
    seed, n = RUNS[run]
    return dict(setting='S1', seed=seed, n=n, updates=1024, targets=2097148,
                endpoint_count=500, endpoint_max_new_tokens=1024,
                automatic_retry=False)


def limits_checked(value):
    keys = {'worker_seconds', 'platform_seconds', 'startup_seconds',
            'full_window_seconds', 'reserved_cents'}
    if (not isinstance(value, dict) or set(value) != keys
            or any(type(v) is not int or v <= 0 for v in value.values())
            or value['worker_seconds'] <= 30
            or value['platform_seconds'] != value['worker_seconds']+60
            or value['startup_seconds'] != 600
            or value['full_window_seconds'] != value['worker_seconds']+700
            or value['reserved_cents'] != cents(value['full_window_seconds'])):
        raise ValueError('Explicit exact whole-worker/platform/window/reserve required')
    return dict(value)


def checked_slot_budget(slots):
    """All original six slots fit after the all four retained NC reservations, or none do.

    This is arithmetic only. It neither supplies time measurements nor admits
    a scientific slot, and cannot reclaim an ended NC reservation by itself.
    """
    if not isinstance(slots, dict) or set(slots) != set(RUNS):
        raise ValueError('All six original S1 slots must be budgeted explicitly')
    remaining = STAGE1_CAP_CENTS-NC_RESERVED_CENTS
    before = {}
    for run in RUNS:
        value = limits_checked(slots[run]); before[run] = remaining
        remaining -= value['reserved_cents']
    if remaining < 0:
        raise ValueError('Exact six-slot reservations exceed the remaining Stage1 cap')
    return before


def forecast(elapsed, train_blocks_left, eval_batches_left, training_seconds,
             endpoint_seconds, stage_remaining_before_cents, limits):
    cap = limits_checked(limits)
    if (type(elapsed) not in (int, float) or not math.isfinite(elapsed) or elapsed < 0
            or type(train_blocks_left) is not int or not 0 <= train_blocks_left <= 64
            or type(eval_batches_left) is not int or not 0 <= eval_batches_left <= 2
            or type(stage_remaining_before_cents) is not int
            or not cap['reserved_cents'] <= stage_remaining_before_cents <= STAGE1_CAP_CENTS):
        raise ValueError('Finite exact S1 remainder and original stage ledger required')
    train = max(checked_observations(training_seconds))
    endpoint = max(checked_observations(endpoint_seconds))
    remaining = 1.2*(train*train_blocks_left + endpoint*eval_batches_left
                     + FUTURE_ALLOWANCE_SECONDS)
    total = elapsed+remaining; price = cents(total+700)
    return dict(elapsed_worker_seconds=elapsed, training_blocks_left=train_blocks_left,
        endpoint_batches_left=eval_batches_left, training_block_max_seconds=train,
        endpoint_batch_max_seconds=endpoint, training_observations=len(training_seconds),
        endpoint_observations=len(endpoint_seconds), future_allowance_seconds=FUTURE_ALLOWANCE_SECONDS,
        forecast_remaining_seconds=remaining, forecast_total_worker_seconds=total,
        forecast_cents=price, stage_remaining_before_cents=stage_remaining_before_cents,
        admitted=(total <= cap['worker_seconds']-30 and price <= cap['reserved_cents']
                  and 5*price <= 4*stage_remaining_before_cents),
        calibrated_bound=False, unmeasured_paid_exception=False,
        observed_proxy_not_future_host_guarantee=True)


def transport_checked(full_endpoint, part, raw):
    """Check preserved backend bytes; never decode, score or fabricate EOS."""
    sampling = checked_endpoint('S1', full_endpoint)
    if not isinstance(raw, list) or not 1 <= len(part) <= 256 or len(raw) != len(part):
        raise ValueError('Incomplete original S1 output; never replay')
    for row, output in zip(part, raw):
        if (output.get('candidate_id') != row['candidate_id']
                or output.get('problem_id') != row['problem_id']
                or output.get('source_row_sha256') != row['source_row_sha256']
                or output.get('sampling') != sampling
                or output.get('prompt_token_ids') != row['input_ids']
                or output.get('output_count') != 1 or not isinstance(output.get('backend_text'), str)):
            raise ValueError('Original S1 prompt/sampling/returned shape differs')
        ids = output['token_ids']; ids_checked(ids, 151936, 1024)
        eos = [i for i, value in enumerate(ids) if value == 151643]
        if eos:
            if eos != [len(ids)-1]:
                raise ValueError('Interior/repeated native EOS; original bytes retained')
            if output.get('finish_reason') == 'stop':
                if output.get('stop_reason') not in (None, 151643):
                    raise ValueError('Unexpected native stop metadata')
            elif not (len(ids) == 1024 and output.get('finish_reason') == 'length'
                      and output.get('stop_reason') is None):
                raise ValueError('Only exact1024 native EOS/length tie is accepted')
        elif (len(ids) != 1024 or output.get('finish_reason') != 'length'
              or output.get('stop_reason') is not None):
            raise ValueError('Unexplained short termination')
    return len(raw)

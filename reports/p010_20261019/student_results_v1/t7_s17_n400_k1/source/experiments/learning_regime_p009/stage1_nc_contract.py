"""Prepared two-NC operational policy, not a dispatch or numerical admission.

Actual all-host timing evidence, exact source/input review and current budget
must be supplied by the later binding. There is no unmeasured-batch exception.
"""
from decimal import Decimal, ROUND_CEILING
import math

from experiments.learning_regime_p009.stage1_endpoint_engine import checked_endpoint
from experiments.learning_regime_p009.stage0_generation_contract_v2 import ids_checked

CAMPAIGN = 'p009-stage1-nc-20261015-r1'
RUNS = {'nc_s17_n400': 400, 'nc_s17_n3200': 3200}
WORKER_SECONDS = 4500
PLATFORM_SECONDS = 4560
STARTUP_SECONDS = 600
FULL_WINDOW_SECONDS = 5200
RESERVED_CENTS = 655
STAGE1_CAP_CENTS = 5000
STAGE1_NC_RESERVE_CENTS = 1310
RATE = Decimal('0.00122044')
ALLOWANCE_CENTS = 20
FUTURE_SETUP_MERGE_CLOSE_ALLOWANCE_SECONDS = 600


def cents(seconds):
    if type(seconds) not in (int, float) or not math.isfinite(seconds) or seconds < 0:
        raise ValueError('Finite nonnegative duration required')
    return int((Decimal(str(seconds))*RATE*100).to_integral_value(rounding=ROUND_CEILING))+ALLOWANCE_CENTS


def slot(run):
    if run not in RUNS or cents(FULL_WINDOW_SECONDS) != RESERVED_CENTS:
        raise ValueError('Only the two registered NC slots and exact reserve')
    return dict(setting='NC', seed=17, n=RUNS[run], updates=1024, targets=2097148,
                worker_seconds=WORKER_SECONDS, platform_seconds=PLATFORM_SECONDS,
                startup_seconds=STARTUP_SECONDS, full_window_seconds=FULL_WINDOW_SECONDS,
                reserved_cents=RESERVED_CENTS, automatic_retry=False)


def checked_observations(values):
    if (not isinstance(values, list) or not values
            or any(type(x) not in (int, float) or not math.isfinite(x) or x <= 0 for x in values)):
        raise ValueError('All applicable complete observed intervals required; unknown is not zero')
    return values


def forecast(elapsed, train_blocks_left, eval_batches_left, training_seconds,
             endpoint_seconds, stage_remaining_before_cents):
    if (type(elapsed) not in (int, float) or not math.isfinite(elapsed) or elapsed < 0
            or type(train_blocks_left) is not int or not 0 <= train_blocks_left <= 64
            or type(eval_batches_left) is not int or not 0 <= eval_batches_left <= 6
            or type(stage_remaining_before_cents) is not int
            or not RESERVED_CENTS <= stage_remaining_before_cents <= STAGE1_CAP_CENTS):
        raise ValueError('Finite exact NC remainder and stage ledger required')
    # Existing timing observations must be source-bound by a real numeric audit.
    # Retain every old applicable observation, including slow hosts, then append
    # complete new-worker measurements; never replace the old vector with a min.
    train = max(checked_observations(training_seconds))
    endpoint = max(checked_observations(endpoint_seconds))
    remaining = 1.2*(train*train_blocks_left + endpoint*eval_batches_left
                     + FUTURE_SETUP_MERGE_CLOSE_ALLOWANCE_SECONDS)
    total = elapsed+remaining
    price = cents(total+700)
    return dict(elapsed_worker_seconds=elapsed, training_blocks_left=train_blocks_left,
                endpoint_batches_left=eval_batches_left, training_block_max_seconds=train,
                endpoint_batch_max_seconds=endpoint,
                training_observations=len(training_seconds), endpoint_observations=len(endpoint_seconds),
                future_allowance_seconds=FUTURE_SETUP_MERGE_CLOSE_ALLOWANCE_SECONDS,
                forecast_remaining_seconds=remaining, forecast_total_worker_seconds=total,
                forecast_cents=price, stage_remaining_before_cents=stage_remaining_before_cents,
                admitted=(total <= WORKER_SECONDS-30 and price <= RESERVED_CENTS
                          and 5*price <= 4*stage_remaining_before_cents),
                calibrated_bound=False, unmeasured_paid_exception=False,
                observed_proxy_not_future_host_guarantee=True)


def transport_checked(full_endpoint, part, raw):
    """Original backend bytes precede this check; no logical parsing/scoring."""
    sampling = checked_endpoint('NC', full_endpoint)
    if not isinstance(raw, list) or not 1 <= len(part) <= 256 or len(raw) != len(part):
        raise ValueError('Incomplete or ambiguous original output, never replay')
    for row, output in zip(part, raw):
        if (output.get('candidate_id') != row['candidate_id']
                or output.get('problem_id') != row['problem_id']
                or output.get('source_row_sha256') != row['source_row_sha256']
                or output.get('sampling') != sampling
                or output.get('prompt_token_ids') != row['input_ids']
                or output.get('output_count') != 1 or not isinstance(output.get('backend_text'), str)):
            raise ValueError('Original NC prompt, sampling or returned shape differs')
        ids = output['token_ids']; ids_checked(ids, 151936, 512)
        eos = [i for i, x in enumerate(ids) if x == 151643]
        if eos:
            if eos != [len(ids)-1]:
                raise ValueError('Interior/repeated native EOS; never edit raw tokens')
            if output.get('finish_reason') == 'stop':
                if output.get('stop_reason') not in (None, 151643):
                    raise ValueError('Unexpected native stop metadata')
            elif not (len(ids) == 512 and output.get('finish_reason') == 'length'
                      and output.get('stop_reason') is None):
                raise ValueError('Only exact512 native-EOS length-metadata boundary is accepted')
        elif (len(ids) != 512 or output.get('finish_reason') != 'length'
              or output.get('stop_reason') is not None):
            raise ValueError('Unexplained short termination')
    return len(raw)

"""A/D numeric gate candidate. No timing evidence or paid exception is invented.

The future exact spec must supply source-bound historical proxies and limits.
All maxima include the observations from the current immutable run. These are
uncalibrated engineering projections, never speed, cost or survival guarantees.
"""
from decimal import Decimal, ROUND_CEILING
import math

CAPS = {'A':Decimal('115'), 'B':Decimal('20'), 'C':Decimal('12'), 'D':Decimal('25')}


def decimal(value):
    x = Decimal(str(value))
    if not x.is_finite() or x < 0:
        raise ValueError('Finite nonnegative amounts required')
    return x


def forecast(policy, training_left, batches_left, new_training, new_batches, now):
    if (policy['category'] not in ('A','D')
            or any(type(x) is not int or x < 0 for x in (training_left,batches_left))
            or any(type(x) not in (int,float) or not math.isfinite(x) or x <= 0
                   for x in (now,policy['worker_start_epoch'],policy['worker_hard_seconds'],
                             policy['result_deadline_epoch'],policy['full_result_seconds']))
            or policy['measurement_exceptions'] != 0
            or policy['projection_multiplier'] != 1.2
            or policy['uncalibrated_future_seconds'] < 300):
        raise ValueError('Exact finite A/D numeric basis without measurement exceptions required')
    maxima = []
    for remaining, prior, fresh in (
            (training_left,policy['training_unit_seconds'],new_training),
            (batches_left,policy['endpoint_batch_seconds'],new_batches)):
        series = list(prior)+list(fresh)
        if (remaining and not series) or any(type(x) not in (int,float)
                or not math.isfinite(x) or x <= 0 for x in series):
            raise ValueError('All source-bound finite positive timing proxies required')
        maxima.append(max(series,default=0))
    elapsed = now-policy['worker_start_epoch']
    future = policy['uncalibrated_future_seconds']
    total_scenario = 1.2*(elapsed + training_left*maxima[0] + batches_left*maxima[1] + future)
    if (elapsed < 0 or total_scenario > policy['worker_hard_seconds']-30
            or policy['worker_start_epoch']+policy['full_result_seconds'] > policy['result_deadline_epoch']):
        raise ValueError('Whole remaining work/result window does not fit original limits')
    rate = decimal(policy['hourly_rate_usd'])
    startup = decimal(policy['startup_allowance_seconds'])
    reserve = decimal(policy['reserved_usd'])
    prior = decimal(policy['prior_reserved_usd'])
    predicted = ((startup+Decimal(str(total_scenario)))*rate/Decimal(3600)).quantize(
        Decimal('.01'),rounding=ROUND_CEILING)
    platform = decimal(policy['platform_timeout_seconds'])
    minimum_reserve = ((startup+platform)*rate/Decimal(3600)).quantize(
        Decimal('.01'),rounding=ROUND_CEILING)
    remaining = CAPS[policy['category']]-prior
    if (rate <= 0 or startup < 600 or platform < policy['worker_hard_seconds']+60
            or policy['full_result_seconds'] < float(startup+platform)
            or reserve < minimum_reserve or reserve > remaining
            or predicted > reserve or predicted > Decimal('.8')*remaining):
        raise ValueError('Full reservation or 80-percent category forecast gate failed')
    return dict(training_updates_left=training_left,endpoint_batches_left=batches_left,
        training_unit_max_seconds=maxima[0],endpoint_batch_max_seconds=maxima[1],
        elapsed_worker_seconds=elapsed,uncalibrated_future_seconds=future,
        projected_total_worker_seconds=total_scenario,projected_usd=str(predicted),
        reserved_usd=str(reserve),prior_reserved_usd=str(prior),
        category=policy['category'],category_remaining_before_usd=str(remaining),
        measurement_exceptions=0,engineering_scenario_not_guarantee=True,
        expense_or_refund=False)

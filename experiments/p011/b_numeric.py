"""Shared B generation/student numerical contract; no selected paid SPEC.

Initial forecasts require source-bound complete-cycle observations. The C1
owner exception is deliberately inapplicable here. Future allowances are
uncalibrated engineering margins, not measured speed or invoice guarantees.
"""
from decimal import Decimal, ROUND_CEILING
import math


def amount(value):
    x = Decimal(str(value))
    if not x.is_finite() or x < 0:
        raise ValueError('Finite nonnegative amount required')
    return x


def forecast(policy, training_left, batches_left, training_times, batch_times, now):
    kind = policy['kind']
    counts = (0, 25) if kind == 'generation' else (64, 10)
    if (kind not in ('generation', 'student') or policy['category'] != 'B'
            or policy['measurement_exceptions'] != 0
            or policy['projection_multiplier'] != 1.2
            or policy['uncalibrated_future_seconds'] < 600
            or any(type(x) is not int or not 0 <= x <= cap
                   for x, cap in zip((training_left, batches_left), counts))
            or any(type(x) not in (int, float) or not math.isfinite(x) or x <= 0
                   for x in (now, policy['worker_start_epoch'], policy['worker_seconds'],
                             policy['full_result_seconds'], policy['result_cutoff_epoch']))):
        raise ValueError('Original complete B numerical scope required')
    maxima = []
    for left, prior, fresh in (
            (training_left, policy['training_cycle_seconds'], training_times),
            (batches_left, policy['batch_cycle_seconds'], batch_times)):
        series = list(prior)+list(fresh)
        if (left and not series) or any(type(x) not in (int, float)
                or not math.isfinite(x) or x <= 0 for x in series):
            raise ValueError('Every complete-cycle timing source must be retained')
        maxima.append(max(series, default=0))
    elapsed = now-policy['worker_start_epoch']
    seconds = elapsed+1.2*(training_left*maxima[0]+batches_left*maxima[1]
                           +policy['uncalibrated_future_seconds'])
    if (elapsed < 0 or seconds > policy['worker_seconds']-30
            or policy['worker_start_epoch']+policy['full_result_seconds'] > policy['result_cutoff_epoch']):
        raise ValueError('Original complete worker/result window does not fit')
    rate = amount(policy['hourly_rate_usd'])
    startup = amount(policy['startup_seconds'])
    platform = amount(policy['platform_seconds'])
    reserve = amount(policy['reserved_usd'])
    prior = amount(policy['prior_B_reserved_usd'])
    predicted = ((startup+Decimal(str(seconds)))*rate/3600).quantize(Decimal('.01'), rounding=ROUND_CEILING)
    minimum = ((startup+platform)*rate/3600).quantize(Decimal('.01'), rounding=ROUND_CEILING)
    if (rate <= 0 or startup < 600 or platform < policy['worker_seconds']+60
            or policy['full_result_seconds'] < float(startup+platform)
            or reserve < minimum or reserve > Decimal('20')-prior
            or predicted > reserve or predicted > Decimal('.8')*(Decimal('20')-prior)):
        raise ValueError('B20 full reservation or 80percent remaining forecast fails')
    return dict(kind=kind, train_blocks_left=training_left, batches_left=batches_left,
        training_cycle_max=maxima[0], batch_cycle_max=maxima[1], elapsed_seconds=elapsed,
        future_allowance_seconds=policy['uncalibrated_future_seconds'],
        forecast_total_seconds=seconds, predicted_usd=str(predicted),
        reserved_usd=str(reserve), prior_B_reserved_usd=str(prior),
        measurement_exceptions=0, engineering_scenario_not_guarantee=True,
        full_cycles_include_commits_and_remote_ack=True)

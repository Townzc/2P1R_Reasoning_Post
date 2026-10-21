"""Delegated D-only operational forecast; no measurement or paid admission.

Original scientific data, dose and schedules are untouched. Historical proxies
remain visible; observed complete training cycles use their arithmetic mean,
endpoint cycles retain their maximum, and elapsed time is counted once.
"""
from decimal import Decimal, ROUND_CEILING
import math

DECISION_SHA='bba65b440106c9272d453f61fe719a3c0b878e497576423434ff5ec3ab819820'


def decimal(value):
    x=Decimal(str(value))
    if not x.is_finite() or x<0:raise ValueError('Finite nonnegative amount required')
    return x


def positive(values):
    values=list(values)
    if any(type(x) not in (int,float) or not math.isfinite(x) or x<=0 for x in values):
        raise ValueError('Complete finite positive timing observations required')
    return values


def forecast(policy,training_left,batches_left,new_training,new_batches,now):
    if (policy.get('category')!='D' or policy.get('delegated_forecast_decision_sha256')!=DECISION_SHA
            or policy.get('training_estimator')!='max_historical_proxy_observed_complete_cycle_mean'
            or policy.get('elapsed_multiplier')!=1.0
            or policy.get('endpoint_uncalibrated_proxy_seconds')!=600
            or any(type(x) is not int or x<0 for x in (training_left,batches_left))
            or any(type(x) not in (int,float) or not math.isfinite(x) or x<=0 for x in
                (now,policy['worker_start_epoch'],policy['worker_hard_seconds'],
                 policy['result_deadline_epoch'],policy['full_result_seconds']))
            or policy['measurement_exceptions']!=0 or policy['projection_multiplier']!=1.2
            or policy['uncalibrated_future_seconds']!=963):
        raise ValueError('Exact delegated D forecast and unchanged future allowance required')
    prior_train=positive(policy['training_unit_seconds']);fresh_train=positive(new_training)
    prior_eval=positive(policy['endpoint_batch_seconds']);fresh_eval=positive(new_batches)
    if (training_left and not prior_train) or (batches_left and not prior_eval) or 600 not in prior_eval:
        raise ValueError('Historical training and explicit uncalibrated600 endpoint basis required')
    historical_max=max(prior_train,default=0)
    observed_mean=math.fsum(fresh_train)/len(fresh_train) if fresh_train else 0
    train_estimate=max(historical_max,observed_mean)
    eval_estimate=max(prior_eval+fresh_eval,default=0)
    elapsed=now-policy['worker_start_epoch'];future=policy['uncalibrated_future_seconds']
    total=elapsed+1.2*(training_left*train_estimate+batches_left*eval_estimate+future)
    if (elapsed<0 or total>policy['worker_hard_seconds']-30
            or policy['worker_start_epoch']+policy['full_result_seconds']>policy['result_deadline_epoch']):
        raise ValueError('Whole remaining D work/result window exceeds fixed limits')
    rate=decimal(policy['hourly_rate_usd']);startup=decimal(policy['startup_allowance_seconds'])
    reserve=decimal(policy['reserved_usd']);prior=decimal(policy['prior_reserved_usd'])
    platform=decimal(policy['platform_timeout_seconds']);remaining=Decimal('25')-prior
    predicted=((startup+Decimal(str(total)))*rate/3600).quantize(Decimal('.01'),rounding=ROUND_CEILING)
    minimum=((startup+platform)*rate/3600).quantize(Decimal('.01'),rounding=ROUND_CEILING)
    if (rate<=0 or startup<600 or platform<policy['worker_hard_seconds']+60
            or policy['full_result_seconds']<float(startup+platform)
            or reserve<minimum or reserve>remaining or predicted>reserve
            or predicted>Decimal('.8')*remaining):
        raise ValueError('Full fixed reservation or80-percent D prediction gate failed')
    return dict(training_updates_left=training_left,endpoint_batches_left=batches_left,
        historical_training_proxy_max_seconds=historical_max,
        observed_complete_training_mean_seconds=observed_mean,
        observed_complete_training_max_seconds=max(fresh_train,default=0),
        observed_complete_training_count=len(fresh_train),training_unit_estimate_seconds=train_estimate,
        endpoint_batch_max_seconds=eval_estimate,elapsed_worker_seconds=elapsed,
        uncalibrated_future_seconds=future,projected_total_worker_seconds=total,
        projected_usd=str(predicted),reserved_usd=str(reserve),prior_reserved_usd=str(prior),
        category='D',category_remaining_before_usd=str(remaining),measurement_exceptions=0,
        delegated_forecast_decision_sha256=DECISION_SHA,endpoint_proxy_is_uncalibrated=True,
        engineering_scenario_not_guarantee=True,expense_or_refund=False)

"""D1/D4 original G settlement arithmetic; no provider calls or ledger writes."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_CEILING


def timestamp(value):
    result=datetime.fromisoformat(value.replace('Z','+00:00'))
    return result.replace(tzinfo=timezone.utc) if result.tzinfo is None else result.astimezone(timezone.utc)


def gross(rows, app_id):
    selected=[r for r in rows if r.get('object_id')==app_id]
    if not selected:raise ValueError('The original app must have its own labeled meter rows')
    values=[Decimal(r['cost']) for r in selected]
    if any(not x.is_finite() or x<0 for x in values):
        raise ValueError('Finite nonnegative gross resource costs required; no credits/netting')
    return sum(values,Decimal(0))


def settle(app_id, prior, provider, hourly_rows, historical_totals):
    """Complete returned hour buckets are period coverage, not finality proof.

    Use the greatest saved gross meter and ceil its 20% buffer to cents. This
    never reduces an observed meter floor or rewrites any original reservation.
    A missing exact owned-container proof keeps the entire original reserve.
    """
    prior=Decimal(str(prior))
    if not prior.is_finite() or prior<=0:raise ValueError('Original positive reserve required')
    if provider is None:
        return dict(app_id=app_id,eligible=False,original_reserved_usd=str(prior),
            charged_usd=str(prior),released_usd='0',
            reason='No saved exact owned-container-zero proof; full original reservation retained')
    if (provider.get('app_id')!=app_id or str(provider.get('state')).lower()!='stopped'
            or type(provider.get('owned_count')) is not int or provider['owned_count']!=0):
        raise ValueError('The exact original app must be STOPPED with owned count zero')
    created=timestamp(provider['created_at']);stopped=timestamp(provider['stopped_at'])
    if stopped<=created:raise ValueError('Actual provider lifecycle required')
    selected=[r for r in hourly_rows if r.get('object_id')==app_id]
    intervals={timestamp(r['interval_start']) for r in selected}
    if any(x.minute or x.second or x.microsecond for x in intervals):
        raise ValueError('Only complete original hour-resolution buckets')
    required=set();cursor=created.replace(minute=0,second=0,microsecond=0)
    while cursor<=stopped:
        required.add(cursor);cursor+=timedelta(hours=1)
    if not required<=intervals:raise ValueError('Returned hour buckets do not cover the entire app lifecycle')
    totals=[gross(hourly_rows,app_id)]+[Decimal(str(x)) for x in historical_totals]
    if any(not x.is_finite() or x<0 for x in totals):raise ValueError('Invalid historical gross floor')
    maximum=max(totals);exact=maximum*Decimal('1.2')
    charge=exact.quantize(Decimal('.01'),rounding=ROUND_CEILING)
    return dict(app_id=app_id,eligible=True,original_reserved_usd=str(prior),
        observed_gross_max_usd=str(maximum),exact_120_percent_usd=str(exact),charged_usd=str(charge),
        released_usd=str(prior-charge),created_utc=created.isoformat(),stopped_utc=stopped.isoformat(),
        returned_hour_starts=sorted(x.isoformat() for x in intervals),
        coverage_through_utc=(max(intervals)+timedelta(hours=1)).isoformat(),
        meter_finality_watermark_available=False,delayed_meter_not_invoice=True,
        historical_meter_floor_retained=True,rounding='ceil buffered charge to whole cents')


def summary(items):
    if len(items)!=6 or len({x['app_id'] for x in items})!=6:
        raise ValueError('All six original G app identities, including failed and cached work, required')
    original=sum((Decimal(x['original_reserved_usd']) for x in items),Decimal(0))
    charge=sum((Decimal(x['charged_usd']) for x in items),Decimal(0))
    if original!=44:raise ValueError('Original G reservation ledger must remain44')
    allowance=(Decimal(50)-charge)*Decimal('.8')
    return dict(original_reserved_G_usd=str(original),proposed_charged_G_usd=str(charge),
        proposed_released_G_usd=str(original-charge),G_remaining_80percent_usd=str(allowance),
        E3_original_reserve_usd='11.13',E3_D4_numeric_condition=allowance>=Decimal('11.13'),
        caps_usd=dict(G=50,T=150,I=15,C=25),overall_cap_usd=240,protected_usd=43,
        original_claims_modified=False,actual_release_applied=False,exact_A2_required=True)

"""Conditional continuation plus two future students; not student admission."""
from decimal import Decimal,ROUND_CEILING
import math

def verify_scenario(v):
    rate=Decimal(str(v['hourly_rate_usd']));W=v['E3_recorded_upper_interval_seconds']
    if (not rate.is_finite() or rate<=0 or type(W) not in (int,float) or not math.isfinite(W)
            or not 0<W<=360 or 2*W*10>7200 or v['generation_full_window_seconds']!=16865
            or v['generation_reserved_usd']!='3.01' or v['retained_failed_B_usd']!='3.01'
            or v['B_protected_floor_usd']!='0' or v['cutoff_epoch']!=1792645200
            or v['original_failed_reservations_retained'] is not True
            or v['students_approved_now'] is not False
            or not v['timing_source_files'] or not v['score_timing_source_files']):
        raise ValueError('Exact delegated scoring and whole budget evidence required')
    ceiling=lambda x:x.quantize(Decimal('.01'),rounding=ROUND_CEILING)
    if ceiling(rate*Decimal(2460)/3600)!=Decimal(v['generation_reserved_usd']):
        raise ValueError('Actual full continuation resource rate changed')
    prior=Decimal('6.02');latest=[]
    if list(v['students'])!=['B1','B3']:raise ValueError('Mandatory future B1 thenB3 required')
    for name,job in v['students'].items():
        if (job['worker_seconds']!=4400 or job['platform_seconds']!=4460 or job['startup_seconds']!=600
                or job['collect_seconds']!=3600 or job['audit_seconds']!=3600 or job['score_seconds']!=25200
                or job['cleanup_seconds']!=5 or job['full_window_seconds']!=37465
                or type(job['initial_worker_scenario_seconds']) not in (int,float)
                or not 0<job['initial_worker_scenario_seconds']<=4370):
            raise ValueError('Concrete prospective student full window differs')
        reserve=ceiling(rate*Decimal(5060)/3600)
        if reserve!=Decimal(job['reserved_usd']) or reserve>Decimal('.8')*(20-prior):
            raise ValueError('Sequential full future student reserve exceeds80percent')
        prior+=reserve;latest.append(1792645200-16865-job['full_window_seconds'])
    # Owner14:00UTC ceiling, additionally narrowed to keep both complete student
    # windows. Sequential admission may run the two distinct students in parallel.
    if v['latest_continuation_dispatch_epoch']!=min(1792591200,*latest):
        raise ValueError('Continuation must leave full future student windows')
    if prior>20:raise ValueError('B category exceeded')
    return dict(B_after_mandatory_attempt_reservations_usd=str(prior),student_calls_authorized=False,
                full_result_window_preserved=True,measurement_exceptions=0)

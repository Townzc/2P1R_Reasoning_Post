"""Original P010 E3 under D4 and audited D1 settlement; no cap increase."""
from decimal import Decimal
from math import isfinite
from experiments.p010.teacher_contract import seed_for, sampling

KEY = 'e3/temperature_supply_r1'
HARD_SECONDS = 1800
RESERVE = Decimal('11.13')
RATE = Decimal('.00463488')
CAPS = {'G': Decimal(50), 'T': Decimal(150), 'I': Decimal(15), 'C': Decimal(25)}
TEMPERATURES = [('t06', .6), ('t10', 1.)]


def check_rosters(roster, groups):
    pids = roster['problem_ids']
    if (len(pids) != 200 or len(set(pids)) != 200
            or roster['new_temperatures'] != [.6, 1.]
            or roster['new_attempts_per_problem'] != 8
            or roster['reused_attempts'] != list(range(1, 9))
            or roster['reused_temperature'] != .8 or set(groups) != {'t06', 't10'}):
        raise ValueError('Original frozen200/eight-attempt/three-temperature scope required')
    all_ids = set()
    for label, temperature in TEMPERATURES:
        rows = groups[label]
        if len(rows) != 1600:
            raise ValueError('Exactly1600 unattempted outputs per new temperature')
        for offset, row in enumerate(rows):
            pid, attempt = pids[offset//8], offset % 8 + 1
            old = f'{pid}::attempt{attempt:02d}'
            cid = 'p010_e3/'+label+'/'+old
            expected = sampling({'seed': seed_for(old)})
            expected['temperature'] = temperature
            if (row['candidate_id'] != cid or cid in all_ids
                    or row['original_seed_candidate_id'] != old
                    or row['problem_id'] != pid or row['attempt'] != attempt
                    or row['model'] != 't72' or row['temperature'] != temperature
                    or row['seed'] != seed_for(old) or row['sampling'] != expected
                    or not row['prompt_token_ids'] or len(row['prompt_token_ids'])+1024 > 2048):
                raise ValueError('Original order, seeds, native chat or sampling differs')
            all_ids.add(cid)
    for left, right in zip(groups['t06'], groups['t10']):
        if left['prompt_token_ids'] != right['prompt_token_ids'] or left['seed'] != right['seed']:
            raise ValueError('Only temperature changes within each original request')
    return 14


def validate_d4(value):
    """The real D4 rejects transfers and approves only the conditional D1 path."""
    if (value.get('scope') != 'p010-E3-original-scope-contingency-to-generation-allocation'
            or value.get('approved') is not False
            or value.get('decision') != 'D4_REJECT_TRANSFER_AND_CAP_INCREASE_CONDITIONAL_D1_PATH'
            or value.get('caps_usd') != {'G': 50, 'T': 150, 'I': 15, 'C': 25}
            or value.get('total_cap_usd') != 240 or value.get('protected_usd') != 43
            or value.get('E3_is_separate_original_generation_item') is not True
            or value.get('E3_original_scope_supported_conditionally') is not True
            or value.get('E3_reserve_usd') != '11.13'
            or not isinstance(value.get('reason'), str) or not value['reason'].strip()):
        raise ValueError('Exact reasoned D4 conditional decision required; no transfer exception')


def forecast(elapsed, completed, times, original_times, setup_seconds, *, model_loaded, charged_G):
    if (type(completed) is not int or not 0 <= completed <= 14 or len(times) != completed
            or not original_times or not isfinite(elapsed) or elapsed < 0
            or not isfinite(setup_seconds) or setup_seconds <= 0
            or any(not isfinite(x) or x <= 0 for x in list(times)+list(original_times))
            or type(model_loaded) is not bool):
        raise ValueError('All finite original and new timing observations required')
    maximum = max(list(times)+list(original_times))
    setup = 0 if model_loaded else setup_seconds
    future = 1.2*(setup+maximum*(14-completed)+300)
    total = elapsed+future
    cost = (Decimal(str(total))+600)*RATE
    charged_G=Decimal(str(charged_G))
    if not charged_G.is_finite() or not 0<=charged_G<=44:
        raise ValueError('Exact audited D1 G charge required')
    available=(CAPS['G']-charged_G)*Decimal('.8')
    if RESERVE>available:
        raise ValueError('D4 requires full E3 reserve within80percent of settled G remainder')
    if total > HARD_SECONDS-30:
        raise TimeoutError('Actual elapsed plus remaining scenario exceeds original E3 window')
    if cost > available or cost > RESERVE:
        raise ValueError('Original G remainder80percent or reserved amount exceeded')
    return dict(elapsed_seconds=elapsed,completed_batches=completed,total_batches=14,
        maximum_observed_batch_seconds=maximum,original_batch_seconds=list(original_times),
        new_batch_seconds=list(times),observed_original_setup_seconds=setup_seconds,
        setup_proxy_remaining_seconds=setup,model_loaded=model_loaded,future_seconds=future,
        projected_total_worker_seconds=total,projected_usd=str(cost),
        original_prior_G_reserved_usd='44',D1_charged_G_usd=str(charged_G),
        new_reserved_usd=str(RESERVE),G_cap_usd='50',original_claims_rewritten=False,
        first_paid_measurement_exceptions=0,uncalibrated_closing_seconds=300,
        margin=1.2,not_a_future_host_bound_or_probability=True)

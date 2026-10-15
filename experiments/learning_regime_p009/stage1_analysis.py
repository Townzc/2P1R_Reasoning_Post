"""Pre-outcome NC/S1 decision core. No model, raw parser or dispatch authority.

The eventual caller must first bind complete independent outcome oracles and
the frozen endpoint IDs. These pure functions do not substitute for that review.
S2 is excluded by its actual Stage0 cap failure; no substitute baseline is used.
"""
import hashlib
import json

from experiments.learning_regime_p009.gates import (
    paired_counts, nc_stop, futility, g1, n_star,
)

BOOTSTRAP = dict(replicates=10000, seed=20261014, generator='numpy.PCG64',
                 numpy_version='2.2.6', quantile_method='linear',
                 quantiles=[0.025, 0.975], unit='paired_question',
                 ordering='lexicographic_frozen_question_id',
                 interval_scope='pointwise_conditional_not_simultaneous_or_seed_population')
S1_KEYS = ('s1_17_n100', 's1_17_n400', 's1_17_n1600', 's1_17_n3200',
           's1_29_n400', 's1_29_n3200')


def _hash(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def checked_outcomes(setting, question_ids, outcomes):
    """Only complete frozen Boolean endpoints; unknowns may not become zeros."""
    if setting not in ('NC', 'S1'):
        raise ValueError('Only actual G0-eligible NC/S1 definitions; S2 is excluded')
    total = 1319 if setting == 'NC' else 500
    if (not isinstance(question_ids, list) or len(question_ids) != total
            or any(not isinstance(k, str) or not k for k in question_ids)
            or len(set(question_ids)) != total or not isinstance(outcomes, dict)
            or set(outcomes) != set(question_ids)
            or any(type(v) is not bool for v in outcomes.values())):
        raise ValueError('Every original question and an exact Boolean verdict are required')
    # A common deterministic order makes row-order changes irrelevant to the
    # paired bootstrap. Identity, not physical dict insertion order, is paired.
    return {k: outcomes[k] for k in sorted(question_ids)}


def pair(setting, question_ids, low, high):
    low = checked_outcomes(setting, question_ids, low)
    high = checked_outcomes(setting, question_ids, high)
    return dict(paired_counts(low, high), low_correct=sum(low.values()),
                high_correct=sum(high.values()),
                question_ids_sha256=_hash(list(low)),
                low_outcomes_sha256=_hash(low), high_outcomes_sha256=_hash(high),
                direction='n3200_minus_n400', technical_unknown=0)


def nc_result(question_ids, n400, n3200):
    result = pair('NC', question_ids, n400, n3200)
    stopped = nc_stop(result['delta_count'], result['n'])
    return dict(pair=result, stop_all_positive_regimes=stopped,
                decision='stop_NC_gap_at_least_5pp' if stopped else 'NC_gate_passed',
                implementation_error_proven=False, runtime_admitted=False)


def first_pair_decision(nc_ids, nc400, nc3200, s1_ids=None, s1_pair=None,
                        *, s1_G0_accepted):
    """Use the registered stop sequence; no empty-set futility conclusion."""
    if type(s1_G0_accepted) is not bool:
        raise ValueError('Explicit actual S1 G0 acceptance is required')
    nc = nc_result(nc_ids, nc400, nc3200)
    if nc['stop_all_positive_regimes']:
        if s1_pair is not None:
            raise ValueError('Positive-regime outcomes after an NC stop require separate disposition')
        return dict(nc=nc, decision='stop_NC', remaining_scientific_slots_allowed=False)
    if not s1_G0_accepted:
        if s1_pair is not None:
            raise ValueError('An ineligible S1 cannot acquire an outcome pair')
        return dict(nc=nc, decision='stop_no_eligible_positive_regime',
                    remaining_scientific_slots_allowed=False, measured_futility=False)
    if not isinstance(s1_pair, dict) or set(s1_pair) != {'n400', 'n3200'}:
        raise ValueError('The complete admitted S1 seed17 pair is required')
    result = pair('S1', s1_ids, s1_pair['n400'], s1_pair['n3200'])
    stopped = futility([result])  # S2 actually failed G0, so S1 is the only candidate.
    return dict(nc=nc, s1_seed17=result,
                decision='stop_registered_futility' if stopped else 'complete_registered_remaining_S1',
                measured_futility=stopped, remaining_scientific_slots_allowed=not stopped,
                A4_independent_review_required=True, runtime_admitted=False)


def paired_bootstrap(question_ids, low, high):
    """Exactly10000 shared-question draws; no new scoring or seed sweeps."""
    low = checked_outcomes('S1', question_ids, low)
    high = checked_outcomes('S1', question_ids, high)
    import numpy as np
    if np.__version__ != BOOTSTRAP['numpy_version']:
        raise ValueError('Use the frozen analysis NumPy version')
    differences = np.asarray([int(high[k])-int(low[k]) for k in low], dtype=np.int64)
    rng = np.random.Generator(np.random.PCG64(BOOTSTRAP['seed']))
    indices = rng.integers(0, len(low), size=(BOOTSTRAP['replicates'], len(low)))
    # Both models use the same resampled IDs, preserving per-question pairing.
    samples_pp = differences[indices].mean(axis=1)*100
    bounds = np.quantile(samples_pp, BOOTSTRAP['quantiles'], method=BOOTSTRAP['quantile_method'])
    return dict(policy=dict(BOOTSTRAP), observed_delta_pp=100*int(differences.sum())/len(low),
                lower95_pp=float(bounds[0]), upper95_pp=float(bounds[1]),
                resampled_deltas_sha256=_hash(samples_pp.tolist()),
                question_ids_sha256=_hash(list(low)),
                low_outcomes_sha256=_hash(low), high_outcomes_sha256=_hash(high))


def complete_s1(nc_ids, nc400, nc3200, s1_ids, outcomes, *, s1_G0_accepted):
    """Require all six registered S1 endpoints before G1/Stage2 selection."""
    if not isinstance(outcomes, dict) or set(outcomes) != set(S1_KEYS):
        raise ValueError('All and only six registered S1 endpoints are required')
    data = {k:checked_outcomes('S1', s1_ids, v) for k,v in outcomes.items()}
    first = first_pair_decision(nc_ids, nc400, nc3200, s1_ids,
        dict(n400=data['s1_17_n400'], n3200=data['s1_17_n3200']), s1_G0_accepted=s1_G0_accepted)
    if not first['remaining_scientific_slots_allowed']:
        raise ValueError('Later outcomes after a registered stop require separate disposition')
    seventeen = first['s1_seed17']
    twenty_nine = pair('S1', s1_ids, data['s1_29_n400'], data['s1_29_n3200'])
    interval = paired_bootstrap(s1_ids, data['s1_17_n400'], data['s1_17_n3200'])
    passed = g1(seventeen, twenty_nine, interval['lower95_pp'])
    n = n_star(sum(data['s1_17_n1600'].values()), sum(data['s1_17_n3200'].values()), len(s1_ids))
    return dict(nc=first['nc'], seed17=seventeen, seed29=twenty_nine, bootstrap=interval,
                G1_passed=passed, selected_setting='S1' if passed else None,
                selected_n_star=n if passed else None,
                decision='G1_passed_pending_A5_and_Stage2_admission' if passed else 'stop_no_G1_setting',
                all_cell_counts={k:sum(v.values()) for k,v in data.items()},
                A5_independent_review_required=True, runtime_admitted=False,
                scientific_claim_scope='conditional_on_seen_benchmark_and_adaptive_selection',
                training_seed_and_data_order_change_together=True,
                stable_seed_or_procurement_population_effect=False)

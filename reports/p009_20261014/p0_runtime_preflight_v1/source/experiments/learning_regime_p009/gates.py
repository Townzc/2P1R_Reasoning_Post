"""Pre-result decision rules. No model calls, score repair, or cloud mutation.

These rules require A0 review before scientific admission. In particular, the
draft's unspecified low-accuracy-gap/high-discordance parity case fails closed.
"""
from decimal import Decimal, ROUND_CEILING
import math


TOTAL_CENTS = 10000
STAGE_CENTS = {"stage0": 1000, "stage1": 5000, "stage2": 3500}
UNALLOCATED_CENTS = 500
UPDATES = 1024
TARGETS = 2097148
SEEDS = (17, 29)
STAGE2_ARMS = ("A", "B", "C", "B_prime", "D")


def _positive_int(value, name):
    if type(value) is not int or value <= 0:
        raise ValueError(f"Positive integer required: {name}")


def paired_counts(left, right):
    if not left or left.keys() != right.keys():
        raise ValueError("Complete identical endpoint identities required")
    if any(type(v) is not bool for v in [*left.values(), *right.values()]):
        raise ValueError("Boolean complete outcomes required; no unknown-to-zero conversion")
    n = len(left)
    delta = sum(right.values()) - sum(left.values())
    discordant = sum(left[k] != right[k] for k in left)
    return {"n": n, "delta_count": delta, "discordant_count": discordant,
            "delta_pp": 100 * delta / n, "discordance_percent": 100 * discordant / n}


def parity(hf, vllm):
    x = paired_counts(hf, vllm)
    # Integer comparisons avoid rounding a result across a scientific threshold.
    gap_numerator = abs(x["delta_count"]) * 100
    if gap_numerator > 3 * x["n"]:
        decision = "stop_investigate_engine_difference"
    elif gap_numerator <= x["n"] and 100 * x["discordant_count"] <= 4 * x["n"]:
        decision = "pass_comparable"
    elif gap_numerator > x["n"]:
        decision = "pass_internal_only"
    else:
        decision = "blocked_unspecified_discordance_case"
    return dict(x, decision=decision, implementation_error_proven=False)


def g0(teacher, student, caps, total, technical_unknown):
    _positive_int(total, "total")
    if any(type(x) is not int or x < 0 or x > total for x in (teacher, student, caps, technical_unknown)):
        raise ValueError("Invalid full endpoint counts")
    return (technical_unknown == 0 and 100 * caps <= 15 * total
            and 100 * (teacher - student) >= 20 * total)


def g1(seed17, seed29, lower95):
    """Each argument is an independently verified paired_counts result."""
    if not math.isfinite(lower95):
        raise ValueError("Finite, independently audited bootstrap bound required")
    for x in (seed17, seed29):
        _positive_int(x["n"], "n")
        if type(x["delta_count"]) is not int or abs(x["delta_count"]) > x["n"]:
            raise ValueError("Invalid paired count")
    return (100 * seed17["delta_count"] >= 5 * seed17["n"] and lower95 > 0
            and 200 * seed29["delta_count"] >= 5 * seed29["n"])


def nc_stop(delta_count, n):
    _positive_int(n, "n")
    if type(delta_count) is not int or abs(delta_count) > n:
        raise ValueError("Invalid negative-control difference")
    return 100 * delta_count >= 5 * n


def futility(candidate_pairs):
    if not candidate_pairs:
        raise ValueError("No eligible candidate is a distinct G0 stop, not a measured futility result")
    for x in candidate_pairs:
        _positive_int(x["n"], "n")
        if type(x["delta_count"]) is not int or abs(x["delta_count"]) > x["n"]:
            raise ValueError("Invalid paired count")
    return all(100 * x["delta_count"] < 2 * x["n"] for x in candidate_pairs)


def n_star(correct1600, correct3200, total):
    _positive_int(total, "total")
    if any(type(v) is not int or not 0 <= v <= total for v in (correct1600, correct3200)):
        raise ValueError("Invalid completed endpoint count")
    return 400 if 100 * (correct3200 - correct1600) <= total else 1600


def batch_forecast_cents(batch_seconds, batches, setup_close_seconds, dollars_per_second):
    """All observed full batch I/O times, never a favorable-host/min-time choice.

Forecast is a proxy, not a hard cost bound. Hard reservation is checked separately.
The first unmeasured pipeline must have its own reviewed calibration admission;
an empty measurement list cannot bypass this function.
"""
    _positive_int(batches, "batches")
    values = [Decimal(str(x)) for x in batch_seconds]
    overhead = Decimal(str(setup_close_seconds))
    rate = Decimal(str(dollars_per_second))
    if (not values or any(not x.is_finite() or x <= 0 for x in values)
            or not overhead.is_finite() or overhead < 0 or not rate.is_finite() or rate <= 0):
        raise ValueError("Real positive complete-batch measurements and finite costs required")
    dollars = (max(values) * batches + overhead) * rate
    return int((100 * dollars).to_integral_value(rounding=ROUND_CEILING))


def budget_gate(stage, actual_or_upper_cents, outstanding_cents, forecast_cents, reserve_cents):
    if stage not in STAGE_CENTS:
        raise ValueError("Unknown stage; unallocated reserve cannot be borrowed automatically")
    numbers = (actual_or_upper_cents, outstanding_cents, forecast_cents, reserve_cents)
    if any(type(v) is not int or v < 0 for v in numbers) or min(forecast_cents, reserve_cents) <= 0:
        raise ValueError("Nonnegative integer ledger amounts and positive forecast/reserve required")
    remaining = STAGE_CENTS[stage] - actual_or_upper_cents - outstanding_cents
    return (remaining > 0 and 5 * forecast_cents <= 4 * remaining
            and forecast_cents <= reserve_cents <= remaining)

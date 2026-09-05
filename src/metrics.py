"""Small, dependency-free evaluation helpers. No model results are fabricated."""
from __future__ import annotations
import math
from collections.abc import Sequence


def pass_at_k(n: int, c: int, k: int) -> float:
    """Unbiased per-problem estimator given n independent samples, c correct.

    Average this quantity over PROBLEMS, not over flattened generations.
    This finite-sampling metric does not prove the model's capability boundary.
    """
    if any(type(x) is not int for x in (n, c, k)):
        raise TypeError('n, c and k must be integers, excluding bool')
    if n < 1 or not 0 <= c <= n or not 1 <= k <= n:
        raise ValueError('Require n >= 1, 0 <= c <= n, 1 <= k <= n')
    if c == 0:
        return 0.0
    if n - c < k:
        return 1.0
    return 1.0 - math.prod((n - c - i) / (n - i) for i in range(k))


def macro_pass_at_k(counts: Sequence[tuple[int, int]], k: int) -> float:
    if not counts:
        raise ValueError('Empty problem set')
    return sum(pass_at_k(n, c, k) for n, c in counts) / len(counts)


def training_gpu_hours(tokens: int, aggregate_tokens_per_second: float, gpus: int = 1) -> float:
    """Measured aggregate throughput -> GPU-hours; excludes evaluation/overheads."""
    if tokens <= 0 or aggregate_tokens_per_second <= 0 or type(gpus) is not int or gpus < 1:
        raise ValueError('Positive token count, throughput and integer GPU count required')
    return tokens / aggregate_tokens_per_second / 3600 * gpus

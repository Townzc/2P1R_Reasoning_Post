"""Paired-question uncertainty conditional on fixed binary model outcomes."""
import numpy as np


def paired_percentile(values, coefficients, *, draws=10000, seed=20261013):
    values = np.asarray(values)
    coef = np.asarray(coefficients, dtype=np.float64)
    if values.ndim != 2 or not all(values.shape) or not np.isin(values, [0, 1]).all():
        raise ValueError('A nonempty model-by-question binary array is required')
    if coef.ndim != 2 or not coef.shape[0] or coef.shape[1] != values.shape[0] or not np.isfinite(coef).all():
        raise ValueError('Finite contrast rows must match every model')
    if type(draws) is not int or draws < 2 or type(seed) is not int or seed < 0:
        raise ValueError('Explicit finite resample count and seed required')
    n = values.shape[1]
    rng = np.random.default_rng(seed)
    point = coef @ values.mean(axis=1) * 100
    boot = np.empty((draws, len(coef)), dtype=np.float64)
    for start in range(0, draws, 100):
        count = min(100, draws-start)
        sample = rng.integers(0, n, size=(count, n))
        # One shared question sample for every fixed model and every contrast.
        means = values[:, sample].mean(axis=2).T
        boot[start:start+count] = means @ coef.T * 100
    interval = np.quantile(boot, [.025, .975], axis=0, method='linear')
    return point, interval

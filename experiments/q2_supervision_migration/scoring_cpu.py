"""A fixed, non-adaptive CPU placement for the isolated completion scorer."""
from __future__ import annotations
import os
import platform


def pin_scoring_cpu():
    """CPU 0 is frozen in advance; no speed search, warmup, or timer changes."""
    if platform.system() != 'Linux':
        raise RuntimeError('CPU scoring placement requires Linux')
    before = sorted(os.sched_getaffinity(0))
    if 0 not in before:
        raise RuntimeError('frozen scoring CPU 0 is unavailable')
    os.sched_setaffinity(0, {0})
    after = sorted(os.sched_getaffinity(0))
    if after != [0]:
        raise RuntimeError('scoring CPU placement was not applied')
    return {'cpu': 0, 'allowed_before': before, 'allowed_after': after,
            'selection': 'fixed_cpu_0_no_performance_selection',
            'timers_changed': False, 'candidate_code_changed': False,
            'guarantees_dedicated_cpu_or_stable_clock': False}

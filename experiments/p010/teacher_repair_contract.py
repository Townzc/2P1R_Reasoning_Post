"""Bounded proposed T7 suffix and unattempted T72 transport repair.

Original failed T7 reserve8 remains. Proposed newT7 reserve5.50 is additional.
No automatic retry, no release of previous reservations, no new scientific arm.
"""
import math
from experiments.p010.common import budget_check
from experiments.p010.teacher_contract import rate

SLOTS = {
    't7': dict(seconds=3600, gpus=1, cpu=4, memory_gib=32, reserve='5.50', prior='14.50'),
    't72': dict(seconds=4500, gpus=4, cpu=8, memory_gib=64, reserve='24.00', prior='20.00'),
}


def bounded_forecast(model, elapsed, batch_seconds, remaining_batches):
    if not batch_seconds or any(not math.isfinite(x) or x <= 0 for x in batch_seconds):
        raise ValueError('Actual measured batch or explicitly retained failure interval required')
    future=1.2*(max(batch_seconds)*remaining_batches+300)
    total=elapsed+future;cost=(total+600)*rate(model)
    if total>SLOTS[model]['seconds']-15:
        raise TimeoutError('Actual scenario exceeds fixed worker window')
    return dict(elapsed_seconds=elapsed,remaining_batches=remaining_batches,
        maximum_observed_full_batch_or_failure_interval_seconds=max(batch_seconds),
        future_seconds=future,projected_usd=cost,
        budget=budget_check('G',SLOTS[model]['prior'],SLOTS[model]['reserve'],cost),
        allowance_calibrated=False,failed_interval_is_not_successful_batch_timing=True)

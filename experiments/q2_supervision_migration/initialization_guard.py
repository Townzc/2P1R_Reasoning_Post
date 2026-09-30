"""Diagnose only an unresolved EvalPlus timeout; never change a known verdict.

Use the pinned upstream evaluator and its existing task wall-time allowance.
The additional timer covers exec(code), which upstream leaves outside per-test
timers. Only an observed TimeoutException in that candidate initialization is
attributed to the candidate. Other failures remain unresolved.
"""
from __future__ import annotations
import builtins
import multiprocessing as mp
import types


def _worker(dataset, entry_point, code, inputs, expected, limits, atol, fast,
            stat, details, progress, initialization_timeout):
    import evalplus.eval as ev
    from evalplus.eval.utils import time_limit, TimeoutException
    budget = min(60.0, sum(limits)) + 1.0

    def timed_exec(*args, **kwargs):
        try:
            with time_limit(budget):
                return builtins.exec(*args, **kwargs)
        except TimeoutException:
            initialization_timeout.value = 1
            raise

    # Preserve every upstream oracle/guard; scope the replacement to this child.
    namespace = {**ev.unsafe_execute.__globals__, 'exec': timed_exec}
    execute = types.FunctionType(ev.unsafe_execute.__code__, namespace)
    execute(dataset, entry_point, code, inputs, expected, limits, atol, fast,
            stat, details, progress)


def diagnose_initialization_timeout(dataset, code, inputs, entry_point, expected,
                                   atol, ref_time, fast_check=True):
    import evalplus.eval as ev
    from evalplus.config import DEFAULT_MIN_TIME_LIMIT, DEFAULT_GT_TIME_LIMIT_FACTOR
    limits = [max(DEFAULT_MIN_TIME_LIMIT, DEFAULT_GT_TIME_LIMIT_FACTOR*t) for t in ref_time]
    budget = min(60.0, sum(limits)) + 1.0
    stat=mp.Value('i', ev._UNKNOWN); progress=mp.Value('i',0)
    details=mp.Array('b',[False]*len(inputs)); timed_out=mp.Value('b',0)
    p=mp.Process(target=_worker,args=(dataset,entry_point,code,inputs,expected,
        limits,atol,fast_check,stat,details,progress,timed_out))
    p.start()
    try:
        p.join(timeout=budget+1.0)
    finally:
        if p.is_alive():p.terminate();p.join(timeout=.2)
        if p.is_alive():p.kill();p.join(timeout=.2)
    observed=list(details[:progress.value])
    confirmed=bool(timed_out.value) and stat.value==ev._FAILED and p.exitcode==0
    return {'confirmed_candidate_initialization_timeout':confirmed,
            'initialization_budget_seconds':budget,
            'upstream_status':ev._mapping[stat.value],
            'child_exitcode':p.exitcode,'observed':observed}

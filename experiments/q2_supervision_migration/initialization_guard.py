"""Diagnose only an unresolved EvalPlus timeout; never change a known verdict.

Use the pinned upstream evaluator and its existing task wall-time allowance.
The additional timer covers exec(code), which upstream leaves outside per-test
timers. Attribution requires a TimeoutException or an exception with a candidate
code frame during initialization, upstream FAIL, and normal child exit. Failures
outside candidate initialization remain unresolved.
"""
from __future__ import annotations
import builtins
import multiprocessing as mp
import types


def _worker(dataset, entry_point, code, inputs, expected, limits, atol, fast,
            stat, details, progress, initialization_timeout, initialization_error,
            initialization_exception):
    import evalplus.eval as ev
    from evalplus.eval.utils import time_limit, TimeoutException
    budget = min(60.0, sum(limits)) + 1.0

    def timed_exec(*args, **kwargs):
        with time_limit(budget):
            try:
                return builtins.exec(*args, **kwargs)
            except BaseException as exc:
                initialization_exception.value=type(exc).__name__.encode('ascii','replace')[:127]
                tb=exc.__traceback__;candidate_frame=False
                while tb is not None:
                    candidate_frame=candidate_frame or tb.tb_frame.f_code.co_filename=='<string>'
                    tb=tb.tb_next
                initialization_timeout.value=int(isinstance(exc,TimeoutException))
                initialization_error.value=int(candidate_frame or isinstance(exc,TimeoutException))
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
    init_error=mp.Value('b',0);init_exception=mp.Array('c',128)
    p=mp.Process(target=_worker,args=(dataset,entry_point,code,inputs,expected,
        limits,atol,fast_check,stat,details,progress,timed_out,init_error,init_exception))
    p.start()
    try:
        p.join(timeout=budget+1.0)
    finally:
        if p.is_alive():p.terminate();p.join(timeout=.2)
        if p.is_alive():p.kill();p.join(timeout=.2)
    observed=list(details[:progress.value])
    confirmed=bool(init_error.value) and stat.value==ev._FAILED and p.exitcode==0
    return {'confirmed_candidate_initialization_timeout':confirmed and bool(timed_out.value),
            'confirmed_candidate_initialization_failure':confirmed,
            'initialization_exception_type':init_exception.value.decode('ascii'),
            'initialization_budget_seconds':budget,
            'upstream_status':ev._mapping[stat.value],
            'child_exitcode':p.exitcode,'observed':observed}

"""Opt-in diagnosis of an unresolved suite timeout, never an automatic scorer.

Known verdicts must use the original scorer. This module preserves the pinned
EvalPlus test body, per-test timers, oracle and memory guard. Only its two
exception handlers gain observations, made *after* an exception has occurred.
There is no tracing or timing instrumentation inside a candidate call. A bounded
outer watchdog and the existing initialization timer are separate safety limits;
exhaustion or contradictory observations remain unknown, never reward zero.

Diagnostic verdicts do not edit historical records or authorize training/replay.
"""
from __future__ import annotations

import ast
import copy
import hashlib
import json
import math
import multiprocessing as mp
from pathlib import Path
import pickle
import platform
import time


PINNED_FILES = {
    "eval": "76857b678cddca08dcaf54d7927b9a77826715cf657654ca5baf6c2b267f4c34",
    "utils": "0aec25f437dbc7637219ba749ba71921670e71cd2e70b1cc23988896c0754bb1",
    "config": "dc14b4400cbf05d5bcab5b94d785f046cca22b0dbc10bc9756f8356dc42f18e3",
}
_ARGUMENTS = ["dataset", "entry_point", "code", "inputs", "expected",
              "time_limits", "atol", "fast_check", "stat", "details", "progress"]
_EVENT_BYTES = 65536
_ATTRIBUTABLE_TEST = {"candidate_call_exception", "candidate_test_timeout", "oracle_assertion"}
_ATTRIBUTABLE_INIT = {"candidate_initialization_exception", "candidate_initialization_timeout",
                      "candidate_syntax_error"}


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _input_hash(value):
    # Hash trusted frozen inputs before execution; candidate mutation is not identity.
    return _sha(pickle.dumps(value, protocol=4))


def _instrument(source, filename):
    """Compile the pinned function with exactly two after-exception observers."""
    tree = ast.parse(source, filename=filename)
    functions = [n for n in tree.body if isinstance(n, ast.FunctionDef)
                 and n.name == "unsafe_execute"]
    if len(functions) != 1:
        raise ValueError("expected one pinned unsafe_execute")
    original = functions[0]
    if [a.arg for a in original.args.args] != _ARGUMENTS:
        raise ValueError("upstream evaluator signature changed")
    function = copy.deepcopy(original)
    handlers = [n for n in ast.walk(function) if isinstance(n, ast.ExceptHandler)]
    if (len(handlers) != 2 or any(n.name is not None or not isinstance(n.type, ast.Name)
                                or n.type.id != "BaseException" for n in handlers)):
        raise ValueError("upstream exception structure changed")
    # The inner handler writes details[i]; the outer writes only terminal status.
    test_handlers = [n for n in handlers if any(isinstance(x, ast.Subscript)
                     and isinstance(x.value, ast.Name) and x.value.id == "details"
                     for x in ast.walk(n))]
    if len(test_handlers) != 1:
        raise ValueError("cannot identify unique upstream test exception handler")
    for handler in handlers:
        scope = "test" if handler is test_handlers[0] else "outer"
        handler.name = "_q2_caught_exception"
        observer = ast.Expr(value=ast.Call(func=ast.Name(id="_q2_observe_exception", ctx=ast.Load()),
            args=[ast.Name(id=handler.name, ctx=ast.Load()), ast.Constant(scope),
                  ast.Name(id="i", ctx=ast.Load()) if scope == "test" else ast.Constant(-1)],
            keywords=[]))
        handler.body.insert(0, ast.copy_location(observer, handler))
    module = ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[]))
    assertions = {n.lineno for n in ast.walk(original) if isinstance(n, ast.Assert)}
    provenance = {
        "unsafe_execute_source_sha256": _sha(ast.get_source_segment(source, original).encode()),
        "instrumented_ast_sha256": _sha(ast.dump(module, include_attributes=False).encode()),
        "exception_observers": 2,
        "candidate_tracing": False,
        "candidate_call_body_changed": False,
    }
    return compile(module, filename, "exec"), assertions, provenance


def _pinned_evaluator():
    import evalplus.eval as ev
    import evalplus.eval.utils as utils
    import evalplus.config as config
    modules = {"eval": ev, "utils": utils, "config": config}
    hashes = {key: _sha(Path(module.__file__).read_bytes()) for key, module in modules.items()}
    if hashes != PINNED_FILES:
        raise ValueError("installed evaluator differs from pinned EvalPlus 0.3.1 wheel")
    if (config.DEFAULT_MIN_TIME_LIMIT, config.DEFAULT_GT_TIME_LIMIT_FACTOR) != (1.0, 4.0):
        raise ValueError("pinned per-test limit constants changed")
    if (ev._SUCCESS, ev._FAILED, ev._UNKNOWN) != (0, 1, 3):
        raise ValueError("pinned evaluator status constants changed")
    source = Path(ev.__file__).read_text()
    compiled, assertions, provenance = _instrument(source, ev.__file__)
    provenance.update({"upstream_modules": {k: m.__name__ for k, m in modules.items()},
                       "upstream_file_sha256": hashes, "pinned_distribution": "evalplus==0.3.1"})
    return ev, utils, compiled, assertions, provenance


def _exception_event(exc, scope, index, input_hashes, evaluator_file, assertion_lines,
                     timeout_type, elapsed_seconds):
    frames = []
    frame_count = 0
    candidate_frame = False
    tb = exc.__traceback__
    while tb is not None:
        frame = tb.tb_frame
        filename = frame.f_code.co_filename
        candidate_frame = candidate_frame or filename == "<string>"
        frame_count += 1
        frames.append({"origin": "candidate" if filename == "<string>" else
                       "evaluator" if filename == evaluator_file else "other",
                       "function": frame.f_code.co_name, "line": tb.tb_lineno})
        if len(frames) > 32:
            # Keep both the caller and deepest failure origin without allowing
            # a candidate RecursionError to exhaust bounded diagnostic storage.
            del frames[4]
        tb = tb.tb_next
    is_timeout = isinstance(exc, timeout_type)
    classification = "harness_or_unattributed_exception"
    if scope == "test":
        if is_timeout and candidate_frame:
            classification = "candidate_test_timeout"
        elif candidate_frame:
            classification = "candidate_call_exception"
        elif (isinstance(exc, AssertionError) and frames
              and frames[-1]["origin"] == "evaluator"
              and frames[-1]["line"] in assertion_lines):
            classification = "oracle_assertion"
    elif scope == "outer":
        # Test exceptions propagate into the outer handler too. Admission uses the
        # test event whenever any test observation exists, so this is not init proof.
        if is_timeout and candidate_frame:
            classification = "candidate_initialization_timeout"
        elif candidate_frame:
            classification = "candidate_initialization_exception"
        elif isinstance(exc, SyntaxError) and exc.filename == "<string>":
            classification = "candidate_syntax_error"
    return {"scope": scope, "test_index": index if scope == "test" else None,
            "input_sha256": input_hashes[index] if scope == "test" and 0 <= index < len(input_hashes) else None,
            "exception_type": type(exc).__name__, "classification": classification,
            "traceback": frames, "traceback_frame_count": frame_count,
            "traceback_truncated": frame_count > len(frames),
            "elapsed_seconds_at_exception": elapsed_seconds,
            "elapsed_origin": "diagnostic_worker_start", "per_test_elapsed_measured": False}


def admit_diagnosis(*, original_details, observed, test_count, upstream_status,
                    child_exitcode, exception_events, observer_error=False):
    """Pure fail-closed admission; useful for tests without executing any candidate."""
    original = list(original_details)
    observations = list(observed)
    valid_bits = all(type(x) in (bool, int) and x in (0, 1) for x in original + observations)
    prefix_consistent = bool(valid_bits and len(original) <= len(observations) <= test_count
                             and observations[:len(original)] == original and all(original))
    result = {"verified_suite_verdict": None, "status": "timeout",
              "prefix_consistent": prefix_consistent, "admission_reason": "unresolved"}
    if observer_error:
        result["admission_reason"] = "observer_failed"
    elif child_exitcode != 0:
        result["admission_reason"] = "child_did_not_exit_normally"
    elif not prefix_consistent:
        result["admission_reason"] = "contradictory_or_incomplete_previous_prefix"
    elif upstream_status == "pass" and len(observations) == test_count and all(observations) and not exception_events:
        result.update(verified_suite_verdict="pass", status="pass", admission_reason="complete_original_suite")
    elif upstream_status == "fail":
        tests = [e for e in exception_events if e.get("scope") == "test"]
        if (len(tests) == 1 and observations and not observations[-1] and all(observations[:-1])
            and tests[0].get("test_index") == len(observations) - 1
            and tests[0].get("input_sha256")
            and tests[0].get("classification") in _ATTRIBUTABLE_TEST):
            result.update(verified_suite_verdict="fail", status="fail", admission_reason=tests[0]["classification"])
        elif (not observations and not original and not tests and len(exception_events) == 1
              and exception_events[0].get("scope") == "outer"
              and exception_events[0].get("classification") in _ATTRIBUTABLE_INIT):
            result.update(verified_suite_verdict="fail", status="fail", admission_reason=exception_events[0]["classification"])
        else:
            result["admission_reason"] = "failure_not_attributed_to_candidate_or_test_oracle"
    return result


def _worker(problem, code, inputs, expected, limits, input_hashes, initialization_budget,
            stat, details, progress, event_storage, event_length, observer_failed):
    # This function is called only in a bounded Linux child by diagnose_timeout.
    import builtins
    started = time.monotonic()
    ev, utils, compiled, assertions, _ = _pinned_evaluator()
    events = []

    def observe(exc, scope, index):
        try:
            events.append(_exception_event(exc, scope, index, input_hashes, ev.__file__,
                                          assertions, utils.TimeoutException, time.monotonic() - started))
            payload = json.dumps(events, sort_keys=True, allow_nan=False).encode()
            if len(payload) > len(event_storage):
                raise ValueError("exception metadata exceeds bounded storage")
            event_storage[:len(payload)] = payload
            event_length.value = len(payload)
        except BaseException:
            # Observation must never turn an original failure into another verdict.
            observer_failed.value = 1

    def timed_exec(*args, **kwargs):
        with utils.time_limit(initialization_budget):
            return builtins.exec(*args, **kwargs)

    namespace = {**ev.unsafe_execute.__globals__, "exec": timed_exec,
                 "_q2_observe_exception": observe}
    # Only our pinned function definition is executed here; the upstream function
    # retains the existing guarded candidate execution in its original location.
    builtins.exec(compiled, namespace)
    namespace["unsafe_execute"]("mbpp", problem["entry_point"], code, inputs, expected,
                                limits, problem["atol"], True, stat, details, progress)


def diagnose_timeout(problem, code, expected, reference_times, *, suite="extra",
                     original_details, original_status="timeout", outer_cap_seconds=180.0):
    """Diagnose one saved/returned code string, without changing any saved verdict.

    Return metadata with ``verified_suite_verdict`` (pass/fail/None), ``status``
    (pass/fail/timeout), admission reason, raw observations, exception attribution
    and provenance. The caller may construct SuiteVerdict(status, json.dumps(meta))
    only after its separately recorded comparison gate is admitted.
    """
    if original_status != "timeout":
        raise ValueError("known verdicts must not enter timeout recovery")
    if platform.system() != "Linux":
        raise ValueError("candidate diagnosis requires isolated Linux execution")
    if suite not in ("base", "extra"):
        raise ValueError("suite must be base or extra")
    if not isinstance(code, str):
        raise ValueError("candidate source must be text")
    cap = float(outer_cap_seconds)
    if not math.isfinite(cap) or not 0 < cap <= 180.0:
        raise ValueError("outer watchdog cap must be positive and at most 180 seconds")
    inputs = problem["base_input" if suite == "base" else "plus_input"]
    if not inputs or len(inputs) != len(expected) or len(inputs) != len(reference_times):
        raise ValueError("nonempty aligned frozen reference metadata required")
    if any(not math.isfinite(float(t)) or float(t) < 0 for t in reference_times):
        raise ValueError("invalid frozen reference timing")
    original = list(original_details)
    if len(original) > len(inputs) or any(type(x) not in (bool, int) or x != 1 for x in original):
        raise ValueError("first-failure outer timeout requires a passing observed prefix")
    ev, _, _, _, provenance = _pinned_evaluator()
    limits = [max(1.0, 4.0 * float(t)) for t in reference_times]
    initialization_budget = min(60.0, sum(limits)) + 1.0
    # Include init plus permitted calls and an explicit 2s orchestration allowance.
    # The 180s safety cap still wins; reaching it is unknown, not candidate failure.
    outer_budget = min(cap, initialization_budget + sum(limits) + 2.0)
    input_hashes = [_input_hash(x) for x in inputs]
    context = mp.get_context("fork")
    # One child writes; the parent reads after join/termination. Raw memory prevents
    # a killed child holding a lock from blocking evidence collection indefinitely.
    stat = context.RawValue("i", ev._UNKNOWN)
    progress = context.RawValue("i", 0)
    details = context.RawArray("b", len(inputs))
    storage = context.RawArray("c", _EVENT_BYTES)
    length = context.RawValue("i", 0)
    failed = context.RawValue("b", 0)
    proc = context.Process(target=_worker, args=(problem, code, inputs, expected, limits,
        input_hashes, initialization_budget, stat, details, progress, storage, length, failed))
    started = time.monotonic()
    proc.start()
    try:
        proc.join(timeout=outer_budget)
    finally:
        if proc.is_alive():
            proc.terminate()
            proc.join(timeout=.2)
        if proc.is_alive():
            proc.kill()
            proc.join(timeout=.2)
    events = []
    observer_error = bool(failed.value)
    try:
        if length.value:
            events = json.loads(bytes(storage[:length.value]).decode())
    except (ValueError, UnicodeError):
        observer_error = True
    observed = list(details[:max(0, min(progress.value, len(inputs)))])
    upstream_status = ev._mapping.get(stat.value)
    admission = admit_diagnosis(original_details=original, observed=observed,
        test_count=len(inputs), upstream_status=upstream_status, child_exitcode=proc.exitcode,
        exception_events=events, observer_error=observer_error or proc.is_alive())
    return {**admission, "original_status": original_status, "original_details": original,
        "observed": observed, "upstream_status": upstream_status,
        "child_exitcode": proc.exitcode, "child_still_alive": proc.is_alive(),
        "exception_events": events, "observer_error": observer_error,
        "per_test_limits_seconds": limits, "per_test_limits_unchanged": True,
        "initialization_budget_seconds": initialization_budget,
        "task_watchdog_budget_seconds": outer_budget,
        "outer_cap_seconds": cap, "orchestration_allowance_seconds": 2.0,
        "termination_grace_seconds": .4, "elapsed_seconds": time.monotonic() - started,
        "input_hash_serialization": "pickle_protocol_4_frozen_before_execution",
        "code_sha256": _sha(code.encode()), "suite": suite, "fast_check": True,
        "historical_records_changed": False, "provenance": provenance}

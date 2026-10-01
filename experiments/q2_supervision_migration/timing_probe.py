"""Finite, CPU-only measurement of a saved scorer discrepancy; never a reward.

Eight predeclared cells cross original/guarded scoring with fresh/fixture-first
process history. Each cell is a new interpreter with the same entry point. We
wrap only EvalPlus's per-test time_limit context boundary, not candidate code.
This is an observationally different execution path and cannot establish timing
equivalence by itself. No output from this module admits training or relabels
historical observations. Launch only in an isolated Linux CPU environment.
CPU-only workload does not mean a half-CPU/2-GiB rental is equivalent to the old
host: changed CPU quota, memory or interpreter can change wall-time verdicts.
Such a run is diagnostic evidence only, never reward-consistency acceptance.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import importlib.metadata
import json
import math
import multiprocessing as mp
import os
from pathlib import Path
import platform
import signal
import sys
import time

from .gpu_profile import ProfileError, durable_json, launch_guarded

MAX_SECONDS = 1800.0
CELL_SECONDS = 210.0
# Forward then reverse: two cells per combination, never stop/select by verdict.
CELL_PLAN = (
    ("original", False), ("guard", True), ("guard", False), ("original", True),
    ("original", True), ("guard", False), ("guard", True), ("original", False),
)
AUTHORED_FIXTURES = (
    ("valid", "def fixture(x):\n    return x", "pass"),
    ("wrong", "def fixture(x):\n    return x+1", "fail"),
    ("syntax", "this is invalid syntax !", "fail"),
    ("init", 'raise ValueError("authored initialization failure")', "fail"),
    ("test_timeout", "def fixture(x):\n    while True: pass", "fail"),
)
_FIELDS = ("limit_seconds", "start_wall", "start_cpu", "end_wall", "end_cpu",
           "alarm_before_delay", "alarm_before_interval", "alarm_armed_delay",
           "alarm_after_delay", "completed", "exception")
_WIDTH = len(_FIELDS)


def diagnostic_json(path, value):
    """Every probe artifact is explicitly ineligible for training or relabelling."""
    durable_json(path, {**value, "diagnostic_only": True, "eligible_for_reward": False,
        "model_admitted": False, "new_model_outputs": 0, "optimizer_updates": 0,
        "historical_records_changed": False})


def _handler_name(handler):
    if isinstance(handler, int):
        return str(int(handler))
    return f"{getattr(handler, '__module__', '?')}.{getattr(handler, '__qualname__', '?')}"


class BoundaryRecorder:
    """One forked writer, post-join reader; no lock held if watchdog kills child."""

    def __init__(self, limits, *, context=None):
        self.limits = tuple(float(v) for v in limits)
        if not self.limits or any(not math.isfinite(v) or v <= 0 for v in self.limits):
            raise ValueError("finite positive per-test limits required")
        context = context or mp.get_context("fork")
        self.count = context.RawValue("i", 0)
        self.error = context.RawValue("b", 0)
        self.values = context.RawArray("d", len(self.limits) * _WIDTH)
        self.exception_names = context.RawArray("c", len(self.limits) * 96)
        self.handlers_before = context.RawArray("c", len(self.limits) * 128)
        self.handlers_armed = context.RawArray("c", len(self.limits) * 128)

    @staticmethod
    def _put_text(storage, width, index, value):
        raw = value.encode("utf-8", errors="replace")[:width - 1]
        storage[index * width:(index + 1) * width] = raw + b"\0" * (width - len(raw))

    @staticmethod
    def _get_text(storage, width, index):
        return bytes(storage[index * width:(index + 1) * width]).split(b"\0", 1)[0].decode("utf-8", errors="replace")

    def wrap(self, original_timer, *, wall=time.monotonic, cpu=time.process_time,
             gettimer=None, gethandler=None):
        gettimer = gettimer or (lambda: signal.getitimer(signal.ITIMER_REAL))
        gethandler = gethandler or (lambda: signal.getsignal(signal.SIGALRM))

        @contextmanager
        def measured_timer(seconds):
            index = self.count.value
            if index >= len(self.limits) or seconds != self.limits[index]:
                self.error.value = 1
                raise ProfileError("diagnostic timer sequence differs from frozen suite")
            self.count.value = index + 1
            offset = index * _WIDTH
            before = gettimer()
            self._put_text(self.handlers_before, 128, index, _handler_name(gethandler()))
            self.values[offset:offset + 3] = [seconds, wall(), cpu()]
            self.values[offset + 5:offset + 7] = before
            try:
                with original_timer(seconds):
                    self.values[offset + 7] = gettimer()[0]
                    self._put_text(self.handlers_armed, 128, index, _handler_name(gethandler()))
                    yield
            except BaseException as exc:
                self.values[offset + 10] = 1
                self._put_text(self.exception_names, 96, index, type(exc).__name__)
                raise
            finally:
                # These clocks include context enter/exit and observation overhead;
                # they are not a claim of the candidate's uninstrumented runtime.
                self.values[offset + 3:offset + 5] = [wall(), cpu()]
                self.values[offset + 8] = gettimer()[0]
                self.values[offset + 9] = 1

        return measured_timer

    def records(self):
        rows = []
        for index in range(min(self.count.value, len(self.limits))):
            values = dict(zip(_FIELDS, self.values[index * _WIDTH:(index + 1) * _WIDTH]))
            complete = bool(values["completed"])
            rows.append({"test_index": index, **values,
                "wall_seconds": values["end_wall"] - values["start_wall"] if complete else None,
                "cpu_seconds": values["end_cpu"] - values["start_cpu"] if complete else None,
                "boundary_completed": complete,
                "exception_type": self._get_text(self.exception_names, 96, index),
                "alarm_handler_before": self._get_text(self.handlers_before, 128, index),
                "alarm_handler_armed": self._get_text(self.handlers_armed, 128, index)})
        return rows


def runtime_metadata():
    """Read a small whitelist; never serialize the full environment or secrets."""
    readings = {}
    paths = ["/proc/self/cgroup", "/proc/self/status", "/proc/pressure/cpu",
             "/sys/fs/cgroup/cpu.max", "/sys/fs/cgroup/cpu.stat",
             "/sys/fs/cgroup/cpu.pressure", "/sys/fs/cgroup/cpu/cpu.cfs_quota_us",
             "/sys/fs/cgroup/cpu/cpu.cfs_period_us", "/sys/fs/cgroup/memory.max",
             "/sys/fs/cgroup/memory/memory.limit_in_bytes"]
    for name in paths:
        try:
            text = Path(name).read_text()
            if name == "/proc/self/status":
                text = "\n".join(line for line in text.splitlines() if line.startswith(
                    ("Threads:", "Cpus_allowed_list:", "Mems_allowed_list:", "VmRSS:", "VmSize:")))
            readings[name] = text[:16384]
        except OSError as exc:
            readings[name] = {"unavailable": type(exc).__name__}
    try:
        distribution = importlib.metadata.version("evalplus")
    except importlib.metadata.PackageNotFoundError:
        distribution = None
    return {"pid": os.getpid(), "ppid": os.getppid(), "python": sys.version,
        "python_executable": sys.executable, "platform": platform.platform(),
        "evalplus_distribution": distribution,
        "affinity": sorted(os.sched_getaffinity(0)),
        "alarm_timer": list(signal.getitimer(signal.ITIMER_REAL)),
        "alarm_handler": _handler_name(signal.getsignal(signal.SIGALRM)),
        "multiprocessing_start_method": mp.get_start_method(allow_none=True),
        "selected_environment": {name: os.environ.get(name) for name in (
            "PYTHONHASHSEED", "PYTHONNOUSERSITE", "CUDA_VISIBLE_DEVICES",
            "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
            "EVALPLUS_TIMEOUT_PER_TASK", "EVALPLUS_MAX_MEMORY_BYTES")},
        "resource_readings": readings,
        "cpu_quota_visibility": "visible cgroup files only; ancestor/host limits may be hidden"}


def _diagnostic_identity(problem, code, reference, manifest):
    # Serialized data only; pickle here does not load/execute anything.
    import pickle
    digest = lambda value: hashlib.sha256(pickle.dumps(value, protocol=4)).hexdigest()
    return {"task_id": "Mbpp/599", "code_sha256": hashlib.sha256(code.encode()).hexdigest(),
        "input_sha256": digest(problem["plus_input"]), "expected_sha256": digest(reference["plus"]),
        "reference_times_sha256": digest(reference["plus_time"]),
        "per_input_sha256": [digest(x) for x in problem["plus_input"]],
        "reference_manifest": manifest, "serialization": "pickle_protocol_4"}


def cell_worker(a):
    from .completion_preflight import saved_sample
    from .screen_scoring import load_problems, load_references
    from .scoring_cpu import pin_scoring_cpu
    from .scoring_guard_v2 import _pinned_evaluator, diagnose_timeout
    out = Path(a.out) / f"cell_{a._cell:02d}"
    mode, fixtures_first = CELL_PLAN[a._cell]
    # Guard already uses fork. Freeze the original path to the same mechanism
    # rather than depending on Python-version-specific default start methods.
    if mp.get_start_method(allow_none=True) is None:
        mp.set_start_method("fork")
    if mp.get_start_method() != "fork":
        raise ProfileError("diagnostic paths require identical fork isolation")
    diagnostic_json(out / "placement.json", pin_scoring_cpu())
    diagnostic_json(out / "runtime_before.json", runtime_metadata())
    old, code = saved_sample(Path(a.continuation_root) / "R_future", 25, 8)
    old_detail = json.loads(old["extra"]["detail"])
    if (old["task_id"] != "Mbpp/599" or old["extra"]["status"] != "timeout"
        or old_detail["tests_observed"] != 34 or old_detail["test_passes_observed"] != 34):
        raise ProfileError("wrong immutable failure fixture")
    problems = load_problems(a.data_json, a.data_sha256)
    refs, manifest = load_references(a.references)
    if manifest["data_sha256"] != a.data_sha256:
        raise ProfileError("reference identity mismatch")
    problem, reference = problems["Mbpp/599"], refs["Mbpp/599"]
    diagnostic_json(out / "fixture_identity.json", _diagnostic_identity(problem, code, reference, manifest))
    # The same imports/hash checks occur in both original and guard cells.
    ev, _, _, _, provenance = _pinned_evaluator()
    diagnostic_json(out / "evaluator_provenance.json", provenance)
    if fixtures_first:
        for name, authored, expected in AUTHORED_FIXTURES:
            result = diagnose_timeout({"base_input": [[1]], "entry_point": "fixture", "atol": 0},
                authored, [1], [.01], suite="base", original_details=[])
            diagnostic_json(out / f"authored_{name}.json", {"raw_result": result})
            if result.get("verified_suite_verdict") != expected:
                raise ProfileError("authored diagnostic fixture failed: " + name)
    limits = [max(1.0, 4.0 * t) for t in reference["plus_time"]]
    recorder = BoundaryRecorder(limits)
    original_timer = ev.time_limit
    ev.time_limit = recorder.wrap(original_timer)
    diagnostic_json(out / "runtime_before_candidate.json", runtime_metadata())
    started = time.monotonic()
    try:
        if mode == "original":
            status, details = ev.untrusted_check("mbpp", code, problem["plus_input"],
                problem["entry_point"], expected=reference["plus"], atol=problem["atol"],
                ref_time=reference["plus_time"], fast_check=True)
            result = {"status": status, "details": [bool(x) for x in details]}
        else:
            result = diagnose_timeout(problem, code, reference["plus"], reference["plus_time"],
                suite="extra", original_details=[True] * 34, outer_cap_seconds=180)
    finally:
        ev.time_limit = original_timer
        diagnostic_json(out / "boundaries.json", {"observations": recorder.records(),
            "recorder_error": bool(recorder.error.value), "elapsed_seconds": time.monotonic() - started,
            "candidate_body_tracing": False, "per_test_limits_changed": False,
            "observation_changes_execution_path": True, "eligible_for_reward": False})
        diagnostic_json(out / "runtime_after.json", runtime_metadata())
    diagnostic_json(out / "diagnostic_result.json", {"mode": mode, "fixtures_first": fixtures_first,
        "raw_result": result, "source_commit": a.source_commit,
        "diagnostic_only": True, "eligible_for_reward": False, "model_admitted": False,
        "new_model_outputs": 0, "optimizer_updates": 0, "historical_records_changed": False})
    if recorder.error.value:
        raise ProfileError("diagnostic boundary sequence invalid")


def available_seconds(deadline_epoch, started_epoch, now_epoch):
    if not all(math.isfinite(v) for v in (deadline_epoch, started_epoch, now_epoch)):
        raise ProfileError("finite absolute shared deadline required")
    return min(deadline_epoch, started_epoch + MAX_SECONDS) - now_epoch


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("continuation-root", "references", "data-json", "data-sha256", "out", "source-commit"):
        p.add_argument("--" + name, required=True)
    p.add_argument("--deadline-epoch", required=True, type=float,
                   help="absolute CPU stop time; must include externally reserved collection time")
    p.add_argument("--execute-saved-output-diagnostic", action="store_true")
    p.add_argument("--_cell", type=int, choices=range(len(CELL_PLAN)), help=argparse.SUPPRESS)
    return p


def main(argv=None):
    raw = list(sys.argv[1:] if argv is None else argv)
    a = parser().parse_args(raw)
    if (sys.platform != "linux" or os.environ.get("CUDA_VISIBLE_DEVICES") != ""
        or not a.execute_saved_output_diagnostic):
        raise ProfileError("explicit isolated Linux CPU-only diagnostic required")
    if not math.isfinite(a.deadline_epoch) or a.deadline_epoch <= time.time():
        raise ProfileError("shared diagnostic deadline already elapsed or invalid")
    if a._cell is not None:
        if os.environ.get("Q2_PROFILE_PARENT_PID") != str(os.getppid()):
            raise ProfileError("owned diagnostic parent required")
        try:
            cell_worker(a)
        except BaseException as exc:
            diagnostic_json(Path(a.out) / f"cell_{a._cell:02d}" / "failure.json",
                {"error": repr(exc), "model_admitted": False, "eligible_for_reward": False})
            os._exit(1)
        os._exit(0)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=False)
    started = time.time()
    diagnostic_json(out / "probe_intent.json", {"cell_plan": CELL_PLAN, "source_commit": a.source_commit,
        "started_epoch": started, "deadline_epoch": min(a.deadline_epoch, started + MAX_SECONDS),
        "max_seconds": MAX_SECONDS, "cell_max_seconds": CELL_SECONDS,
        "fixed_count_not_until_pass": True, "eligible_for_reward": False,
        "model_admitted": False, "new_model_outputs": 0, "optimizer_updates": 0})
    completed = 0
    attempted = 0
    failed_indices = []
    stop_reason = "infrastructure_failure"

    def interrupted(signum, frame):
        raise InterruptedError(f"diagnostic received signal {signum}")

    previous = signal.signal(signal.SIGTERM, interrupted)
    try:
        for index, (mode, fixtures_first) in enumerate(CELL_PLAN):
            remaining = available_seconds(a.deadline_epoch, started, time.time())
            if remaining < CELL_SECONDS + 5:
                stop_reason = "insufficient_shared_window_for_next_fixed_cell"
                break
            cell = out / f"cell_{index:02d}"
            cell.mkdir(exist_ok=False)
            diagnostic_json(cell / "cell_intent.json", {"index": index, "mode": mode,
                "fixtures_first": fixtures_first, "eligible_for_reward": False})
            attempted += 1
            rc = launch_guarded([sys.executable, "-m", __spec__.name, *raw, "--_cell", str(index)],
                cell, min(CELL_SECONDS, remaining - 5), phase="cpu")
            if rc:
                failed_indices.append(index)
            else:
                completed += 1
            # Preserve a failed cell and move to the next predeclared fresh
            # process; never repeat that cell or select a replacement verdict.
        else:
            stop_reason = ("fixed_diagnostic_cells_attempted_with_failures" if failed_indices
                           else "fixed_diagnostic_cells_completed")
    finally:
        signal.signal(signal.SIGTERM, previous)
        diagnostic_json(out / "probe_receipt.json", {"cells_completed": completed,
            "cells_attempted": attempted, "failed_cell_indices": failed_indices,
            "cells_planned": len(CELL_PLAN), "stop_reason": stop_reason,
            "elapsed_seconds": time.time() - started, "eligible_for_reward": False,
            "model_admitted": False, "historical_records_changed": False})
    return 0 if completed == len(CELL_PLAN) else 1


if __name__ == "__main__":
    raise SystemExit(main())

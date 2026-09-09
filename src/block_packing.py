"""One bounded MILP for disjoint four-problem blocks from exact support sets.

The caller must establish complete key coverage separately. Equal *exact*
support sets are interchangeable for packing; coarse candidate masks are not.
Each input group has exactly ``problem_ids`` and an arbitrary JSON
``representative``. Duplicate IDs within a group or duplicate support sets are
rejected. Group IDs in the output are zero-based input positions.

SciPy minimizes -sum(y_g). For each eligible (problem, group), x_pg is binary;
y_g is an integer in [0, floor(|S_g|/4)]. Constraints are sum_g x_pg <= 1 and
sum_p x_pg = 4*y_g. An integral feasible solution partitions into legal blocks
because every assigned problem belongs to the group's exact support set.

SciPy/HiGHS API: https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.milp.html
No solver retry or per-group 60-second allowance is used. The remaining global
time budget is passed to the single solver call; elapsed time is also recorded.
The solver's time limit is not an operating-system hard-kill guarantee.
"""
from __future__ import annotations

import json
import math
import time
from collections import Counter
from typing import Any

import numpy as np
import scipy
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import coo_matrix


INTEGRALITY_TOLERANCE = 1e-6
MAX_TIME_LIMIT_SECONDS = 60.0
STATUS_NAMES = {0: "optimal", 1: "time_or_iteration_limit", 2: "infeasible",
                3: "unbounded", 4: "solver_error"}


class PackingVerificationError(RuntimeError):
    """The solver's reported solution/certificate fails an independent check."""


def _json_copy(value: Any) -> Any:
    def validate(node: Any) -> None:
        if node is None or type(node) in (str, bool, int):
            return
        if type(node) is float and math.isfinite(node):
            return
        if type(node) is list:
            for item in node:
                validate(item)
            return
        if type(node) is dict and all(type(key) is str for key in node):
            for item in node.values():
                validate(item)
            return
        raise ValueError("Representative must contain only finite JSON values")
    validate(value)
    return json.loads(json.dumps(value, allow_nan=False, sort_keys=True))


def _normalize_groups(groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if type(groups) is not list:
        raise ValueError("Support groups must be a JSON list")
    normalized, seen = [], set()
    for group_id, group in enumerate(groups):
        if type(group) is not dict or set(group) != {"problem_ids", "representative"}:
            raise ValueError("Each group requires exactly problem_ids and representative")
        pids = group["problem_ids"]
        if (type(pids) is not list
                or any(type(pid) is not str or not pid for pid in pids)):
            raise ValueError("problem_ids must be a list of nonempty strings")
        if len(set(pids)) != len(pids):
            raise ValueError("Duplicate problem ID within a support group")
        support = tuple(sorted(pids))
        if support in seen:
            raise ValueError("Duplicate exact support group")
        seen.add(support)
        normalized.append({"group_id": group_id, "problem_ids": list(support),
                           "representative": _json_copy(group["representative"])})
    return normalized


def _finite_or_none(value: Any) -> float | None:
    if value is None:
        return None
    result = float(value)
    return result if math.isfinite(result) else None


def _verified_assignments(vector: Any, groups: list[dict[str, Any]],
                          edges: list[tuple[str, int]],
                          upper_bounds: np.ndarray) -> tuple[list[dict[str, Any]],
                                                             list[dict[str, Any]]]:
    values = np.asarray(vector, dtype=float)
    if values.shape != upper_bounds.shape or not np.all(np.isfinite(values)):
        raise PackingVerificationError("Wrong-shape or nonfinite solver solution")
    rounded = np.rint(values)
    tolerance = INTEGRALITY_TOLERANCE
    if np.any(np.abs(values - rounded) > tolerance):
        raise PackingVerificationError("Solver solution exceeds integrality tolerance")
    if (np.any(values < -tolerance) or np.any(values > upper_bounds + tolerance)
            or np.any(rounded < 0) or np.any(rounded > upper_bounds)):
        raise PackingVerificationError("Solver solution violates variable bounds")
    integer = rounded.astype(np.int64)
    assignments = [[] for _ in groups]
    used = Counter()
    for index, (pid, group_id) in enumerate(edges):
        if integer[index]:
            if integer[index] != 1:
                raise PackingVerificationError("Assignment variable is not binary")
            assignments[group_id].append(pid)
            used[pid] += 1
    if any(count > 1 for count in used.values()):
        raise PackingVerificationError("A problem was assigned to multiple groups")
    blocks, assigned_groups = [], []
    for group in groups:
        group_id = group["group_id"]
        pids = sorted(assignments[group_id])
        count = int(integer[len(edges) + group_id])
        if len(pids) != 4 * count:
            raise PackingVerificationError("Group assignment count differs from four times y")
        if not set(pids) <= set(group["problem_ids"]):
            raise PackingVerificationError("Assigned problem lacks exact group support")
        if count:
            assigned_groups.append({"group_id": group_id, "problem_ids": pids,
                                    "block_count": count,
                                    "representative": _json_copy(group["representative"])})
        for start in range(0, len(pids), 4):
            block = pids[start:start + 4]
            if len(block) != 4 or len(set(block)) != 4:
                raise PackingVerificationError("A block does not have four distinct problems")
            blocks.append({"group_id": group_id, "problem_ids": block,
                           "representative": _json_copy(group["representative"])})
    flat = [pid for block in blocks for pid in block["problem_ids"]]
    if len(flat) != len(set(flat)):
        raise PackingVerificationError("Concrete blocks reuse a problem")
    if len(blocks) != int(integer[len(edges):].sum()):
        raise PackingVerificationError("Concrete blocks disagree with the primal objective")
    return blocks, assigned_groups


def pack_support_groups(support_groups: list[dict[str, Any]], *,
                        time_limit: float = MAX_TIME_LIMIT_SECONDS) -> dict[str, Any]:
    """Return a checked packing, solver status and bounds for supplied groups.

    ``dual_upper_bound`` is the sign-corrected finite solver bound for maximum
    blocks, or None if unavailable. ``integer_upper_bound`` also uses the
    elementary union/group-capacity bound. Status 1 is never labelled optimal,
    even when its observed bounds happen to coincide. With no incumbent, the
    known feasible empty packing supplies a lower bound of zero, not a failed
    or negative support result. A false solver certificate is rejected.
    """
    started = time.monotonic()
    if (type(time_limit) not in (int, float) or not math.isfinite(time_limit)
            or not 0 < time_limit <= MAX_TIME_LIMIT_SECONDS):
        raise ValueError("Use one global positive time limit of at most 60 seconds")
    groups = _normalize_groups(support_groups)
    pids = sorted({pid for group in groups for pid in group["problem_ids"]})
    edges = [(pid, group["group_id"]) for group in groups for pid in group["problem_ids"]]
    elementary_upper = min(len(pids) // 4,
                           sum(len(group["problem_ids"]) // 4 for group in groups))
    record: dict[str, Any] = {
        "schema_version": 1, "solver": "scipy.optimize.milp/HiGHS",
        "scipy_version": scipy.__version__, "time_limit_seconds": float(time_limit),
        "mip_rel_gap_target": 0.0, "integrality_tolerance": INTEGRALITY_TOLERANCE,
        "input_group_count": len(groups), "input_problem_count": len(pids),
        "assignment_variable_count": len(edges), "group_variable_count": len(groups),
        "elementary_upper_bound": elementary_upper,
        "scope": "Maximum packing over the supplied exact support sets; key-search completeness is a separate prerequisite",
    }
    if elementary_upper == 0:
        record.update(status="optimal", solver_status=0, is_optimal=True,
                      solver_called=False, solution_source="analytical_empty_packing",
                      primal_block_count=0, dual_upper_bound=0.0, integer_upper_bound=0,
                      absolute_gap_blocks=0, gap=0.0, blocks=[], group_assignments=[],
                      used_problem_ids=[], elapsed_seconds=time.monotonic() - started)
        return record

    problem_row = {pid: index for index, pid in enumerate(pids)}
    rows, columns, entries = [], [], []
    for index, (pid, group_id) in enumerate(edges):
        rows.extend((problem_row[pid], len(pids) + group_id))
        columns.extend((index, index))
        entries.extend((1.0, 1.0))
    for group in groups:
        rows.append(len(pids) + group["group_id"])
        columns.append(len(edges) + group["group_id"])
        entries.append(-4.0)
    variable_count = len(edges) + len(groups)
    matrix = coo_matrix((entries, (rows, columns)),
                        shape=(len(pids) + len(groups), variable_count)).tocsc()
    upper = np.asarray([1.0] * len(edges)
                       + [len(group["problem_ids"]) // 4 for group in groups], dtype=float)
    objective = np.asarray([0.0] * len(edges) + [-1.0] * len(groups))
    remaining = float(time_limit) - (time.monotonic() - started)
    if remaining <= 0:
        record.update(status="time_or_iteration_limit", solver_status=1, is_optimal=False,
                      solver_called=False, solution_source="empty_feasible_fallback",
                      message="Global packing budget exhausted before the solver call",
                      primal_block_count=0, dual_upper_bound=None,
                      integer_upper_bound=elementary_upper, absolute_gap_blocks=elementary_upper,
                      gap=None, blocks=[], group_assignments=[], used_problem_ids=[],
                      elapsed_seconds=time.monotonic() - started)
        return record
    result = milp(c=objective, integrality=np.ones(variable_count, dtype=np.int32),
                  bounds=Bounds(np.zeros(variable_count), upper),
                  constraints=LinearConstraint(matrix, np.zeros(matrix.shape[0]),
                                               np.asarray([1.0] * len(pids) + [0.0] * len(groups))),
                  options={"time_limit": remaining, "mip_rel_gap": 0.0, "presolve": True})
    status = int(result.status)
    if status not in STATUS_NAMES:
        raise PackingVerificationError("Unrecognized solver status")
    if status in (2, 3):
        raise PackingVerificationError("Infeasible/unbounded certificate contradicts a bounded zero-feasible model")
    if result.x is None:
        if status == 0:
            raise PackingVerificationError("Optimal status without a primal solution")
        blocks, assignments = [], []
        solution_source = "empty_feasible_fallback"
    else:
        blocks, assignments = _verified_assignments(result.x, groups, edges, upper)
        solution_source = "solver_incumbent"
        fun = _finite_or_none(getattr(result, "fun", None))
        if fun is not None and abs(fun + len(blocks)) > INTEGRALITY_TOLERANCE:
            raise PackingVerificationError("Reported objective disagrees with checked integer assignments")
    primal = len(blocks)
    lower = _finite_or_none(getattr(result, "mip_dual_bound", None))
    dual_upper = None if lower is None else -lower
    integer_upper = elementary_upper
    if dual_upper is not None:
        if dual_upper < primal - INTEGRALITY_TOLERANCE:
            raise PackingVerificationError("Solver dual upper bound is below the feasible primal")
        integer_upper = min(integer_upper, math.floor(dual_upper + INTEGRALITY_TOLERANCE))
    if status == 0:
        if dual_upper is not None and integer_upper != primal:
            raise PackingVerificationError("Optimal status disagrees with the solver's integer bound")
        integer_upper = primal
    if not primal <= integer_upper <= elementary_upper:
        raise PackingVerificationError("Inconsistent verified packing bounds")
    record.update(status=STATUS_NAMES[status], solver_status=status, is_optimal=status == 0,
                  solver_called=True, solver_time_limit_seconds=remaining,
                  solution_source=solution_source, message=str(result.message),
                  primal_block_count=primal, dual_upper_bound=dual_upper,
                  integer_upper_bound=integer_upper, absolute_gap_blocks=integer_upper - primal,
                  gap=_finite_or_none(getattr(result, "mip_gap", None)),
                  blocks=blocks, group_assignments=assignments,
                  used_problem_ids=sorted(pid for block in blocks for pid in block["problem_ids"]),
                  elapsed_seconds=time.monotonic() - started)
    return record

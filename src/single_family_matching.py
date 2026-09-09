"""Complete local-tuple census for one numerical path family on a fixed pool.

No expression solver or tokenizer is called. Records must already be verified.
Each problem's four paths share one supervised length and four structures, with
four different numeric AC classes. A shared key has at least four problems;
different problems may use different lengths. Deadline-limited discoveries are
feasible lower bounds, never evidence that missing keys are impossible.
"""
from __future__ import annotations

from collections import deque
from collections.abc import Callable, Iterable, Mapping
import itertools
import json
import math
import time


FAMILIES = ("identity_present", "identity_absent")
K = 4


class _Deadline(Exception):
    def __init__(self, stage: str):
        self.stage = stage


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _class_assignment(structures, options, check):
    """Iterative alternating-path matching for four structures and AC classes."""
    owners = {}
    assigned = [None] * K
    for start in range(K):
        predecessors = {start: None}
        pending = deque([start])
        terminal = None
        while pending and terminal is None:
            check("class_assignment")
            slot = pending.popleft()
            for ac_class in sorted(options[structures[slot]]):
                check("class_assignment")
                if ac_class not in owners:
                    terminal = (slot, ac_class)
                    break
                next_slot = owners[ac_class]
                if next_slot not in predecessors:
                    predecessors[next_slot] = (slot, ac_class)
                    pending.append(next_slot)
        if terminal is None:
            return None
        slot, ac_class = terminal
        while True:
            owners[ac_class], assigned[slot] = slot, ac_class
            if predecessors[slot] is None:
                break
            slot, ac_class = predecessors[slot]
    _require(len(set(assigned)) == K, "Internal AC matching collision")
    return assigned


def single_family_keys(records: Iterable[Mapping], family: str = "identity_absent",
                       max_seconds: float = 120,
                       *, clock: Callable[[], float] = time.monotonic) -> dict:
    """Enumerate every four-structure key supported by four distinct problems.

    Index by problem/length first. Enumerate all four-structure combinations in
    each index; never union a problem's structures across incompatible lengths.
    Keep the lowest feasible length for each problem/key and a deterministic
    full-record certificate. A numeric AC class can fill at most one slot even
    for synthetic metadata where class-to-structure is not a function.

    The deadline applies to indexing and tuple/assignment discovery. Output
    assembly retains completed witnesses after a stop; it cannot turn an
    incomplete discovery into a complete negative result. No packing is run.
    """
    _require(family in FAMILIES, "Unknown numerical family")
    _require(type(max_seconds) in (int, float) and math.isfinite(max_seconds) and max_seconds > 0,
             "Positive finite deadline required")
    started = clock()
    counters = {"input_records_seen": 0, "family_records_indexed": 0,
                "other_family_records": 0, "excluded_unencodable_records": 0,
                "problem_length_groups_completed": 0, "structure_combinations_tested": 0,
                "class_assignment_checks_completed": 0,
                "feasible_problem_length_keys": 0, "distinct_problem_key_support": 0}
    index, representative_order, discovered, feasible_lengths = {}, {}, {}, {}
    complete, stop_stage, indexing_complete = True, None, False
    total_combinations = None

    def check(stage):
        if clock() - started >= max_seconds:
            raise _Deadline(stage)

    try:
        for raw in records:
            check("indexing")
            counters["input_records_seen"] += 1
            _require(isinstance(raw, Mapping), "Inventory record must be a mapping")
            _require(raw.get("family") in FAMILIES, "Inventory record has unknown family")
            if raw["family"] != family:
                counters["other_family_records"] += 1
                continue
            _require(type(raw.get("encodable", True)) is bool, "Encodability must be boolean")
            if not raw.get("encodable", True):
                counters["excluded_unencodable_records"] += 1
                continue
            for field in ("problem_id", "structure_id", "ac_class", "expression"):
                _require(isinstance(raw.get(field), str) and raw[field], "Record identity fields must be nonempty strings")
            length = raw.get("n_supervised")
            _require(type(length) is int and length > 0, "Positive supervised length required")
            try:
                stable = json.dumps(dict(raw), sort_keys=True, separators=(",", ":"), allow_nan=False)
            except (TypeError, ValueError) as exc:
                raise ValueError("Inventory records must contain finite JSON values") from exc
            pid, structure, ac_class = raw["problem_id"], raw["structure_id"], raw["ac_class"]
            coordinate = (pid, length, structure, ac_class)
            options = index.setdefault(pid, {}).setdefault(length, {}).setdefault(structure, {})
            if coordinate not in representative_order or stable < representative_order[coordinate]:
                representative_order[coordinate] = stable
                options[ac_class] = json.loads(stable)
            counters["family_records_indexed"] += 1
        check("indexing_completion")
        indexing_complete = True
        total_combinations = sum(math.comb(len(options), K) for lengths in index.values()
                                 for options in lengths.values() if len(options) >= K)
        for pid in sorted(index):
            for length, options in sorted(index[pid].items()):
                check("problem_length_group")
                for structures in itertools.combinations(sorted(options), K):
                    check("structure_combinations")
                    counters["structure_combinations_tested"] += 1
                    assignment = _class_assignment(structures, options, check)
                    counters["class_assignment_checks_completed"] += 1
                    if assignment is None:
                        continue
                    counters["feasible_problem_length_keys"] += 1
                    feasible_lengths.setdefault(pid, set()).add(length)
                    support = discovered.setdefault(structures, {})
                    if pid not in support:
                        support[pid] = {"problem_id": pid, "n_supervised": length,
                                        "slots": [{"family": family, "structure_id": structure,
                                                   "ac_class": ac_class,
                                                   "record": options[structure][ac_class]}
                                                  for structure, ac_class in zip(structures, assignment)]}
                        counters["distinct_problem_key_support"] += 1
                counters["problem_length_groups_completed"] += 1
        check("completion")
    except _Deadline as stop:
        complete, stop_stage = False, stop.stage

    keys = [{"structures": list(structures), "problem_ids": sorted(support),
             "witnesses": {pid: support[pid] for pid in sorted(support)}}
            for structures, support in sorted(discovered.items()) if len(support) >= K]
    supported = sorted({pid for key in keys for pid in key["problem_ids"]})
    if complete:
        _require(counters["structure_combinations_tested"] == total_combinations
                 == counters["class_assignment_checks_completed"], "Complete combination accounting mismatch")
    return {"schema_version": 1, "family": family, "per_family": K,
            "length_mode": "variable_per_problem_single_family",
            "complete": complete, "stop_reason": "completed" if complete else "deadline",
            "stop_stage": stop_stage, "indexing_complete": indexing_complete,
            "max_seconds": max_seconds, "elapsed_seconds": max(0, clock() - started),
            "input_problem_count": len(index) if indexing_complete else None,
            "total_local_structure_combinations": total_combinations,
            "counters": counters, "local_key_count": len(discovered),
            "shared_key_count": len(keys), "keys": keys,
            "supported_problem_ids": supported,
            "per_problem_feasible_lengths": {pid: sorted(lengths) for pid, lengths in sorted(feasible_lengths.items())},
            "support_interpretation": ("complete_shared_support_not_joint_packing" if complete else
                                       "discovered_feasible_lower_bound_not_absence_or_upper_bound"),
            "limitations": ["Only the requested numerical family is required; no opposite-family support is inferred",
                            "Input records must already have verified legality, tokenizer provenance and numerical-family labels",
                            "Shared-key support is not simultaneous disjoint-block capacity or statistical adequacy",
                            "No solution enumeration, tokenizer call, GPU work or training configuration is performed"]}

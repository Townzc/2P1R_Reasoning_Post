"""Bounded, deterministic CPU matching for a fixed two-family K=4 design.

Records are already verified features, not expressions interpreted by this module.
Each selected problem uses eight distinct numerical AC classes at one supervised
length.  The four operator-only structures within each family are distinct; the
two families may use different structure tuples.  A shared block key fixes those
two tuples, but allows each problem to have its own common supervised length.

The search uses union-over-length problem masks as conservative pruning bounds.
Exact assignments subsequently remove candidates whose features occur only at
incompatible lengths.  Exhaustion is distinguished from every resource cap.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable, Iterable, Mapping, Sequence
import json
import time
from typing import Any


K = 4
FAMILIES = ("identity_present", "identity_absent")
Record = dict[str, Any]
FamilyIndex = dict[str, dict[str, dict[str, Record]]]
InventoryIndex = dict[str, dict[int, FamilyIndex]]


def _validated_record(record: Mapping[str, Any]) -> tuple[Record, str]:
    if not isinstance(record, Mapping):
        raise ValueError("Each inventory record must be a mapping")
    row = dict(record)
    for field in ("problem_id", "structure_id", "ac_class"):
        if not isinstance(row.get(field), str) or not row[field]:
            raise ValueError(f"{field} must be a nonempty string")
    if row.get("family") not in FAMILIES:
        raise ValueError(f"family must be one of {FAMILIES}")
    length = row.get("n_supervised")
    if isinstance(length, bool) or not isinstance(length, int) or length <= 0:
        raise ValueError("n_supervised must be a positive integer")
    try:
        stable_key = json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError("Inventory records must contain finite JSON values") from exc
    return row, stable_key


class _SearchStopped(Exception):
    def __init__(self, reason: str, stage: str):
        self.reason = reason
        self.stage = stage


class _Budget:
    def __init__(self, max_key_pair_checks: int, max_structure_nodes: int,
                 max_seconds: float, clock: Callable[[], float]):
        for label, value in (("max_key_pair_checks", max_key_pair_checks),
                             ("max_structure_nodes", max_structure_nodes)):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{label} must be a nonnegative integer")
        if isinstance(max_seconds, bool) or not isinstance(max_seconds, (float, int)):
            raise ValueError("max_seconds must be finite and positive")
        if not 0 < max_seconds < float("inf"):
            raise ValueError("max_seconds must be finite and positive")
        self.clock = clock
        self.start = clock()
        self.max_seconds = max_seconds
        self.limits = {"key_pair_checks": max_key_pair_checks,
                       "structure_nodes": max_structure_nodes}
        self.counters = {"input_records_indexed": 0, "structure_nodes": 0,
                         "key_pair_checks": 0, "raw_key_pairs_support_at_least_four": 0,
                         "slot_assignment_checks": 0, "exact_supported_keys": 0}

    def check(self, stage: str) -> None:
        if self.clock() - self.start >= self.max_seconds:
            raise _SearchStopped("deadline", stage)

    def consume(self, counter: str, stage: str) -> None:
        self.check(stage)
        if self.counters[counter] >= self.limits[counter]:
            raise _SearchStopped(f"{counter}_cap", stage)
        self.counters[counter] += 1


def _index_records(records: Iterable[Mapping[str, Any]],
                   budget: _Budget | None = None) -> InventoryIndex:
    index: InventoryIndex = {}
    representative_keys: dict[tuple[str, int, str, str, str], str] = {}
    for raw in records:
        if budget is not None:
            budget.check("indexing")
        row, stable_key = _validated_record(raw)
        pid, length, family = row["problem_id"], row["n_supervised"], row["family"]
        structure, ac_class = row["structure_id"], row["ac_class"]
        classes = index.setdefault(pid, {}).setdefault(length, {}).setdefault(
            family, {}).setdefault(structure, {})
        coordinate = (pid, length, family, structure, ac_class)
        if coordinate not in representative_keys or stable_key < representative_keys[coordinate]:
            representative_keys[coordinate] = stable_key
            classes[ac_class] = row
        if budget is not None:
            budget.counters["input_records_indexed"] += 1
    return index


def _single_inventory(records: Iterable[Mapping[str, Any]]) -> tuple[str, int, FamilyIndex] | None:
    index = _index_records(records)
    if not index:
        return None
    if len(index) != 1:
        raise ValueError("Assignment inventory must contain exactly one problem_id")
    pid = next(iter(index))
    if len(index[pid]) != 1:
        raise ValueError("Assignment inventory must contain exactly one n_supervised length")
    length = next(iter(index[pid]))
    return pid, length, index[pid][length]


def _structures(values: Sequence[str], label: str) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise ValueError(f"{label} must contain exactly four distinct structure IDs")
    values = tuple(values)
    if (len(values) != K or any(not isinstance(value, str) or not value for value in values)
            or len(set(values)) != K):
        raise ValueError(f"{label} must contain exactly four distinct structure IDs")
    return tuple(sorted(values))


def _witness(pid: str, length: int, selected: Iterable[tuple[str, str, str]],
             index: FamilyIndex) -> dict[str, Any]:
    selected = sorted(selected, key=lambda item: (FAMILIES.index(item[0]), item[1], item[2]))
    return {"problem_id": pid, "n_supervised": length,
            "slots": [{"family": family, "structure_id": structure, "ac_class": ac_class,
                       "record": dict(index[family][structure][ac_class])}
                      for family, structure, ac_class in selected]}


def _slot_assignment(pid: str, length: int, index: FamilyIndex,
                     identity_structures: tuple[str, ...],
                     nonidentity_structures: tuple[str, ...]) -> dict[str, Any] | None:
    slots = [(family, structure) for family, structures in
             zip(FAMILIES, (identity_structures, nonidentity_structures)) for structure in structures]
    candidates = [sorted(index.get(family, {}).get(structure, {})) for family, structure in slots]
    if any(not choices for choices in candidates):
        return None
    owner: dict[str, int] = {}

    def augment(slot: int, seen: set[str]) -> bool:
        for ac_class in candidates[slot]:
            if ac_class in seen:
                continue
            seen.add(ac_class)
            if ac_class not in owner or augment(owner[ac_class], seen):
                owner[ac_class] = slot
                return True
        return False

    for slot in range(2 * K):
        if not augment(slot, set()):
            return None
    return _witness(pid, length, [(slots[slot][0], slots[slot][1], ac_class)
                                 for ac_class, slot in owner.items()], index)


def slot_assignment(inventory: Iterable[Mapping[str, Any]], SI: Sequence[str],
                    SN: Sequence[str]) -> dict[str, Any] | None:
    """Assign eight fixed slots to distinct AC classes, or return None.

    Input must be one problem at one length.  SI and SN each contain four distinct
    structures; their overlap is allowed.  Duplicate feature rows use the smallest
    canonical JSON record as representative.  Returned witnesses are deterministic.
    """
    si, sn = _structures(SI, "SI"), _structures(SN, "SN")
    single = _single_inventory(inventory)
    return None if single is None else _slot_assignment(*single, si, sn)


def family_structure_assignment(inventory: Iterable[Mapping[str, Any]]) -> dict[str, Any] | None:
    """Find any four structures per family with eight distinct AC classes.

    This is an exact integral max-flow check for one problem at one length, with
    source -> family (4) -> family/structure (1) -> AC class (1) -> sink (1).
    It does not require the two families to use the same structure tuple.
    """
    single = _single_inventory(inventory)
    if single is None:
        return None
    pid, length, index = single
    if any(len(index.get(family, {})) < K for family in FAMILIES):
        return None
    source, sink = ("source",), ("sink",)
    residual: dict[tuple[str, ...], dict[tuple[str, ...], int]] = {}

    def add_edge(left: tuple[str, ...], right: tuple[str, ...], capacity: int) -> None:
        residual.setdefault(left, {})[right] = capacity
        residual.setdefault(right, {})[left] = 0

    feature_edges = []
    all_classes = set()
    for family in FAMILIES:
        family_node = ("family", family)
        add_edge(source, family_node, K)
        for structure, classes in sorted(index[family].items()):
            structure_node = ("structure", family, structure)
            add_edge(family_node, structure_node, 1)
            for ac_class in sorted(classes):
                class_node = ("class", ac_class)
                add_edge(structure_node, class_node, 1)
                feature_edges.append((family, structure, ac_class, structure_node, class_node))
                all_classes.add(ac_class)
    for ac_class in sorted(all_classes):
        add_edge(("class", ac_class), sink, 1)
    for _ in range(2 * K):
        parents: dict[tuple[str, ...], tuple[str, ...] | None] = {source: None}
        queue = deque([source])
        while queue and sink not in parents:
            node = queue.popleft()
            for next_node, capacity in sorted(residual[node].items()):
                if capacity > 0 and next_node not in parents:
                    parents[next_node] = node
                    queue.append(next_node)
        if sink not in parents:
            return None
        node = sink
        while node != source:
            previous = parents[node]
            assert previous is not None
            residual[previous][node] -= 1
            residual[node][previous] += 1
            node = previous
    selected = [(family, structure, ac_class)
                for family, structure, ac_class, left, right in feature_edges
                if residual[left][right] == 0]
    return _witness(pid, length, selected, index)


def _has_four_problems(mask: int) -> bool:
    # Clear three lowest bits: works on Python 3.9 as well as newer bit_count runtimes.
    for _ in range(K - 1):
        mask &= mask - 1
    return bool(mask)


def _frequent_tuples(masks: Mapping[str, int], budget: _Budget,
                     family: str, counts: dict[str, int]) -> list[tuple[tuple[str, ...], int]]:
    """Enumerate every size-four tuple supported by at least four distinct pids."""
    candidates = sorted((structure, mask) for structure, mask in masks.items()
                        if _has_four_problems(mask))
    found: list[tuple[tuple[str, ...], int]] = []

    def visit(start: int, prefix: tuple[str, ...], current: int | None) -> None:
        remaining = K - len(prefix)
        for position in range(start, len(candidates) - remaining + 1):
            budget.consume("structure_nodes", f"structure_tuples:{family}")
            structure, mask = candidates[position]
            intersection = mask if current is None else current & mask
            if not _has_four_problems(intersection):
                continue
            extended = prefix + (structure,)
            if len(extended) == K:
                found.append((extended, intersection))
                counts[family] += 1
            else:
                visit(position + 1, extended, intersection)

    visit(0, (), None)
    return found


def find_supported_keys(records: Iterable[Mapping[str, Any]], *,
                        max_key_pair_checks: int = 2_000_000,
                        max_structure_nodes: int = 2_000_000,
                        max_seconds: float = 600.0,
                        clock: Callable[[], float] = time.monotonic) -> dict[str, Any]:
    """Enumerate shared structure keys supporting at least four exact problems.

    Primary mode is ``variable_per_problem``: each problem's eight selected rows
    share a length, but different problems may use different lengths.  Each
    witness uses its smallest feasible length for that key.  Conservative masks
    union each feature across lengths; only exact eight-slot assignments count
    as support.  Caps count attempted structure-prefix nodes and cross-family
    tuple pairs, including pruned attempts.  A partially checked key is discarded.

    ``complete=False`` is never evidence of infeasibility.  Even with a complete
    search, the union of supported problems is only potential coverage, not a
    proof that all of them fit jointly into disjoint four-problem blocks.
    """
    budget = _Budget(max_key_pair_checks, max_structure_nodes, max_seconds, clock)
    keys: list[dict[str, Any]] = []
    frequent_counts = {family: 0 for family in FAMILIES}
    frequent_complete = {family: False for family in FAMILIES}
    complete, stop_reason, stop_stage = True, "completed", None
    total_problems: int | None = None
    try:
        index = _index_records(records, budget)
        problem_ids = sorted(index)
        total_problems = len(problem_ids)
        masks: dict[str, dict[str, int]] = {family: {} for family in FAMILIES}
        for position, pid in enumerate(problem_ids):
            budget.check("support_masks")
            for length_index in index[pid].values():
                for family in FAMILIES:
                    for structure in length_index.get(family, {}):
                        masks[family][structure] = masks[family].get(structure, 0) | (1 << position)
        frequent = {}
        for family in FAMILIES:
            frequent[family] = _frequent_tuples(masks[family], budget, family, frequent_counts)
            frequent_complete[family] = True
        for si, identity_mask in frequent[FAMILIES[0]]:
            for sn, nonidentity_mask in frequent[FAMILIES[1]]:
                budget.consume("key_pair_checks", "key_pairs")
                candidate_mask = identity_mask & nonidentity_mask
                if not _has_four_problems(candidate_mask):
                    continue
                budget.counters["raw_key_pairs_support_at_least_four"] += 1
                witnesses = {}
                while candidate_mask:
                    budget.check("exact_support")
                    lowest_bit = candidate_mask & -candidate_mask
                    pid = problem_ids[lowest_bit.bit_length() - 1]
                    candidate_mask ^= lowest_bit
                    for length, length_index in sorted(index[pid].items()):
                        budget.check("exact_assignment")
                        budget.counters["slot_assignment_checks"] += 1
                        witness = _slot_assignment(pid, length, length_index, si, sn)
                        if witness is not None:
                            witnesses[pid] = witness
                            break
                if len(witnesses) >= K:
                    keys.append({"identity_structures": list(si), "nonidentity_structures": list(sn),
                                 "problem_ids": sorted(witnesses), "witnesses": witnesses})
                    budget.counters["exact_supported_keys"] += 1
        budget.check("completion")
    except _SearchStopped as exc:
        complete, stop_reason, stop_stage = False, exc.reason, exc.stage
    supported = sorted({pid for key in keys for pid in key["problem_ids"]})
    return {"schema_version": 1, "length_mode": "variable_per_problem",
            "complete": complete, "stop_reason": stop_reason, "stop_stage": stop_stage,
            "limits": {"max_key_pair_checks": max_key_pair_checks,
                       "max_structure_nodes": max_structure_nodes, "max_seconds": max_seconds},
            "elapsed_seconds": max(0.0, clock() - budget.start),
            "input_problem_count": total_problems,
            "counters": {**budget.counters, "frequent_tuples_by_family": frequent_counts},
            "frequent_tuple_enumeration_complete_by_family": frequent_complete,
            "keys": keys, "supported_problem_ids": supported,
            "supported_union_interpretation": (
                "complete_search_potential_not_joint_packing" if complete else
                "discovered_feasible_support_only_not_an_upper_bound")}


def greedy_blocks(keys: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Select disjoint blocks by static support-descending, then lexicographic keys.

    Within a key, available problem IDs are sorted and consumed four at a time.
    Unused remainders may participate under later keys.  This deterministic
    heuristic is not maximum packing, and can select fewer blocks than optimum.
    """
    normalized = []
    signatures = set()
    for key in keys:
        si = _structures(key["identity_structures"], "identity_structures")
        sn = _structures(key["nonidentity_structures"], "nonidentity_structures")
        if (si, sn) in signatures:
            raise ValueError("Duplicate structure key")
        signatures.add((si, sn))
        pids = list(key["problem_ids"])
        if any(not isinstance(pid, str) or not pid for pid in pids) or len(set(pids)) != len(pids):
            raise ValueError("Key problem IDs must be unique nonempty strings")
        if len(pids) < K:
            raise ValueError("Every key must support at least four problems")
        witnesses = key["witnesses"]
        if any(pid not in witnesses for pid in pids):
            raise ValueError("Every supported problem needs a witness")
        normalized.append((si, sn, sorted(pids), witnesses))
    normalized.sort(key=lambda item: (-len(item[2]), item[0], item[1]))
    used: set[str] = set()
    blocks = []
    for si, sn, pids, witnesses in normalized:
        available = [pid for pid in pids if pid not in used]
        for offset in range(0, len(available) - K + 1, K):
            selected = available[offset:offset + K]
            blocks.append({"block_index": len(blocks), "identity_structures": list(si),
                           "nonidentity_structures": list(sn), "problem_ids": selected,
                           "witnesses": {pid: witnesses[pid] for pid in selected}})
            used.update(selected)
    return {"blocks": blocks, "n_blocks": len(blocks), "n_selected_problems": len(used),
            "selected_problem_ids": sorted(used),
            "supported_problem_ids": sorted({pid for _, _, pids, _ in normalized for pid in pids}),
            "selection_method": "static_support_descending_then_lexicographic_greedy",
            "maximum_packing_claimed": False,
            "warning": "Greedy packing is a feasible lower bound; it need not maximize blocks. "
                       "The supported union is potential, not a joint packing certificate; "
                       "for a capped search it is not an upper bound on total support."}

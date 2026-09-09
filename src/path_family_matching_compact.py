"""Exact common-length join using verified Hall-component occurrence masks.

Numerical AC classes must map to one operator-only structure within a problem.
After checking that property, eight slots decompose into independent components
of one or two slots: each structure occurs at most once per family.  A shared
structure requires two distinct AC choices; its two-family union must contain
at least two classes.  This is an exact condition, not a support approximation.

All valid keys are streamed as [identity_tuple_id, absent_tuple_id, length_id].
Catalogs recover their structures, exact support and lowest common lengths.
Only each exact-support group's smallest key receives an explicit path witness.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Iterable, Mapping
import hashlib
import itertools
import json
import time
from typing import Any

from src.path_family_matching import FAMILIES, _index_records, _slot_assignment
from src.path_family_matching_complete import record_reference


def compact_key_bytes(key: list[int]) -> bytes:
    """Canonical three-integer JSON array plus one newline, encoded as ASCII."""
    if len(key) != 3 or any(type(value) is not int or value < 0 for value in key):
        raise ValueError("Compact keys contain exactly three nonnegative integers")
    return f"[{key[0]},{key[1]},{key[2]}]\n".encode("ascii")


def _four(mask: int) -> bool:
    for _ in range(3):
        mask &= mask - 1
    return bool(mask)


class _Stopped(Exception):
    def __init__(self, stage):
        self.stage = stage


class _Budget:
    def __init__(self, seconds, clock):
        if type(seconds) not in (int, float) or not 0 < seconds < float("inf"):
            raise ValueError("Positive finite deadline required")
        self.start, self.clock, self.seconds = clock(), clock, seconds
        self.counters = {"input_records_indexed": 0, "structure_combinations_checked": 0,
                         "group_pairs_checked": 0, "pruned_pairs": 0, "exact_pairs": 0,
                         "valid_key_count": 0, "occurrence_projection_cache_hits": 0,
                         "occurrence_projection_cache_misses": 0,
                         "representative_witnesses_checked": 0}

    def check(self, stage):
        if self.clock() - self.start >= self.seconds:
            raise _Stopped(stage)


def compact_supported_key_join(
        records: Iterable[Mapping[str, Any]], *, max_seconds: float = 600.0,
        on_key: Callable[[list[int]], None] | None = None,
        clock: Callable[[], float] = time.monotonic) -> dict[str, Any]:
    """Return a complete finite join or an explicit, non-resumable partial receipt.

    The supplied inventory must already have verified legality and tokenizer
    provenance.  This function validates record schema and AC-to-structure
    functionality, and retains C009's same-length/eight-distinct-class rule.
    It imports the old augmenting matcher only to construct and cross-check the
    final representative witnesses; finite-key classification uses exact masks.

    on_key must synchronously write compact_key_bytes(key) without modifying its
    argument. Callback errors propagate. Memory contains feature catalogs and
    exact support groups, never a list of every key or repeated full responses.
    Cache limits change runtime only; they cannot change support decisions.
    Deadline checks are cooperative, including output and witness finalization.
    """
    budget = _Budget(max_seconds, clock)
    counts = budget.counters
    catalog = {"problem_ids": [], "structure_ids": [], "identity_tuples": [],
               "nonidentity_tuples": [], "length_signatures": []}
    group_states = {}
    tuple_counts = {family: 0 for family in FAMILIES}
    mask_group_counts = {family: 0 for family in FAMILIES}
    tuple_complete = {family: False for family in FAMILIES}
    total_pairs = None
    grid_complete = representatives_complete = functionality_verified = False
    complete, stop_stage = False, None
    cursor = {"stage": "indexing"}
    key_digest = hashlib.sha256()
    try:
        index = _index_records(records, budget)
        pids = catalog["problem_ids"] = sorted(index)
        pid_ids = {pid: i for i, pid in enumerate(pids)}
        structures = catalog["structure_ids"] = sorted({s for lengths in index.values()
                                                        for families in lengths.values()
                                                        for options in families.values() for s in options})
        structure_ids = {s: i for i, s in enumerate(structures)}
        occurrences = sorted((pid, length) for pid in pids for length in index[pid])
        occurrence_ids = {item: i for i, item in enumerate(occurrences)}
        all_occurrences = (1 << len(occurrences)) - 1
        class_ids, ac_structure = {}, {}
        pid_masks, occurrence_masks, class_masks = defaultdict(int), defaultdict(int), defaultdict(int)
        refs = {}
        for pid in pids:
            for length, families in sorted(index[pid].items()):
                oi = occurrence_ids[(pid, length)]
                for family in FAMILIES:
                    for structure, classes in sorted(families.get(family, {}).items()):
                        budget.check("feature_masks")
                        sid = structure_ids[structure]
                        pid_masks[(family, sid)] |= 1 << pid_ids[pid]
                        occurrence_masks[(family, sid)] |= 1 << oi
                        for ac, row in sorted(classes.items()):
                            coordinate = (pid, ac)
                            if coordinate in ac_structure and ac_structure[coordinate] != sid:
                                raise ValueError("Numerical AC class maps to multiple structures; exact-mask precondition failed")
                            ac_structure[coordinate] = sid
                            if coordinate not in class_ids:
                                class_ids[coordinate] = len(class_ids)
                            class_masks[(oi, family, sid)] |= 1 << class_ids[coordinate]
                            refs[(pid, length, family, structure, ac)] = record_reference(row)
        functionality_verified = True
        compatible = {}
        for sid in range(len(structures)):
            budget.check("shared_structure_compatibility")
            mask = 0
            for oi in range(len(occurrences)):
                a, b = class_masks[(oi, FAMILIES[0], sid)], class_masks[(oi, FAMILIES[1], sid)]
                union = a | b
                if a and b and union & (union - 1):
                    mask |= 1 << oi
            compatible[sid] = mask
        tuple_entries, mask_groups = {}, {}
        for family, table_name in zip(FAMILIES, ("identity_tuples", "nonidentity_tuples")):
            cursor = {"stage": "tuple_enumeration", "family": family}
            domain = sorted(sid for f, sid in pid_masks if f == family and _four(pid_masks[(family, sid)]))
            entries, grouped = [], defaultdict(list)
            for item in itertools.combinations(domain, 4):
                budget.check("tuple_enumeration")
                counts["structure_combinations_checked"] += 1
                pm, om = pid_masks[(family, item[0])], occurrence_masks[(family, item[0])]
                for sid in item[1:]:
                    pm &= pid_masks[(family, sid)]
                    om &= occurrence_masks[(family, sid)]
                if _four(pm):
                    ti = len(entries)
                    entries.append((item, om, sum(1 << sid for sid in item)))
                    grouped[pm].append(ti)
                    catalog[table_name].append(list(item))
            tuple_entries[family] = entries
            mask_groups[family] = sorted(grouped.items())
            tuple_counts[family], mask_group_counts[family] = len(entries), len(grouped)
            tuple_complete[family] = True
        total_pairs = tuple_counts[FAMILIES[0]] * tuple_counts[FAMILIES[1]]
        overlap_cache = {0: all_occurrences}
        projection_cache = {}
        signature_ids = {}
        cache_limit = 65536

        def project(mask):
            if mask in projection_cache:
                counts["occurrence_projection_cache_hits"] += 1
                return projection_cache[mask]
            counts["occurrence_projection_cache_misses"] += 1
            pairs = []
            previous_pid = None
            remaining = mask
            while remaining:
                low = remaining & -remaining
                pid, length = occurrences[low.bit_length() - 1]
                remaining ^= low
                if pid != previous_pid:
                    pairs.append((pid_ids[pid], length))
                    previous_pid = pid
            if len(pairs) < 4:
                signature = -1
            else:
                key = tuple(pairs)
                if key not in signature_ids:
                    signature_ids[key] = len(catalog["length_signatures"])
                    catalog["length_signatures"].append([list(pair) for pair in pairs])
                signature = signature_ids[key]
            if len(projection_cache) < cache_limit:
                projection_cache[mask] = signature
            return signature

        left_entries, right_entries = tuple_entries[FAMILIES[0]], tuple_entries[FAMILIES[1]]
        for gi, (mask_i, tuples_i) in enumerate(mask_groups[FAMILIES[0]]):
            for gn, (mask_n, tuples_n) in enumerate(mask_groups[FAMILIES[1]]):
                cursor = {"stage": "group_pair", "identity_group": gi, "nonidentity_group": gn}
                budget.check("group_pair")
                counts["group_pairs_checked"] += 1
                if not _four(mask_i & mask_n):
                    counts["pruned_pairs"] += len(tuples_i) * len(tuples_n)
                    continue
                for ti in tuples_i:
                    _, oi, si_mask = left_entries[ti]
                    for tn in tuples_n:
                        cursor = {"stage": "exact_pair", "identity_tuple_id": ti, "nonidentity_tuple_id": tn}
                        budget.check("exact_pair")
                        _, on, sn_mask = right_entries[tn]
                        feasible = oi & on
                        if feasible:
                            overlap = si_mask & sn_mask
                            if overlap not in overlap_cache:
                                compatible_mask, remaining = all_occurrences, overlap
                                while remaining:
                                    low = remaining & -remaining
                                    compatible_mask &= compatible[low.bit_length() - 1]
                                    remaining ^= low
                                if len(overlap_cache) < cache_limit:
                                    overlap_cache[overlap] = compatible_mask
                            else:
                                compatible_mask = overlap_cache[overlap]
                            feasible &= compatible_mask
                        length_id = project(feasible) if feasible else -1
                        if length_id >= 0:
                            compact_key = [ti, tn, length_id]
                            encoded = compact_key_bytes(compact_key)
                            budget.check("key_output")
                            if on_key is not None:
                                on_key(compact_key)
                            key_digest.update(encoded)
                            counts["valid_key_count"] += 1
                            support = tuple(pair[0] for pair in catalog["length_signatures"][length_id])
                            if support not in group_states:
                                group_states[support] = {"valid_key_count": 1, "minimum": (ti, tn),
                                                         "length_id": length_id, "representative_key": None}
                            else:
                                state = group_states[support]
                                state["valid_key_count"] += 1
                                if (ti, tn) < state["minimum"]:
                                    state["minimum"], state["length_id"] = (ti, tn), length_id
                        counts["exact_pairs"] += 1
        if counts["pruned_pairs"] + counts["exact_pairs"] != total_pairs:
            raise ValueError("Internal finite-grid accounting mismatch")
        grid_complete = True
        # Explicit witness generation is limited to final group representatives.
        for support, state in sorted(group_states.items()):
            ti, tn = state["minimum"]
            si = tuple(structures[sid] for sid in catalog["identity_tuples"][ti])
            sn = tuple(structures[sid] for sid in catalog["nonidentity_tuples"][tn])
            witnesses = {}
            for pi, length in catalog["length_signatures"][state["length_id"]]:
                pid = pids[pi]
                cursor = {"stage": "representative_witness", "identity_tuple_id": ti,
                          "nonidentity_tuple_id": tn, "problem_id": pid}
                budget.check("representative_witness")
                witness = _slot_assignment(pid, length, index[pid][length], si, sn)
                if witness is None:
                    raise ValueError("Exact-mask support contradicts independent augmenting witness")
                witnesses[pid] = {"problem_id": pid, "n_supervised": length,
                                  "slots": [{"family": slot["family"], "structure_id": slot["structure_id"],
                                             "ac_class": slot["ac_class"],
                                             "record_ref": refs[(pid, length, slot["family"], slot["structure_id"], slot["ac_class"])]}
                                            for slot in witness["slots"]]}
                counts["representative_witnesses_checked"] += 1
            state["representative_key"] = {"identity_structures": list(si), "nonidentity_structures": list(sn),
                                            "problem_ids": [pids[pi] for pi in support], "witnesses": witnesses}
        representatives_complete = True
        budget.check("completion")
        complete, cursor = True, {"stage": "completed"}
    except _Stopped as exc:
        stop_stage = exc.stage
        cursor["stage"] = exc.stage
    represented = counts["pruned_pairs"] + counts["exact_pairs"]
    if total_pairs is not None and represented > total_pairs:
        raise ValueError("Represented pair count exceeds finite grid")
    support_groups = [{"problem_ids": [catalog["problem_ids"][pi] for pi in support],
                       "valid_key_count": state["valid_key_count"],
                       "representative_tuple_ids": list(state["minimum"]),
                       "representative_length_signature_id": state["length_id"],
                       "representative_key": state["representative_key"]}
                      for support, state in sorted(group_states.items())]
    if sum(group["valid_key_count"] for group in support_groups) != counts["valid_key_count"]:
        raise ValueError("Valid-key/support-group accounting mismatch")
    return {"schema_version": 1, "algorithm": "verified_Hall_occurrence_bitset_join",
            "length_mode": "common", "across_problem_lengths": "variable_per_problem",
            "complete": complete, "grid_complete": grid_complete,
            "representatives_complete": representatives_complete,
            "stop_reason": "completed" if complete else "deadline", "stop_stage": stop_stage,
            "cursor": cursor, "cursor_is_standalone_resume_checkpoint": False,
            "max_seconds": max_seconds, "elapsed_seconds": max(0.0, clock() - budget.start),
            "ac_to_structure_functionality_verified": functionality_verified,
            "frequent_tuples_by_family": tuple_counts, "mask_groups_by_family": mask_group_counts,
            "tuple_enumeration_complete_by_family": tuple_complete,
            "total_candidate_pairs": total_pairs, "represented_pairs": represented,
            "pruned_pairs": counts["pruned_pairs"], "exact_pairs": counts["exact_pairs"],
            "unrepresented_pairs": None if total_pairs is None else total_pairs - represented,
            "valid_key_count": counts["valid_key_count"], "key_stream_sha256": key_digest.hexdigest(),
            "compact_key_fields": ["identity_tuple_id", "nonidentity_tuple_id", "length_signature_id"],
            "compact_key_encoding": "three nonnegative integers in an ASCII JSON array plus newline",
            "length_signature_encoding": "sorted [problem_id_catalog_index, lowest_common_supervised_length] pairs",
            "catalog": catalog, "support_group_count": len(support_groups), "support_groups": support_groups,
            "supported_problem_ids": sorted({pid for group in support_groups for pid in group["problem_ids"]}),
            "supported_union_interpretation": ("complete_search_potential_not_joint_packing" if complete else
                                                "discovered_feasible_support_only_not_an_upper_bound"),
            "counters": counts}

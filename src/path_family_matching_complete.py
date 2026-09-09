"""Complete finite support-mask join with explicitly separated length designs.

This module does not change C009 or read data files.  It accepts verified feature
records and streams compact valid keys.  Only one representative per exact
problem-support set remains in memory; matching is still performed separately
for every surviving structure pair.  Equal conservative masks do not imply
equal AC-class feasibility.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
import hashlib
import json
import time
from typing import Any

from src.path_family_matching import (FAMILIES, K, _frequent_tuples,
                                      _has_four_problems, _index_records,
                                      _slot_assignment, _validated_record)


def canonical_json_line(record: Mapping[str, Any]) -> bytes:
    """The exact UTF-8/ASCII-escaped bytes hashed for each streamed key."""
    return (json.dumps(record, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=True, allow_nan=False) + "\n").encode("utf-8")


def record_reference(record: Mapping[str, Any]) -> str:
    """SHA-256 of the validated record's canonical JSON, without a final newline."""
    _, encoded = _validated_record(record)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


class _Deadline(Exception):
    def __init__(self, stage: str):
        self.stage = stage


class _TimeBudget:
    """Duck-typed budget for C009's index and frequent-tuple helpers."""

    def __init__(self, max_seconds: float, clock: Callable[[], float]):
        if (isinstance(max_seconds, bool) or not isinstance(max_seconds, (int, float))
                or not 0 < max_seconds < float("inf")):
            raise ValueError("max_seconds must be finite and positive")
        self.clock, self.max_seconds = clock, max_seconds
        self.start = clock()
        self.counters = {"input_records_indexed": 0, "structure_nodes": 0,
                         "group_pair_checks": 0, "pruned_group_pairs": 0,
                         "pruned_pairs": 0, "exact_pairs": 0,
                         "started_exact_pairs": 0, "slot_assignment_checks": 0,
                         "valid_key_count": 0}

    def check(self, stage: str) -> None:
        if self.clock() - self.start >= self.max_seconds:
            raise _Deadline(stage)

    def consume(self, counter: str, stage: str) -> None:
        self.check(stage)
        self.counters[counter] += 1


def complete_supported_key_join(
        records: Iterable[Mapping[str, Any]], *, max_seconds: float = 600.0,
        length_mode: str = "common",
        on_key: Callable[[dict[str, Any]], None] | None = None,
        clock: Callable[[], float] = time.monotonic) -> dict[str, Any]:
    """Exhaust the finite tuple-pair join, or explicitly report a deadline stop.

    Records use the C009 schema.  In "common" mode each problem's eight rows
    share a length, preserving C009; different problems may use different
    lengths.  In the separately declared "per_family" mode, each family's four
    rows share a length but the two family lengths may differ.  The lowest
    feasible common length or lexicographic (present, absent) length pair and
    the same deterministic C009 class assignment are retained.  No old
    key-pair or structure-node cap applies: the only work limit is max_seconds.

    Groups are sorted by integer conservative support mask; each group's tuples
    are lexicographic.  A group intersection with fewer than four distinct pids
    accounts for its entire tuple-pair product in pruned_pairs.  Every other
    tuple pair receives exact same-length eight-class checks.  exact_pairs counts
    completed decisions, including invalid keys; an interrupted pair is excluded.
    Complete accounting requires pruned_pairs + exact_pairs == total_pairs.

    on_key is called synchronously once per valid compact key, in join order.
    It must not mutate its argument; I/O errors propagate so a partial archive
    cannot silently become a successful result.  A caller may write
    canonical_json_line(key) directly into a new private JSONL or gzip stream.
    key_stream_sha256 hashes precisely those concatenated lines even if no
    callback is supplied.  Every slot refers to an original representative via
    record_reference(record), rather than duplicating full records/responses.

    The return value stores only support-set counts and each set's lexicographically
    smallest key/witness.  The cursor is an audit position, not a self-contained
    resume checkpoint: resumption also requires the preceding stream and state.
    A deadline is cooperative, checked before each assignment and output commit;
    one assignment or caller callback cannot be preempted by pure Python.
    """
    if length_mode not in ("common", "per_family"):
        raise ValueError("length_mode must be common or per_family")
    budget = _TimeBudget(max_seconds, clock)
    counts = budget.counters
    frequent_counts = {family: 0 for family in FAMILIES}
    frequent_complete = {family: False for family in FAMILIES}
    mask_group_counts = {family: 0 for family in FAMILIES}
    support_groups: dict[tuple[str, ...], dict[str, Any]] = {}
    key_digest = hashlib.sha256()
    total_pairs: int | None = None
    input_problem_count: int | None = None
    cursor: dict[str, Any] = {"stage": "indexing"}
    complete, stop_reason, stop_stage = False, "deadline", None
    try:
        index = _index_records(records, budget)
        problem_ids = sorted(index)
        input_problem_count = len(problem_ids)
        cursor = {"stage": "support_masks"}
        masks: dict[str, dict[str, int]] = {family: {} for family in FAMILIES}
        refs = {}
        length_options = {}
        for position, pid in enumerate(problem_ids):
            budget.check("support_masks")
            for length, length_index in sorted(index[pid].items()):
                for family in FAMILIES:
                    for structure, classes in sorted(length_index.get(family, {}).items()):
                        masks[family][structure] = masks[family].get(structure, 0) | (1 << position)
                        for ac_class, record in sorted(classes.items()):
                            budget.check("record_references")
                            refs[(pid, length, family, structure, ac_class)] = record_reference(record)
            if length_mode == "common":
                length_options[pid] = [({family: length for family in FAMILIES}, length_index)
                                       for length, length_index in sorted(index[pid].items())]
            else:
                options = []
                for li, left in sorted(index[pid].items()):
                    if not left.get(FAMILIES[0]):
                        continue
                    for ln, right in sorted(index[pid].items()):
                        budget.check("family_length_options")
                        if right.get(FAMILIES[1]):
                            options.append(({FAMILIES[0]: li, FAMILIES[1]: ln},
                                            {FAMILIES[0]: left[FAMILIES[0]],
                                             FAMILIES[1]: right[FAMILIES[1]]}))
                length_options[pid] = options
        groups = {}
        for family in FAMILIES:
            cursor = {"stage": "structure_tuples", "family": family}
            frequent = _frequent_tuples(masks[family], budget, family, frequent_counts)
            frequent_complete[family] = True
            grouped: dict[int, list[tuple[str, ...]]] = {}
            for structures, mask in frequent:
                budget.check("mask_grouping")
                grouped.setdefault(mask, []).append(structures)
            groups[family] = sorted((mask, sorted(tuples)) for mask, tuples in grouped.items())
            mask_group_counts[family] = len(grouped)
        total_pairs = frequent_counts[FAMILIES[0]] * frequent_counts[FAMILIES[1]]
        for gi, (identity_mask, identity_tuples) in enumerate(groups[FAMILIES[0]]):
            for gn, (nonidentity_mask, nonidentity_tuples) in enumerate(groups[FAMILIES[1]]):
                cursor = {"stage": "group_pair", "identity_group": gi, "nonidentity_group": gn}
                budget.consume("group_pair_checks", "group_pair")
                candidate_mask = identity_mask & nonidentity_mask
                if not _has_four_problems(candidate_mask):
                    counts["pruned_pairs"] += len(identity_tuples) * len(nonidentity_tuples)
                    counts["pruned_group_pairs"] += 1
                    continue
                candidate_problems = []
                remaining = candidate_mask
                while remaining:
                    lowest_bit = remaining & -remaining
                    candidate_problems.append(problem_ids[lowest_bit.bit_length() - 1])
                    remaining ^= lowest_bit
                for ti, si in enumerate(identity_tuples):
                    for tn, sn in enumerate(nonidentity_tuples):
                        cursor = {"stage": "exact_pair", "identity_group": gi,
                                  "nonidentity_group": gn, "identity_tuple": ti,
                                  "nonidentity_tuple": tn}
                        budget.consume("started_exact_pairs", "exact_pair")
                        witnesses = {}
                        for pid in candidate_problems:
                            for family_lengths, length_index in length_options[pid]:
                                cursor["problem_id"], cursor["family_lengths"] = pid, family_lengths
                                budget.check("exact_assignment")
                                counts["slot_assignment_checks"] += 1
                                # The helper's scalar length only populates a temporary
                                # header.  All candidate graph edges retain their own
                                # records; the compact public witness below uses actual
                                # family lengths and never exports a false common length.
                                witness = _slot_assignment(pid, family_lengths[FAMILIES[0]], length_index, si, sn)
                                if witness is not None:
                                    witnesses[pid] = {
                                        "problem_id": pid,
                                        "slots": [{"family": slot["family"],
                                                   "structure_id": slot["structure_id"],
                                                   "ac_class": slot["ac_class"],
                                                   "record_ref": refs[(pid, family_lengths[slot["family"]], slot["family"],
                                                                       slot["structure_id"], slot["ac_class"])]}
                                                  for slot in witness["slots"]]}
                                    if length_mode == "common":
                                        witnesses[pid]["n_supervised"] = family_lengths[FAMILIES[0]]
                                    else:
                                        witnesses[pid]["family_lengths"] = dict(family_lengths)
                                    break
                        budget.check("pair_commit")
                        if len(witnesses) >= K:
                            pids = tuple(sorted(witnesses))
                            key = {"identity_structures": list(si), "nonidentity_structures": list(sn),
                                   "problem_ids": list(pids), "witnesses": witnesses}
                            encoded = canonical_json_line(key)
                            budget.check("key_output")
                            if on_key is not None:
                                on_key(key)
                            key_digest.update(encoded)
                            counts["valid_key_count"] += 1
                            if pids not in support_groups:
                                support_groups[pids] = {"problem_ids": list(pids), "valid_key_count": 1,
                                                        "representative_key": key}
                            else:
                                group = support_groups[pids]
                                group["valid_key_count"] += 1
                                previous = group["representative_key"]
                                if (si, sn) < (tuple(previous["identity_structures"]),
                                               tuple(previous["nonidentity_structures"])):
                                    group["representative_key"] = key
                        counts["exact_pairs"] += 1
        cursor = {"stage": "complete"}
        budget.check("completion")
        assert counts["pruned_pairs"] + counts["exact_pairs"] == total_pairs
        complete, stop_reason = True, "completed"
    except _Deadline as exc:
        stop_stage = exc.stage
        cursor["stage"] = exc.stage
    represented = counts["pruned_pairs"] + counts["exact_pairs"]
    assert total_pairs is None or represented <= total_pairs
    assert sum(group["valid_key_count"] for group in support_groups.values()) == counts["valid_key_count"]
    supported = sorted({pid for pids in support_groups for pid in pids})
    return {
        "schema_version": 1, "algorithm": "finite_support_mask_group_join",
        "length_mode": length_mode, "across_problem_lengths": "variable_per_problem",
        "complete": complete,
        "stop_reason": stop_reason, "stop_stage": stop_stage, "cursor": cursor,
        "cursor_is_standalone_resume_checkpoint": False,
        "max_seconds": max_seconds, "elapsed_seconds": max(0.0, clock() - budget.start),
        "input_problem_count": input_problem_count,
        "frequent_tuple_enumeration_complete_by_family": frequent_complete,
        "frequent_tuples_by_family": frequent_counts, "mask_groups_by_family": mask_group_counts,
        "total_candidate_pairs": total_pairs, "represented_pairs": represented,
        "pruned_pairs": counts["pruned_pairs"], "exact_pairs": counts["exact_pairs"],
        "unrepresented_pairs": None if total_pairs is None else total_pairs - represented,
        "counters": counts, "valid_key_count": counts["valid_key_count"],
        "key_stream_sha256": key_digest.hexdigest(),
        "key_stream_format": "UTF-8 canonical sorted-key ASCII-escaped JSON plus newline per valid key",
        "record_ref_format": "SHA-256 of canonical validated record JSON without newline",
        "support_group_count": len(support_groups),
        "support_groups": [support_groups[pids] for pids in sorted(support_groups)],
        "supported_problem_ids": supported,
        "supported_union_interpretation": (
            "complete_search_potential_not_joint_packing" if complete else
            "discovered_feasible_support_only_not_an_upper_bound"),
        "support_group_representative_rule": "lexicographically_smallest_structure_tuple_pair",
    }

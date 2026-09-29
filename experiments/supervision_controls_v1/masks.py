"""Deterministic mask controls; no model, tokenizer, or evaluation data access.

The matched control samples within per-answer position x frozen-base-NLL cells.
Original QDW positions remain eligible: excluding them changes the conditional
null and can make small cells infeasible. We report overlap and forced overlap.
"""
from __future__ import annotations

from bisect import bisect_left
from collections import defaultdict
import hashlib
import json
import math
import random

MASK_SEED = 2026092901
POSITION_BINS = 4
DIFFICULTY_BINS = 4
CONDITIONS = ("random", "position_difficulty")


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    allow_nan=False).encode()).hexdigest()


def validate_annotation(annotation):
    a = annotation
    length = a["L"]
    if type(length) is not int or length <= 0:
        raise ValueError("Positive response length required")
    if len(a["mask"]) != length or any(type(x) is not bool for x in a["mask"]):
        raise ValueError("Invalid original boolean mask")
    if len(a["full_logp"]) != length or any(
            isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) or x > 0
            for x in a["full_logp"]):
        raise ValueError("Invalid frozen-base log probabilities")
    eligible = a["eligible_indices"]
    if (eligible != sorted(set(eligible)) or
            any(type(i) is not int or not 0 <= i < length for i in eligible)):
        raise ValueError("Eligible positions must be unique, sorted, and in range")
    selected = [i for i, value in enumerate(a["mask"]) if value]
    if (type(a["K"]) is not int or a["K"] != len(selected) or
            a["selected_indices"] != selected or not set(selected).issubset(eligible)):
        raise ValueError("Original selected positions/count do not agree")
    return eligible, selected


def strata(annotation):
    eligible, _ = validate_annotation(annotation)
    difficulty = sorted(-annotation["full_logp"][i] for i in eligible)
    # Quantile cut values do not split equal-NLL ties by token index.
    cuts = [difficulty[math.ceil(j * len(difficulty) / DIFFICULTY_BINS) - 1]
            for j in range(1, DIFFICULTY_BINS)] if difficulty else []
    cells = {}
    for i in eligible:
        position = min(POSITION_BINS - 1, POSITION_BINS * i // annotation["L"])
        nll_bin = bisect_left(cuts, -annotation["full_logp"][i])
        cells[i] = (position, nll_bin)
    return cells, cuts


def make_control(problem_id, annotation, condition, seed=MASK_SEED):
    if not isinstance(problem_id, str) or not problem_id or type(seed) is not int:
        raise ValueError("Stable problem ID and integer mask seed required")
    if condition not in CONDITIONS:
        raise ValueError("Unknown control condition")
    eligible, original = validate_annotation(annotation)
    cells, cuts = strata(annotation)
    rng = random.Random(int(digest(["mask-control-v1", seed, problem_id, condition]), 16))
    original_set = set(original)
    forced_overlap = 0
    cell_audit = []
    if condition == "random":
        selected = sorted(rng.sample(eligible, len(original)))
        forced_overlap = max(0, 2 * len(original) - len(eligible))
    else:
        populations = defaultdict(list)
        for i in eligible:
            populations[cells[i]].append(i)
        selected = []
        for cell, population in sorted(populations.items()):
            count = sum(i in original_set for i in population)
            selected.extend(rng.sample(population, count))
            lower_overlap = max(0, 2 * count - len(population))
            forced_overlap += lower_overlap
            cell_audit.append(dict(position_bin=cell[0], difficulty_bin=cell[1],
                                   eligible=len(population), selected=count,
                                   forced_overlap_lower_bound=lower_overlap))
        selected.sort()
    selected_set = set(selected)
    mask = [i in selected_set for i in range(annotation["L"])]
    if len(selected) != annotation["K"] or not set(selected).issubset(eligible):
        raise AssertionError("Control changed the frozen eligible region or count")
    overlap = len(set(selected) & original_set)
    def mean(indices, feature):
        return sum(feature(i) for i in indices) / len(indices) if indices else None
    return dict(schema="supervision_mask_control_v1", id=problem_id, condition=condition,
                seed=seed, L=annotation["L"], K=annotation["K"], mask=mask,
                selected_indices=selected, original_selected_indices=original,
                source_annotation_sha256=digest(annotation), mask_sha256=digest(mask),
                overlap_with_qdw=overlap, forced_overlap_lower_bound=forced_overlap,
                changed_mask=mask != annotation["mask"], cells=cell_audit,
                difficulty_cut_values=cuts, position_bins=POSITION_BINS,
                difficulty_bins=DIFFICULTY_BINS,
                original_mean_nll=mean(original, lambda i: -annotation["full_logp"][i]),
                control_mean_nll=mean(selected, lambda i: -annotation["full_logp"][i]),
                original_mean_relative_position=mean(original, lambda i: i / annotation["L"]),
                control_mean_relative_position=mean(selected, lambda i: i / annotation["L"]))

"""Descriptive selection and numerical-exposure audit for fixed CPU stages.

This module neither selects training examples nor performs arithmetic solution
search. Its pure helpers accept explicit problem IDs and already verified C009
records. No implicit file, model, development or holdout access occurs.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from collections.abc import Mapping
from datetime import datetime, timezone
from fractions import Fraction
import hashlib
import itertools
import json
import math
from pathlib import Path


FAMILIES = ("identity_present", "identity_absent")
FEATURES = ("identity_nodes", "zero_nodes", "one_nodes", "negative_nodes",
            "fraction_nodes", "depth", "max_abs_intermediate")
STRATA = ("target_ge_41", "input_one", "consecutive_pair", "target_is_input",
          "target_is_input_plus_one", "preview_template")
UNITS = ("ordered_inventory_rows", "scheduled_presentations")
DEFINITIONS = {
    "target_ge_41": "The fixed integer target is at least 41.",
    "input_one": "At least one of the four supplied inputs equals 1.",
    "consecutive_pair": "Two different input positions have values differing by exactly 1.",
    "target_is_input": "The target equals at least one supplied input.",
    "target_is_input_plus_one": "The target equals one plus at least one supplied input.",
    "preview_template": "The four distinct supplied numbers can be assigned to four different roles: literal 1, a, a+1, b; the fixed target equals b+1. No input position or value can occupy two roles. This input/target pattern does not certify any semantic strategy.",
    "numbers": "Pooled supplied input values; every problem contributes exactly four values.",
    "retention": "A stage is a subset of its immediately preceding stage. True and false strata are fixed from original problem inputs; zero-denominator retention is null.",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _statistics(values) -> dict:
    values = [Fraction(value) for value in values]
    if not values:
        return {"count": 0, "min": None, "max": None, "mean": None, "mean_exact": None}
    mean = sum(values) / len(values)
    scalar = lambda value: int(value) if value.denominator == 1 else float(value)
    return {"count": len(values), "min": scalar(min(values)), "max": scalar(max(values)),
            "mean": float(mean), "mean_exact": str(mean)}


def _fraction(numerator: int, denominator: int) -> dict:
    require(0 <= numerator <= denominator, "Invalid retention numerator/denominator")
    return {"numerator": numerator, "denominator": denominator,
            "ratio": numerator / denominator if denominator else None}


def problem_characteristics(problem: Mapping) -> dict:
    numbers, target = problem["numbers"], problem["target"]
    require(isinstance(numbers, (list, tuple)) and len(numbers) == 4
            and all(type(value) is int and value > 0 for value in numbers)
            and len(set(numbers)) == 4, "Expected four distinct positive integer inputs")
    require(type(target) is int, "Integer target required")
    pairs = [(i, j) for i, j in itertools.combinations(range(4), 2)
             if abs(numbers[i] - numbers[j]) == 1]
    witnesses = []
    for one in range(4):
        if numbers[one] != 1:
            continue
        remaining = [index for index in range(4) if index != one]
        for first, second in itertools.combinations(remaining, 2):
            if abs(numbers[first] - numbers[second]) != 1:
                continue
            lower, upper = sorted((first, second), key=lambda index: numbers[index])
            base = next(index for index in remaining if index not in (first, second))
            if target == numbers[base] + 1:
                witnesses.append({"one_index": one, "pair_lower_index": lower,
                                  "pair_upper_index": upper, "remaining_index": base,
                                  "role_values": [1, numbers[lower], numbers[upper], numbers[base]]})
    return {"target_ge_41": target >= 41, "input_one": 1 in numbers,
            "consecutive_pair": bool(pairs), "target_is_input": target in numbers,
            "target_is_input_plus_one": any(target == number + 1 for number in numbers),
            "preview_template": bool(witnesses), "preview_template_witnesses": witnesses}


def _describe(ids, problems, labels) -> dict:
    selected = [problems[pid] for pid in ids]
    return {"count": len(ids), "problem_ids": sorted(ids),
            "counts": {flag: sum(labels[pid][flag] for pid in ids) for flag in STRATA},
            "numbers": _statistics(number for problem in selected for number in problem["numbers"]),
            "per_problem_input_min": _statistics(min(problem["numbers"]) for problem in selected),
            "per_problem_input_max": _statistics(max(problem["numbers"]) for problem in selected),
            "targets": _statistics(problem["target"] for problem in selected),
            "target_histogram": dict(sorted(Counter(str(problem["target"]) for problem in selected).items()))}


def _retention(selected: set, baseline: set, labels: dict) -> dict:
    require(selected <= baseline, "Selection is not nested in the retention baseline")
    strata = {}
    for flag in STRATA:
        strata[flag] = {}
        for value in (True, False):
            denominator = sum(labels[pid][flag] == value for pid in baseline)
            numerator = sum(labels[pid][flag] == value for pid in selected)
            strata[flag][str(value).lower()] = _fraction(numerator, denominator)
    return {"overall": _fraction(len(selected), len(baseline)), "strata": strata}


def characterize(problems: Mapping[str, Mapping], stage_ids: Mapping[str, list[str]]) -> dict:
    """Describe a nested stage sequence without changing its fixed problem pool.

    ``stage_ids`` insertion order defines the previous-stage denominator. Compare
    nonnested policy alternatives with separate calls, not a fabricated funnel.
    Empty stages are valid; unknown, duplicated, or reintroduced IDs are errors.
    """
    require(isinstance(problems, Mapping) and isinstance(stage_ids, Mapping), "Mappings required")
    require(all(isinstance(pid, str) and pid for pid in problems), "Nonempty string problem IDs required")
    labels = {pid: problem_characteristics(problem) for pid, problem in problems.items()}
    original, previous, previous_name = set(problems), set(problems), "original"
    stages = {}
    for name, ids in stage_ids.items():
        require(isinstance(name, str) and bool(name), "Nonempty stage name required")
        require(not isinstance(ids, (str, bytes, Mapping)), "Stage IDs must be an explicit sequence")
        ids = list(ids)
        require(all(isinstance(pid, str) for pid in ids), "String stage IDs required")
        require(len(ids) == len(set(ids)), "Duplicate stage problem ID")
        selected = set(ids)
        require(selected <= original, "Unknown stage problem ID")
        require(selected <= previous, "Stage sequence is not nested")
        stages[name] = {**_describe(selected, problems, labels),
                        "retention_from_original": _retention(selected, original, labels),
                        "previous_stage": previous_name,
                        "retention_from_previous": _retention(selected, previous, labels)}
        previous, previous_name = selected, name
    return {"schema_version": 1, "definitions": DEFINITIONS,
            "original": _describe(original, problems, labels), "stage_order": list(stage_ids),
            "stages": stages, "problem_flags": labels,
            "interpretation": "Descriptive selection within the supplied fixed pool. Input/target patterns are not causal mechanisms, strategies, difficulty scores, or proof of representativeness."}


def _record_features(row: Mapping) -> dict[str, Fraction]:
    require(isinstance(row.get("problem_id"), str) and row["problem_id"], "Record problem ID required")
    require(row.get("family") in FAMILIES, "Unknown numerical family")
    require(isinstance(row.get("ac_class"), str) and row["ac_class"], "Record AC class required")
    require(isinstance(row.get("expression"), str) and row["expression"], "Ordered expression required")
    features = row["numeric_features"]
    for name in FEATURES:
        value = features[name]
        require(type(value) in (int, float) and math.isfinite(value) and value >= 0,
                "Numerical features must be finite, nonnegative scalars")
        if name != "max_abs_intermediate":
            require(type(value) is int, "Count/depth feature must be an integer")
    values = features["exact_nonroot_intermediates"]
    require(isinstance(values, list) and len(values) == 2 and all(isinstance(value, str) for value in values),
            "Two exact nonroot values required")
    try:
        values = [Fraction(value) for value in values]
    except (ValueError, ZeroDivisionError) as exc:
        raise ValueError("Invalid exact nonroot fraction") from exc
    expected = {"zero_nodes": sum(value == 0 for value in values),
                "one_nodes": sum(value == 1 for value in values),
                "negative_nodes": sum(value < 0 for value in values),
                "fraction_nodes": sum(value.denominator != 1 for value in values),
                "max_abs_intermediate": float(max(map(abs, values)))}
    require(all(features[key] == value for key, value in expected.items()), "Numeric feature/exact-value mismatch")
    operators = features["operators"]
    require(isinstance(operators, Mapping) and set(operators) <= {"+", "-", "*", "/"}
            and all(type(value) is int and value >= 0 for value in operators.values())
            and sum(operators.values()) == 3, "Four-input expression needs three binary operators")
    require(features["depth"] in (2, 3) and features["identity_nodes"] <= 3,
            "Numerical feature outside four-input grammar")
    require((features["identity_nodes"] > 0) == (row["family"] == FAMILIES[0]),
            "Identity count disagrees with numerical family")
    result = {name: Fraction(features[name]) for name in FEATURES if name != "max_abs_intermediate"}
    result["max_abs_intermediate"] = max(map(abs, values))
    return result


def _numeric_summary(rows: list[Mapping]) -> dict:
    features = [_record_features(row) for row in rows]
    sums = {name: sum((values[name] for values in features), Fraction()) for name in FEATURES}
    means = {name: value / len(rows) if rows else None for name, value in sums.items()}
    operators = Counter()
    for row in rows:
        operators.update(row["numeric_features"]["operators"])
    return {"rows": len(rows), "problem_ids": sorted({row["problem_id"] for row in rows}),
            "problem_ac_classes": len({(row["problem_id"], row["ac_class"]) for row in rows}),
            "ordered_expressions": len({(row["problem_id"], row["expression"]) for row in rows}),
            "sum_numeric_features": {name: float(value) for name, value in sums.items()},
            "sum_numeric_features_exact": {name: str(value) for name, value in sums.items()},
            "mean_numeric_features": {name: float(value) if value is not None else None for name, value in means.items()},
            "mean_numeric_features_exact": {name: str(value) if value is not None else None for name, value in means.items()},
            "operator_histogram": dict(sorted(operators.items()))}


def _difference(first: Mapping, second: Mapping, key: str) -> dict:
    result = {}
    for name in FEATURES:
        left, right = first[key][name], second[key][name]
        result[name] = float(Fraction(left) - Fraction(right)) if left is not None and right is not None else None
    return result


def aggregate_numeric_residuals(phases: Mapping[str, Mapping]) -> dict:
    """Keep inventory rows and scheduled presentations in explicit phases.

    Each phase is ``{unit, conditions}``: unit is ``ordered_inventory_rows`` or
    ``scheduled_presentations``; conditions map family or family_allocation names
    to C009 records. Schedule repetitions count as repeated exposures. Inventory
    duplicates are rejected. Contrasts report first-minus-second means, totals,
    and equal-problem-weight paired mean differences on shared problem support.
    """
    require(isinstance(phases, Mapping), "Phase mapping required")
    output = {}
    valid_conditions = set(FAMILIES) | {family + "_" + allocation for family in FAMILIES for allocation in ("paths", "gcm")}
    for phase_name, phase in phases.items():
        require(isinstance(phase_name, str) and phase_name, "Phase name required")
        require(phase["unit"] in UNITS and isinstance(phase["conditions"], Mapping), "Explicit phase unit and conditions required")
        conditions, by_problem, ordered_seen = {}, {}, set()
        for name, raw_rows in phase["conditions"].items():
            require(name in valid_conditions, "Unknown condition")
            family = next(family for family in FAMILIES if name == family or name.startswith(family + "_"))
            rows = list(raw_rows)
            for row in rows:
                require(row["family"] == family, "Condition includes the wrong family")
                key = (row["problem_id"], row["expression"])
                if phase["unit"] == "ordered_inventory_rows":
                    require(key not in ordered_seen, "Duplicated ordered inventory row")
                    ordered_seen.add(key)
            conditions[name] = _numeric_summary(rows)
            grouped = defaultdict(list)
            for row in rows:
                grouped[row["problem_id"]].append(row)
            by_problem[name] = {pid: _numeric_summary(subset) for pid, subset in sorted(grouped.items())}
        pairs = [(FAMILIES[0], FAMILIES[1])]
        pairs += [(family + "_gcm", family + "_paths") for family in FAMILIES]
        pairs += [(FAMILIES[0] + "_" + allocation, FAMILIES[1] + "_" + allocation) for allocation in ("paths", "gcm")]
        contrasts = {}
        for first, second in pairs:
            if first not in conditions or second not in conditions:
                continue
            shared = sorted(set(by_problem[first]) & set(by_problem[second]))
            paired = {pid: {"first_rows": by_problem[first][pid]["rows"],
                            "second_rows": by_problem[second][pid]["rows"],
                            "mean_difference": _difference(by_problem[first][pid], by_problem[second][pid], "mean_numeric_features_exact")}
                      for pid in shared}
            contrasts[first + "_minus_" + second] = {
                "first": first, "second": second, "sign": "first minus second",
                "global_mean_difference": _difference(conditions[first], conditions[second], "mean_numeric_features_exact"),
                "global_sum_difference": _difference(conditions[first], conditions[second], "sum_numeric_features_exact"),
                "shared_problem_ids": shared,
                "first_only_problem_ids": sorted(set(by_problem[first]) - set(by_problem[second])),
                "second_only_problem_ids": sorted(set(by_problem[second]) - set(by_problem[first])),
                "paired_per_problem": paired,
                "mean_paired_problem_difference": {
                    feature: float(sum((Fraction(by_problem[first][pid]["mean_numeric_features_exact"][feature])
                                        - Fraction(by_problem[second][pid]["mean_numeric_features_exact"][feature])
                                        for pid in shared), Fraction()) / len(shared)) if shared else None
                    for feature in FEATURES}}
        output[phase_name] = {"unit": phase["unit"], "conditions": conditions,
                              "per_problem": by_problem, "contrasts": contrasts}
    return {"schema_version": 1, "phases": output,
            "interpretation": "Descriptive numerical exposure residuals. Inventory means weight ordered programs; schedule means weight presentations. Paired means weight shared problems equally. These are different estimands, not causal effects, difficulty controls, or evidence that every residual is a confounder. No significance test is performed."}


def run(problems_path, stages_path, out, phases_path=None) -> dict:
    out = Path(out)
    require(not out.exists(), "Refusing to overwrite immutable audit output")
    paths = {"problems": Path(problems_path), "stage_ids": Path(stages_path)}
    if phases_path is not None:
        paths["numeric_phases"] = Path(phases_path)
    blobs = {name: path.read_bytes() for name, path in paths.items()}
    result = {"created_utc": datetime.now(timezone.utc).isoformat(),
              "selection": characterize(json.loads(blobs["problems"]), json.loads(blobs["stage_ids"])),
              "input_sha256": {name: hashlib.sha256(data).hexdigest() for name, data in blobs.items()},
              "code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    if "numeric_phases" in blobs:
        result["numeric_residuals"] = aggregate_numeric_residuals(json.loads(blobs["numeric_phases"]))
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("x") as handle:
        json.dump(result, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--problems", required=True)
    parser.add_argument("--stages", required=True)
    parser.add_argument("--phases")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    run(args.problems, args.stages, args.out, args.phases)


if __name__ == "__main__":
    main()

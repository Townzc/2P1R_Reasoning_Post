"""P012 registered numeric analysis, pending Claude's first-use review.

No model calls or rescoring. Real-data execution requires an accepted review.
Question-paired intervals are conditional on the two observed training seeds.
The module reports all threshold components; it does not invent an aggregate
H0-H3 acceptance rule or discard settings with poor termination.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import numpy as np

POLICY = {"replicates": 10000, "seed": 20261111, "generator": "PCG64",
          "numpy_version": "2.5.4", "quantile_method": "linear",
          "unit": "question", "order": "sorted frozen question ID",
          "interval": "pointwise percentile 95%, conditional on observed seeds"}
CONTRASTS = {"data": ("P", "L"), "PR": ("P", "R"),
             "PK": ("P", "K8"), "KR": ("K8", "R")}


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""): h.update(block)
    return h.hexdigest()


def bound_file(spec):
    path = Path(spec["path"])
    if path.is_absolute() or ".." in path.parts or digest(path) != spec["sha256"]:
        raise ValueError("Missing, non-relative or changed frozen input")
    return path


def outcomes(rows, expected_ids):
    ids = set(expected_ids)
    if len(ids) != len(expected_ids) or not ids:
        raise ValueError("Expected question IDs must be nonempty and unique")
    result = {}
    for row in rows:
        key = row["id"]
        if key in result or key not in ids or row.get("draw") != 0:
            raise ValueError("Duplicate, unexpected or non-greedy label")
        if type(row.get("correct")) is not bool or row.get("needs_judge", False):
            raise ValueError("All verdicts must be resolved Boolean labels")
        result[key] = row["correct"]
    if set(result) != ids: raise ValueError("Incomplete labels")
    return result


def read_endpoint(spec, count, seed, family, task):
    cfg = json.loads(bound_file(spec["generation_manifest"]).read_text())["config"]
    if (cfg["protocol"], cfg["n"], cfg["temperature"], cfg["seed"], cfg["template_family"], cfg["task"]) != ("omi2", 1, 0, seed, family, task):
        raise ValueError("Endpoint protocol, sampling, seed, family or task changed")
    inputs = [json.loads(x) for x in bound_file(spec["inputs"]).open() if x.strip()]
    if len(inputs) != count: raise ValueError("Unregistered endpoint dose")
    bound_file(spec["raw"])
    return outcomes((json.loads(x) for x in bound_file(spec["labels"]).open() if x.strip()),
                    [r["id"] for r in inputs])


def differences(high, low):
    if set(high) != set(low) or not high: raise ValueError("Unpaired question sets")
    if any(type(v) is not bool for data in (high, low) for v in data.values()):
        raise ValueError("Non-Boolean outcomes")
    return np.asarray([int(high[k]) - int(low[k]) for k in sorted(high)], dtype=np.float64)


def bootstrap_delta(delta):
    """Resample question IDs jointly, including when delta is a two-seed mean."""
    if np.__version__ != POLICY["numpy_version"]: raise ValueError("NumPy version changed")
    delta = np.asarray(delta, dtype=np.float64)
    if delta.ndim != 1 or not len(delta) or not np.isfinite(delta).all() or np.max(np.abs(delta)) > 1:
        raise ValueError("Invalid per-question difference")
    rng = np.random.Generator(np.random.PCG64(POLICY["seed"]))
    samples = np.empty(POLICY["replicates"], dtype=np.float64)
    for start in range(0, len(samples), 128):
        stop = min(start + 128, len(samples))
        indices = rng.integers(0, len(delta), size=(stop-start, len(delta)))
        samples[start:stop] = delta[indices].mean(axis=1) * 100
    lower, upper = np.quantile(samples, [.025, .975], method="linear")
    point = float(delta.mean() * 100)
    return {"n_questions": len(delta), "delta_pp": point,
            "lower95_pp": float(lower), "upper95_pp": float(upper),
            "abs_delta_at_least_3pp": abs(point) >= 3,
            "ci_excludes_zero": bool(lower > 0 or upper < 0),
            "draws_sha256": hashlib.sha256(samples.astype('<f8').tobytes()).hexdigest()}


def two_seed_contrast(high, low):
    if set(high) != {"17", "29"} or set(low) != {"17", "29"}:
        raise ValueError("Both registered seeds are required")
    if set(high["17"]) != set(high["29"]): raise ValueError("Seeds use different tests")
    delta = {s: differences(high[s], low[s]) for s in ("17", "29")}
    separate = {s: bootstrap_delta(delta[s]) for s in delta}
    return {"by_seed": separate,
            "seed_mean": bootstrap_delta((delta["17"] + delta["29"]) / 2),
            "same_nonzero_direction": bool(delta["17"].sum()*delta["29"].sum() > 0)}


def ranks(values):
    if not all(math.isfinite(x) for x in values): raise ValueError("Nonfinite capability")
    ordered = sorted(range(len(values)), key=values.__getitem__); result = [0.] * len(values)
    i = 0
    while i < len(ordered):
        j = i + 1
        while j < len(ordered) and values[ordered[j]] == values[ordered[i]]: j += 1
        for k in ordered[i:j]: result[k] = (i + 1 + j) / 2
        i = j
    return np.asarray(result)


def spearman(x, y):
    if len(x) != len(y) or len(x) < 2: raise ValueError("Unpaired settings")
    a, b = ranks(x), ranks(y); a -= a.mean(); b -= b.mean()
    denominator = float(np.sqrt(np.dot(a, a) * np.dot(b, b)))
    return None if denominator == 0 else float(np.dot(a, b) / denominator)


def analyze(manifest):
    if not re.fullmatch(r"[0-9a-f]{40}", manifest.get("accepted_analysis_review_commit", "")):
        raise ValueError("First real-data run awaits Claude analysis review")
    expected = {f"{f}_{i}_{t}" for f in ("qwen", "llama") for i in ("base", "instruct") for t in ("math", "gsm8k")}
    if manifest.get("track") != "main_full_finetuning" or set(manifest["settings"]) != expected:
        raise ValueError("All eight main settings only; exploratory tracks are separate")
    result = {}
    for name, setting in sorted(manifest["settings"].items()):
        n = 5000 if name.endswith("math") else 1319
        family = "llama3" if name.startswith("llama") else "qwen"
        task = "math" if n == 5000 else "gsm8k"
        endpoints = {s: {c: read_endpoint(setting["by_seed"][s][c], n, int(s), family, task) for c in ("P", "K8", "R", "L")} for s in ("17", "29")}
        comparisons = {key: two_seed_contrast({s: endpoints[s][high] for s in endpoints},
                         {s: endpoints[s][low] for s in endpoints}) for key, (high, low) in CONTRASTS.items()}
        baseline = read_endpoint(setting["baseline4"], 500 if n == 5000 else 1319, 17, family, task)
        if not set(baseline) <= set(endpoints["17"]["P"]): raise ValueError("Baseline IDs not in test")
        comparisons["SFT"] = two_seed_contrast({s: {k: endpoints[s]["P"][k] for k in baseline} for s in endpoints},
                                                {s: baseline for s in endpoints})
        capability = {}
        if set(setting["capabilities"]) != {"pass_at_1", "pass_at_8", "nll_per_token", "nll_per_char"}:
            raise ValueError("All four pretraining capability summaries required")
        for key, spec in setting["capabilities"].items():
            value = json.loads(bound_file(spec["file"]).read_text())
            for field in spec["keys"]: value = value[field]
            if type(value) not in (int, float) or not math.isfinite(value): raise ValueError("Invalid capability")
            capability[key] = value
        result[name] = {"accuracy_by_seed": {s: {c: sum(v.values())/len(v) for c, v in cells.items()} for s, cells in endpoints.items()},
                        "comparisons": comparisons, "capabilities": capability,
                        "baseline_termination_note": setting["baseline_termination_note"]}
    names = sorted(result); delta = [result[x]["comparisons"]["data"]["seed_mean"]["delta_pp"] for x in names]
    correlations = {}
    for key in ("pass_at_1", "pass_at_8", "nll_per_token", "nll_per_char"):
        sign = -1 if key.startswith("nll_") else 1
        correlations[key] = {"rho_vs_delta_data": spearman([sign*result[x]["capabilities"][key] for x in names], delta),
                             "capability_transform": "negative NLL" if sign == -1 else "identity", "n_settings": 8}
    return {"policy": POLICY, "accepted_analysis_review_commit": manifest["accepted_analysis_review_commit"],
            "settings": result, "H1_spearman_components": correlations,
            "interpretation": "All five contrasts and both seeds reported. Seed-mean CI is supplementary. H0-H3 interpretation uses the registered criteria and independent audit; no automatic reclassification."}


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--manifest', type=Path, required=True); parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); result = analyze(json.loads(args.manifest.read_text())); result['input_manifest_sha256'] = digest(args.manifest)
    with args.output.open('x') as f: json.dump(result, f, indent=2, allow_nan=False); f.write('\n')


if __name__ == '__main__': main()

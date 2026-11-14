"""P012 numeric analysis accepted at 169754c4, with A-1 through A-6 applied.

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
import numpy as np

ACCEPTED_REVIEW = "169754c427d8e2b748fb925e03d31bbabcf8ab9d"
POLICY = {"replicates": 10000, "seed": 20261111, "generator": "PCG64",
          "numpy_version": "2.5.4", "quantile_method": "linear",
          "unit": "question", "order": "sorted frozen question ID",
          "interval": "pointwise percentile 95%, conditional on observed seeds",
          "noticeable": "abs(two-seed mean)>=3pp AND its joint question CI excludes0 AND both seeds have the same nonzero sign",
          "policy_freeze_commit": ACCEPTED_REVIEW,
          "seed_uncertainty": "Mean CI measures question sampling only; two training seeds do not estimate training-seed uncertainty",
          "primary_SFT_baseline": "baseline4",
          "H1_primary_interpretation": "negative teacher NLL per character; pass@k is compromised in three annotated settings"}
CONTRASTS = {"data": ("P", "L"), "PR": ("P", "R"),
             "PK": ("P", "K8"), "KR": ("K8", "R")}
MODELS = {"qwen_base": "Qwen/Qwen2.5-1.5B", "qwen_instruct": "Qwen/Qwen2.5-1.5B-Instruct",
          "llama_base": "meta-llama/Llama-3.2-1B", "llama_instruct": "meta-llama/Llama-3.2-1B-Instruct"}
# Accepted C6 bytes; R and L deliberately use identical examples with different doses.
DATA_SHA = {
    "math": {"P": "06767f89c8393e7c167e42b04987273f21711e5fe5f14977516f55d12077ffac",
             "K8": "f28e7560bae02c7055619941b0e9a757bfc3f8402ddb62af316e079587386a77",
             "K4": "5e56b9b7bc376a0d406cbc051a9ef8b437afd144f7efef39615ed126cee51a96",
             "R": "591cdb97282af217573aa21a912b41bf4e380ca6378db6d87129e0a4f0c01cf3",
             "L": "591cdb97282af217573aa21a912b41bf4e380ca6378db6d87129e0a4f0c01cf3"},
    "gsm8k": {"P": "3be09142476d2a07aef9a5f98e4bfa0236056e81540728a0f09aaad8063ee377",
              "K8": "b1aab92b26e9b6b2906192458fcd052d940198fb3f875edea8cf4f5933e90a00",
              "K4": "64d6e6efddcd754bd3c7711175cb7b7cea2a2238083d9e1a59ff24065dcb7765",
              "R": "929ded680eef7305c0c0cce4f06b0843ae2b2420103ff2357c0b64b271ac8c2a",
              "L": "929ded680eef7305c0c0cce4f06b0843ae2b2420103ff2357c0b64b271ac8c2a"}}
CAPABILITY_FAILURES = {"llama_base_math": "conversation_nontermination",
                       "llama_base_gsm8k": "conversation_nontermination",
                       "llama_instruct_gsm8k": "answer_only_prompt"}


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


def read_endpoint(spec, count, seed, family, task, initialization, cell=None, shots=None):
    generation = json.loads(bound_file(spec["generation_manifest"]).read_text())
    cfg = generation["config"]
    if (cfg["protocol"], cfg["n"], cfg["temperature"], cfg["max_tokens"]) != ("omi2", 1, 0, 4096):
        raise ValueError("Endpoint protocol or sampling changed")
    template = "llama3" if family == "llama" else "qwen"
    if (cfg["template_family"], cfg["task"]) != (template, task):
        raise ValueError("Endpoint family or task changed")
    model = MODELS[f"{family}_{initialization}"]
    if cell is not None:
        training = json.loads(bound_file(spec["training_manifest"]).read_text())
        tcfg = training["config"]
        dataset_name = f"{task}_{cell.lower()}"
        updates = 128 if cell == "L" else 1024
        if (training["cell"], tcfg["seed"], tcfg["data_seed"], training["model"]["repo"]) != (cell, seed, seed, model):
            raise ValueError("Training cell, seed or initialization changed")
        if (training["dataset"]["name"], training["dataset"]["sha256"], tcfg["dataset"], training["dose"]["expected_updates"]) != (dataset_name, DATA_SHA[task][cell], dataset_name, updates):
            raise ValueError("Training task, dataset or update dose changed")
        checkpoint = spec["checkpoint_manifest"]; bound_file(checkpoint)
        verification = generation["checkpoint_verification"]
        if (cfg.get("training_run_id") != training["run_id"] or
                cfg.get("checkpoint_manifest_sha256") != checkpoint["sha256"] or
                cfg["model"] != f'/p012/training/{training["run_id"]}/checkpoint' or
                cfg["revision"] != training["model"]["revision"] or
                verification["training_run_id"] != training["run_id"] or
                verification["training_manifest_sha256"] != spec["training_manifest"]["sha256"] or
                verification["checkpoint_manifest_sha256"] != checkpoint["sha256"] or
                verification["initialization_repo"] != model):
            raise ValueError("Generation is not bound to the declared training checkpoint")
    elif cfg.get("training_run_id") is not None or cfg.get("checkpoint_manifest_sha256") is not None or cfg["model"] != model:
        raise ValueError("Baseline must use this setting's untrained model")
    with bound_file(spec["inputs"]).open() as f:
        inputs = [json.loads(x) for x in f if x.strip()]
    if len(inputs) != count: raise ValueError("Unregistered endpoint dose")
    if generation["input_sha256"] != spec["inputs"]["sha256"]:
        raise ValueError("Generation input binding changed")
    if cell is None:
        if shots not in (0, 4): raise ValueError("Specify baseline shots")
        expected_roles = ["user", "assistant"] * shots + ["user"]
        if any([m["role"] for m in row["messages"]] != expected_roles for row in inputs):
            raise ValueError("Baseline few-shot conversation changed")
    bound_file(spec["raw"])
    with bound_file(spec["labels"]).open() as f:
        values = outcomes((json.loads(x) for x in f if x.strip()), [r["id"] for r in inputs])
    termination = json.loads(bound_file(spec["termination"]).read_text())
    if (termination["raw_sha256"], termination["labels_sha256"]) != (spec["raw"]["sha256"], spec["labels"]["sha256"]):
        raise ValueError("Termination evidence belongs to a different endpoint")
    stats = termination["all"]
    if stats["responses"] != count or stats["correct"] != sum(values.values()) or stats["accuracy"] != sum(values.values())/count:
        raise ValueError("Termination statistics disagree with registered labels")
    diagnostic = None
    if stats["length_cap_rate"] > .2:
        diagnostic = json.loads(bound_file(spec["first_boxed_diagnostic"]).read_text())
        if diagnostic["raw_sha256"] != spec["raw"]["sha256"] or diagnostic["responses"] != count or not diagnostic["diagnostic_only"]:
            raise ValueError("First-box diagnostic belongs to a different endpoint")
    return {"outcomes": values, "termination": stats, "first_boxed_diagnostic": diagnostic,
            "training_binding": None if cell is None else {"run_id": training["run_id"], "cell": cell,
              "seed": seed, "model": model, "task": task, "dataset": training["dataset"], "expected_updates": updates,
              "training_manifest_sha256": spec["training_manifest"]["sha256"], "checkpoint_manifest_sha256": checkpoint["sha256"]}}


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
    mean = bootstrap_delta((delta["17"] + delta["29"]) / 2)
    same_direction = bool(delta["17"].sum()*delta["29"].sum() > 0)
    return {"by_seed": separate, "seed_mean": mean, "same_nonzero_direction": same_direction,
            "noticeable": bool(mean["abs_delta_at_least_3pp"] and mean["ci_excludes_zero"] and same_direction),
            "both_seed_intervals_exclude_zero": all(r["ci_excludes_zero"] for r in separate.values()),
            "both_seed_abs_deltas_at_least_3pp": all(r["abs_delta_at_least_3pp"] for r in separate.values())}


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
    if manifest.get("accepted_analysis_review_commit") != ACCEPTED_REVIEW:
        raise ValueError("First real-data run awaits Claude analysis review")
    expected = {f"{f}_{i}_{t}" for f in ("qwen", "llama") for i in ("base", "instruct") for t in ("math", "gsm8k")}
    if manifest.get("track") != "main_full_finetuning" or set(manifest["settings"]) != expected:
        raise ValueError("All eight main settings only; exploratory tracks are separate")
    result = {}
    for name, setting in sorted(manifest["settings"].items()):
        n = 5000 if name.endswith("math") else 1319
        family, initialization, task = name.split("_")
        task = "math" if n == 5000 else "gsm8k"
        notes = setting["capability_notes"]
        failure = CAPABILITY_FAILURES.get(name, "none")
        if (notes["failure_mode"] != failure or not isinstance(notes["reason"], str) or not notes["reason"].strip() or
                notes["pass_at_k_valid_as_capability"] is not (failure == "none")):
            raise ValueError("Capability notes must describe the audited protocol failure")
        evidence = {s: {c: read_endpoint(setting["by_seed"][s][c], n, int(s), family, task, initialization, c)
                       for c in (("P", "K8", "K4", "R", "L") if s == "17" else ("P", "K8", "R", "L"))}
                    for s in ("17", "29")}
        endpoints = {s: {c: e["outcomes"] for c, e in cells.items()} for s, cells in evidence.items()}
        comparisons = {key: two_seed_contrast({s: endpoints[s][high] for s in endpoints},
                         {s: endpoints[s][low] for s in endpoints}) for key, (high, low) in CONTRASTS.items()}
        comparisons["LR"] = two_seed_contrast({s: endpoints[s]["L"] for s in endpoints},
                                              {s: endpoints[s]["R"] for s in endpoints})
        comparisons["LR"]["registration"] = "Derived from registered PR-data; not independently preregistered"
        baselines = {}; sft = {}
        for label, shots in (("baseline4", 4), ("baseline0", 0)):
            if shots == 0 and initialization != "instruct": continue
            e = read_endpoint(setting[label], 500 if n == 5000 else 1319, None, family, task, initialization, shots=shots)
            baseline = e["outcomes"]
            if not set(baseline) <= set(endpoints["17"]["P"]): raise ValueError("Baseline IDs not in test")
            sft[label] = two_seed_contrast({s: {k: endpoints[s]["P"][k] for k in baseline} for s in endpoints},
                                           {s: baseline for s in endpoints})
            baselines[label] = {"registered_primary": shots == 4, "accuracy": sum(baseline.values())/len(baseline),
                                "n_questions": len(baseline), "termination": e["termination"],
                                "first_boxed_diagnostic": e["first_boxed_diagnostic"]}
        comparisons["SFT"] = sft["baseline4"]
        best = max(b["accuracy"] for b in baselines.values())
        higher_baselines = [label for label, b in baselines.items() if b["accuracy"] == best]
        reference = setting["G0_Li_reference"]
        if reference["available"]:
            value = json.loads(bound_file(reference["file"]).read_text())
            for field in reference["keys"]: value = value[field]
            if not value["protocol"].startswith("li_"): raise ValueError("G0 reference is not the Li protocol")
            li_reference = {"available": True, "paired": False, "reference_only": True, "metrics": value,
                            "source": reference["file"]}
        else:
            if initialization == "instruct" or not reference["reason"]:
                raise ValueError("Measured Instruct Li reference required")
            li_reference = {"available": False, "paired": False, "reason": reference["reason"]}
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
                        "capability_notes": notes, "SFT_by_baseline": sft, "baselines": baselines,
                        "highest_measured_paired_baselines": higher_baselines, "G0_Li_reference": li_reference,
                        "endpoint_evidence_by_seed": {s: {c: {k: v for k, v in e.items() if k != "outcomes"}
                                                             for c, e in cells.items()} for s, cells in evidence.items()}}
    names = sorted(result); delta = [result[x]["comparisons"]["data"]["seed_mean"]["delta_pp"] for x in names]
    correlations = {}
    for key in ("pass_at_1", "pass_at_8", "nll_per_token", "nll_per_char"):
        sign = -1 if key.startswith("nll_") else 1
        correlations[key] = {"rho_vs_delta_data": spearman([sign*result[x]["capabilities"][key] for x in names], delta),
                             "capability_transform": "negative NLL" if sign == -1 else "identity", "n_settings": 8}
    return {"policy": POLICY, "accepted_analysis_review_commit": manifest["accepted_analysis_review_commit"],
            "settings": result, "H1_spearman_components": correlations,
            "interpretation": "Registered contrasts and derived L-R reported for both seeds. Noticeable uses the A-5 frozen mean-CI rule. H0-H3 interpretation and first real-data numeric output await independent audit; no automatic hypothesis reclassification."}


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--manifest', type=Path, required=True); parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); result = analyze(json.loads(args.manifest.read_text())); result['input_manifest_sha256'] = digest(args.manifest)
    with args.output.open('x') as f: json.dump(result, f, indent=2, allow_nan=False); f.write('\n')


if __name__ == '__main__': main()

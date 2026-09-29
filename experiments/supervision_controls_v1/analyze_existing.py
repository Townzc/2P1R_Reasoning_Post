"""Post-hoc descriptive audit of already-observed public-math outputs.

No new grading, generation, filtering, or bootstrap. Unknown scores contribute
lower/upper bounds, and every method retains all 500 original questions.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

METHODS = ("Base", "SFT", "DFT", "TrimSFT", "QDW_v0")


def pattern_counts(draws):
    if len(draws) != 8 or not draws[0] or any(len(x) != len(draws[0]) for x in draws):
        raise ValueError("Eight equally sized draws required")
    if any(x is not None and type(x) is not bool for draw in draws for x in draw):
        raise ValueError("Only true/false/unresolved scores are allowed")
    pairs = [(sum(x is True for x in row), sum(x is None for x in row))
             for row in zip(*draws)]
    n = len(pairs)
    bounds = lambda lo, hi: dict(lower=sum(lo(k, u) for k, u in pairs),
                                 upper=sum(hi(k, u) for k, u in pairs), denominator=n)
    return dict(questions=n, outputs=n * 8, unresolved_outputs=sum(u for _, u in pairs),
                unresolved_questions=sum(u > 0 for _, u in pairs),
                any_correct=bounds(lambda k,u: k > 0, lambda k,u: k + u > 0),
                all_eight_correct=bounds(lambda k,u: k == 8, lambda k,u: k + u == 8),
                zero_correct=bounds(lambda k,u: k + u == 0, lambda k,u: k == 0),
                histogram_known_correct_counts=dict(sorted(Counter(k for k,u in pairs).items())),
                count_pairs_histogram={f"correct={k},unresolved={u}": count
                                       for (k,u),count in sorted(Counter(pairs).items())},
                mean_accuracy_lower=sum(k for k,u in pairs) / (8*n),
                mean_accuracy_upper=sum(k+u for k,u in pairs) / (8*n))


def analyze(path):
    raw = Path(path).read_bytes()
    data = json.loads(raw)
    if data["report"]["training_seed"] != 17:
        raise ValueError("Unexpected historical training seed")
    result = dict(schema=1, analysis="post_hoc_observed_evidence", source_sha256=hashlib.sha256(raw).hexdigest(),
                  original_training_seed=17, independent_new_seeds=0, new_model_calls=0,
                  original_experiment="public_math_pilot_v1", methods={})
    for method in METHODS:
        records = [data["raw_bound_score_runs"][f"{method}-MATH500-draw{j}"] for j in range(8)]
        for record in records:
            arr = record["correct_by_question"]
            if (len(arr) != 500 or record["outputs"] != 500 or
                    sum(x is True for x in arr) != record["correct"] or
                    sum(x is None for x in arr) != record["unresolved"]):
                raise ValueError("Historical per-question score totals do not reconcile")
        counts = pattern_counts([x["correct_by_question"] for x in records])
        prior = data["report"]["methods"][method]["math500"]
        if (counts["mean_accuracy_lower"] != prior["average_lower"] or
                counts["mean_accuracy_upper"] != prior["average_upper"] or
                counts["any_correct"]["lower"] / 500 != prior["pass_at_draws_lower"] or
                counts["any_correct"]["upper"] / 500 != prior["pass_at_draws_upper"]):
            raise ValueError("Derived counts disagree with immutable final report")
        counts["draw_score_sha256"] = [r["score_sha256"] for r in records]
        result["methods"][method] = counts
    result["limitations"] = [
        "Descriptive post-hoc analysis of observed tests, not a new confirmatory result.",
        "All-eight-correct measures this finite set of eight samples, not general determinism or correctness of every reasoning step.",
        "Task and decoding are confounded in the historical GSM8K-greedy versus MATH-sampled comparison.",
        "One training seed; the same examples cannot become an untouched confirmation set.",
        "Unknown scores retain all-question bounds; no difficult question was dropped.",
    ]
    return result


def markdown(result):
    lines = ["# Observed MATH sampling patterns — post-hoc CPU audit", "",
             "No new generation, training, or grading. Each row retains 500 questions × 8 samples.", "",
             "| Method | Average accuracy | At least one correct / 500 | All eight correct / 500 | Unresolved outputs |",
             "|---|---:|---:|---:|---:|"]
    def interval(x):
        return str(x["lower"]) if x["lower"] == x["upper"] else f'{x["lower"]}–{x["upper"]}'
    for method, x in result["methods"].items():
        lines.append(f'| {method} | {100*x["mean_accuracy_lower"]:.3f}–{100*x["mean_accuracy_upper"]:.3f}% | '
                     f'{interval(x["any_correct"])} | {interval(x["all_eight_correct"])} | {x["unresolved_outputs"]} |')
    lines += ["", "DFT and TrimSFT have many more questions correct in all eight observed samples. "
              "This difference is much larger than their difference in questions with any correct sample. "
              "It motivates a same-question decoding comparison; it does not identify the cause.", ""]
    lines += ["- " + x for x in result["limitations"]]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=False)
    result = analyze(args.source)
    (out / "RESULTS.json").write_text(json.dumps(result, indent=2) + "\n")
    (out / "RESULTS.md").write_text(markdown(result))
    print(json.dumps({"status": "complete", "methods": len(result["methods"]), "new_model_calls": 0}))

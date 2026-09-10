"""CPU-only, post-hoc length and selection audit of immutable C017/E013 data.

Lexical distance measures surface overlap, not reasoning-strategy equivalence.
This module never loads a model, changes an accepted decision, or launches SFT.
"""

import argparse
import base64
from collections import Counter, defaultdict
import gzip
import hashlib
import itertools
import json
from pathlib import Path
import re
import statistics


DECISIONS = Path("reports/real_math_c017_solutions_r2/candidate_decisions.jsonl.gz.b64")
PARENTS = Path("reports/real_math_c017_solutions_r2/per_problem.jsonl")
RAW = Path(".local/real_math_c017_solutions_r2/raw_candidates.jsonl")
TRAIN = Path("reports/real_math_e013_inputs_r1/train.jsonl")
OUTPUTS = Path("runs/gsm8k_overfit_e013_r1/final_train.jsonl")
HISTORY = Path("runs/gsm8k_overfit_e013_r1/train_history.jsonl")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def rows(path):
    return [json.loads(line) for line in path.read_bytes().splitlines() if line]


def key(row):
    return tuple(row[x] for x in ("problem_id", "candidate_index", "shard", "row_index"))


def stats(values):
    xs = sorted(values)
    if not xs:
        return {"n": 0}
    return {"n": len(xs), "sum": sum(xs), "min": xs[0],
            "p50": statistics.median(xs), "p90_nearest_rank": xs[(9 * len(xs) + 9) // 10 - 1],
            "max": xs[-1], "mean": statistics.mean(xs)}


def trigrams(text):
    tokens = re.findall(r"\w+|[^\w\s]", text.casefold())
    return set(zip(tokens, tokens[1:], tokens[2:]))


def overlap(a, b):
    union = a | b
    return len(a & b) / len(union) if union else 1.0


def priority(row):
    value = f"c018-seed17\n{row['problem_id']}\n{row['response_sha256']}"
    return digest(value.encode())


def select(candidates, policy, similarity):
    target = min(4, len(candidates))
    if policy == "source_first":
        return sorted(candidates, key=lambda x: x["candidate_index"])[:target]
    if policy == "shortest":
        return sorted(candidates, key=lambda x: (x["n_supervised"], priority(x)))[:target]
    pending = sorted(candidates, key=priority)
    if policy == "hash_random":
        return pending[:target]
    chosen = pending[:1]
    pending = pending[1:]
    while len(chosen) < target:
        best = min(pending, key=lambda x: (
            max(similarity[x["candidate_index"], y["candidate_index"]] for y in chosen),
            priority(x)))
        chosen.append(best)
        pending.remove(best)
    return chosen


def audit():
    decisions = [json.loads(line) for line in gzip.decompress(
        base64.b64decode(DECISIONS.read_bytes())).splitlines()]
    accepted = {key(x): x for x in decisions if x["reason"] == "accepted"}
    if len(accepted) != sum(x["reason"] == "accepted" for x in decisions):
        raise ValueError("Duplicate accepted source keys")
    grams, seen = {}, set()
    for row in rows(RAW):
        ident = key(row)
        if ident not in accepted:
            continue
        if ident in seen:
            raise ValueError("Duplicate raw source keys")
        text = row["row"]["generated_solution"]
        if digest(text.encode()) != accepted[ident]["response_sha256"]:
            raise ValueError("Raw response hash mismatch")
        grams[ident] = trigrams(text)
        seen.add(ident)
    if seen != set(accepted):
        raise ValueError("Missing accepted source responses")
    parents = rows(PARENTS)
    by_parent = defaultdict(list)
    for row in accepted.values():
        by_parent[row["problem_id"]].append(row)
    if len({p["problem_id"] for p in parents}) != len(parents):
        raise ValueError("Duplicate parents")
    if set(by_parent) - {p["problem_id"] for p in parents}:
        raise ValueError("Accepted response outside frozen parent pool")

    summary = {"schema": "c018-selection-audit-v1", "status": "post_hoc_cpu_only",
               "source_sha256": {str(p): digest(p.read_bytes()) for p in
                                  (DECISIONS, PARENTS, RAW, TRAIN, OUTPUTS, HISTORY)},
               "accepted_raw_hashes_checked": len(seen), "datasets": {},
               "definitions": {
                   "length": "C017 exact supervised tokenizer count, including EOS",
                   "similarity": "Jaccard of case-folded word/punctuation trigram sets",
                   "diversity_policy": "Deterministic farthest-first, same first item as hash_random",
                   "random_policy": "SHA256 ordering with fixed seed label 17 per parent/response",
                   "limitations": "Length and lexical overlap do not establish learnability or strategy diversity. Cached K is not teacher pass rate. No SFT outcomes or equal-token training comparison."}}
    for ds in ("gsm8k", "math"):
        group = [p for p in parents if p["dataset"] == ds]
        data = [r for r in accepted.values() if r["dataset"] == ds]
        limits = []
        for cap in (128, 256, 512):
            counts = Counter(r["problem_id"] for r in data if r["n_supervised"] <= cap)
            limits.append({"max_supervised_tokens": cap, "retained_pairs": sum(counts.values()),
                           "parents_with_k1": sum(counts[p["problem_id"]] >= 1 for p in group),
                           "parents_with_k4": sum(counts[p["problem_id"]] >= 4 for p in group)})
        summary["datasets"][ds] = {"frozen_parent_denominator": len(group),
            "baseline_parents_with_k1": sum(p["accepted_k"] >= 1 for p in group),
            "baseline_parents_with_k4": sum(p["accepted_k"] >= 4 for p in group),
            "accepted_lengths": stats([r["n_supervised"] for r in data]),
            "hypothetical_length_filters": limits}

    pool = sorted((p for p in parents if p["dataset"] == "gsm8k" and p["rank"] <= 256),
                  key=lambda p: p["rank"])
    if len(pool) != 256:
        raise ValueError("Unexpected first-256 parent pool")
    records, policy_stats = [], defaultdict(lambda: defaultdict(list))
    for parent in pool:
        pid = parent["problem_id"]
        candidates = by_parent[pid]
        if len(candidates) != parent["accepted_k"]:
            raise ValueError("Acceptance count mismatch")
        sim = {}
        for a, b in itertools.combinations(candidates, 2):
            value = overlap(grams[key(a)], grams[key(b)])
            sim[a["candidate_index"], b["candidate_index"]] = value
            sim[b["candidate_index"], a["candidate_index"]] = value
        rec = {"problem_id": pid, "rank": parent["rank"], "accepted_k": len(candidates),
               "max_pairwise_jaccard": max(sim.values()) if sim else None, "policies": {}}
        for policy in ("source_first", "hash_random", "lexical_diverse", "shortest"):
            chosen = select(candidates, policy, sim)
            values = [sim[a["candidate_index"], b["candidate_index"]]
                      for a, b in itertools.combinations(chosen, 2)]
            rec["policies"][policy] = {
                "candidate_indices": [r["candidate_index"] for r in chosen],
                "supervised_tokens": sum(r["n_supervised"] for r in chosen),
                "mean_pairwise_jaccard": statistics.mean(values) if values else None}
            target = policy_stats[policy]
            target["lengths"].extend(r["n_supervised"] for r in chosen)
            target["parent_counts"].append(len(chosen))
            if values:
                target["parent_mean_jaccard"].append(statistics.mean(values))
        records.append(rec)
    summary["first_256_gsm8k"] = {"frozen_parent_denominator": 256,
        "parents_with_any_pair_jaccard_ge_0_8": sum(r["max_pairwise_jaccard"] is not None and
                                                   r["max_pairwise_jaccard"] >= 0.8 for r in records),
        "policies": {name: {"selected_lengths": stats(d["lengths"]),
                             "parent_count_distribution": dict(sorted(Counter(d["parent_counts"]).items())),
                             "parent_mean_jaccard": stats(d["parent_mean_jaccard"])}
                     for name, d in policy_stats.items()}}
    train = rows(TRAIN)
    outputs = {r["problem_id"]: r for r in rows(OUTPUTS)}
    if set(outputs) != {r["problem_id"] for r in train} or len(train) != 32:
        raise ValueError("Unexpected E013 train outputs")
    summary["e013_reference_lengths"] = {
        group: stats([r["source"]["n_supervised"] for r in train if group == "all" or
                      bool(outputs[r["problem_id"]]["score"]["terminated_correct"]) == (group == "passed")])
        for group in ("all", "passed", "failed")}
    history = rows(HISTORY)
    summary["e013_training_loss"] = {
        "caveat": "Different minibatches across updates; these summaries do not prove optimization causality.",
        "first_32_updates": stats([r["response_nll"] for r in history[:32]]),
        "last_32_updates": stats([r["response_nll"] for r in history[-32:]])}
    return summary, records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError("Immutable output already exists")
    summary, records = audit()
    args.out.mkdir(parents=True, exist_ok=False)
    (args.out / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    (args.out / "selection_by_parent.jsonl").write_text("".join(
        json.dumps(r, sort_keys=True) + "\n" for r in records))
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

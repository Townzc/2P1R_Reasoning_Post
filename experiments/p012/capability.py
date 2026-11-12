"""C7 review candidate: fixed conversations and question-level pass estimates.

Generation and answer grading use the already reviewed evaluation/scoring
modules. This module never chooses demonstrations or changes frozen splits.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict
import json
from pathlib import Path

from .evaluation import EvalConfig, prompt_text, sha256_file


def conversation_rows(rows: list[dict], demonstrations: list[dict], shots: int) -> list[dict]:
    if shots not in (0, 4):
        raise ValueError("C7 registers only zero or four demonstrations")
    if len(demonstrations) != 8 or [m.get("role") for m in demonstrations] != ["user", "assistant"] * 4:
        raise ValueError("Use the eight frozen C6 demonstration messages")
    if any(not isinstance(m.get("content"), str) or not m["content"].strip() for m in demonstrations):
        raise ValueError("Empty demonstration")
    if not rows or len({r["id"] for r in rows}) != len(rows):
        raise ValueError("Unique nonempty question IDs required")
    output = []
    for row in rows:
        if "prompt" in row or "messages" in row:
            raise ValueError("Provide bare questions, not a previous prompt")
        if not isinstance(row["gold"], str) or not row["gold"].strip():
            raise ValueError("Missing answer")
        messages = [dict(m) for m in demonstrations] if shots else []
        messages.append({"role": "user", "content": prompt_text(row["problem"], "omi2")})
        output.append(dict(row, messages=messages))
    return output


def capability_config(model: dict, task: str, endpoint: str, template_file: str) -> dict:
    if endpoint not in {"holdout8", "baseline4", "baseline0"}:
        raise ValueError("Unknown C7 endpoint")
    cfg = EvalConfig(model["repo"], model["revision"], "omi2", task, model["family"],
                     max_tokens=4096, max_model_len=8192, seed=17, batch_size=500 if task == "math" else 1319,
                     temperature=0.7 if endpoint == "holdout8" else 0.0,
                     n=8 if endpoint == "holdout8" else 1, chat_template_file=template_file)
    cfg.validate()
    return asdict(cfg)


def heldout_pass_metrics(labels: list[dict], expected_ids: list[str]) -> dict:
    if len(expected_ids) != 500 or len(set(expected_ids)) != 500:
        raise ValueError("C7 requires the frozen 500 held-out parents")
    counts = Counter()
    seen = set()
    expected = {(id_, draw) for id_ in expected_ids for draw in range(8)}
    for row in labels:
        key = (row["id"], row["draw"])
        if key not in expected or key in seen or type(row["correct"]) is not bool:
            raise ValueError("Missing, repeated or invalid held-out draw")
        seen.add(key)
        counts[row["id"]] += int(row["correct"])
    if seen != expected:
        raise ValueError("Incomplete held-out sample set")
    parents = [{"id": id_, "correct_draws": counts[id_], "draws": 8,
                "pass_at_1": counts[id_] / 8, "pass_at_8": int(counts[id_] > 0)} for id_ in expected_ids]
    return {"questions": 500, "responses": 4000, "pass_at_1": sum(counts.values()) / 4000,
            "pass_at_8": sum(counts[id_] > 0 for id_ in expected_ids) / 500,
            "estimator": "For n=8, pass@1=c/8; pass@8=1[c>0]. Mean over questions.",
            "parents": parents}


def summarize_holdout(inputs: Path, generation: Path, scores: Path, output: Path) -> None:
    manifest = json.loads((generation / "MANIFEST.json").read_text())
    scorer = json.loads((scores / "MANIFEST.json").read_text())
    cfg = manifest["config"]
    if any(cfg.get(k) != v for k, v in {"protocol": "omi2", "n": 8, "temperature": 0.7,
                                      "top_p": 1.0, "max_tokens": 4096, "max_model_len": 8192}.items()):
        raise ValueError("Different capability sampling protocol")
    if manifest["input_sha256"] != sha256_file(inputs) or scorer["input_sha256"] != sha256_file(inputs):
        raise ValueError("Holdout input binding mismatch")
    if scorer["generation_manifest_sha256"] != sha256_file(generation / "MANIFEST.json"):
        raise ValueError("Scores belong to a different generation")
    if scorer["raw_sha256"] != sha256_file(generation / "raw.jsonl"):
        raise ValueError("Raw outputs changed after scoring")
    rows = [json.loads(line) for line in inputs.open() if line.strip()]
    labels = [json.loads(line) for line in (scores / "labels.jsonl").open() if line.strip()]
    result = heldout_pass_metrics(labels, [r["id"] for r in rows])
    result.update(input_sha256=sha256_file(inputs), labels_sha256=sha256_file(scores / "labels.jsonl"),
                  generation_manifest_sha256=sha256_file(generation / "MANIFEST.json"))
    with output.open("x") as file:
        json.dump(result, file, indent=2)
        file.write("\n")

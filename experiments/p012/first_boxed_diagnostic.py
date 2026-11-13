"""A6 diagnostic on immutable saved outputs; registered last-boxed labels stay unchanged."""
import argparse
import json
from pathlib import Path
import re

from .evaluation import score_answer, sha256_file
from .scoring import read_manifest


def first_boxed(text):
    match = re.search(r"\\boxed\s*\{", text)
    if match is None:
        return None
    start, depth = match.end(), 1
    for i in range(start, len(text)):
        escaped = (len(text[:i]) - len(text[:i].rstrip("\\"))) % 2 == 1
        if not escaped and text[i] == "{":
            depth += 1
        elif not escaped and text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start:i].strip() or None
    return None


def summarize(inputs, generation, output):
    manifest, complete = read_manifest(generation)
    if sha256_file(inputs) != manifest["input_sha256"]:
        raise ValueError("Input hash changed")
    rows = {r["id"]: r for r in map(json.loads, inputs.open())}
    raw = [json.loads(x) for x in (generation / "raw.jsonl").open()]
    n = manifest["config"]["n"]
    if {(r["id"], r["draw"]) for r in raw} != {(id_, j) for id_ in rows for j in range(n)} or len(raw) != len(rows) * n:
        raise ValueError("Saved output is incomplete or duplicated")
    caps = sum(r["length_capped"] for r in raw)
    if caps / len(raw) <= .20:
        raise ValueError("A6 first-boxed diagnostic applies only above20percent cap")
    output.mkdir(parents=True, exist_ok=False)
    labels = []
    for r in raw:
        answer = first_boxed(r["text"])
        labels.append({"id": r["id"], "draw": r["draw"], "answer_first_boxed": answer,
                       "correct": score_answer(answer, rows[r["id"]]["gold"], manifest["config"]["task"])})
    (output / "labels.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in labels))
    summary = {"diagnostic_only": True, "registered_metric_unchanged": True,
               "authority_commit": "18f64e2df34944da9b8fc6378609ccbdeed1c587",
               "raw_sha256": complete["raw_sha256"], "input_sha256": manifest["input_sha256"],
               "responses": len(raw), "length_capped": caps, "cap_fraction": caps / len(raw),
               "first_boxed_correct": sum(r["correct"] for r in labels),
               "first_boxed_accuracy": sum(r["correct"] for r in labels) / len(raw)}
    (output / "SUMMARY.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def main():
    p = argparse.ArgumentParser()
    for name in ("inputs", "generation", "output"):
        p.add_argument("--" + name, type=Path, required=True)
    a = p.parse_args(); print(json.dumps(summarize(a.inputs, a.generation, a.output)))


if __name__ == "__main__":
    main()

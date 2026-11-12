"""Freeze the preregistered nested C6 cells from a fully checked C5 inventory."""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import random
import sqlite3

from .data_pool import write_json
from .evaluation import execution_commit, prompt_text, sha256_file
from .training_config import CELLS, grid_dose


def nested_cells(parents: list[str], solutions: dict[str, list[dict]]) -> dict[str, list[dict]]:
    if len(parents) != 4096 or len(set(parents)) != 4096:
        raise ValueError("Freeze exactly 4096 distinct training parents")
    cells = {cell: [row for parent in parents[:p] for row in solutions[parent][:k]]
             for cell, (p, k, _) in CELLS.items()}
    for cell, rows in cells.items():
        p, k, _ = CELLS[cell]
        counts = Counter(r["parent_id"] for r in rows)
        if len(rows) != p * k or set(counts.values()) != {k} or list(counts) != parents[:p]:
            raise ValueError("Cell dose or ordered nesting differs from the frozen design")
        if len({(r["parent_id"], r["solution_hash"]) for r in rows}) != len(rows):
            raise ValueError("Repeated solution within a cell")
    if cells["R"] != cells["L"] or cells["R"] != cells["P"][:512] or cells["R"] != cells["K8"][::8]:
        raise ValueError("The same first solution must define P, K8, R and L")
    if cells["K4"][::4] != cells["P"][:1024]:
        raise ValueError("K4 must share the P first solutions")
    return cells


def write_rows(path: Path, rows: list[dict]) -> dict:
    with path.open("x") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")
    return {"rows": len(rows), "sha256": sha256_file(path), "bytes": path.stat().st_size}


def freeze(pool: Path, lengths: Path, preflight: Path, output: Path) -> dict:
    if not (lengths / "LENGTHS_COMPLETE.json").exists():
        raise ValueError("Length filtering must finish before sampling")
    proof = json.loads(preflight.read_text())
    real_checks = [c for c in proof["checks"] if c["dataset"].startswith("c5_real_")]
    if not proof["all_passed"] or len(real_checks) != 24 or not all(
            c.get("evaluation_prompt_equal") and c.get("length_counter_equal") for c in real_checks):
        raise ValueError("Require actual LF preprocessing proof for both tasks and all four models")
    length_manifest = json.loads((lengths / "MANIFEST.json").read_text())
    if sha256_file(pool / "pool.sqlite") != length_manifest["collection_database_sha256"]:
        raise ValueError("The collection database changed after token counting")
    db = sqlite3.connect(f"file:{pool / 'pool.sqlite'}?mode=ro", uri=True)
    db.execute("ATTACH DATABASE ? AS token_lengths", (f"file:{lengths / 'lengths.sqlite'}?mode=ro",))
    if db.execute("SELECT count(*) FROM solutions").fetchone()[0] != db.execute("SELECT count(*) FROM token_lengths.lengths").fetchone()[0]:
        raise ValueError("Length database does not cover every solution")
    parents = {id_: json.loads(payload) for id_, payload in db.execute("SELECT id,payload FROM parents")}
    counts = dict(db.execute("SELECT s.parent,count(*) FROM solutions s JOIN token_lengths.lengths l ON s.rowid=l.source_rowid WHERE l.qwen_tokens<=4096 AND l.llama_tokens<=4096 GROUP BY s.parent"))
    demonstrations = json.loads((pool / "DEMONSTRATIONS.json").read_text())
    eligible_by_task = {task: sorted((p for p in parents.values() if p["task"] == task and counts.get(p["id"], 0) >= 8), key=lambda p: p["key"])
                        for task in ("math", "gsm8k")}
    if any(len(p) < 4596 for p in eligible_by_task.values()):
        raise ValueError("Registered teacher fallback required: fewer than4596 eligible parents")
    output.mkdir(parents=True, exist_ok=False)
    manifest = {"code_commit": execution_commit(), "source_sha256": sha256_file(Path(__file__)),
        "collection_database_sha256": length_manifest["collection_database_sha256"],
        "length_database_sha256": sha256_file(lengths / "lengths.sqlite"),
        "length_manifest_sha256": sha256_file(lengths / "MANIFEST.json"),
        "actual_preprocessing_sha256": sha256_file(preflight), "seed": 20261111,
        "length_limit": 4096, "length_policy": "Common inventory fits both family encoders and all four initializations",
        "selection": "Sort normalized question keys, fresh Random(20261111) per task; first500 holdout then4096 training. Sort solution hashes then shuffle with int(sha256(question_key+'p012'),16), take8.",
        "tasks": {}}
    for task, eligible in eligible_by_task.items():
        folder = output / task
        folder.mkdir()
        eligible_ids = {p["id"] for p in eligible}
        task_parents = [p for p in parents.values() if p["task"] == task]
        pool_summary = {"canonical_usable_parents_before_OMI_filters": len(task_parents),
            "eligible_parents": len(eligible), "excluded_fraction": 1 - len(eligible) / len(task_parents),
            "eligible_solution_count_distribution": dict(sorted(Counter(counts[p["id"]] for p in eligible).items())),
            "difficulty": {}}
        for name, subset in {"inside": eligible, "outside": [p for p in task_parents if p["id"] not in eligible_ids]}.items():
            if task == "math":
                pool_summary["difficulty"][name] = {"level_counts": dict(Counter(str(p["level"]) for p in subset))}
            else:
                values = sorted(p["difficulty_proxy_characters"] for p in subset)
                pool_summary["difficulty"][name] = {"n": len(values), "mean_human_solution_characters": sum(values) / len(values) if values else None,
                    "median_human_solution_characters": values[len(values)//2] if values else None}
        ordered = list(eligible)
        random.Random(20261111).shuffle(ordered)
        holdout, train = ordered[:500], ordered[500:4596]
        demo_ids = {p["id"] for p in demonstrations[task]}
        held_ids, train_ids = {p["id"] for p in holdout}, {p["id"] for p in train}
        if held_ids & train_ids or demo_ids & (held_ids | train_ids) or len(demo_ids) != 4:
            raise ValueError("Demonstrations, holdout and training must be disjoint")
        selected = {}
        for parent in holdout + train:
            candidates = list(db.execute("SELECT s.hash,s.rowid FROM solutions s JOIN token_lengths.lengths l ON s.rowid=l.source_rowid WHERE s.parent=? AND l.qwen_tokens<=4096 AND l.llama_tokens<=4096 ORDER BY s.hash", (parent["id"],)))
            random.Random(int(hashlib.sha256((parent["key"] + "p012").encode()).hexdigest(), 16)).shuffle(candidates)
            chosen = []
            for solution_hash, rowid in candidates[:8]:
                solution, gold, shard, source_row, qwen_len, llama_len = db.execute("SELECT s.solution,s.expected_answer,s.shard,s.source_row,l.qwen_tokens,l.llama_tokens FROM solutions s JOIN token_lengths.lengths l ON s.rowid=l.source_rowid WHERE s.rowid=?", (rowid,)).fetchone()
                chosen.append({"parent_id": parent["id"], "solution_hash": solution_hash, "task": task,
                    "raw_problem": parent["problem"], "problem": prompt_text(parent["problem"], "omi2"),
                    "solution": solution, "gold": gold, "level": parent["level"],
                    "provenance": {"collection_rowid": rowid, "shard": shard, "source_row": source_row},
                    "training_tokens": {"qwen": qwen_len, "llama3": llama_len}})
            selected[parent["id"]] = chosen
        cells = nested_cells([p["id"] for p in train], selected)
        files, configs = {}, {}
        for cell, rows in cells.items():
            if any(max(r["training_tokens"].values()) > 4096 for r in rows):
                raise ValueError("Main-grid row would be truncated")
            files[cell + ".jsonl"] = write_rows(folder / (cell + ".jsonl"), rows)
            configs[cell] = {"dose": grid_dose(cell), "tokens_per_epoch": {family: sum(r["training_tokens"][family] for r in rows) for family in ("qwen", "llama3")},
                "maximum_full_tokens": {family: max(r["training_tokens"][family] for r in rows) for family in ("qwen", "llama3")}}
        nll = [r for p in holdout for r in selected[p["id"]][:2]]
        holdout_rows = [{"id": p["id"], "problem": p["problem"], "gold": selected[p["id"]][0]["gold"], "task": task} for p in holdout]
        files["holdout500.jsonl"] = write_rows(folder / "holdout500.jsonl", holdout_rows)
        files["nll1000.jsonl"] = write_rows(folder / "nll1000.jsonl", nll)
        files["selected8.jsonl"] = write_rows(folder / "selected8.jsonl", [r for p in holdout + train for r in selected[p["id"]]])
        messages = []
        for demo in demonstrations[task]:
            response = demo["official_solution"]
            if task == "gsm8k":
                response = response.rsplit("####", 1)[0].rstrip() + "\n\\boxed{" + demo["gold"] + "}"
            messages.extend([{"role": "user", "content": prompt_text(demo["problem"], "omi2")},
                             {"role": "assistant", "content": response}])
        write_json(folder / "FOUR_SHOT_MESSAGES.json", messages)
        write_json(folder / "PARENT_ORDER.json", {"full_eligible_order": [p["id"] for p in ordered],
            "holdout500": [p["id"] for p in holdout], "training4096": [p["id"] for p in train],
            "demonstrations": [p["id"] for p in demonstrations[task]]})
        write_json(folder / "POOL_SUMMARY.json", pool_summary)
        manifest["tasks"][task] = {"pool": pool_summary, "files": files, "cells": configs,
            "four_shot_messages_sha256": sha256_file(folder / "FOUR_SHOT_MESSAGES.json"),
            "parent_order_sha256": sha256_file(folder / "PARENT_ORDER.json"),
            "nested_checks_passed": True, "split_disjointness_passed": True}
        print(json.dumps({"task": task, "eligible": len(eligible), "cells": {k: len(v) for k, v in cells.items()}}), flush=True)
    db.close()
    write_json(output / "MANIFEST.json", manifest)
    write_json(output / "FREEZE_COMPLETE.json", {"manifest_sha256": sha256_file(output / "MANIFEST.json"),
        "all_checks_passed": True, "pre_C8_review": "pending; actual frozen-row LF preflight required"})
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("pool", "lengths", "preflight", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    freeze(args.pool, args.lengths, args.preflight, args.output)

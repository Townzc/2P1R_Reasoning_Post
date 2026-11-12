"""CPU-only C5 collection and C6 sampling from the fixed OMI-2 inventory.

Collection scans all 32 original shards, verifies answers, and deduplicates
within each original training problem. Length filtering and C6 are separate
steps so no partially checked pool can be mistaken for frozen training data.
"""
from __future__ import annotations

import argparse
from collections import Counter
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import time
import unicodedata

from .evaluation import execution_commit, extract_answer, last_boxed, numeric_answer, score_answer, sha256_file


def normalized(text: str) -> str:
    return unicodedata.normalize("NFKC", text).strip()


def ngrams(text: str) -> set[str]:
    words = re.findall(r"\w+", normalized(text).casefold())
    return {" ".join(words[i:i + 13]) for i in range(max(0, len(words) - 12))}


def question_id(task: str, key: str) -> str:
    return task + "/" + hashlib.sha256(key.encode()).hexdigest()


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


@lru_cache(maxsize=262144)
def answer_correct(answer: str | None, gold: str) -> bool:
    if answer is None:
        return False
    left, right = numeric_answer(answer), numeric_answer(gold)
    if left is not None and right is not None:
        return left == right
    # Use the fixed math-verify scorer for nontrivial mathematical objects.
    return score_answer(answer, gold, "math")


def canonical_sources(assets: Path, manifests: Path) -> tuple[dict, dict]:
    import pyarrow.parquet as pq
    sources, tasks = {}, {}
    for task, slug, folder in (("math", "DigitalLearningGmbH__MATH-lighteval", "data"),
                               ("gsm8k", "openai__gsm8k", "main")):
        manifest = json.loads((manifests / f"{slug}_FILES.json").read_text())
        splits = {}
        evidence = []
        for split in ("train", "test"):
            relative = f"{folder}/{split}-00000-of-00001.parquet"
            record = next(f for f in manifest["files"] if f["path"] == relative)
            path = assets / slug / relative
            if path.stat().st_size != record["bytes"] or sha256_file(path) != record["sha256"]:
                raise ValueError("Canonical train/test bytes differ from C1")
            splits[split] = pq.read_table(path).to_pylist()
            evidence.append(record | {"rows": len(splits[split])})
        sources[task] = {"repo": manifest["repo"], "revision": manifest["revision"], "files": evidence}
        tasks[task] = splits
    return tasks, sources


def collect(assets: Path, manifests: Path, output: Path) -> dict:
    import pyarrow as pa
    import pyarrow.compute as pc
    import pyarrow.parquet as pq

    started = time.monotonic()
    code_commit = execution_commit()
    tasks, sources = canonical_sources(assets, manifests)
    output.mkdir(parents=True, exist_ok=False)
    parents, lookup, decontamination, demonstrations = {}, {}, {}, {}
    for task, splits in tasks.items():
        field = "problem" if task == "math" else "question"
        test_keys = {normalized(r[field]) for r in splits["test"]}
        test_ngrams = set().union(*(ngrams(r[field]) for r in splits["test"]))
        rows, removed = {}, []
        for index, row in enumerate(splits["train"]):
            key = normalized(row[field])
            reason = "exact_test" if key in test_keys else "13gram_test" if ngrams(key) & test_ngrams else None
            if reason:
                removed.append({"id": question_id(task, key), "source_index": index, "reason": reason})
                continue
            solution = row["solution"] if task == "math" else row["answer"]
            gold = extract_answer(solution, "li_release_math500") if task == "math" else solution.rsplit("####", 1)[-1].strip()
            if not gold:
                raise ValueError("Canonical training solution has no gold answer")
            if key in rows and normalized(rows[key]["gold"]) != normalized(gold):
                raise ValueError("Duplicate canonical question has conflicting gold answers")
            rows.setdefault(key, {"id": question_id(task, key), "task": task, "key": key,
                "problem": row[field], "gold": gold, "source_index": index,
                "level": row.get("level"), "official_solution": solution,
                "difficulty_proxy_characters": len(solution)})
        # Freeze the four out-of-pool demonstrations before OMI quality/length
        # filtering or any model results. Main pool RNG is not consumed here.
        demo_keys = sorted(rows, key=lambda k: hashlib.sha256((k + "p012-baseline").encode()).hexdigest())[:4]
        demonstrations[task] = [rows[k] for k in demo_keys]
        for key in demo_keys:
            del rows[key]
        lookup[task] = {key: value["id"] for key, value in rows.items()}
        parents.update({value["id"]: value for value in rows.values()})
        decontamination[task] = {"test_questions": len(splits["test"]), "train_rows": len(splits["train"]),
            "removed_counts": dict(Counter(r["reason"] for r in removed)), "removed": removed,
            "unique_candidates_after_demo_reservation": len(rows), "demonstrations_reserved": 4}
    write_json(output / "DECONTAMINATION.json", decontamination)
    write_json(output / "DEMONSTRATIONS.json", demonstrations)
    omi = json.loads((manifests / "nvidia__OpenMathInstruct-2_FILES.json").read_text())
    manifest = {"code_commit": code_commit, "source_sha256": sha256_file(Path(__file__)),
        "canonical_sources": sources, "OMI2_repo": omi["repo"], "OMI2_revision": omi["revision"],
        "normalization": "NFKC then strip; same-problem solution dedupe by normalized exact text",
        "decontamination": "exact normalized question OR any13 consecutive Unicode word tokens; casefold; regex\\w+",
        "demonstration_selection": "first4 canonical decontaminated train questions sorted by SHA256(question_key+p012-baseline); excluded before OMI quality filtering",
        "source_order": "lexicographic shard path, then original physical row index",
        "answer_check": "last balanced boxed answer; exact numeric equality or fixed math-verify",
        "collection_is_not_a_length_checked_training_pool": True, "shards": []}
    write_json(output / "MANIFEST.json", manifest)
    db = sqlite3.connect(output / "pool.sqlite")
    db.execute("PRAGMA cache_size=-262144")
    db.execute("PRAGMA synchronous=NORMAL")
    db.execute("CREATE TABLE parents(id TEXT PRIMARY KEY, task TEXT, question_key TEXT, payload TEXT)")
    db.execute("CREATE TABLE solutions(parent TEXT, hash TEXT, solution TEXT, expected_answer TEXT, shard TEXT, source_row INTEGER, qwen_tokens INTEGER, llama_tokens INTEGER, PRIMARY KEY(parent,hash))")
    db.executemany("INSERT INTO parents VALUES(?,?,?,?)", [(k, v["task"], v["key"], json.dumps(v, ensure_ascii=False)) for k, v in parents.items()])
    db.commit()
    counts = Counter()
    for item in sorted(omi["files"], key=lambda f: f["path"]):
        path = assets / "nvidia__OpenMathInstruct-2" / item["path"]
        if path.stat().st_size != item["bytes"] or sha256_file(path) != item["sha256"]:
            raise ValueError("OMI shard differs from the fixed C1 inventory")
        shard_counts = Counter()
        offset = 0
        for batch in pq.ParquetFile(path).iter_batches(batch_size=2048):
            mask = pc.is_in(batch.column("problem_source"), value_set=pa.array(["math", "gsm8k"]))
            indices = pc.indices_nonzero(mask).to_pylist()
            candidates = batch.filter(mask).to_pylist()
            inserts = []
            shard_counts["all_rows"] += batch.num_rows
            for row_index, row in zip(indices, candidates):
                task = row["problem_source"]
                shard_counts["original_" + task] += 1
                parent = lookup[task].get(normalized(row["problem"]))
                if parent is None:
                    shard_counts["outside_decontaminated_train_or_reserved"] += 1
                    continue
                solution, gold = row["generated_solution"], str(row["expected_answer"])
                if not answer_correct(last_boxed(solution), gold):
                    shard_counts["answer_rejected"] += 1
                    continue
                digest = hashlib.sha256(normalized(solution).encode()).hexdigest()
                inserts.append((parent, digest, solution, gold, item["path"], offset + row_index))
                shard_counts["correct_before_dedupe"] += 1
            before = db.total_changes
            db.executemany("INSERT OR IGNORE INTO solutions(parent,hash,solution,expected_answer,shard,source_row) VALUES(?,?,?,?,?,?)", inserts)
            shard_counts["unique_solutions"] += db.total_changes - before
            offset += batch.num_rows
        db.commit()
        counts.update(shard_counts)
        manifest["shards"].append(item | {"counts": dict(shard_counts)})
        write_json(output / "MANIFEST.json", manifest)
        print(json.dumps({"shard": item["path"], "counts": dict(shard_counts), "seconds": time.monotonic() - started}), flush=True)
    totals = {"counts": dict(counts), "by_task": {}, "seconds": time.monotonic() - started,
              "answer_cache": answer_correct.cache_info()._asdict(), "length_filter_complete": False}
    for task in tasks:
        distribution = Counter(n for _, n in db.execute(
            "SELECT p.id,count(s.hash) FROM parents p LEFT JOIN solutions s ON p.id=s.parent WHERE p.task=? GROUP BY p.id", (task,)))
        totals["by_task"][task] = {"distinct_solution_count_distribution_before_length_filter": dict(sorted(distribution.items())),
            "parents_with_at_least8_before_length_filter": sum(n for k, n in distribution.items() if k >= 8)}
    db.close()
    write_json(output / "COLLECTION_COMPLETE.json", totals)
    return totals


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--assets", type=Path, required=True)
    parser.add_argument("--manifests", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(collect(args.assets, args.manifests, args.output)))


if __name__ == "__main__":
    main()

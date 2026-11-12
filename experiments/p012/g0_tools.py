"""Freeze G0 inputs and check the first 20 requests without computing accuracy."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import replace
import hashlib
import json
from pathlib import Path

from .evaluation import EvalConfig, LLAMA_G0_DATE, prompt_text, render_prompt_tokens, sha256_file, stop_flags
from .scoring import jsonl_bytes, read_manifest


def prepare(assets: Path, metadata_path: Path, output: Path) -> dict:
    import pyarrow.parquet as pq

    metadata = {r["repo"]: r for r in json.loads(metadata_path.read_text())}
    sources = {}

    def source(repo: str, name: str) -> Path:
        path = assets / repo.replace("/", "__") / name
        item = next(f for f in metadata[repo]["files"] if f["path"] == name)
        payload = path.read_bytes()
        digest = hashlib.sha256(payload).hexdigest()
        if item.get("lfs"):
            assert digest == item["lfs"]["sha256"], "Source LFS hash mismatch"
        else:
            blob = hashlib.sha1(f"blob {len(payload)}\0".encode() + payload).hexdigest()
            assert blob == item["blob_id"], "Source Git blob mismatch"
        sources[repo] = {"revision": metadata[repo]["revision"], "file": name,
                         "sha256": digest, "bytes": len(payload)}
        return path

    math = [json.loads(s) for s in source("HuggingFaceH4/MATH-500", "test.jsonl").read_text().splitlines()]
    math_rows = [{"id": r["unique_id"], "problem": r["problem"], "gold": r["answer"],
                  "source_index": i} for i, r in enumerate(math)]
    gsm = pq.read_table(source("openai/gsm8k", "main/test-00000-of-00001.parquet")).to_pylist()
    # Keep the complete published answer: the accepted Li filter removes ####.
    gsm_rows = [{"id": f"gsm8k/test/{i:04d}", "problem": r["question"], "gold": r["answer"],
                 "source_index": i} for i, r in enumerate(gsm)]
    assert len(math_rows) == 500 and len(gsm_rows) == 1319
    outputs = {"math500.jsonl": math_rows, "math500_first20.jsonl": math_rows[:20],
               "gsm8k_test.jsonl": gsm_rows}
    output.mkdir(parents=True, exist_ok=False)
    manifest = {"sources": sources, "selection": "Original source order; first 20 for startup checks",
                "first20_role": "n=4 sampling diagnostic, not a reported benchmark endpoint",
                "files": {}}
    for name, rows in outputs.items():
        assert len({r["id"] for r in rows}) == len(rows)
        payload = jsonl_bytes(rows)
        (output / name).write_bytes(payload)
        manifest["files"][name] = {"rows": len(rows), "sha256": hashlib.sha256(payload).hexdigest(),
                                   "ordered_ids": [r["id"] for r in rows]}
    (output / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def check_startup(inputs: Path, generation: Path, tokenizer_path: Path) -> dict:
    from transformers import AutoTokenizer

    manifest, complete = read_manifest(generation)
    if manifest["input_sha256"] != sha256_file(inputs):
        raise ValueError("Startup input binding mismatch")
    config = EvalConfig(**manifest["config"])
    config.validate()
    if config.n != 4 or config.temperature <= 0:
        raise ValueError("S2 requires four sampled draws")
    rows = [json.loads(s) for s in inputs.read_text().splitlines()]
    raw = [json.loads(s) for s in (generation / "raw.jsonl").read_text().splitlines()]
    if len(rows) != 20 or complete["requests"] != 20 or complete["draws"] != 80:
        raise ValueError("Startup check requires exactly 20 questions and 80 draws")
    expected = {(r["id"], d) for r in rows for d in range(4)}
    observed = [(r["id"], r["draw"]) for r in raw]
    if len(observed) != 80 or len(set(observed)) != 80 or set(observed) != expected:
        raise ValueError("Missing, repeated or unexpected startup draws")

    tokenizer = AutoTokenizer.from_pretrained(tokenizer_path, local_files_only=True)
    if config.chat_template_file:
        tokenizer.chat_template = manifest["chat_template"]
    by_id = {r["id"]: r for r in rows}
    draws = defaultdict(list)
    counts = Counter()
    errors = defaultdict(list)
    for response in raw:
        key = [response["id"], response["draw"]]
        flags = stop_flags(response["token_ids"], set(manifest["stop_token_ids"]),
                           response["finish_reason"], response["stop_reason"], config.max_tokens)
        if any(response[k] != v for k, v in flags.items()):
            errors["S1_saved_flags"].append(key)
        categories = [k for k in ("stopped_on_terminator", "string_stop", "length_capped") if flags[k]]
        if len(categories) != 1:
            errors["S1_classification"].append(key)
        counts.update(categories)
        draws[response["id"]].append(tuple(response["token_ids"]))
        if any(response["text"].rstrip().endswith(t) for t in tokenizer.all_special_tokens if t):
            errors["S3_special_tail"].append(key)
        row = by_id[response["id"]]
        tokens = render_prompt_tokens(row, tokenizer, config)
        if tokens != response["prompt_token_ids"]:
            errors["S4_actual_prompt"].append(key)
        if config.apply_chat_template:
            messages = row.get("messages") or [{"role": "user", "content": prompt_text(row["problem"], config.protocol)}]
            kwargs = {"date_string": LLAMA_G0_DATE} if config.template_family == "llama3" else {}
            text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True, **kwargs)
            plain = render_prompt_tokens({"prompt": text}, tokenizer, replace(config, apply_chat_template=False))
            if plain != tokens:
                errors["S4_pre_rendered"].append(key)
    errors["S2_identical_four_draws"] = [identifier for identifier, outputs in draws.items() if len(set(outputs)) == 1]
    errors = {k: v for k, v in errors.items() if v}
    return {"passed": not errors, "questions": 20, "draws": 80, "counts": dict(counts),
            "unclassified_stop": len(errors.get("S1_classification", [])), "errors": errors,
            "input_sha256": sha256_file(inputs), "raw_sha256": complete["raw_sha256"],
            "generation_code_commit": manifest["code_commit"], "accuracy_computed": False,
            "S4_llama_BOS": "Explicit BOS assertion and four-tokenizer tests in review acceptance"}


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--assets", type=Path, required=True)
    p.add_argument("--metadata", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p = sub.add_parser("check")
    p.add_argument("--inputs", type=Path, required=True)
    p.add_argument("--generation", type=Path, required=True)
    p.add_argument("--tokenizer", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        result = prepare(args.assets, args.metadata, args.output)
        print(json.dumps({k: v["rows"] for k, v in result["files"].items()}))
    else:
        result = check_startup(args.inputs, args.generation, args.tokenizer)
        with args.output.open("x") as file:
            json.dump(result, file, indent=2)
            file.write("\n")
        print(json.dumps(result))
        if not result["passed"]:
            raise SystemExit(1)


if __name__ == "__main__":
    main()

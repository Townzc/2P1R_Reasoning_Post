"""Freeze C7 inputs/configurations and check every prompt on CPU, without models."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path

from .capability import capability_config, conversation_rows
from .evaluation import EvalConfig, execution_commit, render_prompt_tokens, sha256_file


def read_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.open() if line.strip()]


def write(path: Path, data) -> None:
    with path.open("x") as file:
        json.dump(data, file, indent=2)
        file.write("\n")


def prepare(frozen: Path, assets: Path, manifests: Path, math_test: Path, gsm_test: Path, output: Path) -> dict:
    from transformers import AutoTokenizer

    commit = execution_commit()
    output.mkdir(parents=True, exist_ok=False)
    accepted = json.loads((frozen / "MANIFEST.json").read_text())
    sources = {"frozen_manifest_sha256": sha256_file(frozen / "MANIFEST.json"),
               "math_test_sha256": sha256_file(math_test), "gsm_test_sha256": sha256_file(gsm_test)}
    math_rows = read_rows(math_test)
    gsm_rows = [{"id": r["id"], "problem": r["problem"], "gold": r["gold"].rsplit("####", 1)[-1].strip()}
                for r in read_rows(gsm_test)]
    if len(math_rows) != 500 or len(gsm_rows) != 1319:
        raise ValueError("C7 test baselines require MATH-500 and complete GSM8K")
    datasets = {}
    for task, tests in (("math", math_rows), ("gsm8k", gsm_rows)):
        task_dir = frozen / task
        for file in ("holdout500.jsonl", "nll1000.jsonl"):
            if sha256_file(task_dir / file) != accepted["tasks"][task]["files"][file]["sha256"]:
                raise ValueError("C6 data changed")
        if sha256_file(task_dir / "FOUR_SHOT_MESSAGES.json") != accepted["tasks"][task]["four_shot_messages_sha256"]:
            raise ValueError("C6 demonstrations changed")
        demos = json.loads((task_dir / "FOUR_SHOT_MESSAGES.json").read_text())
        holdout = read_rows(task_dir / "holdout500.jsonl")
        nll = read_rows(task_dir / "nll1000.jsonl")
        counts = Counter(row["parent_id"] for row in nll)
        if set(counts) != {r["id"] for r in holdout} or set(counts.values()) != {2}:
            raise ValueError("Frozen NLL solutions do not match the 500 held-out parents")
        for endpoint, base in (("holdout", holdout), ("baseline", tests)):
            for shots in (0, 4):
                rows = conversation_rows(base, demos, shots)
                filename = f"{task}_{endpoint}{shots}.jsonl"
                with (output / filename).open("x") as file:
                    for row in rows:
                        file.write(json.dumps(row, ensure_ascii=False) + "\n")
                datasets[(task, endpoint, shots)] = (filename, rows)
    models = []
    for name, family in (("Qwen__Qwen2.5-1.5B", "qwen"), ("Qwen__Qwen2.5-1.5B-Instruct", "qwen"),
                         ("meta-llama__Llama-3.2-1B", "llama3"), ("meta-llama__Llama-3.2-1B-Instruct", "llama3")):
        model = json.loads((manifests / (name + "_FILES.json")).read_text())
        model["family"] = family
        tokenizer = AutoTokenizer.from_pretrained(assets / name, local_files_only=True)
        template = Path(__file__).parent / "templates" / (family + ".jinja")
        tokenizer.chat_template = template.read_text()
        for task in ("math", "gsm8k"):
            endpoints = []
            for endpoint in ("holdout8", "baseline4", "baseline0"):
                shots = (0 if "Instruct" in model["repo"] else 4) if endpoint == "holdout8" else int(endpoint[-1])
                kind = "holdout" if endpoint == "holdout8" else "baseline"
                filename, rows = datasets[(task, kind, shots)]
                config = capability_config(model, task, endpoint, "/workspace/experiments/p012/templates/" + family + ".jinja")
                lengths = [len(render_prompt_tokens(row, tokenizer, EvalConfig(**config))) for row in rows]
                if max(lengths) + 4096 > 8192:
                    raise ValueError("A C7 prompt cannot fit its complete output allowance")
                endpoints.append({"endpoint": endpoint, "shots": shots, "file": filename,
                    "input_sha256": sha256_file(output / filename), "questions": len(rows),
                    "config": config, "maximum_prompt_tokens": max(lengths), "total_prompt_tokens": sum(lengths)})
            nll_path = frozen / task / "nll1000.jsonl"
            nll_rows = read_rows(nll_path)
            lengths = [r["training_tokens"][family] for r in nll_rows]
            models.append({"model": {k: model[k] for k in ("repo", "revision", "family")}, "task": task,
                "generation": endpoints, "nll": {"input_sha256": sha256_file(nll_path), "rows": 1000,
                    "shots": 0, "maximum_training_tokens": max(lengths), "total_training_tokens": sum(lengths),
                    "conditioning": "frozen OMI-2 training prefix; only response and terminator contribute loss"}})
    result = {"code_commit": commit, "sources": sources, "models": models,
              "source_sha256": sha256_file(Path(__file__)),
              "data_sha256": {p.name: sha256_file(p) for p in sorted(output.glob("*.jsonl"))},
              "all_contexts_fit": True, "model_calls": 0, "budget_subcap_usd": 4,
              "production_status": "Awaiting one C7 review and prospective budget admission; no GPU calls"}
    write(output / "MANIFEST.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    for name in ("frozen", "assets", "manifests", "math-test", "gsm-test", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    result = prepare(args.frozen, args.assets, args.manifests, args.math_test, args.gsm_test, args.output)
    print(json.dumps({"model_task_settings": len(result["models"]), "all_contexts_fit": True, "model_calls": 0}))


if __name__ == "__main__":
    main()

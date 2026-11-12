"""G0 base prompts and scores from the actual fixed lm-evaluation-harness.

Only dataset transport is overridden. The stock task, sampler, filters and
metrics run unchanged. This is separate from the main-grid Delta_SFT baseline.
"""
from __future__ import annotations

import argparse
import importlib.metadata
import json
from pathlib import Path
import unicodedata

from .evaluation import EvalConfig, execution_commit, render_prompt_tokens, sha256_file, stop_flags
from .scoring import jsonl_bytes, read_manifest
from .training_config import LI_COMMIT


def make_task(task_name: str, data: dict):
    import datasets
    import lm_eval
    from lm_eval.api.task import ConfigurableTask
    from lm_eval.utils import load_yaml_config

    if task_name == "math":
        config_path = Path(lm_eval.__file__).parent / "tasks/minerva_math/minerva_math_algebra.yaml"
    elif task_name == "gsm8k":
        config_path = Path(__file__).parent / "vendor/gsm8k_v048.yaml"
    else:
        raise ValueError(task_name)
    config = load_yaml_config(yaml_path=str(config_path))
    config["num_fewshot"] = 4

    class OfflineTask(ConfigurableTask):
        def download(self, dataset_kwargs=None):
            self.dataset = datasets.DatasetDict({k: datasets.Dataset.from_list(v) for k, v in data.items()})

    task = OfflineTask(config=config)
    task.set_fewshot_seed(1234)
    return task, config_path


def runtime_manifest() -> dict:
    import lm_eval.tasks.minerva_math.utils as math_utils
    origin = json.loads(importlib.metadata.distribution("lm_eval").read_text("direct_url.json"))
    if origin.get("vcs_info", {}).get("commit_id") != LI_COMMIT:
        raise ValueError("Wrong harness runtime revision")
    if importlib.metadata.version("antlr4-python3-runtime") != "4.11.0":
        raise ValueError("Use the isolated standard-harness math scoring environment")
    # A real reference-function check catches missing ANTLR and signal support.
    cases = math_utils.list_fewshot_samples()
    reference_scores = []
    for index, example in enumerate(cases):
        gold = math_utils.normalize_final_answer(math_utils.remove_boxed(
            math_utils.last_boxed_only_string(example["solution"])))
        result = math_utils.process_results({"answer": gold}, [example["solution"]])["exact_match"]
        reference_scores.append(result)
        # The stock SymPy scorer does not support every interval expression.
        # Record that behavior; do not silently replace the reference scorer.
        if index > 0:
            assert result == 1
    assert math_utils.process_results({"answer": "25"}, [cases[1]["solution"]])["exact_match"] == 0
    return {"code_commit": execution_commit(), "installed_harness_source": origin,
            "harness_math_utils_sha256": sha256_file(Path(math_utils.__file__)),
            "wrapper_sha256": sha256_file(Path(__file__)),
            "versions": {p: importlib.metadata.version(p) for p in
                         ("lm_eval", "antlr4-python3-runtime", "sympy", "transformers", "datasets")},
            "reference_example_scores": reference_scores,
            "three_numeric_reference_and_one_negative_checks_passed": True}


def validate_runtime(payload: dict, output: Path) -> dict:
    """Synthetic integration checks only; no benchmark preparation or model call."""
    from lm_eval.api.instance import Instance
    from transformers import AutoTokenizer
    manifest = runtime_manifest()
    math_doc = {"problem": "What is one plus one?", "solution": r"The answer is \boxed{2}."}
    gsm_doc = {"question": "A box has two balls. Add one ball. How many balls?", "answer": "Two plus one is three. #### 3"}
    checks = []
    for task_name, doc in (("math", math_doc), ("gsm8k", gsm_doc)):
        question_key = "problem" if task_name == "math" else "question"
        training = [doc | {question_key: f"Example {i}: " + doc[question_key]} for i in range(5)]
        task, _ = make_task(task_name, {"train": training, "test": [doc]})
        heldout = list(task.eval_docs)[0]
        state = task.sampler.rnd.getstate()
        prompt = task.fewshot_context(heldout, num_fewshot=4)
        assert prompt.count("Problem:" if task_name == "math" else "Question:") == 5
        task.sampler.rnd.setstate(state)
        changed = heldout | {"answer": "GOLD_SENTINEL", "solution": "GOLD_SENTINEL"}
        assert prompt == task.fewshot_context(changed, num_fewshot=4)
        if task_name == "gsm8k":
            for response, expected in (("Calculation. #### 3", 1), ("Calculation. #### 4", 0)):
                instance = Instance("generate_until", heldout, (), 0)
                instance.resps = [response]
                for filter_ in task._filters:
                    filter_.apply([instance])
                assert set(instance.filtered_resps) == {"strict-match", "flexible-extract"}
                for answer in instance.filtered_resps.values():
                    assert task.process_results(heldout, [answer])["exact_match"] == expected
        for model in payload["models"]:
            tokenizer = AutoTokenizer.from_pretrained(model["repo"], revision=model["revision"],
                cache_dir="/p012/hf", local_files_only=True)
            text = ("<|begin_of_text|>" if model["family"] == "llama3" else "") + prompt
            config = EvalConfig(model["repo"], model["revision"],
                "lm_eval_minerva4" if task_name == "math" else "lm_eval_gsm4", task_name,
                model["family"], apply_chat_template=False)
            config.validate()
            tokens = render_prompt_tokens({"prompt": text}, tokenizer, config)
            assert tokens == tokenizer.encode(text, add_special_tokens=False)
            if model["family"] == "llama3":
                assert tokens.count(tokenizer.bos_token_id) == 1 and tokens[0] == tokenizer.bos_token_id
            checks.append({"model": model, "task": task_name, "prompt_tokens": len(tokens),
                           "heldout_gold_invariance": True, "exact_token_parity": True})
    manifest.update(purpose="synthetic integration validation", benchmark_results=False, checks=checks)
    output.mkdir(parents=True, exist_ok=False)
    (output / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def prepare(payload: dict, output: Path) -> dict:
    from transformers import AutoTokenizer
    manifest = runtime_manifest()
    output.mkdir(parents=True, exist_ok=False)
    normalize = lambda text: unicodedata.normalize("NFKC", text).strip()
    subset = {normalize(r["problem"]): r["id"] for r in payload["math500"]}
    if len(subset) != 500:
        raise ValueError("MATH-500 questions must be distinct")
    manifest.update(data_sources=payload["sources"], fewshot=4, fewshot_seed=1234, files={})
    for task_name in ("math", "gsm8k"):
        task, config_path = make_task(task_name, payload[task_name])
        docs = list(task.eval_docs)
        expected = 5000 if task_name == "math" else 1319
        if len(docs) != expected:
            raise ValueError("Wrong complete test split size")
        # Keep the sampler state unchanged by this gold-leakage check.
        state = task.sampler.rnd.getstate()
        first = task.fewshot_context(docs[0], num_fewshot=4)
        task.sampler.rnd.setstate(state)
        changed_gold = docs[0] | {"answer": "HELDOUT_GOLD_SENTINEL", "solution": "HELDOUT_GOLD_SENTINEL"}
        assert first == task.fewshot_context(changed_gold, num_fewshot=4)
        task.sampler.rnd.setstate(state)
        common = []
        for index, doc in enumerate(docs):
            problem = doc["problem"] if task_name == "math" else doc["question"]
            common.append({"id": f"{task_name}/test/{index:04d}", "problem": problem,
                "gold": doc["answer"], "harness_doc": doc,
                "math500_id": subset.get(normalize(problem)) if task_name == "math" else None,
                "prompt": task.fewshot_context(doc, num_fewshot=4)})
        if task_name == "math" and len({r["math500_id"] for r in common if r["math500_id"]}) != 500:
            raise ValueError("Complete MATH test does not contain all500 frozen subset questions")
        for model in payload["models"]:
            family = model["family"]
            tokenizer = AutoTokenizer.from_pretrained(model["repo"], revision=model["revision"],
                cache_dir="/p012/hf", local_files_only=True)
            rows = [r | {"prompt": ("<|begin_of_text|>" if family == "llama3" else "") + r["prompt"]}
                    for r in common]
            config = EvalConfig(model["repo"], model["revision"],
                "lm_eval_minerva4" if task_name == "math" else "lm_eval_gsm4", task_name,
                family, apply_chat_template=False, stop_strings=tuple(task.config.generation_kwargs["until"]))
            config.validate()
            lengths = [len(render_prompt_tokens(row, tokenizer, config)) for row in rows]
            if max(lengths) + config.max_tokens > config.max_model_len:
                raise ValueError("The frozen context budget would truncate a base prompt")
            if family == "llama3":
                assert all(tokenizer.encode(r["prompt"], add_special_tokens=False).count(tokenizer.bos_token_id) == 1
                           for r in rows)
            name = f"{family}_{task_name}.jsonl"
            (output / name).write_bytes(jsonl_bytes(rows))
            (output / f"{family}_{task_name}_first20.jsonl").write_bytes(jsonl_bytes(rows[:20]))
            manifest["files"][name] = {"rows": len(rows), "sha256": sha256_file(output / name),
                "max_prompt_tokens": max(lengths), "task_config_sha256": sha256_file(config_path),
                "heldout_gold_invariance_passed": True, "model": model,
                "generation_config": config.__dict__}
    (output / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def score(inputs: Path, generation: Path, output: Path) -> dict:
    from lm_eval.api.instance import Instance
    from lm_eval.tasks.minerva_math import utils as math_utils
    manifest = runtime_manifest()
    parent, complete = read_manifest(generation)
    if sha256_file(inputs) != parent["input_sha256"]:
        raise ValueError("Generation input hash mismatch")
    config = EvalConfig(**parent["config"])
    expected_protocol = "lm_eval_minerva4" if config.task == "math" else "lm_eval_gsm4"
    if config.protocol != expected_protocol or config.n != 1 or config.temperature != 0:
        raise ValueError("Not the frozen greedy base protocol")
    rows = [json.loads(line) for line in inputs.read_text().splitlines()]
    by_id = {r["id"]: r for r in rows}
    if len(by_id) != len(rows):
        raise ValueError("Duplicate input IDs")
    task, config_path = make_task(config.task, {"train": [rows[0]["harness_doc"]],
                                               "test": [r["harness_doc"] for r in rows]})
    seen, labels = set(), []
    counts = {"stopped_on_terminator": 0, "length_capped": 0, "string_stop": 0, "completion_tokens": 0}
    for line in (generation / "raw.jsonl").open():
        raw = json.loads(line)
        if raw["id"] not in by_id or raw["id"] in seen or raw["draw"] != 0:
            raise ValueError("Unexpected or duplicate base output")
        seen.add(raw["id"])
        row = by_id[raw["id"]]
        flags = stop_flags(raw["token_ids"], set(parent["stop_token_ids"]), raw["finish_reason"],
                           raw["stop_reason"], config.max_tokens)
        if any(flags[k] != raw[k] for k in flags) or sum(flags[k] for k in counts if k != "completion_tokens") != 1:
            raise ValueError("Invalid stop classification")
        for key in counts:
            counts[key] += len(raw["token_ids"]) if key == "completion_tokens" else int(flags[key])
        if config.task == "math":
            metrics = {"minerva_exact": int(task.process_results(row["harness_doc"], [raw["text"]])["exact_match"])}
            extracted = math_utils.get_unnormalized_answer(raw["text"])
        else:
            instance = Instance(request_type="generate_until", doc=row["harness_doc"], arguments=(),
                                idx=0, metadata=("gsm8k", raw["id"], 1))
            instance.resps = [raw["text"]]
            for filter_ in task._filters:
                filter_.apply([instance])
            metrics = {name: int(task.process_results(row["harness_doc"], [answer])["exact_match"])
                       for name, answer in instance.filtered_resps.items()}
            extracted = instance.filtered_resps
        labels.append({"id": raw["id"], "draw": 0, "math500_id": row["math500_id"],
                       "extracted": extracted, "metrics": metrics})
    if seen != set(by_id) or complete["draws"] != len(rows) or complete["requests"] != len(rows):
        raise ValueError("Incomplete base output set")
    primary = "minerva_exact" if config.task == "math" else "flexible-extract"
    metrics = {key: sum(r["metrics"][key] for r in labels) / len(labels) for key in labels[0]["metrics"]}
    subset = [r for r in labels if r["math500_id"]]
    summary = {"questions": len(rows), "protocol": config.protocol, "primary_metric": primary,
               "accuracy": metrics[primary], "metrics": metrics, "counts": counts,
               "math500_subset_questions": len(subset),
               "math500_subset_accuracy": sum(r["metrics"][primary] for r in subset) / len(subset) if subset else None,
               "official_numeric_gate_applied": False, "LLM_judge_used": False}
    output.mkdir(parents=True, exist_ok=False)
    (output / "labels.jsonl").write_bytes(jsonl_bytes(labels))
    (output / "SUMMARY.json").write_text(json.dumps(summary, indent=2) + "\n")
    manifest.update(input_sha256=sha256_file(inputs), raw_sha256=complete["raw_sha256"],
        generation_manifest_sha256=sha256_file(generation / "MANIFEST.json"),
        task_config_sha256=sha256_file(config_path), labels_sha256=sha256_file(output / "labels.jsonl"))
    (output / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", choices=["validate", "prepare", "score"])
    parser.add_argument("--payload", type=Path)
    parser.add_argument("--inputs", type=Path)
    parser.add_argument("--generation", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.operation == "score":
        result = score(args.inputs, args.generation, args.output)
    else:
        fn = prepare if args.operation == "prepare" else validate_runtime
        result = fn(json.loads(args.payload.read_text()), args.output)
    print(json.dumps(result if args.operation != "prepare" else {"prepared_files": list(result["files"])}))


if __name__ == "__main__":
    main()

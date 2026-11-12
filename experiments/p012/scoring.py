"""Score saved generations; preserve Li exact/judge and OMI-2 metrics separately.

Inputs are JSONL with id, problem, gold. No model is called by this module.
The optional judge directory comes from evaluation.py on judge_inputs.jsonl.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import re

from .evaluation import execution_commit, extract_answer, gsm_numeric_scores, score_answer, sha256_file
from .judge_collection import judge_id
from .vendor.li_math import is_equiv

JUDGE_MODEL = "Qwen/Qwen2.5-32B-Instruct"
LI_MATH = {"li_plan", "li_release_math500", "li_release_math"}


def jsonl_bytes(rows: list[dict]) -> bytes:
    return "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows).encode()


def judge_prompt(problem: str, answer: str, gold: str) -> str:
    # Literal prompt from the pinned math_metric_llm_eval_general.py.
    prompt = (
        "Given a math problem, its correct answer, and the model's generated answer, "
        "determine if the model's generated answer is correct. Respond with 'True' if the answer is correct and "
        "'False' if it is incorrect. Directly provide your judgement 'True' or 'False' without any other description.\n"
        f"Problem: {problem}\nCorrect Answer: {gold}\nModel's Generated Answer: {answer}\nYour judgement:"
    )
    return (
        "<|im_start|>system\nYou are Qwen, created by Alibaba Cloud. You are a helpful assistant.<|im_end|>\n"
        f"<|im_start|>user\n{prompt}<|im_end|>\n<|im_start|>assistant\n"
    )


def judge_decision(text: str) -> bool | None:
    # Preserve the release's case-sensitive substring rule, including priority.
    if "True" in text:
        return True
    if "False" in text:
        return False
    return None


def gsm_release_equal(answer: str | None, gold: str) -> bool:
    if answer is None:
        return False
    def clean(value: str) -> str:
        for pattern in (",", r"\$", r"(?s).*#### ", r"\.$"):
            value = re.sub(pattern, "", value)
        return value.lower()
    return clean(answer) == clean(gold)


def label_response(text: str, gold: str, protocol: str, task: str) -> dict:
    answer = extract_answer(text, protocol)
    needs_judge = False
    if protocol == "omi2" and task == "gsm8k":
        return {"answer": answer, **gsm_numeric_scores(answer, gold),
                "metric": "numeric_equality_then_math_verify", "needs_judge": False}
    if protocol in LI_MATH:
        correct = answer is not None and is_equiv(answer, gold)
        metric = "li_normalized_exact"
        needs_judge = answer is not None and not correct
    elif protocol == "li_release_gsm":
        correct = gsm_release_equal(answer, gold)
        metric = "li_gsm_flexible_extract"
    elif protocol == "omi2":
        correct = score_answer(answer, gold, task)
        metric = "math_verify" if task == "math" else "numeric_equality"
    else:
        raise ValueError("Unknown scoring contract")
    return {"answer": answer, "format_compliant": answer is not None,
            "correct": bool(correct), "metric": metric, "needs_judge": needs_judge}


def read_manifest(directory: Path) -> tuple[dict, dict]:
    manifest = json.loads((directory / "MANIFEST.json").read_text())
    complete = json.loads((directory / "GENERATION_COMPLETE.json").read_text())
    if sha256_file(directory / "raw.jsonl") != complete["raw_sha256"]:
        raise ValueError("Raw generation hash mismatch")
    return manifest, complete


def score_generation(input_path: Path, generation_dir: Path, output_dir: Path,
                     judge_dir: Path | None = None, judge_inputs_path: Path | None = None,
                     judge_group: str | None = None) -> dict:
    if (judge_inputs_path is None) != (judge_group is None) or (judge_group is not None and judge_dir is None):
        raise ValueError("A grouped judge needs the generation directory, combined inputs, and cell name")
    code_commit = execution_commit()
    manifest, complete = read_manifest(generation_dir)
    if sha256_file(input_path) != manifest["input_sha256"]:
        raise ValueError("Input hash mismatch")
    inputs = [json.loads(x) for x in input_path.read_text().splitlines() if x.strip()]
    by_id = {r["id"]: r for r in inputs}
    if not inputs or len(by_id) != len(inputs):
        raise ValueError("Input IDs must be unique and nonempty")
    if any(not isinstance(r["gold"], str) or not r["gold"].strip() for r in inputs):
        raise ValueError("Each input needs an explicit gold answer")
    config = manifest["config"]
    n, protocol, task = config["n"], config["protocol"], config["task"]
    expected = {(r["id"], draw) for r in inputs for draw in range(n)}
    seen, labels, judge_inputs = set(), [], []
    stats = {"stopped_on_terminator": 0, "length_capped": 0, "string_stop": 0,
             "unclassified_stop": 0, "completion_tokens": 0, "prompt_tokens_per_response_sum": 0}
    with (generation_dir / "raw.jsonl").open() as raw_file:
        for line in raw_file:
            raw = json.loads(line)
            key = (raw["id"], raw["draw"])
            if key not in expected or key in seen:
                raise ValueError("Duplicate or unexpected response")
            seen.add(key)
            original = by_id[raw["id"]]
            label = label_response(raw["text"], original["gold"], protocol, task)
            label.update({"id": raw["id"], "draw": raw["draw"]})
            labels.append(label)
            for stat in ("stopped_on_terminator", "length_capped", "string_stop"):
                stats[stat] += int(raw[stat])
            stats["unclassified_stop"] += int(raw["finish_reason"] == "stop" and
                                             not raw["stopped_on_terminator"] and not raw["string_stop"])
            stats["completion_tokens"] += len(raw["token_ids"])
            stats["prompt_tokens_per_response_sum"] += len(raw["prompt_token_ids"])
            if label["needs_judge"]:
                judge_inputs.append({"id": json.dumps(key, separators=(",", ":")),
                    "problem": original["problem"],
                    "prompt": judge_prompt(original["problem"], label["answer"], original["gold"])})
    if seen != expected or complete["requests"] != len(inputs) or complete["draws"] != len(expected):
        raise ValueError("Incomplete response set")
    judge_payload = jsonl_bytes(judge_inputs)
    judged = {}
    if judge_dir is not None:
        jm, jc = read_manifest(judge_dir)
        cfg = jm["config"]
        required = {"protocol": "li_judge", "model": JUDGE_MODEL, "dtype": "float16",
                    "max_tokens": 20, "temperature": 0, "top_p": 1, "top_k": 1,
                    "n": 1, "apply_chat_template": False}
        if any(cfg.get(k) != v for k, v in required.items()):
            raise ValueError("Judge configuration differs from the frozen release contract")
        original_to_combined = {r["id"]: r["id"] for r in judge_inputs}
        expected_judge_ids = set(original_to_combined)
        if judge_inputs_path is None:
            if jm["input_sha256"] != hashlib.sha256(judge_payload).hexdigest():
                raise ValueError("Judge input hash mismatch")
        else:
            if jm["input_sha256"] != sha256_file(judge_inputs_path):
                raise ValueError("Combined judge input hash mismatch")
            collection = [json.loads(line) for line in judge_inputs_path.read_text().splitlines() if line.strip()]
            by_combined_id = {r["id"]: r for r in collection}
            if len(by_combined_id) != len(collection):
                raise ValueError("Duplicate combined judge input ID")
            expected_judge_ids = set(by_combined_id)
            original_to_combined = {r["id"]: judge_id(judge_group, r["id"]) for r in judge_inputs}
            actual_group_ids = {id_ for id_ in expected_judge_ids if json.loads(id_)[0] == judge_group}
            if actual_group_ids != set(original_to_combined.values()):
                raise ValueError("Combined judge group has missing or extra rows")
            for row in judge_inputs:
                combined_id = original_to_combined[row["id"]]
                if by_combined_id[combined_id] != (row | {"id": combined_id}):
                    raise ValueError("Combined judge prompt differs from the original score queue")
        all_judged = {}
        for line in (judge_dir / "raw.jsonl").read_text().splitlines():
            row = json.loads(line)
            if row["draw"] != 0 or row["id"] in all_judged:
                raise ValueError("Duplicate judge response")
            all_judged[row["id"]] = judge_decision(row["text"])
        if set(all_judged) != expected_judge_ids or jc["draws"] != len(expected_judge_ids):
            raise ValueError("Incomplete judge response set")
        judged = {original_id: all_judged[combined_id] for original_id, combined_id in original_to_combined.items()}
    judge_complete = not judge_inputs or judge_dir is not None
    for label in labels:
        key = json.dumps((label["id"], label["draw"]), separators=(",", ":"))
        label["judge_applied"] = key in judged
        label["judge_decision"] = judged.get(key)
        if protocol in LI_MATH:
            label["correct_with_judge"] = (
                judged[key] is True if key in judged else
                None if label["needs_judge"] else label["correct"])
    count = len(labels)
    summary = {"questions": len(inputs), "responses": count, "draws_per_question": n,
               "protocol": protocol, "task": task, "metric": labels[0]["metric"],
               "accuracy": sum(r["correct"] for r in labels) / count,
               "format_compliance": sum(r["format_compliant"] for r in labels) / count,
               "terminator_stop_rate": stats["stopped_on_terminator"] / count,
               "length_cap_rate": stats["length_capped"] / count,
               "mean_completion_tokens": stats["completion_tokens"] / count,
               "counts": stats, "judge_requests": len(judge_inputs)}
    if protocol in LI_MATH:
        summary.update({"judge_complete": judge_complete,
            "judge_unparsed": sum(value is None for value in judged.values()),
            "accuracy_with_judge": sum(r["correct_with_judge"] is True for r in labels) / count
                if judge_complete else None})
    if protocol == "omi2" and task == "gsm8k":
        strict_correct = sum(r["strict_numeric_correct"] for r in labels)
        fallback_correct = sum(r["score_path"] == "math_verify_fallback" for r in labels)
        summary.update({"accuracy_strict_numeric": strict_correct / count,
            "accuracy_with_math_verify_fallback": summary["accuracy"],
            "fallback_gain_pp": 100 * fallback_correct / count,
            "correct_by_path": {"strict_numeric": strict_correct, "math_verify_fallback": fallback_correct},
            "fallback_evaluations": sum(r["math_verify_fallback_used"] for r in labels)})
    output_dir.mkdir(parents=True, exist_ok=False)
    (output_dir / "labels.jsonl").write_bytes(jsonl_bytes(labels))
    (output_dir / "judge_inputs.jsonl").write_bytes(judge_payload)
    (output_dir / "SUMMARY.json").write_text(json.dumps(summary, indent=2) + "\n")
    (output_dir / "MANIFEST.json").write_text(json.dumps({
        "code_commit": code_commit,
        "math_verify_version": importlib.metadata.version("math-verify"),
        "input_sha256": sha256_file(input_path),
        "raw_sha256": complete["raw_sha256"],
        "generation_manifest_sha256": sha256_file(generation_dir / "MANIFEST.json"),
        "scorer_sha256": sha256_file(Path(__file__)),
        "extraction_sha256": sha256_file(Path(__file__).with_name("evaluation.py")),
        "li_normalization_sha256": sha256_file(Path(__file__).parent / "vendor/li_math.py"),
        "judge_raw_sha256": sha256_file(judge_dir / "raw.jsonl") if judge_dir else None,
        "judge_collection_input_sha256": sha256_file(judge_inputs_path) if judge_inputs_path else None,
        "judge_group": judge_group,
        "labels_sha256": sha256_file(output_dir / "labels.jsonl"),
        "judge_inputs_sha256": hashlib.sha256(judge_payload).hexdigest(),
    }, indent=2) + "\n")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    for name in ("inputs", "generation", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--judge", type=Path)
    parser.add_argument("--judge-inputs", type=Path)
    parser.add_argument("--judge-group")
    a = parser.parse_args()
    print(json.dumps(score_generation(a.inputs, a.generation, a.output, a.judge, a.judge_inputs, a.judge_group)))


if __name__ == "__main__":
    main()

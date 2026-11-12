"""C7 review candidate: teacher forcing using the pinned model's standard loss.

Zero-shot OMI training prefix for every initialization. Prompt labels are -100;
all teacher response tokens, including the template terminator, are scored.
No optimization, padding, packing, truncation or generation occurs.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import re
import time

from .evaluation import prompt_text, sha256_file
from .data_pool import normalized
from .training_config import LI_COMMIT


def validate_nll_request(request: dict) -> list[dict]:
    if not re.fullmatch(r"[a-z0-9_]+", request["run_id"]) or not re.fullmatch(r"[a-f0-9]{40}", request["code_commit"]):
        raise ValueError("Pin source and unique run ID")
    model = request["model"]
    allowed = {"Qwen/Qwen2.5-1.5B": "qwen", "Qwen/Qwen2.5-1.5B-Instruct": "qwen",
               "meta-llama/Llama-3.2-1B": "llama3", "meta-llama/Llama-3.2-1B-Instruct": "llama3"}
    if allowed.get(model["repo"]) != model["family"] or not re.fullmatch(r"[a-f0-9]{40}", model["revision"]):
        raise ValueError("Use a pinned, untrained main-grid initialization")
    if not model["files"] or not any(f["path"].endswith(".safetensors") for f in model["files"]):
        raise ValueError("Bind C1 weights")
    dataset = request["dataset"]
    if hashlib.sha256(dataset["jsonl"].encode()).hexdigest() != dataset["sha256"]:
        raise ValueError("NLL input hash mismatch")
    rows = [json.loads(line) for line in dataset["jsonl"].split("\n") if line.strip()]
    counts = Counter(row["parent_id"] for row in rows)
    if len(rows) != 1000 or len(counts) != 500 or set(counts.values()) != {2}:
        raise ValueError("Use two frozen solutions for each of 500 held-out parents")
    if set(counts) != set(request["holdout_parent_ids"]) or len(request["holdout_parent_ids"]) != 500:
        raise ValueError("NLL parents differ from the frozen holdout")
    if len({(r["parent_id"], r["solution_hash"]) for r in rows}) != 1000:
        raise ValueError("Repeated teacher solution")
    for row in rows:
        if row["task"] != request["task"] or row["problem"] != prompt_text(row["raw_problem"], "omi2"):
            raise ValueError("Use the frozen task and zero-shot training prefix")
        if hashlib.sha256(normalized(row["solution"]).encode()).hexdigest() != row["solution_hash"]:
            raise ValueError("Teacher text differs from its frozen hash")
    if not request["forecast"].get("admitted"):
        raise ValueError("Admit the run within the capability budget before loading a model")
    return rows


def validate_encoded(source: list[int], target: list[int], ids: list[int], labels: list[int]) -> int:
    if not source or not target or len(source) + len(target) > 4096:
        raise ValueError("Empty or overlength NLL sequence; never truncate")
    if ids != source + target or labels != [-100] * len(source) + target:
        raise ValueError("Pinned preprocessing changed prompt masking or teacher tokenization")
    # AutoModelForCausalLM shifts labels by one internally. The first position
    # is a masked prompt token, so every target token remains in the loss.
    count = sum(token != -100 for token in labels[1:])
    if count != len(target):
        raise ValueError("Response token count disagrees with causal loss shift")
    return count


def aggregate_nll(records: list[dict]) -> dict:
    if not records or len({(r["parent_id"], r["solution_hash"]) for r in records}) != len(records):
        raise ValueError("Empty or duplicate NLL records")
    if any(r["target_tokens"] <= 0 or not math.isfinite(r["nll_sum"]) or r["nll_sum"] < 0 for r in records):
        raise ValueError("Invalid teacher-forcing loss")
    count = sum(r["target_tokens"] for r in records)
    total = math.fsum(r["nll_sum"] for r in records)
    return {"solutions": len(records), "target_tokens": count, "nll_sum": total,
            "mean_per_token_nll": total / count,
            "mean_per_solution_nll": math.fsum(r["nll_sum"] / r["target_tokens"] for r in records) / len(records),
            "primary_metric": "mean_per_token_nll", "units": "nats",
            "prompt_tokens_scored": 0, "template_terminator_scored": True,
            "conditioning": "zero-shot OMI-2 training prefix for both base and Instruct",
            "cross_family_interpretation": "Per-token NLL uses each family's tokenizer; token units differ across families."}


def run_nll(request: dict, output: Path, snapshot: Path) -> dict:
    rows = validate_nll_request(request)
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from llamafactory.data.processor.supervised import SupervisedDatasetProcessor
    from llamafactory.data.template import get_template_and_fix_tokenizer
    from llamafactory.hparams import DataArguments

    started = time.monotonic()
    origin = json.loads(importlib.metadata.distribution("llamafactory").read_text("direct_url.json"))
    if origin.get("vcs_info", {}).get("commit_id") != LI_COMMIT:
        raise ValueError("NLL preprocessing must use the fixed LLaMA-Factory release")
    spec = request["model"]
    tokenizer = AutoTokenizer.from_pretrained(snapshot, local_files_only=True)
    args = DataArguments(template=spec["family"], cutoff_len=4096, packing=False, train_on_prompt=False)
    template = get_template_and_fix_tokenizer(tokenizer, args)
    template_file = Path(__file__).parent / "templates" / (spec["family"] + ".jinja")
    if template.efficient_eos or template._get_jinja_template(tokenizer) != template_file.read_text():
        raise ValueError("NLL template differs from the frozen training template")
    processor = SupervisedDatasetProcessor(template, tokenizer, None, args)
    encoded = []
    for row in rows:
        user = {"role": "user", "content": row["problem"]}
        assistant = {"role": "assistant", "content": row["solution"]}
        source, target = template.encode_oneturn(tokenizer, [user, assistant])
        example = {"_prompt": [[user]], "_response": [[assistant]], "_system": [""], "_tools": [""],
                   "_images": [None], "_videos": [None], "_audios": [None]}
        processed = processor.preprocess_dataset(example)
        ids, labels = processed["input_ids"][0], processed["labels"][0]
        count = validate_encoded(source, target, ids, labels)
        if len(ids) != row["training_tokens"][spec["family"]]:
            raise ValueError("NLL token count differs from accepted C6")
        encoded.append((ids, labels, count))
    output.mkdir(parents=True, exist_ok=False)
    torch.manual_seed(17)
    model = AutoModelForCausalLM.from_pretrained(snapshot, torch_dtype=torch.bfloat16,
        attn_implementation="flash_attention_2", local_files_only=True, trust_remote_code=False).to("cuda").eval()
    model.config.use_cache = False
    records = []
    with (output / "raw_nll.jsonl").open("x") as file, torch.inference_mode():
        for row, (ids, labels, count) in zip(rows, encoded, strict=True):
            input_ids = torch.tensor([ids], dtype=torch.long, device="cuda")
            label_tensor = torch.tensor([labels], dtype=torch.long, device="cuda")
            loss = model(input_ids=input_ids, attention_mask=torch.ones_like(input_ids), labels=label_tensor,
                         use_cache=False).loss.float().item()
            if not math.isfinite(loss) or loss < 0:
                raise ValueError("Nonfinite teacher-forcing loss")
            record = {"parent_id": row["parent_id"], "solution_hash": row["solution_hash"],
                      "input_tokens": len(ids), "target_tokens": count, "nll_sum": loss * count,
                      "mean_token_nll": loss,
                      "input_ids_sha256": hashlib.sha256(json.dumps(ids).encode()).hexdigest(),
                      "labels_sha256": hashlib.sha256(json.dumps(labels).encode()).hexdigest()}
            records.append(record)
            file.write(json.dumps(record) + "\n")
            file.flush()
            if len(records) % 100 == 0:
                print(json.dumps({"completed": len(records), "total": 1000}), flush=True)
    result = aggregate_nll(records)
    result.update(elapsed_seconds=time.monotonic() - started, model=spec["repo"], revision=spec["revision"],
                  raw_sha256=sha256_file(output / "raw_nll.jsonl"), input_sha256=request["dataset"]["sha256"],
                  template_sha256=sha256_file(template_file), code_commit=request["code_commit"],
                  versions={p: importlib.metadata.version(p) for p in ("torch", "transformers", "llamafactory")})
    (output / "SUMMARY.json").write_text(json.dumps(result, indent=2) + "\n")
    return result

"""Validate an already frozen training payload; never sample or filter its rows."""
from __future__ import annotations

import hashlib
import json
import re


def validate_training_request(request: dict) -> dict:
    if not re.fullmatch(r"[a-z0-9_]+", request["run_id"]):
        raise ValueError("Invalid run ID")
    if not re.fullmatch(r"[a-f0-9]{40}", request["code_commit"]):
        raise ValueError("Missing execution source commit")
    config, dataset, model = request["config"], request["dataset"], request["model"]
    if not re.fullmatch(r"[a-z0-9_]+", dataset["name"]):
        raise ValueError("Invalid dataset name")
    if config["dataset"] != dataset["name"]:
        raise ValueError("Dataset name differs from the frozen training config")
    if (config["model_name_or_path"], config["model_revision"]) != (model["repo"], model["revision"]):
        raise ValueError("Model differs from the frozen asset manifest")
    if not re.fullmatch(r"[a-f0-9]{40}", model["revision"]):
        raise ValueError("Pin the upstream model revision")
    if not model["files"] or not any(f["path"].endswith(".safetensors") for f in model["files"]):
        raise ValueError("Bind the model weights as well as tokenizer files")
    if config["finetuning_type"] != "full" or config["packing"] or config["train_on_prompt"]:
        raise ValueError("P012 requires full SFT without packing or prompt loss")
    if config["template"] not in {"qwen", "llama3"}:
        raise ValueError("Use the registered training-family template")
    if config["per_device_train_batch_size"] * config["gradient_accumulation_steps"] != 8:
        raise ValueError("Effective single-GPU batch must be eight")
    payload = dataset["jsonl"].encode()
    if hashlib.sha256(payload).hexdigest() != dataset["sha256"]:
        raise ValueError("Training data hash mismatch")
    rows = [json.loads(line) for line in payload.splitlines() if line.strip()]
    if not rows or len(rows) != dataset["rows"]:
        raise ValueError("Training row count mismatch")
    if any(not isinstance(row.get(key), str) or not row[key].strip()
           for row in rows for key in ("problem", "solution")):
        raise ValueError("Every training row must contain problem and solution text")
    if not request["forecast"].get("admitted"):
        raise ValueError("A prospective admitted budget forecast is required")
    return {"rows": len(rows), "sha256": dataset["sha256"], "bytes": len(payload)}

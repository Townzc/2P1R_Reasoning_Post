"""Validate an already frozen training payload; never sample or filter its rows."""
from __future__ import annotations

import hashlib
import json
import re

from .training_config import CELLS, LI_COMMIT, training_config


def validate_training_request(request: dict) -> dict:
    if not re.fullmatch(r"[a-z0-9_]+", request["run_id"]):
        raise ValueError("Invalid run ID")
    if not re.fullmatch(r"[a-f0-9]{40}", request["code_commit"]):
        raise ValueError("Missing execution source commit")
    config, dataset, model = request["config"], request["dataset"], request["model"]
    if "cell" not in request or request["cell"] not in (None, *CELLS):
        raise ValueError("Declare the registered cell, or null for reproduction")
    cell = request["cell"]
    long_cot = request.get("long_cot", False)
    if not isinstance(long_cot, bool) or (cell is not None and long_cot):
        raise ValueError("Long CoT is a reproduction-only configuration")
    if config["seed"] not in ((17, 29) if cell else (42,)):
        raise ValueError("Use the registered main-grid or reproduction seed")
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
    if config["template"] != model["family"]:
        raise ValueError("Training template differs from the frozen model family")
    effective_batch = 8 if cell or long_cot else 16
    if config["per_device_train_batch_size"] * config["gradient_accumulation_steps"] != effective_batch:
        raise ValueError("Effective batch must match the registered phase: " + str(effective_batch))
    payload = dataset["jsonl"].encode()
    if hashlib.sha256(payload).hexdigest() != dataset["sha256"]:
        raise ValueError("Training data hash mismatch")
    rows = [json.loads(line) for line in payload.splitlines() if line.strip()]
    if not rows or len(rows) != dataset["rows"]:
        raise ValueError("Training row count mismatch")
    if any(not isinstance(row.get(key), str) or not row[key].strip()
           for row in rows for key in ("problem", "solution")):
        raise ValueError("Every training row must contain problem and solution text")
    if cell is not None and len(rows) != CELLS[cell][0] * CELLS[cell][1]:
        raise ValueError("Training row count differs from the registered P times K dose")
    expected = training_config(model["repo"], model["revision"], model["family"], dataset["name"],
        config["dataset_dir"], config["output_dir"], seed=config["seed"], cell=cell, long_cot=long_cot)
    if long_cot and config["per_device_train_batch_size"] == 1:
        # The owner explicitly approved this memory fallback for R3 only.
        expected.update(per_device_train_batch_size=1, gradient_accumulation_steps=8)
    differences = sorted(k for k in config.keys() | expected.keys() if config.get(k) != expected.get(k)
                         or (k in config) != (k in expected))
    if differences:
        raise ValueError("Training config differs from the frozen recipe: " + ", ".join(differences))
    report = request["length_report"]
    for key, value in {"dataset_sha256": dataset["sha256"], "rows": len(rows),
                       "model": model["repo"], "revision": model["revision"],
                       "cutoff_len": config["cutoff_len"], "llamafactory_commit": LI_COMMIT}.items():
        if report.get(key) != value:
            raise ValueError("Full-template length report differs: " + key)
    if not re.fullmatch(r"[a-f0-9]{64}", report.get("preflight_sha256", "")):
        raise ValueError("Bind the real preprocessing evidence")
    if cell and (report["over_cutoff_rows"] != 0 or report["maximum_full_tokens"] > config["cutoff_len"]):
        raise ValueError("Main-grid data must fit without silent truncation")
    if not request["forecast"].get("admitted"):
        raise ValueError("A prospective admitted budget forecast is required")
    return {"rows": len(rows), "sha256": dataset["sha256"], "bytes": len(payload),
            "cell": cell, "config_matches_registered_recipe": True,
            "over_cutoff_rows": report["over_cutoff_rows"]}

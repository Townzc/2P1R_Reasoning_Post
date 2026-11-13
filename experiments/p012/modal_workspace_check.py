"""Owner-required second-workspace parity check; no training or generation."""
import importlib.metadata
import json
from pathlib import Path
import subprocess
import time

import modal

from .modal_g0 import digest, image as evaluation_image, volume
from .modal_training_runtime import training_image

app = modal.App("p012-second-workspace-parity-20261113")


def check_definition(payload, environment):
    for name, expected in payload["source_sha256"].items():
        if digest(Path(__file__).parent / name) != expected:
            raise ValueError("Pinned image/source definition changed: " + name)
    versions = {name: importlib.metadata.version(name) for name in payload[environment + "_versions"]}
    if versions != payload[environment + "_versions"]:
        raise ValueError("STOP: workspace installed dependencies differ")
    return versions


@app.function(image=training_image, volumes={"/p012": volume}, gpu="H100!", cpu=1,
              memory=8192, timeout=86400, retries=0, max_containers=1,
              scaledown_window=2, include_source=False)
def check_training(payload):
    from huggingface_hub import snapshot_download
    import hashlib
    start = time.monotonic()
    versions = check_definition(payload, "training")
    lf = json.loads(importlib.metadata.distribution("llamafactory").read_text("direct_url.json"))
    if lf["vcs_info"]["commit_id"] != payload["llamafactory_commit"]:
        raise ValueError("STOP: LLaMA-Factory commit differs")
    hardware = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total,driver_version",
        "--format=csv,noheader"], capture_output=True, text=True, check=True).stdout.strip()
    if hardware.split(",")[:2] != payload["reference_hardware"].strip().split(",")[:2]:
        raise ValueError("STOP: H100 model or memory differs")
    models = []
    for model in payload["models"]:
        root = Path(snapshot_download(model["repo"], revision=model["revision"],
            cache_dir="/p012/hf", local_files_only=True))
        for entry in model["files"]:
            f = root / entry["path"]
            if f.stat().st_size != entry["bytes"] or digest(f) != entry["sha256"]:
                raise ValueError("STOP: model bytes differ from original C1")
        models.append({"repo": model["repo"], "revision": model["revision"], "files": model["files"]})
    inputs = []
    for item in payload["frozen_inputs"]:
        if hashlib.sha256(item["jsonl"].encode()).hexdigest() != item["sha256"]:
            raise ValueError("STOP: frozen dataset transport hash differs")
        inputs.append({"name": item["name"], "sha256": item["sha256"]})
    return {"workspace": payload["workspace"], "all_passed": True, "gpu_request": "H100!",
            "hardware": hardware, "versions": versions, "llamafactory_commit": lf["vcs_info"]["commit_id"],
            "models": models, "frozen_inputs": inputs, "source_sha256": payload["source_sha256"],
            "function_seconds": time.monotonic() - start, "model_calls": 0}


@app.function(image=evaluation_image, cpu=1, memory=4096, timeout=86400,
              retries=0, max_containers=1, scaledown_window=2, include_source=False)
def check_evaluation(payload):
    start = time.monotonic()
    return {"workspace": payload["workspace"], "all_passed": True,
            "versions": check_definition(payload, "evaluation"),
            "source_sha256": payload["source_sha256"],
            "function_seconds": time.monotonic() - start, "model_calls": 0}


@app.local_entrypoint()
def main(request: str, output: str):
    payload = json.loads(Path(request).read_text())
    if not payload["forecast"]["admitted"]:
        raise ValueError("Prospective workspace admission required")
    destination = Path(output)
    destination.mkdir(parents=True, exist_ok=False)
    for name, fn in (("training", check_training), ("evaluation", check_evaluation)):
        result = fn.remote(payload)
        (destination / (name + ".json")).write_text(json.dumps(result, indent=2) + "\n")
    print("Both original-image parity checks passed; no model forward/update called.")

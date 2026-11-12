"""Review candidate: run the pinned standard LLaMA-Factory CLI on Modal.

Invoke as `modal run -m experiments.p012.modal_train`. This module does not
choose data, change training doses, retry failures, or implement an optimizer.
"""
from __future__ import annotations

import importlib.metadata
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
import zipfile

import modal

from .modal_g0 import digest, volume
from .modal_training_runtime import training_image
from .training_config import LI_COMMIT
from .training_inputs import validate_training_request

app = modal.App("p012-standard-training-20261111")
image = training_image.env({"HF_HUB_CACHE": "/p012/hf", "TRANSFORMERS_OFFLINE": "1"})


@app.function(image=image, volumes={"/p012": volume}, gpu="H100", cpu=4, memory=32768,
              timeout=86400, retries=0, max_containers=1, scaledown_window=2,
              include_source=False)
def train(request: dict) -> dict:
    import yaml
    from huggingface_hub import snapshot_download

    started = time.monotonic()
    data_check = validate_training_request(request)
    for name in ("modal_train.py", "modal_g0.py", "training_inputs.py", "training_config.py",
                 "modal_training_runtime.py", "requirements-train.lock"):
        if digest(Path(__file__).parent / name) != request["source_sha256"][name]:
            raise ValueError("Training source differs from the frozen request")
    origin = json.loads(importlib.metadata.distribution("llamafactory").read_text("direct_url.json"))
    if origin.get("vcs_info", {}).get("commit_id") != LI_COMMIT:
        raise ValueError("LLaMA-Factory differs from the fixed paper release")
    model = request["model"]
    snapshot = Path(snapshot_download(model["repo"], revision=model["revision"],
                                     cache_dir="/p012/hf", local_files_only=True))
    for entry in model["files"]:
        path = snapshot / entry["path"]
        if path.stat().st_size != entry["bytes"] or digest(path) != entry["sha256"]:
            raise ValueError("Cached model differs from C1 hashes")
    work = Path("/p012/training") / request["run_id"]
    work.mkdir(parents=True, exist_ok=False)
    inputs = work / "inputs"
    inputs.mkdir()
    (inputs / "examples.jsonl").write_text(request["dataset"]["jsonl"])
    (inputs / "dataset_info.json").write_text(json.dumps({request["dataset"]["name"]: {
        "file_name": "examples.jsonl", "columns": {"prompt": "problem", "response": "solution"}}}, indent=2) + "\n")
    config = dict(request["config"], dataset_dir=str(inputs), output_dir=str(work / "checkpoint"),
                  overwrite_output_dir=False, skip_memory_metrics=False)
    (work / "config.yaml").write_text(yaml.safe_dump(config, sort_keys=False))
    # Store the dataset once, while binding its complete bytes in the request.
    manifest = dict(request)
    manifest["dataset"] = {k: v for k, v in request["dataset"].items() if k != "jsonl"}
    manifest.update(effective_config=config, data_validation=data_check,
        installed_lf_source=origin,
        runtime_overrides={"dataset_dir": "container path", "output_dir": "unique persistent-volume path",
                           "skip_memory_metrics": "false: standard Trainer memory accounting"},
        versions={p: importlib.metadata.version(p) for p in
                  ("llamafactory", "torch", "transformers", "datasets", "accelerate", "flash-attn", "pyarrow")})
    (work / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    gpu = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total,driver_version",
                          "--format=csv,noheader"], capture_output=True, text=True, check=True)
    (work / "HARDWARE.txt").write_text(gpu.stdout)
    status = {"run_id": request["run_id"], "success": False, "gpu": "H100", "cpu": 4, "memory_MiB": 32768}
    volume.commit()
    try:
        with (work / "training.log").open("x") as log:
            command = [str(Path(sys.executable).with_name("llamafactory-cli")), "train", str(work / "config.yaml")]
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, env=dict(os.environ, P012_CODE_COMMIT=request["code_commit"]))
            last_commit = time.monotonic()
            for line in process.stdout:
                log.write(line)
                log.flush()
                print(line, end="", flush=True)
                if time.monotonic() - last_commit >= 60:
                    volume.commit()
                    last_commit = time.monotonic()
            status["returncode"] = process.wait()
            status["success"] = status["returncode"] == 0
        checkpoint = work / "checkpoint"
        files = [{"path": str(p.relative_to(checkpoint)), "bytes": p.stat().st_size, "sha256": digest(p)}
                 for p in sorted(checkpoint.rglob("*")) if p.is_file()]
        (work / "CHECKPOINT_FILES.json").write_text(json.dumps(files, indent=2) + "\n")
        if status["success"] and not list(checkpoint.glob("*.safetensors")):
            raise ValueError("Trainer returned success without final model weights")
    except Exception:
        status["success"] = False
        (work / "ERROR.txt").write_text(traceback.format_exc())
    finally:
        status["function_seconds"] = time.monotonic() - started
        (work / "STATUS.json").write_text(json.dumps(status, indent=2) + "\n")
        volume.commit()
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
        for path in sorted(work.rglob("*")):
            relative = path.relative_to(work)
            if path.is_file() and (relative.parts[0] != "checkpoint" or
                                  path.name in {"train_results.json", "all_results.json", "trainer_state.json"}):
                z.write(path, str(relative))
    return {"status": status, "archive": archive.getvalue(), "checkpoint_path": str(work / "checkpoint")}


@app.local_entrypoint()
def main(request: str, output: str):
    spec = json.loads(Path(request).read_text())
    validate_training_request(spec)
    destination = Path(output)
    if destination.exists():
        raise FileExistsError("Keep previous attempts and use a new output directory")
    result = train.remote(spec)
    destination.mkdir(parents=True)
    (destination / "artifacts.zip").write_bytes(result["archive"])
    with zipfile.ZipFile(io.BytesIO(result["archive"])) as z:
        if any(Path(name).is_absolute() or ".." in Path(name).parts for name in z.namelist()):
            raise ValueError("Unsafe archive path")
        z.extractall(destination)
    (destination / "CHECKPOINT_LOCATION.json").write_text(json.dumps({
        "volume": "p012-g0-assets-results-20261111", "path": result["checkpoint_path"],
        "retention": ("Main grid: remove only after raw evaluation output publication and review; headline checkpoints through 2026-12-14" if spec["cell"] else
                      "Reproduction: preserve; independent full-weight backup pending"),
        "independent_full_weight_backup_required": spec["cell"] is None,
        "deletion_performed": False}, indent=2) + "\n")
    print(json.dumps(result["status"]))
    if not result["status"]["success"]:
        raise SystemExit(1)

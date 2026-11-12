"""C7 NLL transport. Candidate awaiting its single owner-requested review."""
from __future__ import annotations

import io
import json
from pathlib import Path
import subprocess
import time
import traceback
import zipfile

import modal

from .capability_nll import validate_nll_request
from .modal_g0 import digest, volume
from .modal_training_runtime import training_image

app = modal.App("p012-capability-nll-20261111")
image = training_image.env({"HF_HUB_CACHE": "/p012/hf", "TRANSFORMERS_OFFLINE": "1"})
REQUIRED_SOURCES = {"capability_nll.py", "modal_capability.py", "modal_training_runtime.py",
                    "training_config.py", "evaluation.py", "data_pool.py", "requirements-train.lock"}


@app.function(image=image, volumes={"/p012": volume}, gpu="H100", cpu=2, memory=16384,
              timeout=86400, retries=0, max_containers=1, scaledown_window=2, include_source=False)
def measure(request: dict) -> dict:
    from huggingface_hub import snapshot_download
    from .capability_nll import run_nll

    started = time.monotonic()
    validate_nll_request(request)
    required = REQUIRED_SOURCES | {"templates/" + request["model"]["family"] + ".jinja"}
    if set(request["source_sha256"]) != required:
        raise ValueError("Bind every C7 execution source and the training template")
    for name, expected in request["source_sha256"].items():
        if digest(Path(__file__).parent / name) != expected:
            raise ValueError("C7 execution source mismatch: " + name)
    spec = request["model"]
    snapshot = Path(snapshot_download(spec["repo"], revision=spec["revision"],
                                     cache_dir="/p012/hf", local_files_only=True))
    for entry in spec["files"]:
        path = snapshot / entry["path"]
        if path.stat().st_size != entry["bytes"] or digest(path) != entry["sha256"]:
            raise ValueError("Initial model differs from C1")
    work = Path("/p012/capability_nll") / request["run_id"]
    work.mkdir(parents=True, exist_ok=False)
    (work / "REQUEST.json").write_text(json.dumps(request, indent=2) + "\n")
    hardware = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total,driver_version",
                               "--format=csv,noheader"], capture_output=True, text=True, check=True)
    (work / "HARDWARE.txt").write_text(hardware.stdout)
    if "H100" not in hardware.stdout:
        raise ValueError("Resource differs from the forecast")
    status = {"success": False, "run_id": request["run_id"], "gpu": "H100", "cpu": 2, "memory_MiB": 16384}
    try:
        run_nll(request, work / "nll", snapshot)
        status["success"] = True
    except Exception:
        (work / "ERROR.txt").write_text(traceback.format_exc())
    finally:
        status["function_seconds"] = time.monotonic() - started
        (work / "STATUS.json").write_text(json.dumps(status, indent=2) + "\n")
        volume.commit()
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zipped:
        for path in sorted(work.rglob("*")):
            if path.is_file():
                zipped.write(path, str(path.relative_to(work)))
    return {"status": status, "archive": archive.getvalue()}


@app.local_entrypoint()
def main(request: str, output: str):
    spec = json.loads(Path(request).read_text())
    validate_nll_request(spec)
    destination = Path(output)
    if destination.exists():
        raise FileExistsError("Preserve previous C7 attempts")
    result = measure.remote(spec)
    destination.mkdir(parents=True)
    (destination / "artifacts.zip").write_bytes(result["archive"])
    with zipfile.ZipFile(io.BytesIO(result["archive"])) as zipped:
        if any(Path(name).is_absolute() or ".." in Path(name).parts for name in zipped.namelist()):
            raise ValueError("Unsafe output path")
        zipped.extractall(destination)
    print(json.dumps(result["status"]))
    if not result["status"]["success"]:
        raise SystemExit(1)

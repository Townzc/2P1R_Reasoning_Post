"""Minimal Modal transport for approved G0-E. Review this shared path before C8."""
from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import traceback
import zipfile

import modal

SOURCE = Path(__file__).resolve().parent
app = modal.App("p012-g0-e-20261111")
volume = modal.Volume.from_name("p012-g0-assets-results-20261111", create_if_missing=True)
image = (modal.Image.debian_slim(python_version="3.11")
         .apt_install("git")
         .pip_install_from_requirements(SOURCE / "requirements-eval.lock")
         .run_commands("python -m pip check")
         .add_local_dir(SOURCE, "/workspace/experiments/p012", copy=True,
                        ignore=["__pycache__", "*.pyc"])
         .env({"PYTHONPATH": "/workspace", "PYTHONUNBUFFERED": "1",
               "HF_HUB_CACHE": "/p012/hf", "HF_HUB_DISABLE_TELEMETRY": "1"}))


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


@app.function(image=image, volumes={"/p012": volume}, cpu=1, memory=4096,
              timeout=86400, retries=0, max_containers=1, scaledown_window=2,
              include_source=False)
def cache_model(spec: dict) -> dict:
    from huggingface_hub import snapshot_download
    started = time.monotonic()
    path = Path(snapshot_download(spec["repo"], revision=spec["revision"], token=False,
                                 allow_patterns=[f["path"] for f in spec["files"]]))
    checked = []
    for item in spec["files"]:
        actual = path / item["path"]
        if actual.stat().st_size != item["bytes"] or digest(actual) != item["sha256"]:
            raise ValueError(f"Cached asset mismatch: {item['path']}")
        checked.append(item["path"])
    receipt = {"repo": spec["repo"], "revision": spec["revision"], "files_checked": checked,
               "elapsed_seconds": time.monotonic() - started}
    saved = Path("/p012/cache_receipts")
    saved.mkdir(exist_ok=True)
    (saved / (spec["revision"] + ".json")).write_text(json.dumps(receipt, indent=2) + "\n")
    volume.commit()
    return receipt


@app.function(image=image, volumes={"/p012": volume}, gpu="L4", cpu=2, memory=12288,
              timeout=86400, retries=0, max_containers=1, scaledown_window=2,
              include_source=False)
def generate(request: dict) -> dict:
    from experiments.p012.evaluation import EvalConfig
    started = time.monotonic()
    run_id = request["run_id"]
    if not re.fullmatch(r"[a-z0-9_]+", run_id):
        raise ValueError("Invalid run ID")
    if not re.fullmatch(r"[a-f0-9]{40}", request["code_commit"]):
        raise ValueError("Missing execution source commit")
    EvalConfig(**request["config"]).validate()
    for relative, expected in request["source_sha256"].items():
        if relative not in {"evaluation.py", "scoring.py", "modal_g0.py", "g0_tools.py"}:
            raise ValueError("Unexpected source binding")
        if digest(Path("/workspace/experiments/p012") / relative) != expected:
            raise ValueError("Uploaded execution source differs from frozen request")
    work = Path("/p012/runs") / run_id
    work.mkdir(parents=True, exist_ok=False)
    (work / "REQUEST.json").write_text(json.dumps(request, indent=2) + "\n")
    (work / "config.json").write_text(json.dumps(request["config"], indent=2) + "\n")
    (work / "inputs.jsonl").write_text(request["input_jsonl"])
    if digest(work / "inputs.jsonl") != request["input_sha256"]:
        raise ValueError("Transport input digest mismatch")
    hardware = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total,driver_version",
                               "--format=csv,noheader"], capture_output=True, text=True, check=True)
    (work / "HARDWARE.txt").write_text(hardware.stdout)
    env = dict(os.environ, P012_CODE_COMMIT=request["code_commit"], HF_HUB_OFFLINE="1",
               TRANSFORMERS_OFFLINE="1")
    status = {"run_id": run_id, "success": False, "gpu": "L4", "cpu": 2, "memory_MiB": 12288}
    try:
        # A fresh process releases vLLM workers between calls; no custom training loop.
        with (work / "generation.log").open("x") as log:
            process = subprocess.Popen([sys.executable, "-m", "experiments.p012.evaluation",
                "--config", str(work / "config.json"), "--inputs", str(work / "inputs.jsonl"),
                "--output", str(work / "generation")], stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, text=True, env=env)
            for line in process.stdout:
                log.write(line)
                log.flush()
                print(line, end="", flush=True)
            status["returncode"] = process.wait()
            status["success"] = status["returncode"] == 0
    except Exception:
        (work / "ERROR.txt").write_text(traceback.format_exc())
    finally:
        status["function_seconds"] = time.monotonic() - started
        (work / "STATUS.json").write_text(json.dumps(status, indent=2) + "\n")
        volume.commit()
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zipped:
        for path in sorted(work.rglob("*")):
            if path.is_file():
                zipped.write(path, str(path.relative_to(work)))
    return {"status": status, "archive": archive.getvalue()}


@app.local_entrypoint()
def main(request: str, output: str, prepare: bool = False):
    spec = json.loads(Path(request).read_text())
    destination = Path(output)
    if destination.exists():
        raise ValueError("Use a new output path; old attempts are immutable")
    if prepare:
        result = cache_model.remote(spec)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result))
        return
    result = generate.remote(spec)
    destination.mkdir(parents=True)
    archive = destination / "artifacts.zip"
    archive.write_bytes(result["archive"])
    with zipfile.ZipFile(archive) as zipped:
        for name in zipped.namelist():
            if Path(name).is_absolute() or ".." in Path(name).parts:
                raise ValueError("Unsafe result archive member")
        zipped.extractall(destination)
    print(json.dumps(result["status"]))
    if not result["status"]["success"]:
        raise SystemExit(1)

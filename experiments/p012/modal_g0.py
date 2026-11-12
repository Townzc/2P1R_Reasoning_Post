"""Minimal Modal transport for approved G0-E. Review this shared path before C8."""
from __future__ import annotations

import hashlib
import base64
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
import urllib.request

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
    if not spec["files"] or not any(f["path"].endswith(".safetensors") for f in spec["files"]):
        raise ValueError("The pinned repository has no model weights")
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


@app.function(image=image, volumes={"/p012": volume}, cpu=1, memory=4096,
              timeout=86400, retries=0, max_containers=1, scaledown_window=2,
              include_source=False)
def cache_authorized_snapshot(payload: dict) -> dict:
    """Cache C1 files using local small files and file-scoped download URLs.

    The HF token stays on the local machine. Temporary URLs are not logged or
    included in receipts; every resulting file must match its frozen C1 hash.
    """
    started = time.monotonic()
    spec = payload["spec"]
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", spec["repo"]):
        raise ValueError("Invalid model repo")
    if not re.fullmatch(r"[a-f0-9]{40}", spec["revision"]):
        raise ValueError("Pin a model revision")
    snapshot = Path("/p012/hf") / ("models--" + spec["repo"].replace("/", "--")) / "snapshots" / spec["revision"]
    checked = []
    for item in spec["files"]:
        relative = Path(item["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("Invalid asset path")
        path = snapshot / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            transfer = payload["transfers"][item["path"]]
            temporary = path.with_name(path.name + ".partial")
            try:
                with temporary.open("wb") as output:
                    if "base64" in transfer:
                        output.write(base64.b64decode(transfer["base64"], validate=True))
                    else:
                        with urllib.request.urlopen(transfer["url"], timeout=120) as response:
                            while block := response.read(8 * 1024 * 1024):
                                output.write(block)
                if temporary.stat().st_size != item["bytes"] or digest(temporary) != item["sha256"]:
                    raise ValueError("Downloaded model asset differs from C1")
                temporary.rename(path)
            except Exception as error:
                # Network errors can contain temporary URLs. Preserve only the
                # error type and public filename in remote logs.
                raise RuntimeError(f"Asset transfer failed: {item['path']} ({type(error).__name__})") from None
        if path.stat().st_size != item["bytes"] or digest(path) != item["sha256"]:
            raise ValueError("Cached model asset differs from C1")
        checked.append(item["path"])
    receipt = {"repo": spec["repo"], "revision": spec["revision"], "files_checked": checked,
               "elapsed_seconds": time.monotonic() - started, "hf_token_transferred": False}
    saved = Path("/p012/cache_receipts")
    saved.mkdir(exist_ok=True)
    (saved / (spec["revision"] + ".json")).write_text(json.dumps(receipt, indent=2) + "\n")
    volume.commit()
    return receipt


@app.function(image=image, volumes={"/p012": volume}, gpu="H100", cpu=2, memory=12288,
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
        if relative not in {"evaluation.py", "scoring.py", "modal_g0.py", "g0_tools.py", "checkpoints.py"}:
            raise ValueError("Unexpected source binding")
        if digest(Path("/workspace/experiments/p012") / relative) != expected:
            raise ValueError("Uploaded execution source differs from frozen request")
    if request["config"].get("training_run_id") and "checkpoints.py" not in request["source_sha256"]:
        raise ValueError("Bind the checkpoint verification source for local evaluation")
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
    gpu = "H200" if request["config"]["protocol"] == "li_judge" else "H100"
    if gpu not in hardware.stdout:
        raise ValueError("Actual GPU differs from the forecast resource")
    env = dict(os.environ, P012_CODE_COMMIT=request["code_commit"], HF_HUB_OFFLINE="1",
               TRANSFORMERS_OFFLINE="1")
    status = {"run_id": run_id, "success": False, "gpu": gpu, "cpu": 2, "memory_MiB": 12288}
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
        result = cache_authorized_snapshot.remote(spec) if "transfers" in spec else cache_model.remote(spec)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result))
        return
    # 32B FP16 weights plus a 32K KV cache need more room than the small-model
    # H100 allocation. Keep the same precision, decoding and single judge load.
    worker = generate.with_options(gpu="H200") if spec["config"]["protocol"] == "li_judge" else generate
    result = worker.remote(spec)
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

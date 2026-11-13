"""A4 reviewed-candidate Modal transport for unmerged LoRA inference."""
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
from .modal_g0 import image,volume,digest
app=modal.App('p012-lora-bridge-eval-20261113')

@app.function(image=image, volumes={"/p012": volume}, gpu="H100!", cpu=2, memory=12288,
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
    if not re.fullmatch(r"[a-f0-9]{40}",request.get("accepted_review_commit", "")):
        raise ValueError("Bridge formal evaluation awaits combined review")
    required = {"evaluation.py", "scoring.py", "modal_g0.py", "g0_tools.py", "bridge_evaluation.py",
                "bridge_config.py", "modal_bridge_evaluation.py", "training_config.py", "training_inputs.py"}
    if set(request["source_sha256"]) != required:
        raise ValueError("Bind every bridge execution source")
    for relative, expected in request["source_sha256"].items():
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
    (work / "BRIDGE.json").write_text(json.dumps(request["bridge"]))
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
            process = subprocess.Popen([sys.executable, "-m", "experiments.p012.bridge_evaluation",
                "--config", str(work / "config.json"), "--inputs", str(work / "inputs.jsonl"),
                "--output", str(work / "generation"), "--bridge", str(work / "BRIDGE.json")], stdout=subprocess.PIPE,
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
def main(request: str, output: str):
    spec=json.loads(Path(request).read_text());dest=Path(output)
    if dest.exists():raise FileExistsError('Preserve earlier outputs')
    result=generate.remote(spec);dest.mkdir(parents=True)
    (dest/'artifacts.zip').write_bytes(result['archive'])
    with zipfile.ZipFile(io.BytesIO(result['archive'])) as z:
        if any(Path(n).is_absolute() or '..' in Path(n).parts for n in z.namelist()):raise ValueError('Unsafe archive')
        z.extractall(dest)
    print(json.dumps(result['status']))
    if not result['status']['success']:raise SystemExit(1)

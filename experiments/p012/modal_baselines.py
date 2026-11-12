"""CPU-only standard-harness prompt preparation and scoring of saved raw outputs."""
from __future__ import annotations
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import zipfile
import modal
from .modal_g0 import image as eval_image, volume

app = modal.App("p012-standard-base-cpu-20261112")
image = (eval_image.run_commands("python -m pip uninstall -y math-verify latex2sympy2-extended")
    .pip_install("antlr4-python3-runtime==4.11.0")
    .run_commands("python -m pip check", "python -c 'from sympy.parsing.latex import parse_latex; assert parse_latex(\"1\") == 1'")
    .env({"HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"}))


@app.function(image=image, volumes={"/p012": volume}, cpu=2, memory=8192, timeout=86400,
              retries=0, max_containers=1, scaledown_window=2, include_source=False)
def execute(request: dict) -> dict:
    if not re.fullmatch(r"[a-z0-9_]+", request["run_id"]):
        raise ValueError("Invalid CPU batch ID")
    work = Path("/p012/base_cpu") / request["run_id"]
    work.mkdir(parents=True, exist_ok=False)
    command = [sys.executable, "-m", "experiments.p012.harness_baselines", request["operation"],
               "--output", str(work / "output")]
    if request["operation"] in {"prepare", "validate"}:
        (work / "payload.json").write_text(json.dumps(request["payload"]))
        command.extend(["--payload", str(work / "payload.json")])
    elif request["operation"] == "score":
        if not re.fullmatch(r"[a-z0-9_]+", request["generation_run_id"]):
            raise ValueError("Invalid generation ID")
        parent = Path("/p012/runs") / request["generation_run_id"]
        command.extend(["--inputs", str(parent / "inputs.jsonl"), "--generation", str(parent / "generation")])
    else:
        raise ValueError("Unknown CPU operation")
    with (work / "process.log").open("x") as log:
        result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT,
                                env=dict(os.environ, P012_CODE_COMMIT=request["code_commit"]))
    status = {"returncode": result.returncode, "operation": request["operation"], "code_commit": request["code_commit"]}
    (work / "STATUS.json").write_text(json.dumps(status, indent=2) + "\n")
    volume.commit()
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
        for path in sorted(work.rglob("*")):
            if path.is_file() and path.name != "payload.json":
                z.write(path, str(path.relative_to(work)))
    return {"status": status, "archive": archive.getvalue()}


@app.local_entrypoint()
def main(request: str, output: str):
    destination = Path(output)
    if destination.exists():
        raise FileExistsError("Use a new immutable CPU output directory")
    result = execute.remote(json.loads(Path(request).read_text()))
    destination.mkdir(parents=True)
    (destination / "artifacts.zip").write_bytes(result["archive"])
    with zipfile.ZipFile(io.BytesIO(result["archive"])) as z:
        if any(Path(n).is_absolute() or ".." in Path(n).parts for n in z.namelist()):
            raise ValueError("Unsafe archive member")
        z.extractall(destination)
    print(json.dumps(result["status"]))
    if result["status"]["returncode"]:
        print((destination / "process.log").read_text()[-5000:])
        raise SystemExit(1)

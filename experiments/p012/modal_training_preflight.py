"""CPU transport for the required real-row training preprocessing check."""
from __future__ import annotations
import json
from pathlib import Path
import time
import modal
from .modal_training_runtime import training_image

app = modal.App("p012-training-preflight-20261112")


@app.function(image=training_image, cpu=2, memory=8192, timeout=86400,
              retries=0, max_containers=1, scaledown_window=2, include_source=False)
def check(payload: dict) -> dict:
    from experiments.p012.evaluation import sha256_file
    from experiments.p012.training_preflight import check_training_rows
    for name, expected in payload["source_sha256"].items():
        if Path(name).name != name or sha256_file(Path(__file__).parent / name) != expected:
            raise ValueError("Preflight source differs from frozen payload")
    started = time.monotonic()
    result = check_training_rows(payload, Path("/tokenizers"))
    result["function_seconds"] = time.monotonic() - started
    return result


@app.local_entrypoint()
def main(request: str, output: str):
    destination = Path(output)
    if destination.exists():
        raise FileExistsError("Preflight evidence is immutable")
    payload = json.loads(Path(request).read_text())
    if not payload["forecast"]["admitted"]:
        raise ValueError("Admit CPU cost before execution")
    result = check.remote(payload)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"all_passed": result["all_passed"], "checks": len(result["checks"]),
                      "reports": [{k: r[k] for k in ("dataset", "model", "rows", "maximum_full_tokens", "over_cutoff_rows")} for r in result["reports"]],
                      "function_seconds": result["function_seconds"]}))

"""Pinned training image and CPU template export; no training is launched here."""
from __future__ import annotations

import json
from pathlib import Path

import modal

from .modal_g0 import image as evaluation_image

SOURCE = Path(__file__).resolve().parent
TOKENIZERS = SOURCE.parents[1] / ".local/p012_20261111/train_runtime/tokenizers"
FLASH_WHEEL = (
    "https://github.com/Dao-AILab/flash-attention/releases/download/v2.7.4.post1/"
    "flash_attn-2.7.4.post1%2Bcu12torch2.5cxx11abiFALSE-cp311-cp311-linux_x86_64.whl"
    "#sha256=d944fc7d2f962bce83fc4708c2fc0c21eaf8255962a0b350ae919362a51b7ef2"
)

app = modal.App("p012-training-runtime-20261111")
training_image = (modal.Image.debian_slim(python_version="3.11")
    .apt_install("git", "libgl1", "libglib2.0-0")
    .pip_install("torch==2.5.1", "packaging==26.3")
    .pip_install(FLASH_WHEEL)
    .pip_install_from_requirements(SOURCE / "requirements-train.lock")
    .run_commands("python -m pip check",
        "python -c 'from llamafactory.data.template import get_template_and_fix_tokenizer; "
        "from llamafactory.hparams import DataArguments; print(\"Training imports passed\")'")
    .add_local_dir(SOURCE, "/workspace/experiments/p012", copy=True,
                   ignore=["__pycache__", "*.pyc"])
    .add_local_dir(TOKENIZERS, "/tokenizers", copy=True)
    .env({"PYTHONPATH": "/workspace", "PYTHONUNBUFFERED": "1",
          "HF_HUB_DISABLE_TELEMETRY": "1", "HF_HUB_OFFLINE": "1"}))


@app.function(image=training_image, cpu=1, memory=4096, timeout=86400,
              retries=0, max_containers=1, scaledown_window=2, include_source=False)
def check_templates(models: list[dict]) -> dict:
    from experiments.p012.training_templates import export_and_check
    return export_and_check(Path("/tokenizers"), models)


@app.function(image=evaluation_image.add_local_dir(TOKENIZERS, "/tokenizers", copy=True),
              cpu=1, memory=4096, timeout=86400, retries=0, max_containers=1,
              scaledown_window=2, include_source=False)
def check_eval_templates(models: list[dict], reference: dict) -> dict:
    from experiments.p012.training_templates import check_evaluation_environment
    return check_evaluation_environment(Path("/tokenizers"), models, reference)


@app.local_entrypoint()
def main(models: str, output: str):
    destination = Path(output)
    if destination.exists():
        raise FileExistsError("Template-check outputs are immutable")
    model_specs = json.loads(Path(models).read_text())
    result = check_templates.remote(model_specs)
    destination.mkdir(parents=True)
    (destination / "FACTORY_TEMPLATE_PARITY.json").write_text(json.dumps(result, indent=2) + "\n")
    for family, template in result["templates"].items():
        (destination / (family + ".jinja")).write_text(template)
    evaluation = check_eval_templates.remote(model_specs, result)
    (destination / "EVAL_TEMPLATE_PARITY.json").write_text(json.dumps(evaluation, indent=2) + "\n")
    print(json.dumps({"all_passed": result["all_passed"], "checks": len(result["checks"]),
                      "versions": result["versions"], "evaluation_environment": evaluation}))

"""Produce standard LLaMA-Factory YAML; no training implementation."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import yaml

LI_COMMIT = "1863f15a7c58b8a69fb1d18235ea85bca26d0484"
CELLS = {"P": (4096, 1, 2), "K8": (512, 8, 2),
         "K4": (1024, 4, 2), "R": (512, 1, 16), "L": (512, 1, 2)}


def training_config(model: str, revision: str, family: str, dataset: str,
                    dataset_dir: str, output_dir: str, seed: int | None = None,
                    cell: str | None = None, long_cot: bool = False) -> dict:
    if family not in {"qwen", "llama3"}:
        raise ValueError("Freeze one of the two registered family templates")
    if not revision or revision in {"main", "master"}:
        raise ValueError("Model revision must be fixed")
    if cell is not None and cell not in CELLS:
        raise ValueError(cell)
    if cell is not None and long_cot:
        raise ValueError("Long-chain allocation grid is outside P012")
    # G0 inherits the fixed Transformers default; the main grid registers 17/29.
    seed = (17 if cell else 42) if seed is None else seed
    config = {
        "model_name_or_path": model, "model_revision": revision,
        "stage": "sft", "do_train": True, "finetuning_type": "full",
        "flash_attn": "fa2", "dataset": dataset, "dataset_dir": dataset_dir,
        "template": family, "cutoff_len": 16384 if long_cot else (4096 if cell else 8192),
        "packing": False, "train_on_prompt": False,
        "preprocessing_num_workers": 4, "max_samples": 10000,
        "output_dir": output_dir, "overwrite_output_dir": False,
        "logging_steps": 1, "save_steps": 1000, "save_total_limit": 2,
        "plot_loss": True, "per_device_train_batch_size": 2,
        "gradient_accumulation_steps": 4, "learning_rate": 1e-5,
        "num_train_epochs": CELLS[cell][2] if cell else 2,
        "lr_scheduler_type": "cosine", "bf16": True,
        "optim": "adamw_torch", "warmup_ratio": 0.0, "warmup_steps": 0,
        "weight_decay": 0.0, "adam_beta1": 0.9, "adam_beta2": 0.999,
        "adam_epsilon": 1e-8, "max_grad_norm": 1.0,
        "seed": seed, "data_seed": seed if cell else None, "report_to": "none",
        "ddp_timeout": 180000000,
        # Li release's validation split belongs only to reproduction. The main
        # grid exposes every registered row; the separate 500 parents stay held out.
        "val_size": 0.0 if cell else 0.01,
        "eval_strategy": "no" if cell else "steps",
        "per_device_eval_batch_size": 1,
    }
    if not cell:
        config["eval_steps"] = 100
    return config


def grid_dose(cell: str) -> dict:
    parents, paths, epochs = CELLS[cell]
    return {"parents": parents, "paths_per_parent": paths,
            "distinct_rows": parents * paths, "epochs": epochs,
            "presentations": parents * paths * epochs,
            "effective_batch": 8, "expected_updates": parents * paths * epochs // 8,
            "constraint": "sample_presentations", "equal_tokens_or_flops_claimed": False}


def main() -> None:
    p = argparse.ArgumentParser()
    for name in ("model", "revision", "family", "dataset", "dataset-dir", "output-dir", "yaml"):
        p.add_argument("--" + name, required=True)
    p.add_argument("--seed", type=int)
    p.add_argument("--cell", choices=list(CELLS))
    p.add_argument("--long-cot", action="store_true")
    a = p.parse_args()
    config = training_config(a.model, a.revision, a.family, a.dataset, a.dataset_dir,
                             a.output_dir, a.seed, a.cell, a.long_cot)
    path = Path(a.yaml)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as f:
        yaml.safe_dump(config, f, sort_keys=False)
    print(json.dumps(grid_dose(a.cell) if a.cell else {"phase": "G0-T", "epochs": 2}))


if __name__ == "__main__":
    main()

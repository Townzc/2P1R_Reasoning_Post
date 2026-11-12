"""Verify the final model on the persistent volume before evaluation loads it."""
from __future__ import annotations
import json
from pathlib import Path
import re

from .evaluation import sha256_file


def verify_checkpoint(model_path: str, run_id: str, manifest_sha256: str,
                      root: Path = Path("/p012/training")) -> dict:
    if not re.fullmatch(r"[a-z0-9_]+", run_id) or not re.fullmatch(r"[a-f0-9]{64}", manifest_sha256):
        raise ValueError("Bind the training run and checkpoint manifest")
    work, checkpoint = root / run_id, Path(model_path)
    if checkpoint != work / "checkpoint" or checkpoint.is_symlink():
        raise ValueError("Checkpoint must be the named training run's final directory")
    manifest_path = work / "CHECKPOINT_FILES.json"
    if sha256_file(manifest_path) != manifest_sha256:
        raise ValueError("Checkpoint file manifest differs from the frozen request")
    status = json.loads((work / "STATUS.json").read_text())
    if status.get("success") is not True or status.get("run_id") != run_id:
        raise ValueError("Training did not finish successfully")
    training = json.loads((work / "MANIFEST.json").read_text())
    if training["run_id"] != run_id:
        raise ValueError("Training manifest belongs to a different run")
    declared = {}
    for entry in json.loads(manifest_path.read_text()):
        relative = Path(entry["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("Invalid checkpoint manifest path")
        if len(relative.parts) == 1:
            if entry["path"] in declared:
                raise ValueError("Duplicate checkpoint manifest entry")
            declared[entry["path"]] = entry
    actual = {p.name for p in checkpoint.iterdir() if p.is_file() or p.is_symlink()}
    if actual != set(declared):
        raise ValueError("Final checkpoint has missing or extra files")
    weights = []
    for name, entry in declared.items():
        path = checkpoint / name
        if path.is_symlink() or path.stat().st_size != entry["bytes"] or sha256_file(path) != entry["sha256"]:
            raise ValueError("Final checkpoint hash mismatch: " + name)
        if name.endswith(".safetensors"):
            weights.append(entry)
    if not weights or not {"config.json", "tokenizer_config.json", "tokenizer.json"} <= actual:
        raise ValueError("Final model weights and tokenizer must be complete")
    return {"training_run_id": run_id, "checkpoint_manifest_sha256": manifest_sha256,
            "training_manifest_sha256": sha256_file(work / "MANIFEST.json"),
            "initialization_repo": training["model"]["repo"],
            "initialization_revision": training["model"]["revision"],
            "final_weights": sorted(weights, key=lambda r: r["path"]),
            "all_final_files_verified": sorted(actual)}

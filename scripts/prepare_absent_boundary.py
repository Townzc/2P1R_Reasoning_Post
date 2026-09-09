"""Immutable, prepublished-source CPU preparation for the C012 absent pair."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess

from scripts.audit_family_matching import verified_tokenizer
from src.family_boundary_runtime import (COPY_FILES, DATA_FILES, MODEL, ORIGINAL_HASHES, PLANNED_ARMS, STATUS,
                                         audit_boundary_encoding, build_boundary_payload, check_split_membership,
                                         load_candidate_sources, load_original_inputs)
from src.pilot_data import canonical_hash
from src.sft_data import sha256_file


SOURCES = ["scripts/prepare_absent_boundary.py", "src/family_boundary_runtime.py", "src/pilot_data.py",
           "src/sft_data.py", "src/countdown_smoke.py", "scripts/audit_matching_selection.py",
           "scripts/audit_pilot_structure_bias.py", "scripts/audit_family_matching.py", "configs/models.lock.json"]


def source_provenance(repo, input_paths):
    paths = SOURCES + list(input_paths)
    subprocess.check_output(["git", "-C", str(repo), "ls-files", "--error-unmatch", *paths], text=True)
    dirty = subprocess.check_output(["git", "-C", str(repo), "status", "--porcelain", "--untracked-files=no"], text=True)
    if dirty.strip():
        raise ValueError("Publish clean source/input changes before real boundary preparation")
    return {"source_commit": subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip(),
            "source_worktree_dirty": False, "source_files_sha256": {name: sha256_file(repo / name) for name in paths}}


def prepare_absent_boundary(out, tokenizer_dir, *, candidate_dir=Path("reports/absent_support_20260909_r1"), repo=None):
    repo = Path(repo or Path.cwd()).resolve()
    out, candidate_dir = Path(out), Path(candidate_dir)
    if out.exists():
        raise FileExistsError("Immutable output already exists")
    candidate_dir = candidate_dir if candidate_dir.is_absolute() else repo / candidate_dir
    candidate = {key: {"path": str((candidate_dir / (key + ".json")).resolve().relative_to(repo)),
                       "sha256": sha256_file(candidate_dir / (key + ".json"))}
                 for key in ("summary", "packing", "selection")}
    provenance = source_provenance(repo, [value["path"] for value in candidate.values()])
    problems, copied = load_original_inputs(repo)
    sources = load_candidate_sources(repo, candidate)
    blocks, rows, schedule, selection, cycles = build_boundary_payload(problems, sources)
    # The public CLI runs from the repository root; this helper checks all five original tokenizer files.
    tokenizer, tokenizer_record = verified_tokenizer(Path(tokenizer_dir))
    audit = audit_boundary_encoding(blocks, rows, schedule, tokenizer)
    dev, broad = ([json.loads(line) for line in copied[name].splitlines() if line.strip()]
                  for name in ("dev_matched.jsonl", "dev_broad.jsonl"))
    check_split_membership([item["problem"] for block in blocks for item in block["problems"]],
                           dev, broad, json.loads(copied["split_allocation.json"]))
    out.mkdir(parents=True, exist_ok=False)
    def dump(name, value):
        (out / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    dump("train_blocks.json", blocks)
    dump("selection_audit.json", selection)
    dump("schedule_seed31.json", schedule)
    dump("matching_audit.json", audit)
    for arm, values in rows.items():
        with (out / f"train_{arm}.jsonl").open("x") as stream:
            for row in values:
                stream.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
    for name in COPY_FILES:
        (out / name).write_bytes(copied[name])
    if provenance["source_files_sha256"] != {name: sha256_file(repo / name) for name in provenance["source_files_sha256"]}:
        raise RuntimeError("Preparation source/input changed during execution; output remains an incomplete attempt")
    manifest = {"schema_version": 1, "status": STATUS, "family": "identity_absent", **provenance,
                "prepared_at_utc": datetime.now(timezone.utc).isoformat(), "gpu_seconds_added": 0,
                "model_or_development_outputs_read": False, "model": MODEL, "tokenizer": tokenizer_record,
                "model_lock_sha256": sha256_file(repo / "configs/models.lock.json"),
                "original_files_sha256": ORIGINAL_HASHES, "candidate_sources": candidate,
                "candidate_source_commit": sources["summary"]["source_commit"],
                "candidate_join_complete": True, "candidate_packing_blocks": len(sources["packing"]["blocks"]),
                "paired_seed": 31, "selection_seed": 31, "eval_seed": 17, "cycles": cycles,
                "training_blocks": len(blocks), "training_questions": len(blocks) * 4, "optimizer_updates": 1024,
                "schedule_file": "schedule_seed31.json", "schedule_canonical_sha256": canonical_hash(schedule),
                "planned_arms": list(PLANNED_ARMS), "compatibility_only_arms": ["repeat", "surface"],
                "budget_per_arm": audit["arms"], "group_disjoint_before_augmentation": True,
                "limitations": ["Selected fixed-pool development boundary pilot; minimum scale is not a power calculation.",
                                "Only paths and gcm are planned; repeat and surface files are compatibility audits.",
                                "Identity-absent can include cancellation and computed constants; no semantic-strategy claim.",
                                "Preparation is not GPU launch authorization or a new spending allowance.",
                                "Unchanged development references are copied; holdout groups are checked only for overlap."],
                "files_sha256": {name: sha256_file(out / name) for name in sorted(DATA_FILES)}}
    dump("manifest.json", manifest)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--tokenizer-dir", type=Path, required=True)
    parser.add_argument("--candidate-dir", type=Path, default=Path("reports/absent_support_20260909_r1"))
    args = parser.parse_args()
    result = prepare_absent_boundary(args.out, args.tokenizer_dir, candidate_dir=args.candidate_dir)
    print(json.dumps({"status": result["status"], "training_questions": result["training_questions"],
                      "cycles": result["cycles"], "planned_arms": result["planned_arms"]}, sort_keys=True))


if __name__ == "__main__":
    main()

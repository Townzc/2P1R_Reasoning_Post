"""Reconstruct and verify the frozen C012 absence-family boundary pilot on CPU."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import random

from scripts.audit_matching_selection import characterize
from scripts.audit_pilot_structure_bias import identity_operations
from .countdown_smoke import canonical, render_trace, safe_parse
from .pilot_data import ARMS, audit_arms, canonical_hash, make_arms, paired_schedule, verify_row
from .sft_data import encode_row, read_jsonl, sha256_file


REPO_ROOT = Path(__file__).resolve().parents[1]
STATUS = "FROZEN_ABSENT_BOUNDARY_V1"
MODEL = {"repo_id": "Qwen/Qwen2.5-1.5B", "revision": "8faed761d45a263340a0528343f099c05c9a4323",
         "tokenizer_revision": "8faed761d45a263340a0528343f099c05c9a4323", "kind": "base"}
ORIGINAL_DIR = "runs/pilot_v1_20260908_r3"
ORIGINAL_HASHES = {
    "train_blocks.json": "e15857122ad9148a1a209cce7c8ef4c107ff0de27bcfe11b97ba6fce6b7a2cea",
    "dev_matched.jsonl": "c83bfcf156b53f6c75f443981d79045b1394f1d7383d17ba46d3200d23181cd3",
    "dev_broad.jsonl": "88ac632dfa1d4d5ac3e757021162156c8ac8891d6124cc040db97f38b4f81e73",
    "split_allocation.json": "8cfa236b3cfd1a29b7ef18ba126737672b3946bfbe206a80162a2de48a657143",
}
DATA_FILES = {"train_blocks.json", "schedule_seed31.json", "selection_audit.json", "matching_audit.json",
              "dev_matched.jsonl", "dev_broad.jsonl", "split_allocation.json"} | {
                  f"train_{arm}.jsonl" for arm in ARMS}
COPY_FILES = ("dev_matched.jsonl", "dev_broad.jsonl", "split_allocation.json")
PLANNED_ARMS = ("paths", "gcm")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def relative_file(repo, name):
    path = Path(name)
    require(not path.is_absolute() and path.parts and ".." not in path.parts,
            "Repository-relative provenance path required")
    result = (Path(repo) / path).resolve()
    require(result.is_relative_to(Path(repo).resolve()), "Provenance path escapes repository")
    return result


def load_original_inputs(repo):
    root = Path(repo) / ORIGINAL_DIR
    for name, digest in ORIGINAL_HASHES.items():
        require(sha256_file(root / name) == digest, "Original frozen source changed: " + name)
    blocks = json.loads((root / "train_blocks.json").read_text())
    problems = {}
    for block in blocks:
        for item in block["problems"]:
            problem = item["problem"]
            pid = problem["problem_id"]
            require(pid not in problems, "Duplicate original problem identity")
            problems[pid] = copy.deepcopy(problem)
    require(len(problems) == 256, "Expected all 256 original training questions")
    lock = json.loads((Path(repo) / "configs/models.lock.json").read_text())["main"]
    require(all(lock.get(k) == v for k, v in MODEL.items()), "Pinned main base model changed")
    return problems, {name: (root / name).read_bytes() for name in COPY_FILES}


def load_candidate_sources(repo, candidate):
    require(set(candidate) == {"summary", "packing", "selection"}, "Three C012 provenance inputs required")
    result = {}
    for key, source in candidate.items():
        require(set(source) == {"path", "sha256"}, "Malformed candidate provenance")
        path = relative_file(repo, source["path"])
        require(sha256_file(path) == source["sha256"], "C012 source changed: " + key)
        result[key] = json.loads(path.read_text())
    summary = result["summary"]
    for key in ("packing", "selection"):
        require(summary["output_sha256"][key + ".json"] == candidate[key]["sha256"],
                "C012 output is not the one recorded in its summary")
    return result


def build_boundary_payload(problems, sources):
    """Pure reconstruction from verified C012 objects; no solving or model access."""
    summary, packing, previous = (sources[k] for k in ("summary", "packing", "selection"))
    require(summary.get("diagnostic_id") == "C012" and summary.get("status") == "complete"
            and summary.get("join_complete") is True, "C012 complete-join gate has not passed")
    require(summary.get("gpu_seconds_added") == 0 and summary.get("model_or_development_outputs_read") is False,
            "Unexpected model use in CPU candidate provenance")
    config = summary["config"]
    require(config.get("training_family") == "identity_absent"
            and config.get("training_seed") == config.get("selection_seed") == 31
            and config.get("training_updates") == 1024 and config.get("block_tiers") == [32, 16],
            "C012 prespecified candidate/config changed")
    require(packing.get("input_join_complete") is True and packing.get("solver_status") in (0, 1),
            "Packing lacks complete input coverage or an acceptable solver status")
    packed = packing["blocks"]
    require(type(packed) is list and len(packed) == packing.get("primal_block_count")
            == summary.get("packing_block_count"), "Packing count/summary mismatch")
    require(len(packed) >= 16, "Fewer than 16 verified blocks; no tiny training fallback")
    all_ids, constructed = [], []
    for packed_block in packed:
        pids = packed_block["problem_ids"]
        representative = packed_block["representative"]
        structures = representative["structures"]
        require(type(packed_block["group_id"]) is int and packed_block["group_id"] >= 0,
                "Integer packing group identity required")
        require(len(pids) == len(set(pids)) == 4 and pids == sorted(pids), "Four sorted unique assigned questions required")
        require(len(structures) == len(set(structures)) == 4 and structures == sorted(structures),
                "Four lexicographic structures required")
        require(set(representative["problem_ids"]) == set(pids)
                and set(representative["witnesses"]) == set(pids),
                "Packing representative must contain exactly its four assigned questions")
        items = []
        for pid in pids:
            require(pid in problems, "Candidate question is not in the original population")
            problem, witness = problems[pid], representative["witnesses"][pid]
            require(witness["problem_id"] == pid and type(witness["n_supervised"]) is int
                    and witness["n_supervised"] > 0, "Malformed candidate witness")
            slots = witness["slots"]
            require(len(slots) == 4 and [slot["structure_id"] for slot in slots] == structures,
                    "Witness slots do not follow the shared structure order")
            paths = []
            for slot in slots:
                row = copy.deepcopy(slot["record"])
                require(slot["family"] == row.get("family") == "identity_absent", "Wrong path family")
                require(all(row[k] == problem[k] for k in ("problem_id", "numbers", "target", "prompt")),
                        "Candidate changed original question, target or prompt")
                require(slot["ac_class"] == row["ac_class"] == row["path_id"]
                        and slot["structure_id"] == row["structure_id"], "Candidate path/slot identity mismatch")
                require(row.get("encodable") is True and row["n_supervised"] == witness["n_supervised"],
                        "Candidate is not at its common supervised length")
                verify_row(row)
                tree = safe_parse(row["expression"])
                require(row["response"] == render_trace(tree), "Candidate reference is not the canonical rendering")
                require(not identity_operations(tree)[1], "Claimed absent reference contains an identity event")
                require(canonical(tree) == row["ac_class"], "Numeric AC class mismatch")
                paths.append(row)
            require(len({row["path_id"] for row in paths}) == 4, "Four distinct absent AC paths required")
            items.append({"problem": copy.deepcopy(problem), "paths": paths})
        all_ids.extend(pids)
        constructed.append((packed_block, {"structures": list(structures), "problems": items}))
    require(len(all_ids) == len(set(all_ids)), "Packing reuses a question")
    require(sorted(all_ids) == sorted(packing["used_problem_ids"]), "Packing problem list mismatch")
    stages = {name: previous["stages"][name]["problem_ids"] for name in previous["stage_order"]}
    require(previous["stage_order"] == ["individual_family_feasible", "shared_key_supported", "packed"]
            and sorted(stages["packed"]) == sorted(all_ids), "Candidate selection stages disagree with packing")
    require(characterize(problems, stages) == previous, "Candidate descriptive selection is not reproducible")
    constructed.sort(key=lambda pair: (pair[0]["group_id"], tuple(pair[0]["representative"]["structures"]),
                                       tuple(pair[0]["problem_ids"])))
    random.Random(31).shuffle(constructed)
    block_count = 32 if len(constructed) >= 32 else 16
    chosen, omitted = constructed[:block_count], constructed[block_count:]
    blocks = [pair[1] for pair in chosen]
    selected_ids = sorted(pid for packed_block, _ in chosen for pid in packed_block["problem_ids"])
    stages["training_selected"] = selected_ids
    selection = characterize(problems, stages)
    selection["selection_seed"] = 31
    selection["selection_rule"] = "sort(group_id, structures, problem_ids); independent Random(31).shuffle; take 32 else 16 blocks"
    selection["selected_packing_blocks"] = [dict(group_id=block["group_id"], problem_ids=block["problem_ids"],
                                                  structures=block["representative"]["structures"]) for block, _ in chosen]
    selection["omitted_packing_blocks"] = [dict(group_id=block["group_id"], problem_ids=block["problem_ids"],
                                                 structures=block["representative"]["structures"]) for block, _ in omitted]
    selection["original_unselected_problem_ids"] = sorted(set(problems) - set(selected_ids))
    cycles = 256 // block_count
    rows = make_arms(blocks, seed=31)
    schedule = paired_schedule(block_count, cycles=cycles, seed=31)
    require(len(schedule) == 1024 and len(selected_ids) in (64, 128), "Frozen dose/scale mismatch")
    return blocks, rows, schedule, selection, cycles


def audit_boundary_encoding(blocks, rows, schedule, tokenizer):
    for block in blocks:
        for item in block["problems"]:
            for row in item["paths"]:
                encoded = encode_row(row, tokenizer, 384)
                require(all(row[key] == encoded[key] for key in ("n_supervised", "n_prompt", "n_processed", "response_hash")),
                        "C012 token metadata differs from actual tokenizer")
    audit = audit_arms(rows, schedule, tokenizer, max_length=384)
    audit["encoding_sha256_by_arm"] = {
        arm: canonical_hash([encode_row(row, tokenizer, 384) for row in values]) for arm, values in rows.items()}
    audit["planned_arms"] = list(PLANNED_ARMS)
    audit["compatibility_only_arms"] = ["repeat", "surface"]
    for arm in ARMS:
        budget = audit["arms"][arm]
        require(budget["optimizer_updates"] == 1024 and budget["presentations"] == 4096,
                "Incomplete boundary-pilot accounting")
    for metric in ("supervised_response_tokens", "processed_nonpadding_tokens", "padding_tokens", "per_update"):
        require(audit["arms"]["paths"][metric] == audit["arms"]["gcm"][metric],
                "Paths/GCM exposure or token budget mismatch")
    # Exposure maps use integer row indices in memory; freeze their JSON form so
    # a reconstructed audit compares exactly to the persisted representation.
    return json.loads(json.dumps(audit))


def check_split_membership(problems, dev, broad, split):
    require(split["stage"] == "before_solving_or_augmentation", "Split allocation was not presolver")
    allocations = {name: {tuple(sorted(nums)) for nums in groups} for name, groups in split["groups"].items()}
    require(set(allocations) == {"train", "dev", "holdout_reserved"}, "Unknown split categories")
    require(all(len(allocations[name]) == len(split["groups"][name]) for name in allocations), "Duplicate raw split group")
    require(not (allocations["train"] & allocations["dev"] or allocations["train"] & allocations["holdout_reserved"]
                 or allocations["dev"] & allocations["holdout_reserved"]), "Original split groups overlap")
    populations = [{tuple(sorted(row["numbers"])) for row in values} for values in (problems, dev, broad)]
    require(populations[0] <= allocations["train"] and populations[1] <= allocations["dev"]
            and populations[2] <= allocations["dev"], "Rows lack membership in their original raw split")
    require(not (populations[0] & populations[1] or populations[0] & populations[2] or populations[1] & populations[2]),
            "Training/development group overlap")
    require(len(dev) == len(populations[1]) == 64 and len(broad) == len(populations[2]) == 64,
            "Both unchanged development references must contain 64 unique groups")
    for row in dev + broad:
        verify_row(row)


def load_family_boundary_inputs(cfg, tokenizer=None):
    repo, root = REPO_ROOT, Path(cfg["data_dir"])
    require(sha256_file(root / "manifest.json") == cfg["data_manifest_sha256"], "Frozen boundary manifest changed")
    manifest = json.loads((root / "manifest.json").read_text())
    require(manifest.get("status") == STATUS and manifest.get("family") == "identity_absent"
            and manifest.get("planned_arms") == list(PLANNED_ARMS)
            and cfg["arm"] in PLANNED_ARMS, "Unknown boundary dataset or unplanned training arm")
    expected = {"mode": "scientific_pilot", "model_role": "main", "seed": 31, "eval_seed": 17,
                "batch_size": 4, "microbatch_size": 2, "steps": 1024, "max_length": 384,
                "max_new_tokens": 384, "learning_rate": 5e-5, "weight_decay": .01, "grad_clip": 1.0}
    require(all(cfg.get(key) == value for key, value in expected.items()), "Boundary model/recipe/seed/dose changed")
    require(manifest["model"] == MODEL and manifest["paired_seed"] == manifest["selection_seed"] == 31
            and manifest["eval_seed"] == 17, "Manifest model or seeds changed")
    require(manifest["original_files_sha256"] == ORIGINAL_HASHES, "Original-byte provenance changed")
    require(sha256_file(repo / "configs/models.lock.json") == manifest["model_lock_sha256"], "Model lock changed")
    require(set(manifest["files_sha256"]) == DATA_FILES, "Manifest file inventory is incomplete or unexpected")
    for name, digest in manifest["files_sha256"].items():
        require(Path(name).name == name and sha256_file(root / name) == digest, "Frozen boundary artifact changed: " + name)
    problems, copied = load_original_inputs(repo)
    for name, original in copied.items():
        require((root / name).read_bytes() == original, "Development/split bytes differ from original")
    sources = load_candidate_sources(repo, manifest["candidate_sources"])
    blocks, rows, schedule, selection, cycles = build_boundary_payload(problems, sources)
    require(json.loads((root / "train_blocks.json").read_text()) == blocks, "Frozen training blocks differ from source selection")
    require(json.loads((root / "selection_audit.json").read_text()) == selection, "Frozen selection audit differs from reconstruction")
    for arm in ARMS:
        require(read_jsonl(root / f"train_{arm}.jsonl") == rows[arm], "Frozen training rows differ from reconstruction: " + arm)
    require(manifest["schedule_file"] == "schedule_seed31.json"
            and json.loads((root / manifest["schedule_file"]).read_text()) == schedule
            and canonical_hash(schedule) == manifest["schedule_canonical_sha256"], "Schedule differs from full seeded reconstruction")
    require(manifest["cycles"] == cycles and manifest["training_blocks"] == len(blocks)
            and manifest["training_questions"] == 4 * len(blocks) and manifest["optimizer_updates"] == 1024,
            "Manifest scale does not match the selected complete-cycle schedule")
    dev, broad = read_jsonl(root / "dev_matched.jsonl"), read_jsonl(root / "dev_broad.jsonl")
    check_split_membership([item["problem"] for block in blocks for item in block["problems"]], dev, broad,
                           json.loads((root / "split_allocation.json").read_text()))
    audit = audit_boundary_encoding(blocks, rows, schedule, tokenizer) if tokenizer is not None else None
    if audit is not None:
        require(audit == json.loads((root / "matching_audit.json").read_text()), "Recomputed tokenizer/budget audit differs from frozen audit")
        require(manifest["budget_per_arm"] == audit["arms"], "Manifest budgets differ from actual schedules")
    return rows[cfg["arm"]], dev, broad, schedule, audit

"""Independent CPU audit of the 128-question identity-absent boundary pair.

No producer reconstruction, sampler, budget-report or arithmetic parser is used.
Compatibility files and unchanged dev/split copies are checked by bytes only;
the two planned training arms receive full arithmetic, encoding and dose checks.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
from fractions import Fraction
import json
from pathlib import Path
import random
import re
import subprocess

from scripts.audit_matching_selection import aggregate_numeric_residuals, characterize, FEATURES
from scripts.verify_family_matching import (
    TRAIN_HASH, TRAIN_FILE, independent_encoding, require, sha,
    verify_expression_record, verify_tokenizer_files,
)


ARMS = ("paths", "gcm")
MODEL = {"repo_id": "Qwen/Qwen2.5-1.5B", "revision": "8faed761d45a263340a0528343f099c05c9a4323",
         "tokenizer_revision": "8faed761d45a263340a0528343f099c05c9a4323", "kind": "base"}
PREPARATION_SOURCES = {
    "scripts/prepare_absent_boundary.py", "src/family_boundary_runtime.py", "src/pilot_data.py",
    "src/sft_data.py", "src/countdown_smoke.py", "scripts/audit_matching_selection.py",
    "scripts/audit_pilot_structure_bias.py", "scripts/audit_family_matching.py", "configs/models.lock.json",
    *(f"reports/absent_support_20260909_r1/{name}.json" for name in ("summary", "packing", "selection")),
}
COPIED_HASHES = {
    "dev_matched.jsonl": "c83bfcf156b53f6c75f443981d79045b1394f1d7383d17ba46d3200d23181cd3",
    "dev_broad.jsonl": "88ac632dfa1d4d5ac3e757021162156c8ac8891d6124cc040db97f38b4f81e73",
    "split_allocation.json": "8cfa236b3cfd1a29b7ef18ba126737672b3946bfbe206a80162a2de48a657143",
}


def canonical_hash(value):
    return sha(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def provenance_header(manifest):
    require(set(manifest["source_files_sha256"]) == PREPARATION_SOURCES, "Preparation source inventory differs")
    require(manifest["model"] == MODEL and manifest["source_worktree_dirty"] is False
            and manifest["gpu_seconds_added"] == 0 and manifest["model_or_development_outputs_read"] is False,
            "Invalid preparation model/provenance")
    require(manifest["candidate_join_complete"] is True and manifest["candidate_packing_blocks"] == 33
            and set(manifest["candidate_sources"]) == {"summary", "packing", "selection"}, "Candidate provenance differs")
    require(manifest["schedule_file"] == "schedule_seed31.json"
            and manifest["compatibility_only_arms"] == ["repeat", "surface"]
            and manifest["group_disjoint_before_augmentation"] is True, "Frozen schedule/compatibility/split claims differ")


def selected_packing_blocks(packing, count=32):
    require(type(count) is int and count == 32, "This audit is frozen for the 32-block tier")
    ordered = sorted(packing["blocks"], key=lambda block:
                     (block["group_id"], tuple(block["representative"]["structures"]), tuple(block["problem_ids"])))
    require(len(ordered) >= count, "Insufficient blocks for the frozen 128-question tier")
    random.Random(31).shuffle(ordered)
    return ordered[:count], ordered[count:]


def seeded_schedule(block_count, cycles, seed=31):
    rng, schedule = random.Random(seed), []
    for _ in range(cycles):
        order, rounds = list(range(block_count)), list(range(4))
        rng.shuffle(order)
        rng.shuffle(rounds)
        for round_id in rounds:
            for block_id in order:
                indices = [block_id * 16 + round_id * 4 + q for q in range(4)]
                rng.shuffle(indices)
                schedule.append(indices)
    return schedule


def expected_main_rows(blocks):
    rng, result = random.Random(31), {arm: [] for arm in ARMS}
    for block_id, block in enumerate(blocks):
        assignment = list(range(4))
        rng.shuffle(assignment)
        rng.randrange(4)  # The frozen compatibility anchor consumes one RNG draw.
        for round_id in range(4):
            for q, item in enumerate(block["problems"]):
                for arm in ARMS:
                    slot = (assignment[q] + (round_id if arm == "paths" else 0)) % 4
                    result[arm].append(dict(item["paths"][slot], block_id=block_id,
                                            round_id=round_id, rendering_id=0))
    return result


def independent_budget(rows, encoded, schedule):
    row_counts, problem_counts, path_counts, text_counts = Counter(), Counter(), Counter(), Counter()
    updates, padding = [], 0
    for batch in schedule:
        require(len(batch) == 4 and len(set(batch)) == 4
                and all(type(i) is int and 0 <= i < len(rows) for i in batch), "Invalid update row indices")
        selected = [encoded[i] for i in batch]
        lengths = [row["n_processed"] for row in selected]
        updates.append({"supervised_tokens": sum(row["n_supervised"] for row in selected),
                        "processed_tokens": sum(lengths)})
        padding += abs(lengths[0] - lengths[1]) + abs(lengths[2] - lengths[3])
        for index in batch:
            row, code = rows[index], encoded[index]
            row_counts[str(index)] += 1
            problem_counts[row["problem_id"]] += 1
            path_counts[json.dumps([row["problem_id"], row["path_id"]])] += 1
            text_counts[json.dumps([row["problem_id"], code["response_hash"]])] += 1
    return {"optimizer_updates": len(schedule), "presentations": sum(row_counts.values()),
            "supervised_response_tokens": sum(update["supervised_tokens"] for update in updates),
            "processed_nonpadding_tokens": sum(update["processed_tokens"] for update in updates),
            "padding_tokens": padding, "eos_supervised": True, "packing": False,
            "normalization": "sum_shifted_response_cross_entropy / update_response_token_count",
            "per_update": updates, "row_exposures": dict(row_counts), "problem_exposures": dict(problem_counts),
            "path_exposures": dict(path_counts), "text_exposures": dict(text_counts),
            "cross_condition_token_matching_claimed": False}


def audit_exposures(rows, encoded, schedule, *, expected_problems=128, cycles=8):
    budgets = {arm: independent_budget(rows[arm], encoded[arm], schedule) for arm in ARMS}
    require(len(schedule) == expected_problems * cycles, "Incomplete update dose")
    for arm in ARMS:
        budget = budgets[arm]
        require(len(rows[arm]) == expected_problems * 4, "Incorrect reference-row inventory")
        require(len(budget["problem_exposures"]) == expected_problems
                and set(budget["problem_exposures"].values()) == {cycles * 4}, "Per-problem exposure differs")
        require(len(budget["row_exposures"]) == len(rows[arm])
                and set(budget["row_exposures"].values()) == {cycles}, "Row dose differs")
        expected_paths = expected_problems * (4 if arm == "paths" else 1)
        expected_count = cycles if arm == "paths" else cycles * 4
        require(len(budget["path_exposures"]) == expected_paths
                and set(budget["path_exposures"].values()) == {expected_count}, "Paths/GCM distinct-path dose differs")
    for batch in schedule:
        first, second = ([rows[arm][i] for i in batch] for arm in ARMS)
        require([row["problem_id"] for row in first] == [row["problem_id"] for row in second], "Update problem sequence differs")
        require(len({row["problem_id"] for row in first}) == 4, "Update does not contain four different questions")
        require(Counter(row["structure_id"] for row in first) == Counter(row["structure_id"] for row in second),
                "Per-update structure histogram differs")
        operator_counts = []
        for group in (first, second):
            counts = Counter()
            for row in group:
                counts.update(row["numeric_features"]["operators"])
            operator_counts.append(counts)
        require(operator_counts[0] == operator_counts[1], "Per-update operator histogram differs")
        for i in batch:
            require(all(encoded["paths"][i][field] == encoded["gcm"][i][field]
                        for field in ("n_prompt", "n_supervised", "n_processed")), "Per-example exact token dose differs")
    for field in ("per_update", "supervised_response_tokens", "processed_nonpadding_tokens", "padding_tokens"):
        require(budgets["paths"][field] == budgets["gcm"][field], "Pair budget differs")
    return budgets


def _numeric_value(row, field):
    if field == "max_abs_intermediate":
        return max(abs(Fraction(value)) for value in row["numeric_features"]["exact_nonroot_intermediates"])
    return Fraction(row["numeric_features"][field])


def update_residuals(rows, schedule):
    histograms = {field: Counter() for field in FEATURES}
    for batch in schedule:
        for field in FEATURES:
            difference = sum((_numeric_value(rows["gcm"][i], field) - _numeric_value(rows["paths"][i], field)
                              for i in batch), Fraction())
            histograms[field][str(difference)] += 1
    return {"sign": "GCM minus Paths, per-update sum of four presentations",
            "histograms": {field: dict(sorted(counts.items())) for field, counts in histograms.items()},
            "updates_with_nonzero_residual": {field: len(schedule) - counts.get("0", 0) for field, counts in histograms.items()}}


def verify(data_dir, tokenizer_dir, out, repo=None):
    data_dir, tokenizer_dir, out = map(Path, (data_dir, tokenizer_dir, out))
    require(not out.exists(), "Refusing to overwrite independent CPU audit")
    repo = Path(repo) if repo is not None else Path(__file__).resolve().parents[1]
    manifest_bytes = (data_dir / "manifest.json").read_bytes()
    manifest = json.loads(manifest_bytes)
    require(manifest["status"] == "FROZEN_ABSENT_BOUNDARY_V1" and manifest["family"] == "identity_absent"
            and manifest["planned_arms"] == list(ARMS), "Wrong frozen training dataset")
    require(manifest["training_blocks"] == 32 and manifest["training_questions"] == 128 and manifest["cycles"] == 8
            and manifest["optimizer_updates"] == 1024 and manifest["selection_seed"] == manifest["paired_seed"] == 31
            and manifest["eval_seed"] == 17, "Frozen scale/seed/dose differs")
    provenance_header(manifest)
    commit = manifest["source_commit"]
    require(re.fullmatch("[0-9a-f]{40}", commit) is not None, "Invalid preparation commit")
    for name, digest in manifest["source_files_sha256"].items():
        require(not Path(name).is_absolute() and ".." not in Path(name).parts
                and name.startswith(("scripts/", "src/", "configs/", "reports/absent_support_20260909_r1/")), "Unexpected preparation source path")
        data = subprocess.check_output(["git", "show", commit + ":" + name], cwd=repo)
        require(sha(data) == digest, "Published preparation source differs")
    expected_files = {"train_blocks.json", "selection_audit.json", "schedule_seed31.json", "matching_audit.json",
                      *COPIED_HASHES, *("train_" + arm + ".jsonl" for arm in ("paths", "gcm", "repeat", "surface"))}
    require(set(manifest["files_sha256"]) == expected_files, "Frozen file manifest differs")
    blobs = {}
    for name, digest in manifest["files_sha256"].items():
        data = (data_dir / name).read_bytes()
        require(sha(data) == digest, "Frozen artifact hash differs")
        if name not in COPIED_HASHES:
            blobs[name] = data
    for name, digest in COPIED_HASHES.items():
        require(manifest["files_sha256"][name] == digest, "Copied development/split byte hash differs")
    require(manifest["original_files_sha256"] == {"train_blocks.json": TRAIN_HASH, **COPIED_HASHES}, "Original source hashes differ")
    original_bytes = (repo / TRAIN_FILE).read_bytes()
    require(sha(original_bytes) == TRAIN_HASH, "Original train pool changed")
    problems = {item["problem"]["problem_id"]: item["problem"] for block in json.loads(original_bytes) for item in block["problems"]}
    require(len(problems) == 256, "Original problem denominator differs")
    candidates = {}
    for name in ("summary", "packing", "selection"):
        item = manifest["candidate_sources"][name]
        require(item["path"] == f"reports/absent_support_20260909_r1/{name}.json", "Unexpected C012 candidate source")
        data = (repo / item["path"]).read_bytes()
        require(sha(data) == item["sha256"], "C012 candidate source hash differs")
        require(manifest["source_files_sha256"][item["path"]] == item["sha256"], "Candidate and published source hashes differ")
        candidates[name] = json.loads(data)
    summary, packing = candidates["summary"], candidates["packing"]
    require(summary["diagnostic_id"] == "C012" and summary["status"] == "complete"
            and summary["join_complete"] is True and summary["source_commit"] == manifest["candidate_source_commit"],
            "C012 complete-source gate differs")
    require(packing["input_join_complete"] is True and len(packing["blocks"]) == packing["primal_block_count"]
            == summary["packing_block_count"] == 33, "C012 packing gate differs")
    require(all(summary["output_sha256"][name + ".json"] == manifest["candidate_sources"][name]["sha256"]
                for name in ("packing", "selection")), "C012 summary/output linkage differs")
    chosen, omitted = selected_packing_blocks(candidates["packing"])
    blocks = json.loads(blobs["train_blocks.json"])
    require(len(blocks) == 32, "Expected 32 selected blocks")
    base_paths, selected_ids = [], []
    for block, candidate in zip(blocks, chosen):
        rep = candidate["representative"]
        require(block["structures"] == rep["structures"]
                and [item["problem"]["problem_id"] for item in block["problems"]] == candidate["problem_ids"], "Seed31 block selection/order differs")
        for item in block["problems"]:
            pid = item["problem"]["problem_id"]
            require(item["problem"] == problems[pid], "Selected fixed problem differs")
            expected = [slot["record"] for slot in rep["witnesses"][pid]["slots"]]
            require(item["paths"] == expected and len(expected) == 4
                    and len({row["ac_class"] for row in expected}) == 4
                    and [row["structure_id"] for row in expected] == block["structures"]
                    and len(set(block["structures"])) == 4, "Selected four-path witness differs")
            require(all(all(row[field] == item["problem"][field] for field in ("problem_id", "numbers", "target", "prompt"))
                        for row in expected), "Reference changed its selected problem")
            selected_ids.append(pid)
            base_paths.extend(expected)
    require(len(set(selected_ids)) == 128 and len(base_paths) == 512, "Selected problem/path inventory differs")
    lock_bytes = (repo / "configs/models.lock.json").read_bytes()
    require(sha(lock_bytes) == manifest["model_lock_sha256"], "Model lock hash differs")
    lock = json.loads(lock_bytes)["main"]
    require(all(lock[key] == value for key, value in MODEL.items()), "Main model recipe differs")
    tokenizer = verify_tokenizer_files(tokenizer_dir, lock, manifest["tokenizer"])
    for row in base_paths:
        require(verify_expression_record(row, tokenizer).identity_count == 0, "Selected reference contains a numerical identity")
    rows = {arm: [json.loads(line) for line in blobs["train_" + arm + ".jsonl"].splitlines()] for arm in ARMS}
    require(rows == expected_main_rows(blocks), "Seeded main training rows differ")
    encoded = {}
    for arm in ARMS:
        encoded[arm] = []
        for row in rows[arm]:
            require(verify_expression_record(row).identity_count == 0, "Main row is not identity-absent")
            code = independent_encoding(row["prompt"], row["response"], tokenizer)
            code.update(problem_id=row["problem_id"], path_id=row["path_id"])
            encoded[arm].append(code)
    schedule = json.loads(blobs["schedule_seed31.json"])
    require(schedule == seeded_schedule(32, 8) and canonical_hash(schedule) == manifest["schedule_canonical_sha256"], "Seed31 full schedule differs")
    budgets = audit_exposures(rows, encoded, schedule)
    audit = json.loads(blobs["matching_audit.json"])
    for arm in ARMS:
        require(audit["arms"][arm] == manifest["budget_per_arm"][arm] == budgets[arm], "Saved main-arm budget differs")
        require(audit["encoding_sha256_by_arm"][arm] == canonical_hash(encoded[arm]), "Main-arm full encoding hash differs")
    selection = json.loads(blobs["selection_audit.json"])
    stages = {name: candidates["selection"]["stages"][name]["problem_ids"] for name in candidates["selection"]["stage_order"]}
    stages["training_selected"] = sorted(selected_ids)
    expected_selection = characterize(problems, stages)
    require(all(selection[key] == value for key, value in expected_selection.items()), "Final selected strata differ")
    block_description = lambda block: {"group_id": block["group_id"], "problem_ids": block["problem_ids"],
                                       "structures": block["representative"]["structures"]}
    require(selection["selected_packing_blocks"] == [block_description(block) for block in chosen]
            and selection["omitted_packing_blocks"] == [block_description(block) for block in omitted], "Selected/omitted block receipt differs")
    excluded = sorted(set(problems) - set(selected_ids))
    require(selection["original_unselected_problem_ids"] == excluded, "Original excluded IDs differ")
    phases = {"selected_path_inventory": {"unit": "ordered_inventory_rows", "conditions": {"identity_absent": base_paths}},
              "scheduled_presentations": {"unit": "scheduled_presentations", "conditions": {
                  "identity_absent_" + arm: [rows[arm][i] for batch in schedule for i in batch] for arm in ARMS}}}
    result = {"status": "verified", "created_utc": datetime.now(timezone.utc).isoformat(),
              "prepared_source_commit": commit, "training_blocks": 32, "training_questions": 128,
              "distinct_absent_reference_paths": 512, "optimizer_updates": 1024, "presentations_per_arm": 4096,
              "exposure_per_question": 32, "paths_exposure_per_distinct_path": 8, "gcm_exposure_per_assigned_path": 32,
              "budgets": budgets, "selected_strata": expected_selection,
              "excluded_strata": characterize(problems, {"original_unselected": excluded}),
              "numeric_residuals": aggregate_numeric_residuals(phases), "per_update_numeric_residuals": update_residuals(rows, schedule),
              "input_sha256": {"manifest.json": sha(manifest_bytes), **manifest["files_sha256"]},
              "verifier_sha256": sha(Path(__file__).read_bytes()),
              "verifier_dependencies_sha256": {name: sha((repo / name).read_bytes()) for name in
                                                ("scripts/verify_family_matching.py", "scripts/audit_matching_selection.py")},
              "limitations": ["Planned Paths/GCM receive full independent arithmetic, token and exposure checks; compatibility-only Repeat/Surface files are hash checked",
                              "Copied development/split artifacts are checked by bytes only; no development outcomes or reserved problems are parsed or evaluated",
                              "Numerical residuals and selection summaries are descriptive, not semantic-strategy or causal-mechanism evidence",
                              "CPU validation does not launch or authorize a GPU run"]}
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("x") as handle:
        json.dump(result, handle, sort_keys=True, indent=2, allow_nan=False)
        handle.write("\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", required=True)
    parser.add_argument("--tokenizer-dir", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    result = verify(args.data, args.tokenizer_dir, args.out)
    print(json.dumps({key: result[key] for key in ("status", "training_questions", "optimizer_updates", "presentations_per_arm")}, sort_keys=True))


if __name__ == "__main__":
    main()

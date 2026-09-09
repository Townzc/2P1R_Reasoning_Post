"""Fresh C013 compact exact CPU join and bounded packing; no GPU connection."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import gzip
import importlib.metadata
import json
from pathlib import Path
import subprocess
import time

from scripts.run_matching_completion import (INVENTORY_SHA, STREAM_SHA,
                                             SOURCE_NAMES as PREVIOUS_SOURCES,
                                             dump, expand_key, hash_stream,
                                             load_inputs, sha)
from scripts.audit_matching_selection import characterize
from src.block_packing import pack_support_groups
from src.path_family_matching_complete import record_reference
from src.path_family_matching_compact import compact_key_bytes, compact_supported_key_join


CONFIG = {"schema_version": 1, "diagnostic_id": "C013", "length_mode": "common",
          "join_seconds": 600, "packing_seconds": 60, "expected_records": 5774,
          "expected_problems": 66, "expected_pairs": 48429084}
SOURCE_NAMES = sorted(set(PREVIOUS_SOURCES + [
    "scripts/run_compact_join.py", "src/path_family_matching_compact.py",
    "tests/test_path_family_matching_compact.py",
    "docs/experiments/C013_compact_exact_join.md",
    "reports/complete_join_20260909_r1/summary.json",
]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--private-out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists() or args.private_out.exists():
        raise FileExistsError("Fresh immutable public and private output directories required")
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    if subprocess.check_output(["git", "status", "--porcelain", "--", *SOURCE_NAMES], text=True).strip():
        raise ValueError("Publish all C013 sources before real-inventory execution")
    tracked = set(subprocess.check_output(["git", "ls-files", "--", *SOURCE_NAMES], text=True).splitlines())
    if tracked != set(SOURCE_NAMES):
        raise ValueError("Every declared C013 source must be tracked")
    source_hashes = {name: sha(Path(name).read_bytes()) for name in SOURCE_NAMES}
    args.out.mkdir(parents=True)
    args.private_out.mkdir(parents=True)
    started = time.monotonic()
    summary = {"diagnostic_id": "C013", "config": CONFIG, "source_commit": commit,
               "source_sha256": source_hashes, "gpu_seconds_added": 0,
               "server_connected": False, "model_or_development_outputs_read": False,
               "inventory_compressed_sha256": INVENTORY_SHA, "inventory_stream_sha256": STREAM_SHA}
    try:
        summary["environment"] = {name: importlib.metadata.version(name) for name in ("numpy", "scipy", "networkx")}
        if summary["environment"]["scipy"] != "1.18.0":
            raise ValueError("C013 packing requires the registered SciPy 1.18.0 runtime")
        records, problems = load_inputs(args.inventory)
        old_path = Path("reports/family_matching_20260909_r1/per_problem.jsonl")
        old_summary = json.loads(Path("reports/family_matching_20260909_r1/summary.json").read_text())
        if sha(old_path.read_bytes()) != old_summary["output_sha256"][old_path.name]:
            raise ValueError("C009 completed per-problem filter changed")
        old = [json.loads(line) for line in old_path.read_text().splitlines()]
        lengths = {row["problem_id"]: row["structure_lengths"] for row in old}
        eligible = [row for row in records if row["encodable"] and row["n_supervised"] in lengths[row["problem_id"]]]
        if len(eligible) != CONFIG["expected_records"] or len({r["problem_id"] for r in eligible}) != CONFIG["expected_problems"]:
            raise ValueError("Necessary C009 filter no longer gives 5774 rows and 66 problems")
        lookup = {record_reference(row): row for row in eligible}
        archive = args.private_out / "compact_keys.jsonl.gz"
        print(json.dumps({"stage": "verified_inputs", "eligible_records": len(eligible), "source_commit": commit}), flush=True)
        with gzip.GzipFile(filename=str(archive), mode="xb", mtime=0) as writer:
            result = compact_supported_key_join(
                eligible, max_seconds=CONFIG["join_seconds"],
                on_key=lambda key: writer.write(compact_key_bytes(key)))
        with gzip.open(archive, "rb") as inp:
            stream_receipt = hash_stream(inp)
        with archive.open("rb") as inp:
            archive_receipt = hash_stream(inp)
        if stream_receipt["sha256"] != result["key_stream_sha256"]:
            raise ValueError("C013 compact stream digest mismatch")
        if result["complete"] and not (
                result["total_candidate_pairs"] == result["represented_pairs"] == CONFIG["expected_pairs"]
                and result["pruned_pairs"] + result["exact_pairs"] == result["represented_pairs"]
                and result["unrepresented_pairs"] == 0 and result["representatives_complete"]
                and result["ac_to_structure_functionality_verified"]):
            raise ValueError("C013 declared completeness does not satisfy finite-grid accounting")
        catalog, support_groups = result.pop("catalog"), result.pop("support_groups")
        dump(args.out / "catalog.json", catalog)
        dump(args.out / "support_groups.json", support_groups)
        result.update(catalog_file="catalog.json", support_groups_file="support_groups.json")
        dump(args.out / "join.json", result)
        stages = {name: sorted(row["problem_id"] for row in old if row[name])
                  for name in ("raw_disjoint", "token_matched", "structure_matched")}
        stages["shared_key_supported"] = result["supported_problem_ids"]
        if result["complete"]:
            groups = [{"problem_ids": group["problem_ids"], "representative": group["representative_key"]}
                      for group in support_groups]
            packing = pack_support_groups(groups, time_limit=CONFIG["packing_seconds"])
            packing.update(input_join_complete=True, optimality_scope="complete_key_universe",
                           global_optimal=packing["is_optimal"])
            for block in packing["blocks"]:
                selected = set(block["problem_ids"])
                representative = block["representative"]
                representative = dict(representative, problem_ids=block["problem_ids"],
                                      witnesses={pid: w for pid, w in representative["witnesses"].items() if pid in selected})
                block["representative"] = expand_key(representative, lookup)
            stages["packed"] = packing["used_problem_ids"]
            summary.update(packing_block_count=packing["primal_block_count"],
                           packing_proved_optimal=packing["is_optimal"],
                           packing_upper_bound=packing["integer_upper_bound"])
        else:
            packing = {"status": "not_run_incomplete_join", "input_join_complete": False,
                       "global_optimal": False, "reason": "Complete join and representative witnesses are required"}
        dump(args.out / "packing.json", packing)
        dump(args.out / "selection.json", characterize(problems, stages))
        if source_hashes != {name: sha(Path(name).read_bytes()) for name in SOURCE_NAMES}:
            raise ValueError("Declared source changed during C013 execution")
        summary.update(status="complete" if result["complete"] else "incomplete_join",
                       join_complete=result["complete"], private_key_archive=archive_receipt,
                       private_key_stream=stream_receipt, valid_key_count=result["valid_key_count"],
                       support_group_count=result["support_group_count"],
                       supported_problem_count=len(result["supported_problem_ids"]),
                       represented_pairs=result["represented_pairs"], total_candidate_pairs=result["total_candidate_pairs"])
    except Exception as exc:
        summary.update(status="failed", error_type=type(exc).__name__, error=str(exc))
        raise
    finally:
        summary.update(runtime_seconds=time.monotonic() - started,
                       completed_at_utc=datetime.now(timezone.utc).isoformat(),
                       output_sha256={path.name: sha(path.read_bytes()) for path in args.out.iterdir() if path.is_file()})
        dump(args.out / "summary.json", summary)
        print(json.dumps({k: v for k, v in summary.items() if k not in ("source_sha256", "output_sha256", "config")}, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()

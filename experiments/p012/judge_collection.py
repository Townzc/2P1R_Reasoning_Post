"""Combine G0 judge queues with unambiguous cell IDs; no inference or scoring."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re


def judge_id(group: str, original_id: str) -> str:
    if not re.fullmatch(r"[a-z0-9_]+", group):
        raise ValueError("Judge group must be a stable cell identifier")
    return json.dumps([group, original_id], separators=(",", ":"))


def merge_queues(groups: dict[str, Path], output: Path) -> dict:
    combined, index = [], {}
    if not groups:
        raise ValueError("Specify the completed G0 score directories")
    for group, directory in groups.items():
        payload = (directory / "judge_inputs.jsonl").read_bytes()
        original = [json.loads(line) for line in payload.splitlines() if line.strip()]
        source_manifest = json.loads((directory / "MANIFEST.json").read_text())
        digest = hashlib.sha256(payload).hexdigest()
        if digest != source_manifest["judge_inputs_sha256"]:
            raise ValueError("Original judge queue differs from the score manifest")
        if len({row["id"] for row in original}) != len(original):
            raise ValueError("Duplicate ID in original judge queue")
        combined.extend(row | {"id": judge_id(group, row["id"])} for row in original)
        index[group] = {"questions_to_judge": len(original), "original_queue_sha256": digest,
                        "parent_generation_raw_sha256": source_manifest["raw_sha256"]}
    payload = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in combined).encode()
    report = {"groups": index, "rows": len(combined),
              "combined_input_sha256": hashlib.sha256(payload).hexdigest()}
    output.mkdir(parents=True, exist_ok=False)
    (output / "inputs.jsonl").write_bytes(payload)
    (output / "GROUPS.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--group", action="append", required=True, help="cell=score_directory")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    pairs = [item.split("=", 1) for item in args.group]
    if len({group for group, _ in pairs}) != len(pairs):
        raise ValueError("Repeated cell name")
    print(json.dumps(merge_queues({group: Path(path) for group, path in pairs}, args.output)))


if __name__ == "__main__":
    main()

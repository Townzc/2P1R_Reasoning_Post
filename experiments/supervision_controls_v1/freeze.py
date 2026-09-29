"""Build new masks from verified existing annotations; no model calls."""
from __future__ import annotations

import argparse
from collections import Counter
import fcntl
import gzip
from pathlib import Path
import json

from .io import PHASE, NEW_ARMS, independent_output, read, sha, digest, save
from .masks import make_control


def freeze(prior, release, output):
    output, prior = independent_output(output, prior)
    release = Path(release)
    manifest = read(release/"manifest.json")
    if sha(release/"manifest.json") != "f7c67a1c523c3ec5dfbd1ae63506a9ce91dd03683643dcf3b7a72c70b16fa370":
        raise ValueError("Original input release differs")
    for name in ("tokenized_pilot.jsonl.gz", "dev.jsonl"):
        if sha(release/name) != manifest["files_sha256"][name]:
            raise ValueError("Original input bytes differ")
    with gzip.open(release/"tokenized_pilot.jsonl.gz", "rt") as f:
        rows = [json.loads(line) for line in f]
    by_id = {r["problem_id"]:r for r in rows}
    if len(rows) != 4096 or len(by_id) != 4096:
        raise ValueError("Training question coverage differs")
    old = read(prior/"TRAIN_CONTRACT.json")
    done = read(prior/"TRAINING_COMPLETE.json")
    masks = read(prior/"MASK_MANIFEST.json")
    if (done["contract_sha256"] != digest(old) or old["training_seed"] != 17 or
            old["mask_manifest_sha256"] != sha(prior/"MASK_MANIFEST.json") or
            masks["identity"] != old["scientific_identity"] or masks["count"] != 4096):
        raise ValueError("Historical mask/training identity differs")
    output.mkdir(parents=True, exist_ok=True)
    with (output/"FREEZE.lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        records = {name:[] for name in NEW_ARMS}
        seen = set()
        for item in masks["records"]:
            path = (prior/"annotations"/item["path"]).resolve()
            if (prior/"annotations").resolve() not in path.parents or sha(path) != item["sha256"]:
                raise ValueError("Invalid annotation path/hash")
            value = read(path)
            a, pid = value["annotation"], value["id"]
            if (pid != item["id"] or pid in seen or pid not in by_id or
                    value["identity"] != old["scientific_identity"] or
                    a["response_ids"] != by_id[pid]["response_ids"] or
                    digest(a["mask"]) != item["mask_sha256"]):
                raise ValueError("Historical annotation content differs")
            seen.add(pid)
            for condition in NEW_ARMS:
                control = make_control(pid, a, condition)
                save(output/"masks"/condition/(f"{len(seen)-1:04d}.json"), control)
                records[condition].append(dict(id=pid, path=f"{len(seen)-1:04d}.json",
                                               sha256=sha(output/"masks"/condition/(f"{len(seen)-1:04d}.json"))))
        if seen != set(by_id):
            raise ValueError("Missing annotation rows")
        contract = dict(old, phase=PHASE, arms=list(NEW_ARMS), scientific_endpoints=[128],
                        scientific_question="question-dependence beyond coarse position/difficulty",
                        inherited_training_contract_sha256=digest(old),
                        protocol_sha256=sha(Path(__file__).with_name("PROTOCOL.md")),
                        mask_control_source_sha256=sha(Path(__file__).with_name("masks.py")),
                        new_annotations=0, generation_cap=4096)
        summaries = {}
        for condition, roster in records.items():
            save(output/"masks"/condition/"MANIFEST.json", dict(condition=condition, records=roster))
            values = [read(output/"masks"/condition/r["path"]) for r in roster]
            summaries[condition] = dict(questions=len(values), selected=sum(v["K"] for v in values),
                overlap=sum(v["overlap_with_qdw"] for v in values),
                forced_overlap_lower_bound=sum(v["forced_overlap_lower_bound"] for v in values),
                changed_masks=sum(v["changed_mask"] for v in values), zero_K=sum(v["K"]==0 for v in values),
                selected_token_weighted_nll_difference=sum(v["K"]*(v["control_mean_nll"]-v["original_mean_nll"])
                    for v in values if v["K"]) / max(1,sum(v["K"] for v in values)),
                selected_token_weighted_position_difference=sum(v["K"]*(v["control_mean_relative_position"]-v["original_mean_relative_position"])
                    for v in values if v["K"]) / max(1,sum(v["K"] for v in values)))
        contract["control_mask_manifests_sha256"] = {name:sha(output/"masks"/name/"MANIFEST.json") for name in NEW_ARMS}
        save(output/"TRAIN_CONTRACT.json", contract)
        save(output/"MASK_AUDIT.json", dict(summary=summaries, coarse_matching_not_exact_continuous_balance=True,
                                          source_annotation_manifest_sha256=sha(prior/"MASK_MANIFEST.json")))
        save(output/"FROZEN.json", dict(contract_sha256=digest(contract), mask_audit_sha256=sha(output/"MASK_AUDIT.json"),
                                       questions=4096, new_annotation_forwards=0))
        return summaries


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for key in ("prior", "release", "output"):
        p.add_argument("--"+key, required=True)
    args=p.parse_args()
    print(json.dumps(freeze(args.prior, args.release, args.output), sort_keys=True))

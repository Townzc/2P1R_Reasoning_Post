"""Independent streaming and finite-grid audit of C010, without tokenization.

No production matcher is imported.  The exact support check exploits a property
that is first validated on every fixed inventory row: a numerical AC class has
one operator-only structure.  The eight slots therefore decompose by structure
into components of size one or two.  Each two-slot component needs nonempty
family choices and an AC-class union of size at least two (Hall's condition).
This checks negative as well as positive keys without rerunning expression search.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import gzip
import hashlib
import itertools
import json
from pathlib import Path
import subprocess
import time


FAMILIES = ("identity_present", "identity_absent")
INVENTORY_SHA = "ba890778096197a3f9683cf6d6b4a4675dcc930ff41c5e8ec977ab84611c8ed0"
INVENTORY_STREAM_SHA = "4302986b7f74c390ed740720715326e3e3db422649031204ab131dae55e0e58e"
TRAIN_SHA = "e15857122ad9148a1a209cce7c8ef4c107ff0de27bcfe11b97ba6fce6b7a2cea"
# The C009 per-problem digest is read from its hash-checked source snapshot;
# this module never uses training/development model predictions.


class AuditFailure(Exception):
    pass


class AuditDeadline(Exception):
    def __init__(self, message, counters):
        super().__init__(message)
        self.counters = dict(counters)


def require(condition, message):
    if not condition:
        raise AuditFailure(message)


def canonical(record):
    return json.dumps(record, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("utf-8")


def digest_file(path):
    digest, size = hashlib.sha256(), 0
    with Path(path).open("rb") as inp:
        for chunk in iter(lambda: inp.read(1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)
    return {"sha256": digest.hexdigest(), "bytes": size}


def at_least_four(mask):
    for _ in range(3):
        mask &= mask - 1
    return bool(mask)


def key_signature(key):
    si, sn = tuple(key["identity_structures"]), tuple(key["nonidentity_structures"])
    require(len(si) == len(sn) == 4 and len(set(si)) == len(set(sn)) == 4,
            "Key does not have four distinct structures per family")
    require(si == tuple(sorted(si)) and sn == tuple(sorted(sn)), "Unsorted structure key")
    return si, sn


def exact_support(si, sn, occurrence_mask, occurrences, class_sets):
    """Independent exact test, conditional on validated AC -> structure mapping."""
    overlap = set(si) & set(sn)
    found = {}
    while occurrence_mask:
        low = occurrence_mask & -occurrence_mask
        pid, length = occurrences[low.bit_length() - 1]
        occurrence_mask ^= low
        if pid in found:
            continue  # Occurrences are sorted by pid and increasing length.
        feasible = True
        for structure in overlap:
            union = (class_sets[(pid, length, FAMILIES[0], structure)] |
                     class_sets[(pid, length, FAMILIES[1], structure)])
            if union & (union - 1) == 0:
                feasible = False
                break
        if feasible:
            found[pid] = length
    return found


def audit(report_dir, key_archive, inventory, *, max_seconds=300.0):
    started = time.monotonic()
    counters = {"stream_keys_checked": 0, "stream_witnesses_checked": 0,
                "stream_slots_checked": 0, "independent_pruned_pairs": 0,
                "independent_exact_pairs": 0, "independent_valid_keys": 0}

    def check():
        if time.monotonic() - started >= max_seconds:
            raise AuditDeadline("Independent audit deadline reached", counters)

    summary_path, join_path = report_dir / "summary.json", report_dir / "join.json"
    require(summary_path.is_file(), "C010 final summary must exist before audit")
    summary = json.loads(summary_path.read_text())
    join = json.loads(join_path.read_text())
    require(summary["diagnostic_id"] == "C010", "Wrong diagnostic")
    require(summary["join_complete"] and join["complete"], "Cannot certify an incomplete join")
    require(join["length_mode"] == "common", "Audit requires original common-length design")
    for name, expected in summary["output_sha256"].items():
        require(digest_file(report_dir / name)["sha256"] == expected, f"Changed output: {name}")
    for name, expected in summary["source_sha256"].items():
        check()
        snapshot = subprocess.check_output(["git", "show", f"{summary['source_commit']}:{name}"])
        require(hashlib.sha256(snapshot).hexdigest() == expected, f"Committed source hash mismatch: {name}")
    old_source = Path("reports/family_matching_20260909_r1/per_problem.jsonl")
    old_summary = json.loads(Path("reports/family_matching_20260909_r1/summary.json").read_text())
    require(digest_file(old_source)["sha256"] == old_summary["output_sha256"][old_source.name],
            "Changed completed C009 per-problem stage records")
    require(digest_file(old_source)["sha256"] == summary["source_sha256"][str(old_source)],
            "C009 filter differs from C010 execution snapshot")
    lengths = {p["problem_id"]: set(p["structure_lengths"])
               for p in map(json.loads, old_source.read_text().splitlines())}
    train = Path("runs/pilot_v1_20260908_r3/train_blocks.json")
    require(digest_file(train)["sha256"] == TRAIN_SHA, "Original train inputs changed")
    problems = {p["problem"]["problem_id"]: p["problem"]
                for block in json.loads(train.read_text()) for p in block["problems"]}
    require(len(problems) == 256, "Wrong original problem count")
    require(digest_file(inventory)["sha256"] == INVENTORY_SHA, "Changed tokenized archive")
    lookup, selected, ac_structure = {}, [], {}
    inventory_digest = hashlib.sha256()
    inventory_rows = 0
    with gzip.open(inventory, "rb") as inp:
        for line in inp:
            check()
            inventory_digest.update(line)
            row = json.loads(line)
            inventory_rows += 1
            pid, ac, structure = row["problem_id"], row["ac_class"], row["structure_id"]
            require(pid in problems and row["numbers"] == problems[pid]["numbers"]
                    and row["target"] == problems[pid]["target"], "Inventory problem identity mismatch")
            require(row["family"] in FAMILIES, "Unknown inventory family")
            coordinate = (pid, ac)
            require(coordinate not in ac_structure or ac_structure[coordinate] == structure,
                    "AC class maps to multiple structures: generic flow audit required")
            ac_structure[coordinate] = structure
            ref = hashlib.sha256(canonical(row)).hexdigest()
            lookup[ref] = row
            if row["encodable"] and row["n_supervised"] in lengths[pid]:
                selected.append(row)
    require(inventory_rows == 25846 and inventory_digest.hexdigest() == INVENTORY_STREAM_SHA,
            "Tokenized stream count or digest mismatch")
    pids = sorted({r["problem_id"] for r in selected})
    require(len(selected) == 5774 and len(pids) == 66, "Necessary filter does not reproduce C009")
    pid_positions = {pid: i for i, pid in enumerate(pids)}
    occurrences = sorted({(r["problem_id"], r["n_supervised"]) for r in selected})
    occurrence_positions = {value: i for i, value in enumerate(occurrences)}
    pid_masks, occurrence_masks = defaultdict(int), defaultdict(int)
    class_sets = defaultdict(int)
    class_ids = {ac: i for i, ac in enumerate(sorted({r["ac_class"] for r in selected}))}
    representative = {}
    for row in selected:
        pid, length, family, structure, ac = (row[k] for k in
                                            ("problem_id", "n_supervised", "family", "structure_id", "ac_class"))
        pid_masks[(family, structure)] |= 1 << pid_positions[pid]
        occurrence_masks[(family, structure)] |= 1 << occurrence_positions[(pid, length)]
        class_sets[(pid, length, family, structure)] |= 1 << class_ids[ac]
        coordinate = (pid, length, family, structure, ac)
        encoded = canonical(row)
        if coordinate not in representative or encoded < representative[coordinate][0]:
            representative[coordinate] = (encoded, hashlib.sha256(encoded).hexdigest())
    # Independent itertools enumeration; do not import the production DFS/helper.
    grouped, tuple_occurrences = {}, {}
    tuple_counts = {}
    for family in FAMILIES:
        domain = sorted(structure for f, structure in pid_masks if f == family
                        and at_least_four(pid_masks[(family, structure)]))
        masks = defaultdict(list)
        found = {}
        for structures in itertools.combinations(domain, 4):
            check()
            support = pid_masks[(family, structures[0])]
            occurrence = occurrence_masks[(family, structures[0])]
            for structure in structures[1:]:
                support &= pid_masks[(family, structure)]
                occurrence &= occurrence_masks[(family, structure)]
            if at_least_four(support):
                masks[support].append((structures, occurrence))
                found[structures] = occurrence
        grouped[family] = sorted(masks.items())
        tuple_occurrences[family] = found
        tuple_counts[family] = len(found)
    require(tuple_counts == join["frequent_tuples_by_family"], "Independent tuple counts disagree")
    total = tuple_counts[FAMILIES[0]] * tuple_counts[FAMILIES[1]]
    require(total == join["total_candidate_pairs"] == 48429084, "Finite pair grid mismatch")
    require(join["pruned_pairs"] + join["exact_pairs"] == join["represented_pairs"] == total,
            "Producer pair accounting does not close")
    require(join["unrepresented_pairs"] == 0, "Unrepresented pairs remain")
    print(json.dumps({"audit_stage": "inventory_and_tuple_grid_verified", "total_pairs": total}), flush=True)
    stream_digest, stream_size = hashlib.sha256(), 0
    emitted, groups_seen = {}, {}
    with gzip.open(key_archive, "rb") as inp:
        for line in inp:
            check()
            stream_digest.update(line)
            stream_size += len(line)
            key = json.loads(line)
            require(canonical(key) + b"\n" == line, "Noncanonical key stream encoding")
            si, sn = sig = key_signature(key)
            require(sig not in emitted, "Duplicate structure-pair key in stream")
            support = tuple(key["problem_ids"])
            require(len(support) >= 4 and support == tuple(sorted(set(support))), "Invalid key support list")
            require(set(key["witnesses"]) == set(support), "Witness/support mismatch")
            witness_lengths = {}
            for pid, witness in key["witnesses"].items():
                require(pid in pid_positions and witness["problem_id"] == pid, "Unknown witness problem")
                length = witness["n_supervised"]
                require(length in lengths[pid], "Witness uses filtered-out length")
                witness_lengths[pid] = length
                slots = witness["slots"]
                require(len(slots) == 8 and len({s["ac_class"] for s in slots}) == 8,
                        "Witness does not contain eight distinct AC classes")
                for family, structures in zip(FAMILIES, (si, sn)):
                    chosen = [s for s in slots if s["family"] == family]
                    require(sorted(s["structure_id"] for s in chosen) == list(structures),
                            "Witness slot structures disagree with key")
                for slot in slots:
                    ref = slot["record_ref"]
                    require(ref in lookup, "Unresolved record reference")
                    row = lookup[ref]
                    require(row["encodable"] and row["problem_id"] == pid and row["n_supervised"] == length,
                            "Referenced row violates problem or length constraint")
                    require(all(row[k] == slot[k] for k in ("family", "structure_id", "ac_class")),
                            "Referenced row disagrees with slot")
                    coordinate = (pid, length, slot["family"], slot["structure_id"], slot["ac_class"])
                    require(representative[coordinate][1] == ref, "Noncanonical coordinate representative")
                    counters["stream_slots_checked"] += 1
                counters["stream_witnesses_checked"] += 1
            occurrence = tuple_occurrences[FAMILIES[0]][si] & tuple_occurrences[FAMILIES[1]][sn]
            actual = exact_support(si, sn, occurrence, occurrences, class_sets)
            require(actual == witness_lengths, "Key support omits/adds a problem or does not choose lowest length")
            emitted[sig] = tuple(sorted(actual.items()))
            encoded_hash = hashlib.sha256(line).hexdigest()
            group = groups_seen.setdefault(support, {"count": 0, "minimum": sig, "hash": encoded_hash})
            group["count"] += 1
            if sig < group["minimum"]:
                group["minimum"], group["hash"] = sig, encoded_hash
            counters["stream_keys_checked"] += 1
    require(stream_digest.hexdigest() == join["key_stream_sha256"] == summary["private_key_stream"]["sha256"],
            "Key stream digest mismatch")
    require(stream_size == summary["private_key_stream"]["bytes"], "Key stream byte count mismatch")
    require(digest_file(key_archive) == summary["private_key_archive"], "Key gzip receipt mismatch")
    require(len(emitted) == join["valid_key_count"] == join["counters"]["valid_key_count"],
            "Valid-key count mismatch")
    require(len(groups_seen) == join["support_group_count"] == len(join["support_groups"]),
            "Exact-support group count mismatch")
    for group in join["support_groups"]:
        support = tuple(group["problem_ids"])
        require(support in groups_seen, "Unknown exact-support group")
        observed = groups_seen[support]
        require(group["valid_key_count"] == observed["count"], "Group multiplicity mismatch")
        representative_key = group["representative_key"]
        require(key_signature(representative_key) == observed["minimum"], "Group representative is not lexicographic minimum")
        require(hashlib.sha256(canonical(representative_key) + b"\n").hexdigest() == observed["hash"],
                "Group representative differs from emitted witness")
    supported = sorted({pid for support in groups_seen for pid in support})
    require(supported == join["supported_problem_ids"], "Supported-problem union mismatch")
    print(json.dumps({"audit_stage": "full_stream_verified", "valid_keys": len(emitted)}), flush=True)
    # Enumerate every surviving pair independently, including keys absent from
    # the stream, to test completeness rather than only validating witnesses.
    remaining_keys = set(emitted)
    for mask_i, tuples_i in grouped[FAMILIES[0]]:
        for mask_n, tuples_n in grouped[FAMILIES[1]]:
            check()
            if not at_least_four(mask_i & mask_n):
                counters["independent_pruned_pairs"] += len(tuples_i) * len(tuples_n)
                continue
            for si, oi in tuples_i:
                for sn, on in tuples_n:
                    check()
                    support = exact_support(si, sn, oi & on, occurrences, class_sets)
                    sig = (si, sn)
                    if len(support) >= 4:
                        require(sig in emitted and emitted[sig] == tuple(sorted(support.items())),
                                "Full finite audit found an omitted or altered valid key")
                        remaining_keys.remove(sig)
                        counters["independent_valid_keys"] += 1
                    else:
                        require(sig not in emitted, "Full finite audit found an invalid emitted key")
                    counters["independent_exact_pairs"] += 1
    require(not remaining_keys, "Emitted keys were not covered by finite audit")
    require(counters["independent_pruned_pairs"] == join["pruned_pairs"], "Independent pruned-pair count mismatch")
    require(counters["independent_exact_pairs"] == join["exact_pairs"], "Independent exact-pair count mismatch")
    require(counters["independent_pruned_pairs"] + counters["independent_exact_pairs"] == total,
            "Independent finite accounting does not close")
    require(counters["independent_valid_keys"] == len(emitted), "Independent valid-key total mismatch")
    return {"status": "passed", "audit_complete": True, "diagnostic_id": "C010",
            "producer_source_commit": summary["source_commit"], "total_candidate_pairs": total,
            "frequent_tuples_by_family": tuple_counts, "eligible_records": len(selected),
            "eligible_problems": len(pids), "inventory_rows": inventory_rows,
            "ac_to_structure_function_verified": True,
            "support_group_count": len(groups_seen), "supported_problem_count": len(supported),
            "supported_problem_ids": supported, "key_stream_sha256": stream_digest.hexdigest(),
            "source_summary_sha256": digest_file(summary_path)["sha256"],
            "source_join_sha256": digest_file(join_path)["sha256"], "counters": counters,
            "verification_method": "Independent itertools tuple enumeration and exact occurrence-mask Hall checks after validating AC-to-structure functionality; full positive and negative candidate-key audit",
            "scope_limits": ["No retokenization, expression enumeration, model inference, or development/holdout reads",
                             "Legality and numerical-family semantics inherit the byte-verified C009 inventory",
                             "MILP optimality is outside this join audit"],
            "elapsed_seconds": time.monotonic() - started}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--keys", type=Path, required=True)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--max-seconds", type=float, default=300)
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError("Fresh immutable audit output required")
    require(0 < args.max_seconds < float("inf"), "Positive finite audit deadline required")
    try:
        result = audit(args.report, args.keys, args.inventory, max_seconds=args.max_seconds)
    except (AuditFailure, AuditDeadline) as exc:
        result = {"status": "incomplete" if isinstance(exc, AuditDeadline) else "failed",
                  "audit_complete": False, "error": str(exc)}
        if isinstance(exc, AuditDeadline):
            result["counters"] = exc.counters
    result.update(completed_at_utc=datetime.now(timezone.utc).isoformat(),
                  verifier_source_sha256=digest_file(Path(__file__))["sha256"],
                  gpu_seconds_added=0)
    with args.out.open("x") as out:
        json.dump(result, out, sort_keys=True, indent=2, allow_nan=False)
        out.write("\n")
    print(json.dumps(result, sort_keys=True), flush=True)
    if result["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()

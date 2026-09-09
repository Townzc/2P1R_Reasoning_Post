"""Independent C011/C012 checks against the already verified C009 archive.

No producer matching/selection/packing implementation is imported. Four-slot
support uses NetworkX bipartite matching; C011 flow uses preflow-push. Original
token byte verification is inherited only after checking the pinned inventory
and the earlier independent receipt. Arithmetic and numeric metadata are checked
again, without re-tokenizing every record.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from fractions import Fraction
import gzip
import itertools
import json
import math
from pathlib import Path
import re
import subprocess
import time

import networkx as nx

from scripts.verify_family_matching import (
    FAMILIES, TRAIN_FILE, TRAIN_HASH, expected_prompt, require, sha,
    verify_expression_record,
)


INVENTORY_HASH = "ba890778096197a3f9683cf6d6b4a4675dcc930ff41c5e8ec977ab84611c8ed0"
STREAM_HASH = "4302986b7f74c390ed740720715326e3e3db422649031204ab131dae55e0e58e"
PRIOR_RECEIPT_HASH = "22c567dcb5271af4a70de7f9b1402074c419352791ce47f278042884bdef05a2"
SOURCE_NAMES = {
    "scripts/run_matching_completion.py", "scripts/diagnose_family_lengths.py",
    "scripts/audit_legal_support.py", "scripts/audit_pilot_structure_bias.py", "src/countdown_smoke.py",
    "scripts/audit_matching_selection.py", "src/path_family_matching_complete.py",
    "src/path_family_matching.py", "src/block_packing.py", "src/single_family_matching.py",
    "configs/diagnostics/matching_completion_v1.json",
    "docs/experiments/C010_complete_support_join.md", "docs/experiments/C011_family_length_diagnostic.md",
    "docs/experiments/C012_identity_absent_boundary_preparation.md",
    "reports/family_matching_20260909_r1/summary.json", "reports/family_matching_20260909_r1/per_problem.jsonl",
}
FLAGS = ("target_ge_41", "input_one", "consecutive_pair", "target_is_input",
         "target_is_input_plus_one", "preview_template")


def record_ref(record):
    return sha(json.dumps(record, sort_keys=True, separators=(",", ":"), allow_nan=False).encode())


def fixed_structure_matching(rows, structures):
    """Four fixed slots -> four different classes, via Hopcroft-Karp."""
    require(len(structures) == 4 and len(set(structures)) == 4, "Four distinct structures required")
    left = [("slot", structure) for structure in structures]
    graph = nx.Graph()
    graph.add_nodes_from(left, bipartite=0)
    allowed = set(structures)
    for row in rows:
        if row["structure_id"] in allowed:
            graph.add_edge(("slot", row["structure_id"]), ("class", row["ac_class"]))
    matching = nx.algorithms.bipartite.maximum_matching(graph, top_nodes=left)
    return all(node in matching for node in left)


def _two_family_support(rows, structures_required):
    classes = {family: {row["ac_class"] for row in rows if row["family"] == family} for family in FAMILIES}
    if min(map(len, classes.values())) < 4 or len(set.union(*classes.values())) < 8:
        return False
    if not structures_required:
        return True
    graph = nx.DiGraph()
    source, sink = ("source",), ("sink",)
    for family in FAMILIES:
        graph.add_edge(source, ("family", family), capacity=4)
    for row in rows:
        family, structure, ac = row["family"], row["structure_id"], row["ac_class"]
        graph.add_edge(("family", family), ("structure", family, structure), capacity=1)
        graph.add_edge(("structure", family, structure), ("class", ac), capacity=1)
        graph.add_edge(("class", ac), sink, capacity=1)
    return nx.maximum_flow_value(graph, source, sink, flow_func=nx.algorithms.flow.preflow_push) == 8


def _index(records, family=None):
    groups = defaultdict(lambda: defaultdict(list))
    for row in records:
        if row["encodable"] and (family is None or row["family"] == family):
            groups[row["problem_id"]][row["n_supervised"]].append(row)
    return groups


def verify_family_witness(rows, pid, pair, inventory):
    require(len(rows) == 8 and len({row["ac_class"] for row in rows}) == 8,
            "C011 needs eight different classes")
    for family, length in zip(FAMILIES, pair):
        selected = [row for row in rows if row["family"] == family]
        require(len(selected) == 4 and len({row["structure_id"] for row in selected}) == 4,
                "C011 needs four structures per family")
        for row in selected:
            require(row["problem_id"] == pid and row["n_supervised"] == length
                    and inventory.get(record_ref(row)) == row, "C011 family length/record mismatch")


def verify_lengths(payload, records, problems):
    grouped = _index(records)
    names = ("common_class", "common_structure", "per_family_class", "per_family_structure")
    public = {row["problem_id"]: row for row in payload["per_problem"]}
    require(len(public) == len(payload["per_problem"]) and set(public) == set(problems), "C011 problem coverage differs")
    inventory = {record_ref(row): row for row in records}
    stages, pair_count, witnesses = {name: [] for name in names}, 0, 0
    for pid in sorted(problems):
        row, lengths = public[pid], grouped[pid]
        require(all(row[field] == problems[pid][field] for field in ("numbers", "target")), "C011 fixed problem differs")
        family_rows = {family: {length: [r for r in rows if r["family"] == family]
                               for length, rows in lengths.items()} for family in FAMILIES}
        eligible = {family: sorted(length for length, rows in family_rows[family].items()
                                  if len({r["ac_class"] for r in rows}) >= 4) for family in FAMILIES}
        require(row["individual_family_class_lengths"] == eligible, "C011 individual length support differs")
        require(row["individual_family_lengths_intersect"] == bool(set(eligible[FAMILIES[0]]) & set(eligible[FAMILIES[1]])),
                "C011 length intersection differs")
        pairs = {name: [] for name in names}
        for li, ln in itertools.product(eligible[FAMILIES[0]], eligible[FAMILIES[1]]):
            pair_count += 1
            selected = family_rows[FAMILIES[0]][li] + family_rows[FAMILIES[1]][ln]
            if _two_family_support(selected, False):
                pairs["per_family_class"].append([li, ln])
                if li == ln:
                    pairs["common_class"].append([li, ln])
                if _two_family_support(selected, True):
                    pairs["per_family_structure"].append([li, ln])
                    if li == ln:
                        pairs["common_structure"].append([li, ln])
        require(row["feasible_length_pairs"] == pairs, "C011 feasible length-pair list differs")
        require(row["flags"] == {name: bool(pairs[name]) for name in names}, "C011 cell flag differs")
        expected_witness_names = {name for name in ("common_structure", "per_family_structure") if pairs[name]}
        require(set(row["structure_witnesses"]) == expected_witness_names, "C011 witness categories differ")
        for name in expected_witness_names:
            verify_family_witness(row["structure_witnesses"][name], pid, pairs[name][0], inventory)
            witnesses += 1
        for name in names:
            if pairs[name]:
                stages[name].append(pid)
    require(payload["stage_ids"] == stages and payload["counts"] == {name: len(ids) for name, ids in stages.items()},
            "C011 aggregate cell counts differ")
    return {"stage_ids": stages, "counts": {name: len(ids) for name, ids in stages.items()},
            "length_pairs_checked": pair_count, "structure_witnesses_checked": witnesses}


def verify_single_keys(join, records, problems):
    require(join["complete"] is True and join["indexing_complete"] is True
            and join["stop_reason"] == "completed", "C012 complete certificate required")
    require(join["family"] == "identity_absent" and join["per_family"] == 4,
            "Unexpected C012 family/cardinality")
    groups = _index(records, "identity_absent")
    # Derive the entire finite local tuple universe independently; absent tuples
    # for a pid/L have an isolated matching slot and are therefore impossible.
    support, feasible_lengths = defaultdict(dict), defaultdict(set)
    tested, feasible = 0, 0
    for pid, lengths in sorted(groups.items()):
        require(pid in problems, "Unknown C012 problem")
        for length, rows in sorted(lengths.items()):
            structures = sorted({row["structure_id"] for row in rows})
            for key in itertools.combinations(structures, 4):
                tested += 1
                if fixed_structure_matching(rows, key):
                    feasible += 1
                    support[key].setdefault(pid, length)
                    feasible_lengths[pid].add(length)
    expected = {key: pids for key, pids in support.items() if len(pids) >= 4}
    public = {tuple(key["structures"]): key for key in join["keys"]}
    require(len(public) == len(join["keys"]) and set(public) == set(expected), "C012 full key listing differs")
    inventory = {record_ref(row): row for row in records}
    witness_count = 0
    for structures, support_at_length in expected.items():
        key = public[structures]
        require(key["problem_ids"] == sorted(support_at_length)
                and set(key["witnesses"]) == set(support_at_length), "C012 exact key support differs")
        for pid, lowest_length in support_at_length.items():
            witness = key["witnesses"][pid]
            verify_single_witness(witness, structures, inventory, pid, lowest_length)
            witness_count += 1
    computed_lengths = {pid: sorted(values) for pid, values in sorted(feasible_lengths.items())}
    require(join["per_problem_feasible_lengths"] == computed_lengths, "C012 local feasible lengths differ")
    indexed = sum(len(rows) for lengths in groups.values() for rows in lengths.values())
    expected_counters = {"input_records_seen": indexed, "family_records_indexed": indexed,
                         "other_family_records": 0, "excluded_unencodable_records": 0,
                         "problem_length_groups_completed": sum(len(lengths) for lengths in groups.values()),
                         "structure_combinations_tested": tested,
                         "class_assignment_checks_completed": tested,
                         "feasible_problem_length_keys": feasible,
                         "distinct_problem_key_support": sum(len(pids) for pids in support.values())}
    require(join["counters"] == expected_counters, "C012 full local-combination accounting differs")
    require(join["total_local_structure_combinations"] == tested and join["local_key_count"] == len(support)
            and join["shared_key_count"] == len(expected) and join["input_problem_count"] == len(groups),
            "C012 complete key totals differ")
    supported = sorted({pid for pids in expected.values() for pid in pids})
    require(join["supported_problem_ids"] == supported, "C012 support union differs")
    return {"local_combinations_checked": tested, "feasible_local_combinations": feasible,
            "shared_keys_checked": len(expected), "key_problem_witnesses_checked": witness_count,
            "supported_problem_ids": supported, "individual_family_feasible": sorted(feasible_lengths)}


def verify_single_witness(witness, structures, inventory, pid, length=None):
    require(witness["problem_id"] == pid, "Single-family witness problem differs")
    if length is not None:
        require(witness["n_supervised"] == length, "Witness does not use lowest feasible length")
    slots = witness["slots"]
    require(len(slots) == 4 and len({slot["ac_class"] for slot in slots}) == 4
            and sorted(slot["structure_id"] for slot in slots) == sorted(structures),
            "Single-family witness repeats class/structure")
    for slot in slots:
        if "record_ref" in slot:
            row = inventory.get(slot["record_ref"])
        else:
            row = slot.get("record")
            require(row is not None and inventory.get(record_ref(row)) == row, "Expanded witness record is altered")
        require(row is not None and row["problem_id"] == pid and row["family"] == "identity_absent"
                and row["n_supervised"] == witness["n_supervised"], "Single-family witness record differs")
        require(all(slot[field] == row[field] for field in ("family", "structure_id", "ac_class")),
                "Single-family slot metadata differs")


def component_upper_bound(support_sets):
    graph = nx.Graph()
    for support in support_sets:
        pids = sorted(support)
        graph.add_nodes_from(pids)
        if pids:
            graph.add_edges_from((pids[0], pid) for pid in pids[1:])
    components = sorted((sorted(component) for component in nx.connected_components(graph)), key=lambda ids: (len(ids), ids))
    return {"components": [{"problem_ids": ids, "size": len(ids), "block_upper_bound": len(ids) // 4}
                           for ids in components],
            "upper_bound": sum(len(ids) // 4 for ids in components),
            "proof": "Every feasible block is contained in one support set and therefore one connected component. Disjoint four-problem blocks in a component use at most floor(component_size/4) slots."}


def verify_packing(packing, join, records):
    groups = {}
    for key in join["keys"]:
        support = tuple(key["problem_ids"])
        if support not in groups or key["structures"] < groups[support]["structures"]:
            groups[support] = key
    ordered = sorted(groups)
    inventory = {record_ref(row): row for row in records}
    used, assigned, expected_blocks = set(), {}, []
    for item in packing["group_assignments"]:
        gid, ids, blocks = item["group_id"], item["problem_ids"], item["block_count"]
        require(type(gid) is int and 0 <= gid < len(ordered) and gid not in assigned,
                "Invalid/duplicate packing group ID")
        require(type(blocks) is int and blocks > 0 and len(ids) == 4 * blocks
                and ids == sorted(set(ids)), "Nonintegral or inconsistent group assignment")
        require(set(ids) <= set(ordered[gid]) and not used.intersection(ids), "Packing reuses/unsupported problem")
        require(item["representative"] == groups[ordered[gid]], "Packing group is not the lexicographic exact-support representative")
        used.update(ids)
        assigned[gid] = ids
        expected_blocks.extend((gid, ids[offset:offset + 4]) for offset in range(0, len(ids), 4))
    require(len(expected_blocks) == len(packing["blocks"]), "Packing block count disagrees with integral assignments")
    for block, (gid, ids) in zip(packing["blocks"], expected_blocks):
        require(block["group_id"] == gid and block["problem_ids"] == ids, "Concrete block partition differs")
        representative = block["representative"]
        key = groups[ordered[gid]]
        require(representative["structures"] == key["structures"] and representative["problem_ids"] == ids
                and set(representative["witnesses"]) == set(ids), "Block representative differs")
        for pid in ids:
            verify_single_witness(representative["witnesses"][pid], key["structures"], inventory, pid,
                                  key["witnesses"][pid]["n_supervised"])
    lower = len(expected_blocks)
    require(packing["primal_block_count"] == packing["block_count"] == lower
            and packing["selected_problem_ids"] == packing["used_problem_ids"] == sorted(used), "Packing primal totals differ")
    union = set().union(*(set(support) for support in ordered)) if ordered else set()
    require(packing["input_group_count"] == packing["group_variable_count"] == len(ordered)
            and packing["input_problem_count"] == len(union)
            and packing["assignment_variable_count"] == sum(map(len, ordered)), "Packing formulation dimensions differ")
    require(packing["elementary_upper_bound"] == min(len(union) // 4, sum(len(support) // 4 for support in ordered)),
            "Elementary upper bound differs")
    proof = component_upper_bound(ordered)
    independently_optimal = lower == proof["upper_bound"]
    require(lower <= packing["integer_upper_bound"] <= proof["upper_bound"], "Packing integer bound contradicts independent support bound")
    if packing["global_optimal"]:
        require(join["complete"] is True and packing["solver_status"] == 0
                and packing["integer_upper_bound"] == lower and independently_optimal,
                "Global optimality lacks matching independent upper certificate")
    require(packing["input_join_complete"] == join["complete"]
            and packing["optimality_scope"] == "complete_key_universe", "Packing completeness scope differs")
    return {"verified_integer_blocks": lower, "verified_selected_problem_ids": sorted(used),
            "independent_optimality_proved": independently_optimal, "combinatorial_upper_certificate": proof}


def _problem_flags(problem):
    numbers, target = problem["numbers"], problem["target"]
    require(len(numbers) == 4 and len(set(numbers)) == 4, "Selection inputs must remain distinct")
    positions = {number: index for index, number in enumerate(numbers)}
    witnesses = []
    if 1 in positions and target - 1 in positions and target - 1 != 1:
        others = sorted(set(numbers) - {1, target - 1})
        if len(others) == 2 and others[1] == others[0] + 1:
            witnesses.append({"one_index": positions[1], "pair_lower_index": positions[others[0]],
                              "pair_upper_index": positions[others[1]], "remaining_index": positions[target - 1],
                              "role_values": [1, others[0], others[1], target - 1]})
    return {"target_ge_41": target >= 41, "input_one": 1 in positions,
            "consecutive_pair": any(number + 1 in positions for number in numbers),
            "target_is_input": target in positions, "target_is_input_plus_one": target - 1 in positions,
            "preview_template": bool(witnesses), "preview_template_witnesses": witnesses}


def _stats(values):
    values = list(values)
    mean = Fraction(sum(values), len(values)) if values else None
    return {"count": len(values), "min": min(values) if values else None, "max": max(values) if values else None,
            "mean": float(mean) if mean is not None else None, "mean_exact": str(mean) if mean is not None else None}


def _description(ids, problems, labels):
    return {"count": len(ids), "problem_ids": sorted(ids),
            "counts": {flag: sum(labels[pid][flag] for pid in ids) for flag in FLAGS},
            "numbers": _stats(number for pid in ids for number in problems[pid]["numbers"]),
            "per_problem_input_min": _stats(min(problems[pid]["numbers"]) for pid in ids),
            "per_problem_input_max": _stats(max(problems[pid]["numbers"]) for pid in ids),
            "targets": _stats(problems[pid]["target"] for pid in ids),
            "target_histogram": dict(Counter(str(problems[pid]["target"]) for pid in ids))}


def _retention(ids, baseline, labels):
    require(set(ids) <= set(baseline), "Selection stages are not nested")
    ratio = lambda a, b: {"numerator": a, "denominator": b, "ratio": a / b if b else None}
    return {"overall": ratio(len(ids), len(baseline)),
            "strata": {flag: {str(value).lower(): ratio(sum(labels[pid][flag] == value for pid in ids),
                                                       sum(labels[pid][flag] == value for pid in baseline))
                              for value in (True, False)} for flag in FLAGS}}


def verify_selection(payload, problems, stages):
    labels = {pid: _problem_flags(problem) for pid, problem in problems.items()}
    require(payload["problem_flags"] == labels and payload["stage_order"] == list(stages), "Selection flag/order mismatch")
    original, previous, previous_name = sorted(problems), sorted(problems), "original"
    require(payload["original"] == _description(original, problems, labels), "Original selection denominator differs")
    require(set(payload["stages"]) == set(stages), "Selection stage names differ")
    for name, ids in stages.items():
        require(len(ids) == len(set(ids)), "Repeated selected ID")
        expected = {**_description(ids, problems, labels), "previous_stage": previous_name,
                    "retention_from_original": _retention(ids, original, labels),
                    "retention_from_previous": _retention(ids, previous, labels)}
        require(payload["stages"][name] == expected, "Selection statistics/retention differs")
        previous, previous_name = ids, name
    return {name: {"count": len(ids), "counts": _description(ids, problems, labels)["counts"]} for name, ids in stages.items()}


def verify_report(report, archive, out, repo=None):
    report, archive, out = map(Path, (report, archive, out))
    require(not out.exists(), "Refusing to overwrite independent verification")
    repo = Path(repo) if repo is not None else Path(__file__).resolve().parents[1]
    started = time.monotonic()
    summary_bytes = (report / "summary.json").read_bytes()
    summary = json.loads(summary_bytes)
    diagnostic = summary["diagnostic_id"]
    require(diagnostic in ("C011", "C012") and summary["status"] == "complete", "Expected a completed C011/C012 artifact")
    require(summary["gpu_seconds_added"] == 0 and summary["server_connected"] is False
            and summary["model_or_development_outputs_read"] is False, "Unexpected execution scope")
    require(set(summary["source_sha256"]) == SOURCE_NAMES, "Unexpected published source scope")
    commit = summary["source_commit"]
    require(re.fullmatch("[0-9a-f]{40}", commit) is not None, "Invalid execution commit")
    sources = {}
    for name, expected in summary["source_sha256"].items():
        data = subprocess.check_output(["git", "show", commit + ":" + name], cwd=repo)
        require(sha(data) == expected, "Published source hash mismatch")
        sources[name] = data
    train = (repo / TRAIN_FILE).read_bytes()
    require(sha(train) == TRAIN_HASH, "Original training pool hash differs")
    problems = {item["problem"]["problem_id"]: item["problem"]
                for block in json.loads(train) for item in block["problems"]}
    require(len(problems) == 256, "Expected 256 original problems")
    compressed = archive.read_bytes()
    require(sha(compressed) == INVENTORY_HASH == summary["inventory_compressed_sha256"], "Inventory compressed hash differs")
    stream = gzip.decompress(compressed)
    require(sha(stream) == STREAM_HASH == summary["inventory_stream_sha256"], "Inventory stream hash differs")
    prior_bytes = (repo / "reports/family_matching_20260909_r1/independent_verification.json").read_bytes()
    require(sha(prior_bytes) == PRIOR_RECEIPT_HASH, "Prior independent receipt changed")
    prior = json.loads(prior_bytes)
    require(prior["status"] == "verified" and prior["input_sha256"]["tokenized_stream"] == STREAM_HASH
            and prior["verifier_sha256"] == sha((repo / "scripts/verify_family_matching.py").read_bytes()),
            "Prior exact-token validation cannot be inherited")
    records = [json.loads(line) for line in stream.splitlines()]
    require(len(records) == 25846, "Original record count differs")
    seen = set()
    for row in records:
        key = row["problem_id"], row["expression"]
        require(key not in seen and row["problem_id"] in problems, "Repeated or unknown inventory record")
        seen.add(key)
        problem = problems[row["problem_id"]]
        require(all(row[field] == problem[field] for field in ("numbers", "target", "prompt")), "Original problem metadata differs")
        verify_expression_record(row)
    payloads = {}
    expected_names = {"length_diagnostic.json", "selection.json"} if diagnostic == "C011" else {"join.json", "packing.json", "selection.json"}
    require(set(summary["output_sha256"]) == expected_names, "Unexpected output manifest")
    for name, expected in summary["output_sha256"].items():
        data = (report / name).read_bytes()
        require(sha(data) == expected, "Frozen output hash mismatch")
        payloads[name] = json.loads(data)
    if diagnostic == "C011":
        checked = verify_lengths(payloads["length_diagnostic.json"], records, problems)
        require(summary["counts"] == checked["counts"], "C011 summary cells differ")
        selection = {}
        for mode in ("common", "per_family"):
            stages = {mode + "_class": checked["stage_ids"][mode + "_class"],
                      mode + "_structure": checked["stage_ids"][mode + "_structure"]}
            selection[mode] = verify_selection(payloads["selection.json"][mode], problems, stages)
        checked["selection"] = selection
    else:
        join, packing = payloads["join.json"], payloads["packing.json"]
        checked = verify_single_keys(join, records, problems)
        checked["packing"] = verify_packing(packing, join, records)
        require(summary["supported_problem_count"] == len(checked["supported_problem_ids"])
                and summary["packing_block_count"] == checked["packing"]["verified_integer_blocks"]
                and summary["packing_proved_optimal"] == checked["packing"]["independent_optimality_proved"],
                "C012 summary support/packing differs")
        checked["selection"] = verify_selection(payloads["selection.json"], problems,
            {"individual_family_feasible": checked["individual_family_feasible"],
             "shared_key_supported": checked["supported_problem_ids"],
             "packed": checked["packing"]["verified_selected_problem_ids"]})
    result = {"status": "verified", "diagnostic_id": diagnostic,
              "created_utc": datetime.now(timezone.utc).isoformat(), "verification_seconds": time.monotonic() - started,
              "source_commit": commit, "verified_inventory_rows": len(records), "checks": checked,
              "input_sha256": {"summary.json": sha(summary_bytes), **summary["output_sha256"],
                               "tokenized_inventory": INVENTORY_HASH, "tokenized_stream": STREAM_HASH,
                               "prior_independent_token_receipt": PRIOR_RECEIPT_HASH},
              "verifier_sha256": sha(Path(__file__).read_bytes()),
              "dependencies_sha256": {"scripts/verify_family_matching.py": sha((repo / "scripts/verify_family_matching.py").read_bytes())},
              "networkx_version": nx.__version__,
              "limitations": ["No new arithmetic solution enumeration, tokenization, model, GPU, development or holdout access",
                              "C011 cells describe mathematical constraint feasibility, not four model outcomes or a cross-family equal-dose design",
                              "C012 complete local-tuple support and packing apply only to the fixed verified numerical-family inventory",
                              "Selection/template summaries are descriptive and do not establish a reasoning mechanism or statistical adequacy"]}
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("x") as handle:
        json.dump(result, handle, sort_keys=True, indent=2, allow_nan=False)
        handle.write("\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", required=True)
    parser.add_argument("--archive", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    result = verify_report(args.report, args.archive, args.out)
    print(json.dumps({key: result[key] for key in ("status", "diagnostic_id", "verification_seconds")}, sort_keys=True))


if __name__ == "__main__":
    main()

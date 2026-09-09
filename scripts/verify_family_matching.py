"""Independent C009 witness checks; no enumeration, model or remote access.

Arithmetic uses a separate Python AST/Fraction implementation. Structural-family
support uses NetworkX maximum flow, not the producer's assignment algorithm.
Only the fixed public training pool and supplied CPU artifacts are inspected.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from fractions import Fraction
import gzip
import hashlib
import json
from pathlib import Path
import random
import re
import subprocess
import time

import networkx as nx


FAMILIES = ("identity_present", "identity_absent")
OPERATORS = {ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.Div: "/"}
SURFACE_FRAMES = (
    "Step {i}: {equation}.", "We now calculate: {equation}.",
    "Next, we obtain {equation}.", "This calculation gives us {equation}.",
)
STAGES = ("raw_disjoint", "encodable_disjoint", "token_matched", "structure_matched")
FEATURES = ("identity_nodes", "zero_nodes", "one_nodes", "negative_nodes",
            "fraction_nodes", "depth", "max_abs_intermediate")
TRAIN_FILE = "runs/pilot_v1_20260908_r3/train_blocks.json"
TRAIN_HASH = "e15857122ad9148a1a209cce7c8ef4c107ff0de27bcfe11b97ba6fce6b7a2cea"
CENSUS_HASH = "42c00622cdf8e9953d50f4a5c781b28e054198dff72915524577fe5a6407f5ef"
CENSUS_STREAM_HASH = "fa0563f030ffaa810f23e4eb5e9c63a2e12096f2dc675128a9bd9a9362c338d8"
CONFIGURATION = {"schema_version": 1, "per_family": 4, "max_length": 384,
                 "schedule_cycles": 1, "microbatch_size": 2, "assignment_seed": 17,
                 "max_structure_nodes": 2000000, "max_key_pair_checks": 2000000,
                 "max_key_search_seconds": 600}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


@dataclass(frozen=True)
class Arithmetic:
    value: Fraction
    leaves: tuple[int, ...]
    expression: str
    ac_class: str
    structure_id: str
    family: str
    identity_count: int
    intermediate_values: tuple[Fraction, ...]
    depth: int
    equations: tuple[str, ...]
    operators: dict


def inspect_arithmetic(expression: str) -> Arithmetic:
    """Check a bounded binary-only grammar without invoking producer parsers."""
    require(isinstance(expression, str) and 0 < len(expression) <= 2048,
            "Invalid expression length")
    try:
        tree = ast.parse(expression.strip(), mode="eval").body
    except (SyntaxError, RecursionError) as exc:
        raise ValueError("Invalid arithmetic syntax") from exc
    require(sum(1 for _ in ast.walk(tree)) <= 64, "Expression exceeds node bound")
    values, events, equations, postorder, operators = {}, [], [], [], Counter()

    def evaluate(node: ast.AST, depth: int = 0):
        require(depth <= 32, "Expression exceeds depth bound")
        if isinstance(node, ast.Constant) and type(node.value) is int:
            require(0 <= node.value <= 10000, "Integer literal outside grammar")
            values[id(node)] = Fraction(node.value)
            return Fraction(node.value), [node.value], str(node.value), 0
        require(isinstance(node, ast.BinOp) and type(node.op) in OPERATORS,
                "Only unsigned integer literals and binary + - * / are allowed")
        left, leaves_l, text_l, depth_l = evaluate(node.left, depth + 1)
        right, leaves_r, text_r, depth_r = evaluate(node.right, depth + 1)
        op = OPERATORS[type(node.op)]
        if op == "+":
            result, identity = left + right, left == 0 or right == 0
        elif op == "-":
            result, identity = left - right, right == 0
        elif op == "*":
            result, identity = left * right, left == 1 or right == 1
        else:
            require(right != 0, "Division by zero")
            result, identity = left / right, right == 1
        values[id(node)] = result
        postorder.append(node)
        operators[op] += 1
        events.append(bool(identity))
        operand = lambda x: f"({x})" if x < 0 or x.denominator != 1 else str(x)
        equations.append(f"{operand(left)} {op} {operand(right)} = {result}")
        return result, leaves_l + leaves_r, f"({text_l} {op} {text_r})", 1 + max(depth_l, depth_r)

    result, leaves, normalized, depth = evaluate(tree)

    def signature(node: ast.AST, structural: bool):
        if isinstance(node, ast.Constant):
            return "N" if structural else str(node.value)
        op = OPERATORS[type(node.op)]
        if op not in ("+", "*"):
            return f"{op}({signature(node.left, structural)},{signature(node.right, structural)})"
        # Expand equal-operator descendants before sorting their complete forms.
        pending, operands = [node], []
        while pending:
            child = pending.pop()
            if isinstance(child, ast.BinOp) and type(child.op) is type(node.op):
                pending.extend((child.left, child.right))
            else:
                operands.append(signature(child, structural))
        return op + "(" + ",".join(sorted(operands)) + ")"

    intermediate = tuple(values[id(node)] for node in postorder if node is not tree)
    return Arithmetic(result, tuple(leaves), normalized, signature(tree, False),
                      signature(tree, True), FAMILIES[0] if any(events) else FAMILIES[1],
                      sum(events), intermediate, depth, tuple(equations), dict(operators))


def expected_numeric_features(arithmetic: Arithmetic) -> dict:
    values = arithmetic.intermediate_values
    require(len(values) == 2, "Four-number binary programs require two nonroot values")
    return {"identity_nodes": arithmetic.identity_count,
            "zero_nodes": sum(value == 0 for value in values),
            "one_nodes": sum(value == 1 for value in values),
            "negative_nodes": sum(value < 0 for value in values),
            "fraction_nodes": sum(value.denominator != 1 for value in values),
            "depth": arithmetic.depth,
            "max_abs_intermediate": float(max(abs(value) for value in values)),
            "exact_nonroot_intermediates": [str(value) for value in values],
            "operators": arithmetic.operators}


def expected_response(arithmetic: Arithmetic, variant: int = 0) -> str:
    require(type(variant) is int and variant in range(4), "Unknown Surface variant")
    return "\n".join([
        SURFACE_FRAMES[variant].format(i=i, equation=equation)
        for i, equation in enumerate(arithmetic.equations, 1)
    ] + ["Answer: " + arithmetic.expression])


def expected_prompt(numbers: list[int], target: int) -> str:
    return (f'Use the numbers {", ".join(map(str, numbers))} exactly once each with '
            f'+, -, *, / and parentheses to make {target}. Show calculations, '
            'then write Answer: followed by one expression.')


def independent_encoding(prompt: str, response: str, tokenizer, max_length: int | None = 384) -> dict:
    """Rebuild shifted supervision from token offsets; never use encode_row."""
    require(bool(prompt.strip()) and bool(response.strip()), "Empty serialization")
    prefix = "Problem: " + prompt + "\nSolution:\n"
    encoded = tokenizer(prefix + response, add_special_tokens=False,
                        return_offsets_mapping=True)
    ids = list(encoded["input_ids"])
    offsets = list(encoded["offset_mapping"])
    require(len(ids) == len(offsets), "Offset count differs from token count")
    boundary = len(prefix)
    require(all(not (start < boundary < end) for start, end in offsets),
            "Token crosses prompt/response boundary")
    labels = [token if start >= boundary and end > start else -100
              for token, (start, end) in zip(ids, offsets)]
    supervised_positions = [i for i, label in enumerate(labels) if label != -100]
    require(bool(supervised_positions) and supervised_positions[0] > 0,
            "No valid shifted supervision")
    first = supervised_positions[0]
    require(ids[:first] == list(tokenizer(prefix, add_special_tokens=False)["input_ids"]),
            "Training/inference prefix differs")
    eos = tokenizer.eos_token_id
    require(type(eos) is int and eos not in ids, "Missing or embedded EOS")
    ids.append(eos)
    labels.append(eos)
    require(max_length is None or len(ids) <= max_length, "Sequence requires prohibited truncation")
    return {"input_ids": ids, "labels": labels, "n_prompt": first,
            "n_supervised": sum(x != -100 for x in labels[1:]),
            "n_processed": len(ids),
            "response_hash": hashlib.sha256(response.encode()).hexdigest()}


def verify_expression_record(record: dict, tokenizer=None) -> Arithmetic:
    arithmetic = inspect_arithmetic(record["expression"])
    numbers = record["numbers"]
    require(isinstance(numbers, list) and len(numbers) == 4
            and all(type(n) is int for n in numbers), "Expected four integer inputs")
    require(Counter(arithmetic.leaves) == Counter(numbers), "Input-number use differs")
    require(type(record["target"]) is int and arithmetic.value == record["target"],
            "Final expression misses target")
    for key in ("ac_class", "structure_id", "family"):
        require(record[key] == getattr(arithmetic, key), f"Incorrect {key}")
    require(record["expression"] == arithmetic.expression, "Noncanonical expression serialization")
    require(record["response"] == expected_response(arithmetic), "Displayed calculations differ")
    if "response_hash" in record:
        require(record["response_hash"] == hashlib.sha256(record["response"].encode()).hexdigest(),
                "Response hash differs")
    if "path_id" in record:
        require(record["path_id"] == arithmetic.ac_class, "Path ID differs")
    if "numeric_features" in record:
        require(record["numeric_features"] == expected_numeric_features(arithmetic),
                "Numerical features differ")
    if tokenizer is not None:
        prompt = expected_prompt(numbers, record["target"])
        if "prompt" in record:
            require(record["prompt"] == prompt, "Prompt differs from frozen serialization")
        encoded = independent_encoding(prompt, record["response"], tokenizer, max_length=None)
        encodable = encoded["n_processed"] <= 384
        require(type(record["encodable"]) is bool and record["encodable"] == encodable,
                "Encodability differs")
        if not encodable:
            require(not any(k in record for k in ("n_prompt", "n_supervised", "n_processed")),
                    "Excluded record still claims usable token lengths")
            return arithmetic
        for field in ("n_prompt", "n_supervised", "n_processed", "response_hash"):
            require(record[field] == encoded[field], f"Re-encoded {field} differs")
        lengths = []
        for variant in range(4):
            variant_encoded = independent_encoding(prompt, expected_response(arithmetic, variant),
                                                    tokenizer, max_length=None)
            lengths.append(variant_encoded["n_supervised"] if variant_encoded["n_processed"] <= 384 else None)
        compatible = all(length == encoded["n_supervised"] for length in lengths)
        require(type(record["surface_compatible"]) is bool
                and record["surface_compatible"] == compatible, "Surface eligibility differs")
        require(record["surface_lengths"] == lengths, "Surface token lengths differ")
    return arithmetic


def hall_support(records: list[dict], k: int = 4) -> bool:
    """Closed-form two-family Hall condition; mixed classes cannot fill twice."""
    require(type(k) is int and k > 0, "Positive family cardinality required")
    classes = {family: set() for family in FAMILIES}
    for record in records:
        require(record["family"] in FAMILIES, "Unknown identity family")
        classes[record["family"]].add(record["ac_class"])
    first, second = (classes[family] for family in FAMILIES)
    return len(first) >= k and len(second) >= k and len(first | second) >= 2 * k


def structure_flow_support(records: list[dict], k: int = 4,
                           n_supervised: int | None = None) -> dict | None:
    """Choose k different structures/family and 2*k total different AC classes.

    The unit-capacity family-structure and shared class nodes enforce different
    constraints. Simply checking family counts or structure counts is unsafe.
    Returned records are an explicit feasible certificate, not just a flag.
    """
    require(type(k) is int and k > 0, "Positive family cardinality required")
    selected = [r for r in records if n_supervised is None or r["n_supervised"] == n_supervised]
    graph = nx.DiGraph()
    source, sink = ("source",), ("sink",)
    graph.add_nodes_from((source, sink))
    representatives = {}
    for family in FAMILIES:
        graph.add_edge(source, ("family", family), capacity=k)
    for record in sorted(selected, key=lambda r: (r["family"], r["structure_id"],
                                                  r["ac_class"], r["expression"])):
        family, structure, ac = record["family"], record["structure_id"], record["ac_class"]
        require(family in FAMILIES, "Unknown identity family")
        fnode, snode, cnode = ("family", family), ("structure", family, structure), ("class", ac)
        graph.add_edge(fnode, snode, capacity=1)
        graph.add_edge(snode, cnode, capacity=1)
        graph.add_edge(cnode, sink, capacity=1)
        representatives.setdefault((family, structure, ac), record)
    flow_value, flow = nx.maximum_flow(graph, source, sink,
                                       flow_func=nx.algorithms.flow.edmonds_karp)
    if flow_value != 2 * k:
        return None
    witness = {family: [] for family in FAMILIES}
    for (family, structure, ac), record in representatives.items():
        if flow[("structure", family, structure)].get(("class", ac), 0):
            witness[family].append(record)
    require(all(len(rows) == k for rows in witness.values()), "Internal flow witness cardinality")
    require(len({r["ac_class"] for rows in witness.values() for r in rows}) == 2 * k,
            "Internal flow witness class collision")
    return witness


def support_by_length(records: list[dict], k: int = 4) -> dict:
    lengths = defaultdict(list)
    for record in records:
        lengths[record["n_supervised"]].append(record)
    return {length: {"hall": hall_support(rows, k),
                     "structure_flow": structure_flow_support(rows, k) is not None}
            for length, rows in sorted(lengths.items())}


def independent_stages(records: list[dict], problem_ids) -> dict:
    grouped = {pid: [] for pid in problem_ids}
    for record in records:
        require(record["problem_id"] in grouped, "Unknown problem in stage inventory")
        grouped[record["problem_id"]].append(record)
    result = {}
    for pid, rows in grouped.items():
        encodable = [row for row in rows if row["encodable"]]
        support = support_by_length(encodable)
        token_lengths = [length for length, flags in support.items() if flags["hall"]]
        structure_lengths = [length for length, flags in support.items() if flags["structure_flow"]]
        result[pid] = {"raw_disjoint": hall_support(rows),
                       "encodable_disjoint": hall_support(encodable),
                       "token_matched": bool(token_lengths),
                       "structure_matched": bool(structure_lengths),
                       "token_lengths": token_lengths, "structure_lengths": structure_lengths}
    return result


def stage_aggregates(stages: dict, problems: dict) -> dict:
    result, previous = {}, len(problems)
    for stage in STAGES:
        ids = sorted(pid for pid in problems if stages[pid][stage])
        result[stage] = {"count": len(ids), "denominator": len(problems),
                         "previous_stage_count": previous, "problem_ids": ids,
                         "target_histogram": dict(Counter(str(problems[pid]["target"]) for pid in ids)),
                         "contains_input_one": sum(1 in problems[pid]["numbers"] for pid in ids)}
        previous = len(ids)
    return result


def independent_inventory_counts(records: list[dict]) -> dict:
    class_families, counts = defaultdict(set), defaultdict(Counter)
    for row in records:
        class_families[row["problem_id"], row["ac_class"]].add(row["family"])
        counts[row["problem_id"]][row["family"]] += 1
    mixed = sorted([list(key) for key, labels in class_families.items() if labels == set(FAMILIES)])
    return {"ordered_records": len(records), "problem_ac_classes": len(class_families),
            "mixed_label_classes": len(mixed), "mixed_class_ids": mixed,
            "ordered_four_plus_four_problem_ids": sorted(
                pid for pid, counter in counts.items() if all(counter[family] >= 4 for family in FAMILIES))}


def independent_policy(records: list[dict], policy: str) -> list[dict]:
    encoded = [row for row in records if row["encodable"]]
    if policy == "surface":
        return [row for row in encoded if row["surface_compatible"]]
    grouped = defaultdict(list)
    for row in encoded:
        coordinate = (row["problem_id"], row["n_supervised"])
        if policy == "first_representative":
            coordinate += (row["structure_id"],)
        grouped[coordinate].append(row)
    if policy == "first_representative":
        return [min(rows, key=lambda row: (row["ac_class"], row["expression"]))
                for rows in grouped.values()]
    require(policy == "first12", "Unknown policy")
    selected = []
    for rows in grouped.values():
        allowed = set(sorted({row["structure_id"] for row in rows})[:12])
        selected.extend(row for row in rows if row["structure_id"] in allowed)
    return selected


def verify_public_stages(public: list[dict], computed: dict, problems: dict,
                         supported: set[str], selected: set[str]) -> None:
    ids = [row["problem_id"] for row in public]
    require(len(ids) == len(set(ids)) and set(ids) == set(problems),
            "Public problem IDs missing or duplicated")
    for row in public:
        pid = row["problem_id"]
        for field in ("numbers", "target"):
            require(row[field] == problems[pid][field], "Public problem changed")
        for field, value in computed[pid].items():
            require(type(row[field]) is type(value) and row[field] == value,
                    f"Public stage differs: {field}")
        require(type(row["shared_key_supported"]) is bool and row["shared_key_supported"] == (pid in supported),
                "Public shared-key flag differs")
        require(type(row["greedy_selected"]) is bool and row["greedy_selected"] == (pid in selected),
                "Public selection flag differs")


def verify_slot_witness(witness: dict, structures: dict, inventory: dict) -> dict:
    pid, length = witness["problem_id"], witness["n_supervised"]
    require(type(length) is int and length > 0, "Invalid witness length")
    slots = witness["slots"]
    require(len(slots) == 8, "Witness requires eight slots")
    coordinates, classes, by_family = set(), set(), {family: [] for family in FAMILIES}
    for slot in slots:
        row = slot["record"]
        require((pid, row["expression"]) in inventory
                and row == inventory[pid, row["expression"]], "Witness is not an exact inventory record")
        family = slot["family"]
        require(family in FAMILIES and row["family"] == family, "Witness family mismatch")
        require(row["problem_id"] == pid and row["encodable"] and row["n_supervised"] == length,
                "Witness problem or length mismatch")
        require(slot["structure_id"] == row["structure_id"] and slot["ac_class"] == row["ac_class"],
                "Witness slot metadata mismatch")
        coordinates.add((family, slot["structure_id"]))
        classes.add(slot["ac_class"])
        by_family[family].append(row)
    require(len(classes) == 8 and len(coordinates) == 8, "Witness reuses class or family structure")
    for family in FAMILIES:
        require(len(by_family[family]) == 4
                and sorted(row["structure_id"] for row in by_family[family]) == sorted(structures[family]),
                "Witness structure tuple differs")
        by_family[family].sort(key=lambda row: row["structure_id"])
    return by_family


def schedule_totals(blocks: list[dict]) -> dict:
    result = {}
    for family in FAMILIES:
        for allocation in ("paths", "gcm"):
            name = family + "_" + allocation
            updates = [update for block in blocks for update in block["conditions"][name]]
            rows = [row for update in updates for row in update["records"]]
            operators = Counter()
            for row in rows:
                operators.update(row["numeric_features"]["operators"])
            result[name] = {"updates": len(updates), "presentations": len(rows),
                            **{field: sum(update[field] for update in updates)
                               for field in ("supervised_tokens", "processed_tokens", "padding_tokens")},
                            "mean_numeric_features": {
                                field: sum(row["numeric_features"][field] for row in rows) / len(rows) if rows else None
                                for field in FEATURES}, "operator_histogram": dict(operators)}
    return result


def verify_blocks(payload: dict, inventory: dict) -> dict:
    blocks = payload["blocks"]
    seen_problems, rng = set(), random.Random(17)
    expected_conditions = {family + "_" + allocation for family in FAMILIES for allocation in ("paths", "gcm")}
    for block_index, block in enumerate(blocks):
        require(block["block_id"] == block_index, "Block index differs")
        pids = block["problem_ids"]
        require(len(pids) == 4 and pids == sorted(set(pids)), "Block needs four sorted unique problems")
        require(not seen_problems.intersection(pids), "Problem reused across blocks")
        seen_problems.update(pids)
        structures = dict(zip(FAMILIES, (block["identity_structures"], block["nonidentity_structures"])))
        for family in FAMILIES:
            require(len(structures[family]) == 4 and len(set(structures[family])) == 4,
                    "Four different structures per family required")
        require([witness["problem_id"] for witness in block["witnesses"]] == pids,
                "Witness problem sequence differs")
        options = {witness["problem_id"]: verify_slot_witness(witness, structures, inventory)
                   for witness in block["witnesses"]}
        assignment = list(range(4))
        rng.shuffle(assignment)
        require(block["assignment"] == assignment, "Seeded assignment differs")
        conditions = block["conditions"]
        require(set(conditions) == expected_conditions, "Four condition names differ")
        for name, updates in conditions.items():
            family, allocation = name.rsplit("_", 1)
            require(len(updates) == 4, "One cycle requires four updates")
            for round_id, update in enumerate(updates):
                require(update["round"] == round_id, "Round order differs")
                rows = update["records"]
                require(len(rows) == 4 and [row["problem_id"] for row in rows] == pids,
                        "Update problem order differs")
                for position, row in enumerate(rows):
                    index = (assignment[position] + (round_id if allocation == "paths" else 0)) % 4
                    require(row == options[pids[position]][family][index], "Paths/GCM exposure differs from assignment")
                lengths = [row["n_processed"] for row in rows]
                expected = {"supervised_tokens": sum(row["n_supervised"] for row in rows),
                            "processed_tokens": sum(lengths),
                            "padding_tokens": abs(lengths[0] - lengths[1]) + abs(lengths[2] - lengths[3]),
                            "structure_histogram": dict(Counter(row["structure_id"] for row in rows))}
                for field, value in expected.items():
                    require(update[field] == value, f"Update accounting differs: {field}")
        for round_id in range(4):
            reference = conditions[FAMILIES[0] + "_paths"][round_id]
            for name in conditions:
                other = conditions[name][round_id]
                for field in ("supervised_tokens", "processed_tokens", "padding_tokens"):
                    require(other[field] == reference[field], "Cross-condition token budgets differ")
                for first, second in zip(reference["records"], other["records"]):
                    require(all(first[field] == second[field] for field in ("n_supervised", "n_prompt", "n_processed")),
                            "Corresponding example token counts differ")
            for family in FAMILIES:
                require(conditions[family + "_paths"][round_id]["structure_histogram"]
                        == conditions[family + "_gcm"][round_id]["structure_histogram"],
                        "Within-family per-update structures differ")
        for pid in pids:
            for family in FAMILIES:
                for allocation, cardinality in (("paths", 4), ("gcm", 1)):
                    exposed = [row for update in conditions[family + "_" + allocation]
                               for row in update["records"] if row["problem_id"] == pid]
                    require(len(exposed) == 4 and len({row["ac_class"] for row in exposed}) == cardinality,
                            "Per-problem path diversity differs")
    totals = schedule_totals(blocks)
    require(payload["condition_totals"] == totals, "Condition totals differ")
    return {"block_count": len(blocks), "selected_problem_ids": sorted(seen_problems), "condition_totals": totals}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def shared_key_bytes(report: Path) -> bytes:
    """Prefer the original; losslessly reconstruct compact storage if absent."""
    original = report / "shared_keys.json"
    if original.exists():
        return original.read_bytes()
    catalog = json.loads((report / "shared_key_catalog.json").read_text())
    records = catalog["records"]
    result = dict(catalog["metadata"])
    keys = []
    for key in catalog["keys"]:
        rebuilt = {name: value for name, value in key.items() if name != "witnesses"}
        witnesses = {}
        for pid, witness in key["witnesses"].items():
            indices = witness["record_indices"]
            require(len(indices) == 8 and all(type(index) is int and 0 <= index < len(records) for index in indices),
                    "Catalog witness record index invalid")
            witnesses[pid] = {"problem_id": pid, "n_supervised": witness["n_supervised"],
                              "slots": [{"family": records[index]["family"],
                                         "structure_id": records[index]["structure_id"],
                                         "ac_class": records[index]["ac_class"], "record": records[index]}
                                        for index in indices]}
        rebuilt["witnesses"] = witnesses
        keys.append(rebuilt)
    result["keys"] = keys
    return (json.dumps(result, indent=2, sort_keys=True) + "\n").encode()


def published_sources(summary: dict, repo: Path) -> dict:
    allowed = {TRAIN_FILE, "configs/diagnostics/family_matching_v1.json",
               "docs/experiments/C009_token_structure_block_matching.md", "configs/models.lock.json",
               "scripts/audit_family_matching.py", "src/path_family_matching.py", "src/sft_data.py",
               "src/countdown_smoke.py", "scripts/audit_legal_support.py",
               "scripts/audit_pilot_structure_bias.py", "src/pilot_data.py"}
    require(set(summary["source_sha256"]) == allowed, "Unexpected published input scope")
    commit = summary["source_commit"]
    require(isinstance(commit, str) and re.fullmatch(r"[0-9a-f]{40}", commit) is not None,
            "Invalid execution commit")
    source = {}
    for name in sorted(allowed):
        data = subprocess.check_output(["git", "show", commit + ":" + name], cwd=repo)
        require(sha(data) == summary["source_sha256"][name], "Published source hash differs")
        source[name] = data
    require(sha(source[TRAIN_FILE]) == TRAIN_HASH == summary["original_train_sha256"], "Fixed train hash differs")
    return source


def verify_tokenizer_files(path: Path, lock: dict, claimed: dict):
    require(lock["repo_id"] == "Qwen/Qwen2.5-1.5B"
            and lock["tokenizer_revision"] == "8faed761d45a263340a0528343f099c05c9a4323",
            "Unexpected tokenizer recipe")
    files = {}
    for name in ("config.json", "tokenizer.json", "vocab.json", "merges.txt", "tokenizer_config.json"):
        item = next(item for item in lock["files"] if item["rfilename"] == name)
        data = (path / name).read_bytes()
        blob = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        require(len(data) == item["size"] and blob == item["blobId"], "Original tokenizer byte validation failed")
        files[name] = {"git_blob_sha1": blob, "sha256": sha(data), "bytes": len(data)}
    require(claimed == {"repo_id": lock["repo_id"], "revision": lock["tokenizer_revision"], "files": files},
            "Tokenizer provenance differs")
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(str(path), local_files_only=True, use_fast=True)
    require(tokenizer.is_fast, "Fast offset tokenizer required")
    return tokenizer


def verify_report(report, inventory_path, tokenizer_dir, out, repo=None):
    """Verify supplied artifacts; never enumerate solutions or launch matching.

    All per-problem length checks are independently recomputed. Shared-key search
    exhaustion is source/accounting-reviewed, not independently re-enumerated.
    Every published key and schedule must supply valid inventory-backed witnesses.
    """
    report, inventory_path, tokenizer_dir, out = map(Path, (report, inventory_path, tokenizer_dir, out))
    require(not out.exists(), "Refusing to overwrite verification output")
    repo = Path(repo) if repo is not None else Path(__file__).resolve().parents[1]
    started = time.monotonic()
    summary_bytes = (report / "summary.json").read_bytes()
    summary = json.loads(summary_bytes)
    require(summary["diagnostic_id"] == "C009" and summary["configuration"] == CONFIGURATION,
            "Unexpected diagnostic configuration")
    require(summary["gpu_process_seconds"] == 0 and summary["packing_is_maximum"] is False,
            "Unsupported GPU or maximum-packing claim")
    source = published_sources(summary, repo)
    require(json.loads(source["configs/diagnostics/family_matching_v1.json"]) == CONFIGURATION,
            "Published config differs")
    problems = {}
    for block in json.loads(source[TRAIN_FILE]):
        for item in block["problems"]:
            problem = item["problem"]
            require(problem["problem_id"] not in problems, "Duplicate frozen problem")
            require(problem["prompt"] == expected_prompt(problem["numbers"], problem["target"]),
                    "Frozen prompt formula differs")
            problems[problem["problem_id"]] = problem
    require(len(problems) == 256, "Fixed pool must contain 256 problems")
    names = {"per_problem.jsonl", "block_witnesses.json", "policy_emulations.json", "shared_keys.json"}
    require(set(summary["output_sha256"]) == names, "Unexpected output manifest scope")
    payloads = {}
    for name in sorted(names):
        data = shared_key_bytes(report) if name == "shared_keys.json" else (report / name).read_bytes()
        require(sha(data) == summary["output_sha256"][name], "Public output hash differs")
        payloads[name] = ([json.loads(line) for line in data.splitlines()] if name.endswith("jsonl") else json.loads(data))
    compressed = inventory_path.read_bytes()
    require(sha(compressed) == summary["tokenized_compressed_sha256"], "Tokenized gzip hash differs")
    stream = gzip.decompress(compressed)
    require(sha(stream) == summary["tokenized_stream_sha256"], "Tokenized stream hash differs")
    require(summary["census_compressed_sha256"] == CENSUS_HASH
            and summary["census_stream_sha256"] == CENSUS_STREAM_HASH, "C008 lineage differs")
    records = [json.loads(line) for line in stream.splitlines()]
    require(len(records) == 25846 == summary["inventory_records"], "Full inventory count differs")
    tokenizer = verify_tokenizer_files(tokenizer_dir, json.loads(source["configs/models.lock.json"])["main"], summary["tokenizer"])
    inventory, exclusions = {}, []
    for row in records:
        pid = row["problem_id"]
        require(pid in problems and all(row[field] == problems[pid][field] for field in ("numbers", "target", "prompt")),
                "Inventory differs from frozen problem")
        require("numeric_features" in row and "encodable" in row, "Required record metadata absent")
        verify_expression_record(row, tokenizer)
        key = (pid, row["expression"])
        require(key not in inventory, "Duplicate ordered expression")
        inventory[key] = row
        if not row["encodable"]:
            exclusions.append({"problem_id": pid, "expression": row["expression"], "reason": "max_length"})
    require({row["problem_id"] for row in records} == set(problems), "Inventory problem coverage differs")
    require(sorted(exclusions, key=lambda row: (row["problem_id"], row["expression"]))
            == sorted(summary["length_exclusions"], key=lambda row: (row["problem_id"], row["expression"])),
            "Length exclusion records differ")
    require(sum(row["encodable"] for row in records) == summary["encodable_records"], "Encodable count differs")
    require(independent_inventory_counts(records) == summary["inventory_counts"], "Inventory class counts differ")
    computed = independent_stages(records, problems)
    aggregate = stage_aggregates(computed, problems)
    require(aggregate == summary["stages"], "Public aggregate stages differ")
    policies, serial = {}, records
    for policy in ("surface", "first_representative", "first12"):
        for label, subset in ((policy, independent_policy(records, policy)),
                              ("serial_through_" + policy, independent_policy(serial, policy))):
            policies[label] = {"records": len(subset), "inventory_counts": independent_inventory_counts(subset),
                               "stages": stage_aggregates(independent_stages(subset, problems), problems)}
            if label.startswith("serial_through_"):
                serial = subset
    require(policies == payloads["policy_emulations.json"], "Inventory policy simulation differs")
    search = payloads["shared_keys.json"]
    require(summary["shared_key_search"] == {key: value for key, value in search.items() if key != "keys"},
            "Search accounting snapshot differs")
    require(summary["status"] == ("complete" if search["complete"] else "incomplete_shared_key_search"),
            "Search status mislabels completeness")
    require(search["length_mode"] == "variable_per_problem", "Unexpected common-length constraint")
    require((search["stop_reason"] == "completed") == search["complete"], "Search stopping reason inconsistent")
    require(summary["shared_key_count"] == len(search["keys"]) == search["counters"]["exact_supported_keys"],
            "Shared key count differs")
    require(search["counters"]["key_pair_checks"] <= CONFIGURATION["max_key_pair_checks"]
            and search["counters"]["structure_nodes"] <= CONFIGURATION["max_structure_nodes"],
            "Search operation cap exceeded")
    search_rows = [row for row in records if row["encodable"]
                   and row["n_supervised"] in computed[row["problem_id"]]["structure_lengths"]]
    require(summary["search_input_records"] == len(search_rows)
            and search["counters"]["input_records_indexed"] <= len(search_rows), "Search input count differs")
    key_signatures, supported = set(), set()
    witness_count = 0
    for key in search["keys"]:
        structures = dict(zip(FAMILIES, (key["identity_structures"], key["nonidentity_structures"])))
        signature = tuple(tuple(structures[family]) for family in FAMILIES)
        require(all(len(part) == 4 and list(part) == sorted(set(part)) for part in signature)
                and signature not in key_signatures, "Duplicate or invalid shared key")
        key_signatures.add(signature)
        pids = key["problem_ids"]
        require(len(pids) >= 4 and pids == sorted(set(pids)) and set(pids) == set(key["witnesses"]),
                "Shared-key problem support differs")
        for pid in pids:
            require(pid in computed and computed[pid]["structure_matched"], "Unsupported key problem")
            require(key["witnesses"][pid]["problem_id"] == pid, "Key witness ID differs")
            verify_slot_witness(key["witnesses"][pid], structures, inventory)
            witness_count += 1
        supported.update(pids)
    require(sorted(supported) == summary["shared_key_supported_problem_ids"] == search["supported_problem_ids"]
            and len(supported) == summary["shared_key_supported_count"], "Shared support union differs")
    blocks_payload = payloads["block_witnesses.json"]
    block_results = verify_blocks(blocks_payload, inventory)
    require(summary["greedy_block_count"] == block_results["block_count"]
            and summary["greedy_selected_problem_ids"] == block_results["selected_problem_ids"]
            and summary["greedy_selected_count"] == len(block_results["selected_problem_ids"]),
            "Public selected block counts differ")
    selected = set(block_results["selected_problem_ids"])
    require(selected <= supported, "Selected problem lacks shared-key support")
    require(summary["condition_totals"] == block_results["condition_totals"], "Summary condition totals differ")
    for block in blocks_payload["blocks"]:
        signature = (tuple(block["identity_structures"]), tuple(block["nonidentity_structures"]))
        require(signature in key_signatures, "Block structure key is absent from search")
        matching_key = next(key for key in search["keys"] if
                            (tuple(key["identity_structures"]), tuple(key["nonidentity_structures"])) == signature)
        require(set(block["problem_ids"]) <= set(matching_key["problem_ids"]), "Block problem absent from its key")
    verify_public_stages(payloads["per_problem.jsonl"], computed, problems, supported, selected)
    result = {"status": "verified", "created_utc": datetime.now(timezone.utc).isoformat(),
              "verification_seconds": time.monotonic() - started, "execution_source_commit": summary["source_commit"],
              "verified_inventory_records": len(records), "verified_problem_count": len(problems),
              "verified_shared_key_problem_witnesses": witness_count, "verified_block_count": block_results["block_count"],
              "verified_stages": aggregate, "verified_policies": policies,
              "condition_totals": block_results["condition_totals"],
              "input_sha256": {"summary.json": sha(summary_bytes), **summary["output_sha256"],
                               "tokenized_inventory.jsonl.gz": sha(compressed), "tokenized_stream": sha(stream)},
              "verifier_sha256": sha(Path(__file__).read_bytes()), "networkx_version": nx.__version__,
              "methods": ["Independent bounded Python AST and Fraction arithmetic; no producer parser or audit imports",
                          "Independent prompt/EOS/offset token accounting for every inventory record and Surface variant",
                          "Two-family Hall support and NetworkX Edmonds-Karp for every problem/length",
                          "Independent complete per-problem stages and policy emulations",
                          "Inventory-backed eight-class witnesses and four-condition Latin schedule accounting"],
              "limitations": ["No new solution enumeration, GPU, development, holdout or model outcome access",
                              "Global shared-key enumeration exhaustion and runtime rely on reviewed execution source/accounting; not independently re-enumerated",
                              "Published shared keys are checked as feasible witnesses; omission of other feasible keys is not independently excluded",
                              "Greedy packing is a feasible lower bound; no maximum-packing or statistical-adequacy claim",
                              "C008 stream lineage is checked against pinned digests; this verifier does not re-enumerate rejected programs"]}
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("x") as handle:
        json.dump(result, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", required=True)
    parser.add_argument("--inventory", required=True)
    parser.add_argument("--tokenizer-dir", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    result = verify_report(args.report, args.inventory, args.tokenizer_dir, args.out)
    print(json.dumps({field: result[field] for field in
                      ("status", "verified_inventory_records", "verified_problem_count",
                       "verified_shared_key_problem_witnesses", "verified_block_count", "verification_seconds")}, sort_keys=True))


if __name__ == "__main__":
    main()

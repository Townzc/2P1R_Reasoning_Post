"""CPU-only, question-first public-math data freeze.

MinHash retrieves approximate candidates; exact character-shingle Jaccard decides
edges, and connected components decide exclusion/splits. It is not a semantic
deduplication guarantee. Minerva is read through a question-only Arrow schema.
"""
from __future__ import annotations

import argparse
import bisect
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from functools import lru_cache
import gzip
import hashlib
import itertools
import json
import math
from pathlib import Path
import re
import sqlite3
import time
import unicodedata

import numpy as np

RELEASE = Path("experiments/public_math_pilot_v1/release_v1")
DATA_SEED = 20260917
NUM_PERM = 128
BANDS = 16
ROWS_PER_BAND = 8
PILOT_COUNT = 4096
DEV_COUNT = 512
POOL_COUNT = 20000
EXPECTED_NUMINA_ROWS = 859494
BENCHMARKS = {"math500": 500, "math": 5000, "minerva_math": 272, "gsm8k": 1319}
_IMAGE = re.compile(r"!\[[^\]]*\]\s*\(|<\s*img\b|<\s*image\b|\\includegraphics\b|\[asy\]|"
                    r"\[(?:image|diagram|figure)(?:\s+\d+)?\]|"
                    r"(?:image|diagram|figure)\s+(?:is\s+)?(?:not\s+(?:provided|shown)|missing)", re.I)
_QUESTION_IMAGE_REFERENCE = re.compile(
    r"\b(?:in|from|using|see|refer\s+to|referring\s+to)\s+"
    r"(?:(?:the|this|that|a|an|given|adjoining|attached|accompanying|following|new)\s+){0,3}"
    r"(?:diagram|figure|picture)\b|"
    r"\b(?:diagram|figure|picture|image|graph)\s+(?:(?:is|are|shown|displayed|given|illustrated)\s+){0,3}(?:below|above)\b|"
    r"\b(?:diagram|figure|picture)\s+(?:shows|shown|depicts|depicted|numbered)\b|"
    r"\b(?:following|accompanying|given|attached)\s+(?:diagram|figure|picture|image)\b|"
    r"\b(?:formed|constructed|made)\s+(?:the|this|following|shown)\s+(?:figure|diagram|picture)\b|"
    r"\[(?:include|insert|attach)[^\]\n]{0,100}\b(?:figure|diagram|picture|image)\b|"
    r"如图|如下图|图中", re.I)
# Question-only independent preparation review, before any model use. These
# shaded-region questions omit geometric markings despite no literal image tag.
# Do not generalize this to all 'shaded' or all mathematical uses of 'image'.
_MISSING_VISUAL_ADJUDICATIONS = {
    "2a3ba485a1ee7823093a0ed38d97a8f7b36aba8b2ceda6095bedebe3cea3bc6b": {
        "source_row_id": 239535, "evidence": "Two intersecting infinite lines do not specify which bounded region is shaded; bounding axes/markings are absent."},
    "7df2a28c509815f7e2c072d672d576c0471bb83ba37186780495558a78730917": {
        "source_row_id": 282532, "evidence": "The semicircle orientation and shaded set relative to the rectangle are not supplied."},
    "731d788912e42838e70dfe42d5e0b4257d8577bbe289137a8f7b87fd5ff4f99a": {
        "source_row_id": 505088, "evidence": "O/E/F positions and the shaded boundary are not supplied."},
}
_MINHASH = None


def sha256_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(4 << 20), b""):
            h.update(block)
    return h.hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def canonical_question(text):
    if not isinstance(text, str) or not text.strip():
        raise ValueError("missing_question")
    if "\ufffd" in text:
        raise ValueError("bad_encoding")
    try:
        text.encode("utf-8", errors="strict")
    except UnicodeEncodeError as exc:
        raise ValueError("bad_encoding") from exc
    return " ".join(unicodedata.normalize("NFKC", text).split())


def split_key(canonical):
    return hashlib.sha256((str(DATA_SEED) + "|" + canonical).encode()).hexdigest()


def shingles(canonical):
    return {canonical[i:i + 5] for i in range(max(0, len(canonical) - 4))}


def near_duplicate(a, b):
    """Exact gate after approximate retrieval; short questions use exact only."""
    if a == b:
        return True, 1., "exact"
    if min(len(a), len(b)) < 40:
        return False, None, "short_exact_only"
    if not .8 <= len(a) / len(b) <= 1.25:
        return False, None, "length_ratio"
    aa, bb = shingles(a), shingles(b)
    score = len(aa & bb) / len(aa | bb)
    return score >= .9, score, "jaccard_pass" if score >= .9 else "jaccard_below_threshold"


class UnionFind:
    def __init__(self, n):
        self.parents = np.arange(n, dtype=np.int32)

    def find(self, a):
        root = int(a)
        while root != self.parents[root]:
            root = int(self.parents[root])
        while a != root:
            old = int(self.parents[a])
            self.parents[a] = root
            a = old
        return root

    def union(self, a, b):
        aa, bb = self.find(a), self.find(b)
        if aa != bb:
            self.parents[max(aa, bb)] = min(aa, bb)


def _write_json(path, value):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        stream.write("\n")


def _write_rows(path, rows):
    path = Path(path)
    with path.open("xb") as raw:
        if path.suffix == ".gz":
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as stream:
                for row in rows:
                    stream.write((json.dumps(row, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n").encode())
        else:
            for row in rows:
                raw.write((json.dumps(row, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n").encode())


def _read_rows(path):
    opener = gzip.open if Path(path).suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def _progress(stage, **kwargs):
    print(json.dumps({"stage": stage, **kwargs}, sort_keys=True), flush=True)


def verify_assets(assets):
    assets = Path(assets)
    main = json.loads((assets / "ASSET_MANIFEST.json").read_text())
    extra = json.loads((assets / "benchmark_extra_manifest.json").read_text())
    if main.get("errors"):
        raise ValueError("Unresolved asset download errors")
    records = main["files"] + extra
    if len({r["path"] for r in records}) != len(records):
        raise ValueError("Duplicate asset manifest paths")
    for row in records:
        rel = Path(row["path"])
        if rel.is_absolute() or ".." in rel.parts or not row.get("revision"):
            raise ValueError("Invalid asset path or unpinned revision")
        path = assets / rel
        if path.stat().st_size != row["bytes"] or sha256_file(path) != row["sha256"]:
            raise ValueError("Asset SHA/size mismatch: " + row["path"])
    return {"asset_manifest_sha256": sha256_file(assets / "ASSET_MANIFEST.json"),
            "benchmark_extra_manifest_sha256": sha256_file(assets / "benchmark_extra_manifest.json"),
            "files": records}


def read_benchmark_questions(assets, *, canonical=True):
    # Unknown fields, including all answers/solutions, are ignored by the
    # parser itself. They never become Python values or selected data columns.
    import pyarrow as pa
    import pyarrow.json as paj
    result = {}
    for name, expected in BENCHMARKS.items():
        column = "question" if name == "gsm8k" else "problem"
        table = paj.read_json(Path(assets) / name / "test.jsonl", parse_options=paj.ParseOptions(
            explicit_schema=pa.schema([(column, pa.string())]), unexpected_field_behavior="ignore"))
        questions = table[column].to_pylist()
        if len(questions) != expected:
            raise ValueError(f"Unexpected {name} size")
        result[name] = [canonical_question(q) for q in questions] if canonical else questions
    return result


def build_question_index(assets):
    import pyarrow.parquet as pq
    questions, mapping, row_nodes, rejected, shards = [], {}, [], [], []
    total = 0
    for path in sorted((Path(assets) / "numina" / "data").glob("train-*.parquet")):
        parquet = pq.ParquetFile(path)
        shards.append({"path": path.relative_to(assets).as_posix(), "offset": total,
                       "rows": parquet.metadata.num_rows})
        for batch in parquet.iter_batches(columns=["problem"], batch_size=8192):
            for question in batch.column(0).to_pylist():
                try:
                    canonical = canonical_question(question)
                except ValueError as exc:
                    rejected.append({"row_id": total, "reason": str(exc), "scope": "full_question_scan"})
                    row_nodes.append(-1)
                else:
                    node = mapping.get(canonical)
                    if node is None:
                        node = len(questions)
                        mapping[canonical] = node
                        questions.append(canonical)
                    row_nodes.append(node)
                total += 1
        _progress("question_scan", rows=total, unique_exact_questions=len(questions))
    if total != EXPECTED_NUMINA_ROWS or len(shards) != 5:
        raise ValueError("Numina full train split is incomplete")
    benchmark_nodes = defaultdict(list)
    for name, items in read_benchmark_questions(assets).items():
        for i, canonical in enumerate(items):
            node = mapping.get(canonical)
            if node is None:
                node = len(questions)
                mapping[canonical] = node
                questions.append(canonical)
            benchmark_nodes[node].append({"dataset": name, "row_index": i,
                                          "question_sha256": hashlib.sha256(canonical.encode()).hexdigest()})
    del mapping
    return questions, np.asarray(row_nodes, dtype=np.int32), dict(benchmark_nodes), rejected, shards


def _sketch_chunk(chunk):
    from datasketch import MinHash
    global _MINHASH
    if _MINHASH is None:
        _MINHASH = MinHash(num_perm=NUM_PERM, seed=DATA_SEED)
    output = []
    for index, text in chunk:
        _MINHASH.clear()
        _MINHASH.update_batch([s.encode("utf-8") for s in shingles(text)])
        output.append((index, _MINHASH.hashvalues.astype(np.uint32)))
    return output


def build_candidates(questions, work, workers=4):
    """Bounded RAM: one uint32 sketch array and one sorted 32-byte band at a time."""
    work = Path(work)
    work.mkdir(parents=True, exist_ok=True)
    identity = {"question_sha256": digest(questions), "nodes": len(questions), "seed": DATA_SEED,
                "num_perm": NUM_PERM, "bands": BANDS, "rows_per_band": ROWS_PER_BAND,
                "shingles": "canonical_unicode_character_5grams", "hash": "datasketch_default_sha1_hash32"}
    identity_path = work / "sketch_identity.json"
    done = work / "sketch_complete.json"
    if identity_path.exists() and json.loads(identity_path.read_text()) != identity:
        raise ValueError("Private MinHash cache belongs to different question identities")
    if not identity_path.exists():
        _write_json(identity_path, identity)
    sketch_path = work / "minhash.uint32"
    if done.exists():
        completion = json.loads(done.read_text())
        if completion["sha256"] != sha256_file(sketch_path):
            raise ValueError("Cached MinHash bytes changed")
        sketch = np.memmap(sketch_path, mode="r", dtype=np.uint32, shape=(len(questions), NUM_PERM))
    else:
        sketch = np.memmap(sketch_path, mode="w+", dtype=np.uint32, shape=(len(questions), NUM_PERM))
        def chunks():
            values = ((i, q) for i, q in enumerate(questions) if len(q) >= 40)
            while part := list(itertools.islice(values, 512)):
                yield part
        completed = 0
        with ProcessPoolExecutor(max_workers=workers) as pool:
            for result in pool.map(_sketch_chunk, chunks(), chunksize=1):
                for i, hashes in result:
                    sketch[i] = hashes
                completed += len(result)
                if completed % 32768 == 0:
                    _progress("minhash", long_questions=completed)
        sketch.flush()
        _write_json(done, {"sha256": sha256_file(sketch_path), "long_questions": completed})
    database = work / "candidates.sqlite3"
    db = sqlite3.connect(database)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA cache_size=-32768")
    db.execute("CREATE TABLE IF NOT EXISTS pairs (a INTEGER NOT NULL,b INTEGER NOT NULL,bands INTEGER NOT NULL,PRIMARY KEY(a,b)) WITHOUT ROWID")
    db.execute("CREATE TABLE IF NOT EXISTS completed_bands (band INTEGER PRIMARY KEY)")
    long_nodes = np.asarray([i for i, q in enumerate(questions) if len(q) >= 40], dtype=np.int32)
    for band in range(BANDS):
        if db.execute("SELECT 1 FROM completed_bands WHERE band=?", (band,)).fetchone():
            continue
        keys = np.ascontiguousarray(sketch[long_nodes, band*8:(band+1)*8]).view("V32").reshape(-1)
        order = np.argsort(keys, kind="stable")
        sorted_keys = keys[order]
        breaks = np.r_[0, np.flatnonzero(sorted_keys[1:] != sorted_keys[:-1]) + 1, len(order)]
        pending = []
        collisions = 0
        for begin, end in zip(breaks[:-1], breaks[1:]):
            if end - begin < 2:
                continue
            bucket = sorted(int(x) for x in long_nodes[order[begin:end]])
            for a, b in itertools.combinations(bucket, 2):
                pending.append((a, b, 1 << band))
                collisions += 1
                if len(pending) >= 10000:
                    db.executemany("INSERT INTO pairs VALUES(?,?,?) ON CONFLICT(a,b) DO UPDATE SET bands=pairs.bands|excluded.bands", pending)
                    pending.clear()
        if pending:
            db.executemany("INSERT INTO pairs VALUES(?,?,?) ON CONFLICT(a,b) DO UPDATE SET bands=pairs.bands|excluded.bands", pending)
        db.execute("INSERT INTO completed_bands VALUES(?)", (band,))
        db.commit()
        _progress("candidate_band", band=band, pair_collisions=collisions)
    return db, identity


def group_candidates(questions, row_nodes, benchmark_nodes, db, output):
    uf = UnionFind(len(questions))
    counts = Counter()
    @lru_cache(maxsize=2048)
    def gram_set(i):
        return shingles(questions[i])
    def checked():
        for a, b, bands in db.execute("SELECT a,b,bands FROM pairs ORDER BY a,b"):
            qa, qb = questions[a], questions[b]
            if not .8 <= len(qa) / len(qb) <= 1.25:
                score, matched, reason = None, False, "length_ratio"
            else:
                aa, bb = gram_set(a), gram_set(b)
                score = len(aa & bb) / len(aa | bb)
                matched, reason = score >= .9, "jaccard"
            if matched:
                uf.union(a, b)
            counts["all_candidates"] += 1
            counts["accepted_edges" if matched else "rejected_candidates"] += 1
            yield {"a": a, "b": b, "matching_bands_bitset": bands, "jaccard": score,
                   "matched": matched, "reason": reason}
    _write_rows(Path(output) / "near_duplicate_candidates.jsonl.gz", checked())
    roots = np.asarray([uf.find(i) for i in range(len(questions))], dtype=np.int32)
    benchmark_components = defaultdict(list)
    for node, entries in benchmark_nodes.items():
        benchmark_components[int(roots[node])].extend(entries)
    groups = defaultdict(list)
    for row, node in enumerate(row_nodes):
        if node >= 0:
            groups[int(roots[node])].append(row)
    gram_set.cache_clear()
    return roots, dict(groups), dict(benchmark_components), dict(counts)


def reference_text_issue(question, reference):
    for label, text in (("question", question), ("reference", reference)):
        if not isinstance(text, str) or not text.strip():
            return "missing_" + label
        if "\ufffd" in text or "\x00" in text:
            return "bad_encoding"
        try:
            text.encode("utf-8", errors="strict")
        except UnicodeEncodeError:
            return "bad_encoding"
        if _IMAGE.search(text):
            return "unprovided_image_marker"
        if label == "question" and _QUESTION_IMAGE_REFERENCE.search(text):
            return "question_refers_to_unprovided_image"
        if label == "question" and hashlib.sha256(canonical_question(text).encode()).hexdigest() in _MISSING_VISUAL_ADJUDICATIONS:
            return "independently_adjudicated_missing_visual_definition"
    return None


def image_exclusion_evidence(question, reference):
    """Literal technical evidence only, not a claim that every visual mention is invalid."""
    result = []
    for field, text in (("question", question), ("reference", reference)):
        if not isinstance(text, str):
            continue
        rules = [("literal_image_marker", _IMAGE)]
        if field == "question":
            rules.append(("explicit_question_visual_reference", _QUESTION_IMAGE_REFERENCE))
        for name, pattern in rules:
            for match in pattern.finditer(text):
                result.append({"field": field, "rule": name, "char_span": [match.start(), match.end()],
                               "matched_text": match.group()})
    if isinstance(question, str) and question.strip():
        key = hashlib.sha256(canonical_question(question).encode()).hexdigest()
        if key in _MISSING_VISUAL_ADJUDICATIONS:
            result.append({"field": "question", "rule": "independent_question_only_missing_visual_review",
                           "canonical_question_sha256": key, **_MISSING_VISUAL_ADJUDICATIONS[key]})
    return result


def fetch_references(assets, shards, wanted):
    """Project only question/reference/source, and retain only requested rows."""
    import pyarrow.parquet as pq
    wanted = sorted(set(wanted))
    result = {}
    for shard in shards:
        parquet = pq.ParquetFile(Path(assets) / shard["path"])
        start = shard["offset"]
        for group in range(parquet.num_row_groups):
            stop = start + parquet.metadata.row_group(group).num_rows
            selected = wanted[bisect.bisect_left(wanted, start):bisect.bisect_left(wanted, stop)]
            if selected:
                table = parquet.read_row_group(group, columns=["problem", "solution", "source"])
                part = table.take(np.asarray([row - start for row in sorted(selected)], dtype=np.int64)).to_pylist()
                for row, raw in zip(sorted(selected), part):
                    result[row] = {"question": raw["problem"], "response": raw["solution"], "source": raw["source"],
                                   "source_file": shard["path"], "source_row_index": row - shard["offset"], "row_id": row}
            start = stop
    if set(result) != set(wanted):
        raise ValueError("Requested original source rows are missing")
    return result


def choose_splits(ordered_groups, references, qualify, parse_reference, *, dev_count=DEV_COUNT,
                  pool_count=POOL_COUNT, pilot_count=PILOT_COUNT):
    """Lazy ordered selection equivalent to full eligibility filtering then sort.

    Group identities/order are computed before this function. The first passing
    row_id reference wins within each group; answer parseability selects dev only.
    Once dev is full, no later group could precede it. Once pool is full as well,
    no unvisited later group could enter either selected prefix. Eligibility of
    the unvisited suffix is deliberately unknown.
    """
    dev, pool, pilot_encoded, rejected = [], [], [], []
    scanned = 0
    for group in ordered_groups:
        scanned += 1
        chosen = None
        for raw in references(group):
            encoded, reason = qualify(raw)
            if reason is not None:
                rejection = {"row_id": raw["row_id"], "group_id": group["group_id"],
                             "reason": reason, "scope": "ordered_eligibility_prefix"}
                if reason in ("unprovided_image_marker", "question_refers_to_unprovided_image",
                              "independently_adjudicated_missing_visual_definition"):
                    rejection["evidence"] = image_exclusion_evidence(raw["question"], raw["response"])
                rejected.append(rejection)
                continue
            chosen = (raw, encoded)
            break
        if chosen is None:
            continue
        raw, encoded = chosen
        row = {**raw, "problem_id": f"numina-train-{raw['row_id']:09d}",
               "group_id": group["group_id"], "group_canonical_question_sha256": group["canonical_question_sha256"],
               "canonical_question_sha256": hashlib.sha256(canonical_question(raw["question"]).encode()).hexdigest(),
               "split_sort_key": group["sort_key"], "n_input_tokens": len(encoded["input_ids"]),
               "n_supervised": encoded["response_length"], "encoded_sha256": digest(encoded)}
        answer = None
        if len(dev) < dev_count:
            answer = parse_reference(raw["response"])
        if answer is not None and str(answer).strip():
            dev.append({**row, "reference": str(answer)})
        elif len(pool) < pool_count:
            pool.append(row)
            if len(pool) <= pilot_count:
                pilot_encoded.append({"problem_id": row["problem_id"], "group_id": row["group_id"], **encoded})
        if len(dev) == dev_count and len(pool) == pool_count:
            return dev, pool, pilot_encoded, rejected, {"groups_scanned": scanned,
                "last_scanned_sort_key": group["sort_key"], "qualified_pool_size_globally": None,
                "eligibility_scope": "ordered_prefix_sufficient_for_exact_requested_selection",
                "suffix_eligibility_scanned": False}
    raise ValueError(f"Insufficient qualified groups: dev={len(dev)}, train_pool={len(pool)}; standards unchanged")


def _distribution(values):
    values = np.asarray(values, dtype=np.int64)
    return {"count": int(values.size), "min": int(values.min()), "max": int(values.max()),
            "mean": float(values.mean()), "quantiles_0_25_50_75_100": np.quantile(values, [0, .25, .5, .75, 1]).tolist()}


def prepare(assets, output=RELEASE, work_dir=None, workers=4):
    from transformers import AutoTokenizer
    from .scoring import ground_truth, ground_truth_info, extraction_route, source_identity
    from .tokenization import encode_training_pair, validate_tokenizer, validate_eval_context
    started = time.monotonic()
    assets, output = Path(assets), Path(output)
    if output.exists():
        raise FileExistsError("Frozen release output already exists: " + str(output))
    if workers < 1 or workers > 8:
        raise ValueError("Use one to eight bounded CPU workers")
    work = Path(work_dir) if work_dir else Path(".local/public_math_session/data_freeze_work_v1")
    asset_identity = verify_assets(assets)
    _progress("assets_verified", files=len(asset_identity["files"]))
    questions, row_nodes, benchmark_nodes, rejected, shards = build_question_index(assets)
    db, minhash_identity = build_candidates(questions, work, workers)
    # A failed preparation remains a separate incomplete directory; do not
    # overwrite it or manufacture a successful release manifest.
    output.mkdir(parents=True)
    previous_attempts = work / "preparation_attempts.json"
    if previous_attempts.exists():
        _write_json(output / "PREPARATION_ATTEMPTS.json", json.loads(previous_attempts.read_text()))
    roots, groups, benchmark_groups, near_counts = group_candidates(questions, row_nodes, benchmark_nodes, db, output)
    db.close()
    blocked_rows = sum(len(groups.get(g, [])) for g in benchmark_groups)
    _progress("groups_complete", numina_components=len(groups), excluded_rows=blocked_rows, **near_counts)
    def node_records():
        for node, text in enumerate(questions):
            yield {"node": node, "component": int(roots[node]),
                   "canonical_question_sha256": hashlib.sha256(text.encode()).hexdigest(),
                   "canonical_characters": len(text), "benchmarks": benchmark_nodes.get(node, [])}
    _write_rows(output / "question_identities.jsonl.gz", node_records())
    _write_rows(output / "source_group_membership.jsonl.gz", (
        {"row_id": row, "node": int(node), "component": int(roots[node]) if node >= 0 else None}
        for row, node in enumerate(row_nodes)))
    ordered = []
    for component, members in groups.items():
        if component in benchmark_groups:
            continue
        canonical = questions[row_nodes[members[0]]]
        ordered.append({"component": component, "members": members,
                        "group_id": digest({"original_row_ids": members}),
                        "canonical_question_sha256": hashlib.sha256(canonical.encode()).hexdigest(),
                        "sort_key": split_key(canonical)})
    ordered.sort(key=lambda g: (g["sort_key"], g["members"][0]))
    if len(ordered) < DEV_COUNT + POOL_COUNT:
        raise ValueError("Insufficient question groups before eligibility filtering")
    tokenizer = AutoTokenizer.from_pretrained(assets / "model", local_files_only=True)
    token_identity = validate_tokenizer(tokenizer)
    # Fetch references for a finite ordered chunk. Projection does not retain the
    # other 800k+ solutions, nor any messages column. No GPU mask scores exist.
    loaded = {}
    loaded_until = 0
    group_position = {g["group_id"]: i for i, g in enumerate(ordered)}
    def references(group):
        nonlocal loaded, loaded_until
        position = group_position[group["group_id"]]
        if position >= loaded_until:
            end = min(len(ordered), position + 4096)
            loaded = fetch_references(assets, shards, itertools.chain.from_iterable(g["members"] for g in ordered[position:end]))
            loaded_until = end
            _progress("reference_prefix", groups_loaded_through=end)
        return (loaded[i] for i in group["members"])
    def qualify(raw):
        reason = reference_text_issue(raw["question"], raw["response"])
        if reason:
            return None, reason
        try:
            return encode_training_pair(tokenizer, raw["question"], raw["response"]), None
        except ValueError as exc:
            if str(exc).startswith("Complete reference exceeds"):
                return None, "complete_sequence_over_2048"
            if str(exc).startswith("Reference contains a special/control token"):
                return None, "reference_special_control_token"
            raise
    parse_routes = Counter()
    def parse_reference(response):
        try:
            answer = ground_truth({"solution": response}, "math")
        except ValueError as exc:
            if str(exc) != "Empty official reference answer":
                raise
            return None
        if answer:
            parse_routes[extraction_route(response)] += 1
        return answer
    dev, pool, encoded, eligibility_rejected, prefix = choose_splits(ordered, references, qualify, parse_reference)
    pilot = pool[:PILOT_COUNT]
    if len({r["group_id"] for r in dev + pool}) != DEV_COUNT + POOL_COUNT:
        raise ValueError("Train/dev group identities overlap")
    # Freeze references only for this pilot/dev. The other 15,904 references
    # were CPU-qualified but only their immutable source/token identities ship.
    _write_rows(output / "pilot.jsonl", pilot)
    _write_rows(output / "dev.jsonl", dev)
    id_fields = ("problem_id", "group_id", "row_id", "source", "source_file", "source_row_index",
                 "canonical_question_sha256", "group_canonical_question_sha256", "split_sort_key", "n_input_tokens", "n_supervised", "encoded_sha256")
    _write_rows(output / "future_train_pool_ids.jsonl", ({k: r[k] for k in id_fields} for r in pool))
    _write_rows(output / "tokenized_pilot.jsonl.gz", encoded)
    selections = {}
    for name, count, seed in (("audit64", 64, "20260917|mask-audit"), ("train_profile32", 32, "20260917|train-profile")):
        selected = sorted(pilot, key=lambda r: hashlib.sha256((seed + "|" + r["problem_id"]).encode()).hexdigest())[:count]
        selections[name] = {"seed_string": seed, "problem_ids": [r["problem_id"] for r in selected]}
    selections["dev_profile32"] = {"selection": "first_32_in_frozen_dev_order", "problem_ids": [r["problem_id"] for r in dev[:32]]}
    _write_json(output / "predeclared_subsets.json", selections)
    def exclusions():
        yield from rejected
        for component, benchmarks in sorted(benchmark_groups.items()):
            for row in groups.get(component, []):
                yield {"row_id": row, "component": component, "reason": "benchmark_connected_component",
                       "benchmarks": benchmarks, "scope": "full_question_scan"}
        yield from eligibility_rejected
    _write_rows(output / "exclusions.jsonl.gz", exclusions())
    contexts = {}
    for name, items in read_benchmark_questions(assets, canonical=False).items():
        lengths, invalid = [], []
        for i, question in enumerate(items):
            try:
                rec = validate_eval_context(tokenizer, question)
                lengths.append(rec["prompt_tokens"])
            except ValueError:
                invalid.append(i)
        contexts[name] = {"question_only": True, "original_question_text_audit": True,
                          "count": len(items), "valid_prompt_length": _distribution(lengths) if lengths else None,
                          "over_context_row_indices": invalid}
    unresolved_references = []
    for name in ("math500", "gsm8k"):
        with (assets / name / "test.jsonl").open(encoding="utf-8") as stream:
            official = [json.loads(line) for line in stream if line.strip()]
        rows = []
        for index, raw in enumerate(official):
            question = raw["question"] if name == "gsm8k" else raw["problem"]
            context = validate_eval_context(tokenizer, question)
            reference_info = ground_truth_info(raw, name)
            if reference_info["normalization_empty"]:
                unresolved_references.append({"dataset": name, "problem_id": f"{name}-test-{index:04d}",
                                              "source_row_index": index, **reference_info})
            rows.append({"problem_id": f"{name}-test-{index:04d}", "source_row_index": index,
                         "question": question, **reference_info,
                         "question_sha256": hashlib.sha256(canonical_question(question).encode()).hexdigest(),
                         "prompt_tokens": context["prompt_tokens"], "max_new_tokens": 2048,
                         "context_limit": 4096, "truncated": False})
        _write_rows(output / f"{name}.jsonl", rows)
        contexts[name]["original_generation_questions_all_passed"] = True
    for row in dev:
        validate_eval_context(tokenizer, row["question"])
    contexts["dev"] = {"count": len(dev), "original_generation_questions_all_passed": True}
    _write_json(output / "eval_context_audit.json", contexts)
    reasons = Counter(r["reason"] for r in rejected + eligibility_rejected)
    reasons["benchmark_connected_component"] = blocked_rows
    summary = {"schema": "public_math_data_summary_v1", "source_train_rows": len(row_nodes),
        "numina_exact_unique_questions": len(set(int(x) for x in row_nodes if x >= 0)),
        "all_question_nodes_including_benchmarks": len(questions), "numina_connected_components": len(groups),
        "benchmark_excluded_rows": blocked_rows, "benchmark_excluded_components": sum(g in groups for g in benchmark_groups),
        "unexcluded_components_before_reference_eligibility": len(ordered), "near_duplicate": near_counts,
        "dev_questions": len(dev), "future_train_pool_questions": len(pool), "pilot_questions": len(pilot),
        "rejection_counts_by_scope_as_recorded": dict(reasons), "selection_prefix": prefix,
        "dev_answer_parse_routes": dict(parse_routes), "pilot_source_counts": dict(Counter(r["source"] for r in pilot)),
        "known_unresolved_reference_count": len(unresolved_references),
        "known_unresolved_references": unresolved_references,
        "scoring_readiness": "blocked_by_known_unresolved_reference" if unresolved_references else "reference_normalization_ready",
        "dev_source_counts": dict(Counter(r["source"] for r in dev)),
        "pilot_input_lengths": _distribution([r["n_input_tokens"] for r in pilot]),
        "pilot_response_lengths": _distribution([r["n_supervised"] for r in pilot]),
        "dev_input_lengths": _distribution([r["n_input_tokens"] for r in dev]),
        "intersection_audit": {"dev_train_groups": 0, "selected_benchmark_components": 0,
                               "pilot_unique_groups": len({r["group_id"] for r in pilot})},
        "minerva_scope": "question-only identity/context exclusion; answers neither projected nor published; no generation",
        "dedup_limitations": "Fixed MinHash candidates then exact Jaccard; approximate retrieval is not exhaustive pairwise or semantic deduplication.",
        "lazy_selection_proof": "All question components are fixed first; groups ordered by seeded hash of minimum-source-row canonical question; each group's first qualified row_id reference is deterministic. Later unvisited groups cannot replace any chosen dev or train prefix. Global reference-qualified pool size remains unknown.",
        "image_exclusion_regex": _IMAGE.pattern,
        "question_only_image_reference_regex": _QUESTION_IMAGE_REFERENCE.pattern,
        "question_visual_reference_scope": "Conservative external-visual-reference rule; not every excluded reference is proven indispensable. Generic math image/figure, books, tables, and fully defined shaded sets are not excluded merely by those words.",
        "independent_missing_visual_adjudications": _MISSING_VISUAL_ADJUDICATIONS,
        "visual_review_limitations": "Known literal/reference cues plus three independently reviewed question hashes; not a guarantee that every implicit visual dependency in the source is detected. No solutions, correctness scores, or model outputs informed the three question-only adjudications.",
        "group_representative": "canonical question of minimum original global Numina row_id",
        "reference_selection": "minimum original row_id passing common text/length eligibility; no model or mask-success filtering",
        "training_references_truncated": False, "tokenization": token_identity,
        "wall_seconds_cpu": time.monotonic() - started}
    _write_json(output / "DATA_AUDIT.json", summary)
    _write_json(output / "ASSET_PROVENANCE.json", asset_identity)
    _write_json(output / "MINHASH_PROTOCOL.json", minhash_identity)
    source_paths = [Path(__file__), Path(__file__).with_name("tokenization.py"), Path(__file__).with_name("scoring.py")]
    repo = Path(__file__).resolve().parents[2]
    manifest = {"schema": "public_math_data_release_v1", "status": "frozen", "data_seed": DATA_SEED,
        "scoring_readiness": summary["scoring_readiness"],
        "known_unresolved_reference_count": len(unresolved_references),
        "known_unresolved_reference_ids": [r["problem_id"] for r in unresolved_references],
        "counts": {"pilot": PILOT_COUNT, "dev": DEV_COUNT, "future_train_pool": POOL_COUNT, **BENCHMARKS},
        "source_files_sha256": {p.resolve().relative_to(repo).as_posix(): sha256_file(p) for p in source_paths}, "qwen_source": source_identity(),
        "files_sha256": {p.name: sha256_file(p) for p in sorted(output.iterdir()) if p.is_file()},
        "files_bytes": {p.name: p.stat().st_size for p in sorted(output.iterdir()) if p.is_file()},
        "split_files": {"train": "pilot.jsonl", "pilot": "pilot.jsonl", "dev": "dev.jsonl",
                        "future_train_pool": "future_train_pool_ids.jsonl", "tokenized_pilot": "tokenized_pilot.jsonl.gz",
                        "math500": "math500.jsonl", "gsm8k": "gsm8k.jsonl"}}
    _write_json(output / "manifest.json", manifest)
    _progress("frozen", manifest_sha256=sha256_file(output / "manifest.json"), **manifest["counts"])
    return manifest


def load_inputs(release=RELEASE, *, verify=True):
    release = Path(release)
    manifest = json.loads((release / "manifest.json").read_text())
    if manifest.get("status") != "frozen":
        raise ValueError("Data release is incomplete")
    if verify:
        for path, expected in manifest["files_sha256"].items():
            if sha256_file(release / path) != expected:
                raise ValueError("Frozen data SHA mismatch: " + path)
    result = {key: _read_rows(release / path) for key, path in manifest["split_files"].items() if key != "train"}
    result["train"] = result["pilot"]
    subsets = json.loads((release / "predeclared_subsets.json").read_text())
    for name, record in subsets.items():
        result[name] = record["problem_ids"]
    result["manifest"] = manifest
    return result


def longest_profile_ids(encoded):
    """Four fixed stress slots, each repeated eight times; engineering only."""
    if len(encoded) < 2:
        raise ValueError("The stress profile requires at least two released examples")
    by_input = sorted(encoded, key=lambda r: (-len(r["input_ids"]), r["problem_id"]))[:2]
    by_response = sorted(encoded, key=lambda r: (-len(r["response_ids"]), r["problem_id"]))[:2]
    slots = [r["problem_id"] for r in by_input + by_response]
    return slots * 8, {"engineering_only": True, "formal_training_updates": 0,
                      "selection_rule": "two_longest_total_input_then_two_longest_response; ascending_problem_id_ties; four_slots_repeated_eight_times",
                      "four_slots": slots, "unique_ids": sorted(set(slots)), "sample_presentations": 32}


def write_preflight_inputs(assets, output, release=RELEASE):
    """Write a separate executable input file after the immutable release exists."""
    from transformers import AutoTokenizer
    from .tokenization import MODEL_REVISION, encode_prompt
    released = load_inputs(release)
    raw = {r["problem_id"]: r for r in released["pilot"]}
    encoded = {r["problem_id"]: r for r in released["tokenized_pilot"]}
    dev = {r["problem_id"]: r for r in released["dev"]}
    tokenizer = AutoTokenizer.from_pretrained(Path(assets) / "model", local_files_only=True)
    def train_row(problem_id):
        return {**encoded[problem_id], "id": problem_id, "response": raw[problem_id]["response"]}
    longest_ids, longest_audit = longest_profile_ids(released["tokenized_pilot"])
    model_dir = Path(assets) / "model"
    files = {}
    for path in sorted(model_dir.rglob("*")):
        if path.is_symlink():
            raise ValueError("Do not include symlinked model assets")
        if path.is_file():
            files[path.relative_to(model_dir).as_posix()] = sha256_file(path)
    record = {"schema": "public_math_preflight_inputs_v1", "model_revision": MODEL_REVISION,
              "model_files_sha256": files, "release_manifest_sha256": sha256_file(Path(release) / "manifest.json"),
              "train_profile": [train_row(i) for i in released["train_profile32"]],
              "dev_profile": [{"id": i, "prompt_ids": encode_prompt(tokenizer, dev[i]["question"])}
                              for i in released["dev_profile32"]],
              "longest_profile": [train_row(i) for i in longest_ids],
              "profile_selection": {"train_profile_ids": released["train_profile32"],
                                    "dev_profile_ids": released["dev_profile32"],
                                    "longest_profile": longest_audit},
              "formal_training_updates": 0,
              "scoring_readiness": released["manifest"]["scoring_readiness"]}
    _write_json(output, record)
    return {"path": str(output), "sha256": sha256_file(output),
            "release_manifest_sha256": record["release_manifest_sha256"],
            "counts": {key: len(record[key]) for key in ("train_profile", "dev_profile", "longest_profile")},
            "longest_profile": longest_audit}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--assets", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=RELEASE)
    parser.add_argument("--work-dir", type=Path)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    prepare(args.assets, args.output, args.work_dir, args.workers)

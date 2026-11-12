"""Count actual exported-template tokens for every C5 candidate on CPU."""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sqlite3
import time

from .data_pool import write_json
from .evaluation import execution_commit, prompt_text, sha256_file


def check_lengths(pool: Path, assets: Path, output: Path) -> dict:
    from transformers import AutoTokenizer
    if not (pool / "COLLECTION_COMPLETE.json").exists():
        raise ValueError("C5 collection must be complete")
    output.mkdir(parents=True, exist_ok=False)
    source = sqlite3.connect(f"file:{pool / 'pool.sqlite'}?mode=ro", uri=True)
    parents = {id_: json.loads(payload) for id_, payload in source.execute("SELECT id,payload FROM parents")}
    tokenizers, prompt_lengths, suffixes, proofs = {}, {}, {}, {}
    for family, names in {"qwen": ["Qwen__Qwen2.5-1.5B", "Qwen__Qwen2.5-1.5B-Instruct"],
                          "llama3": ["meta-llama__Llama-3.2-1B", "meta-llama__Llama-3.2-1B-Instruct"]}.items():
        members = [AutoTokenizer.from_pretrained(assets / name, local_files_only=True) for name in names]
        backend_configs = [json.loads(t.backend_tokenizer.to_str()) for t in members]
        # add_special_tokens=False bypasses the post processor. Padding and
        # truncation are disabled. All vocabulary/normalization/added-token
        # behavior must match before sharing a family's length computation.
        for config in backend_configs:
            for key in ("post_processor", "truncation", "padding"):
                config.pop(key, None)
        if backend_configs[0] != backend_configs[1]:
            raise ValueError("Base/Instruct tokenizers differ; count all four explicitly")
        tok = members[0]
        tok.backend_tokenizer.no_truncation()
        tok.backend_tokenizer.no_padding()
        template = Path(__file__).parent / "templates" / f"{family}.jinja"
        tok.chat_template = template.read_text()
        texts, ids, possible_suffixes = [], [], set()
        for id_, parent in parents.items():
            message = {"role": "user", "content": prompt_text(parent["problem"], "omi2")}
            prefix = tok.apply_chat_template([message], tokenize=False, add_generation_prompt=True)
            marker = "__P012_RESPONSE_SENTINEL__"
            full = tok.apply_chat_template([message, {"role": "assistant", "content": marker}],
                                          tokenize=False, add_generation_prompt=False)
            if not full.startswith(prefix + marker):
                raise ValueError("Cannot separate the actual template's source and target")
            possible_suffixes.add(full[len(prefix + marker):])
            texts.append(prefix)
            ids.append(id_)
        if len(possible_suffixes) != 1:
            raise ValueError("Assistant suffix unexpectedly depends on the problem")
        suffixes[family] = possible_suffixes.pop()
        encodings = tok.backend_tokenizer.encode_batch(texts, add_special_tokens=False)
        prompt_lengths[family] = {k: len(e.ids) for k, e in zip(ids, encodings)}
        tokenizers[family] = tok
        proofs[family] = {"members": names, "backend_equivalent_without_postprocessor": True,
            "backend_config_sha256": hashlib.sha256(json.dumps(backend_configs[0], sort_keys=True).encode()).hexdigest(),
            "template_sha256": sha256_file(template), "assistant_suffix": suffixes[family]}
    manifest = {"code_commit": execution_commit(), "source_sha256": sha256_file(Path(__file__)),
        "collection_database_sha256": sha256_file(pool / "pool.sqlite"), "family_equivalence": proofs,
        "maximum_training_tokens": 4096,
        "method": "source and target encoded separately, matching LLaMA-Factory encode_oneturn; no truncation; efficient_eos=False for both fixed templates"}
    write_json(output / "MANIFEST.json", manifest)
    out = sqlite3.connect(output / "lengths.sqlite")
    out.execute("CREATE TABLE lengths(source_rowid INTEGER PRIMARY KEY,qwen_tokens INTEGER,llama_tokens INTEGER)")
    cursor = source.execute("SELECT rowid,parent,solution FROM solutions ORDER BY rowid")
    started, counts, histograms = time.monotonic(), Counter(), {k: Counter() for k in tokenizers}
    while batch := cursor.fetchmany(512):
        sizes = {}
        for family, tok in tokenizers.items():
            encodings = tok.backend_tokenizer.encode_batch([r[2] + suffixes[family] for r in batch], add_special_tokens=False)
            sizes[family] = [prompt_lengths[family][r[1]] + len(e.ids) for r, e in zip(batch, encodings)]
            histograms[family].update(sizes[family])
        out.executemany("INSERT INTO lengths VALUES(?,?,?)", [(r[0], q, l) for r, q, l in zip(batch, sizes["qwen"], sizes["llama3"])])
        counts["rows"] += len(batch)
        counts["within_both_4096"] += sum(q <= 4096 and l <= 4096 for q, l in zip(sizes["qwen"], sizes["llama3"]))
        if counts["rows"] % 32768 == 0:
            out.commit()
            print(json.dumps({"counts": dict(counts), "seconds": time.monotonic() - started}), flush=True)
    out.commit()
    expected = source.execute("SELECT count(*) FROM solutions").fetchone()[0]
    if counts["rows"] != expected:
        raise ValueError("Incomplete length scan")
    result = {"counts": dict(counts), "seconds": time.monotonic() - started,
              "histograms": {f: dict(sorted(h.items())) for f, h in histograms.items()},
              "maximum_before_filter": {f: max(h) for f, h in histograms.items()},
              "maximum_retained_per_family_bound": 4096, "actual_LF_preprocessing_proof": "required in C6 before C8"}
    out.close()
    source.close()
    write_json(output / "LENGTHS_COMPLETE.json", result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("pool", "assets", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    a = parser.parse_args()
    result = check_lengths(a.pool, a.assets, a.output)
    print(json.dumps({"counts": result["counts"], "seconds": result["seconds"]}))

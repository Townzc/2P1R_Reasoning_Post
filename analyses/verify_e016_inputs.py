"""Independent CPU reconstruction of the frozen E016 prompt-only release."""
import argparse
import base64
import gzip
import hashlib
import json
from pathlib import Path
import subprocess


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def lines(path):
    with Path(path).open() as f:
        return [json.loads(line) for line in f if line.strip()]


def verify(tokenizer_dir, raw_train, ledger, out):
    from scripts.audit_family_matching import verified_tokenizer
    tokenizer, _ = verified_tokenizer(tokenizer_dir)
    root = Path("reports/real_math_e016_inputs_r1")
    release = json.loads(Path("configs/real_math_e016/release.json").read_text())
    manifest = json.loads((root / "manifest.json").read_text())
    assert digest(root / "manifest.json") == release["manifest_sha256"]
    cfgpath = Path("configs/real_math_e016/capability.json")
    cfg = json.loads(cfgpath.read_text())
    assert digest(cfgpath) == manifest["config_sha256"]
    assert (cfg["max_seconds"], cfg["guard_seconds"], cfg["expected_prior_jobs"],
            cfg["expected_prior_used_seconds"]) == (470, 15, 19, 6686)
    assert (cfg["eval_batch_size"], cfg["max_length"], cfg["max_new_tokens"], cfg["optimizer_updates"]) == (8, 1024, 768, 0)
    for path, expected in manifest["source_files_sha256"].items():
        assert digest(path) == expected
        raw = subprocess.check_output(["git", "show", manifest["source_commit"]+":"+path])
        assert hashlib.sha256(raw).hexdigest() == expected
    assert set(manifest["files_sha256"]) == {"rows.jsonl", "cases.json", "cpu_evidence.json"}
    for name, expected in manifest["files_sha256"].items():
        assert digest(root / name) == expected
    parent_root = Path("reports/real_math_c017_parents_r2")
    freeze = json.loads((parent_root / "freeze.json").read_text())
    raw = gzip.decompress(base64.b64decode((parent_root / "problem_manifest.jsonl.gz.b64").read_bytes()))
    assert hashlib.sha256(raw).hexdigest() == freeze["problem_manifest_sha256"]
    parents = [json.loads(line) for line in raw.splitlines()]
    dev = sorted((p for p in parents if p["dataset"] == "gsm8k" and p["partition"] == "development"), key=lambda p: p["rank"])
    selected = dev[16:80]
    assert len(dev) == 512 and [p["rank"] for p in selected] == list(range(17, 81))
    old = lines("reports/real_math_e013_inputs_r1/dev.jsonl")
    assert [r["problem_id"] for r in old] == [p["id"] for p in dev[:16]]
    forbidden = {p["group_id"] for p in parents if p["partition"] != "development" or p["dataset"] != "gsm8k"}
    forbidden |= {r["group_id"] for r in old}
    assert not forbidden.intersection(p["group_id"] for p in selected)
    receipts = json.loads((parent_root / "source_receipts.json").read_text())
    assert digest(raw_train) == receipts["gsm8k_train.jsonl"]["sha256"]
    original = lines(raw_train)
    expected_rows, expected_cases = [], []
    for parent in selected:
        row = original[int(parent["id"].rsplit("/", 1)[1])]
        answer = row["answer"].split("####")[-1].strip()
        assert hashlib.sha256(row["question"].encode()).hexdigest() == parent["problem_sha256"]
        assert hashlib.sha256(answer.encode()).hexdigest() == parent["answer_sha256"]
        expected_rows.append({"problem_id": parent["id"], "group_id": parent["group_id"],
                              "development_rank": parent["rank"], "prompt": row["question"], "answer": answer})
        prompt = "Problem: " + row["question"] + "\nSolution:\n"
        ids = tokenizer(prompt, add_special_tokens=False)["input_ids"]
        assert len(ids) + 768 <= 1024 and tokenizer.eos_token_id not in ids
        expected_cases.append({"problem_id": parent["id"], "serialized_prompt": prompt, "prompt_ids": ids})
    assert lines(root / "rows.jsonl") == expected_rows
    assert json.loads((root / "cases.json").read_text()) == expected_cases
    state = json.loads(Path(ledger).read_text())
    assert digest(ledger) == cfg["expected_ledger_sha256"]
    assert state["authorized_gpu_seconds"] == 7200 and len(state["jobs"]) == 19
    assert len({j["run_id"] for j in state["jobs"]}) == 19
    assert sum(j["charged_seconds"] for j in state["jobs"]) == 6686
    for job in state["jobs"]:
        assert job["status"] != "reserved"
        assert job == json.loads((Path("runs") / job["run_id"] / "resource_receipt.json").read_text())
    report = {"status": "passed_independent_cpu_reconstruction", "release_sha256": digest("configs/real_math_e016/release.json"),
              "parents": 64, "prompt_streams_reconstructed": 64, "group_overlap": 0,
              "old_observed_parents_excluded": 16, "unused_development_reserve": 432,
              "ledger_receipts_reconciled": 19, "used_seconds": 6686, "remaining_seconds": 514,
              "maximum_reservation": 485, "remaining_after_maximum": 29,
              "new_model_calls": 0, "server_contacted": False, "official_test_read": False}
    with out.open("x") as f:
        json.dump(report, f, indent=2, sort_keys=True); f.write("\n")
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--tokenizer-dir", required=True, type=Path)
    p.add_argument("--raw-train", required=True, type=Path)
    p.add_argument("--ledger", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    a = p.parse_args()
    print(json.dumps(verify(a.tokenizer_dir, a.raw_train, a.ledger, a.out), indent=2))


if __name__ == "__main__":
    main()

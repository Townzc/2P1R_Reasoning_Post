"""Prepare and inspect E016 on CPU; one explicit bounded inference-only launch.

The two fixed endpoints are the original base and the retained E015 checkpoint.
No optimizer, new checkpoint, downloads, prompt search or automatic next job.
"""
import argparse
from datetime import datetime, timezone
import gc
import hashlib
import json
import math
import os
from pathlib import Path
import random
import signal
import subprocess
import sys
import time

from analyses.e014 import (audit_predictions, check_generation_settings,
                          effective_generation_config, library_sources, stream_hash)
from analyses.gsm8k_answer_audit import score, summarize, VERSION
from scripts.audit_family_matching import verified_tokenizer
from scripts.run_relation_engineering import check_ledger, server_preflight
from src.real_math_engineering import dump, git, parent_index, source_files, write_rows
from src.real_math_experiment import generate
from src.sft_data import prefix, read_jsonl, sha256_file

CONFIG = Path("configs/real_math_e016/capability.json")
RELEASE = Path("configs/real_math_e016/release.json")
INPUTS = Path("reports/real_math_e016_inputs_r1")
CHECKPOINT_MANIFEST = Path("runs/gsm8k_terminal_decay_e015_r1/checkpoint_manifest.json")
OLD_DEV = Path("reports/real_math_e013_inputs_r1/dev.jsonl")


def dependencies():
    return sorted(set(source_files() + [str(CONFIG), "analyses/e016.py",
        "analyses/gsm8k_answer_audit.py", "analyses/verify_e016_inputs.py", "analyses/e014.py", "analyses/e014_audit.py",
        "analyses/real_math_e013_failures.py", "tests/test_e016.py", "tests/test_gsm8k_answer_audit.py"]))


def provenance():
    if git("status", "--porcelain", "--untracked-files=no"):
        raise ValueError("Publish tracked source before E016")
    commit = git("rev-parse", "HEAD")
    if commit != git("rev-parse", "origin/main"):
        raise ValueError("Synchronize published origin/main")
    git("ls-files", "--error-unmatch", *dependencies())
    return {"source_commit": commit, "source_files_sha256": {p: sha256_file(p) for p in dependencies()}}


def selected_parents():
    old = json.loads(Path("configs/real_math_e013/overfit.json").read_text())
    parents = parent_index(old)
    development = sorted((p for p in parents.values() if p["dataset"] == "gsm8k"
                          and p["partition"] == "development"), key=lambda p: p["rank"])
    if len(development) != 512 or [p["rank"] for p in development] != list(range(1, 513)):
        raise ValueError("Original development population differs")
    observed = read_jsonl(OLD_DEV)
    if [r["problem_id"] for r in observed] != [p["id"] for p in development[:16]]:
        raise ValueError("Observed development identities differ")
    selected = development[16:80]
    forbidden = {p["group_id"] for p in parents.values()
                 if p["partition"] != "development" or p["dataset"] != "gsm8k"}
    forbidden.update(r["group_id"] for r in observed)
    if len({p["group_id"] for p in selected}) != 64 or any(
            p["group_id"] in forbidden or p["original_split"] != "train" or p["exclusions"] for p in selected):
        raise ValueError("Calibration group overlap or source exclusion")
    return selected


def validate_rows(rows, tokenizer):
    selected = selected_parents()
    if len(rows) != 64:
        raise ValueError("Keep all 64 calibration parents")
    cases = []
    for row, parent in zip(rows, selected):
        if (set(row) != {"problem_id", "group_id", "development_rank", "prompt", "answer"}
                or row["problem_id"] != parent["id"] or row["group_id"] != parent["group_id"]
                or row["development_rank"] != parent["rank"]):
            raise ValueError("Fixed calibration parent/order differs")
        for key, source in (("prompt", "problem_sha256"), ("answer", "answer_sha256")):
            if hashlib.sha256(row[key].encode()).hexdigest() != parent[source]:
                raise ValueError("Original prompt/reference bytes differ")
        ids = tokenizer(prefix(row["prompt"]), add_special_tokens=False)["input_ids"]
        if not ids or tokenizer.eos_token_id in ids or len(ids) + 768 > 1024:
            raise ValueError("Context cap fails; no filtering or truncation")
        cases.append({"problem_id": row["problem_id"], "serialized_prompt": prefix(row["prompt"]), "prompt_ids": ids})
    return cases


def prepare(tokenizer, raw_train):
    if INPUTS.exists() or RELEASE.exists():
        raise FileExistsError("Immutable E016 release already exists")
    source = provenance()
    receipts = json.loads(Path("reports/real_math_c017_parents_r2/source_receipts.json").read_text())
    if sha256_file(raw_train) != receipts["gsm8k_train.jsonl"]["sha256"]:
        raise ValueError("Pinned original training source differs")
    original = read_jsonl(raw_train)
    rows = []
    for parent in selected_parents():
        item = original[int(parent["id"].rsplit("/", 1)[1])]
        rows.append({"problem_id": parent["id"], "group_id": parent["group_id"],
                     "development_rank": parent["rank"], "prompt": item["question"],
                     "answer": item["answer"].rsplit("####", 1)[1].strip()})
    cases = validate_rows(rows, tokenizer)
    widths = [max(len(c["prompt_ids"]) for c in cases[i:i+8]) for i in range(0, 64, 8)]
    cfg = json.loads(CONFIG.read_text())
    if cfg["scorer_version"] != VERSION or sha256_file(CHECKPOINT_MANIFEST) != cfg["checkpoint_manifest_sha256"]:
        raise ValueError("Scorer or checkpoint identity differs")
    evidence = {"phase": "E016_CPU_INPUTS", "parents": 64, "development_ranks": [17, 80],
                "original_development_count": 512, "previously_observed": 16,
                "remaining_development_reserve": 432, "group_overlap": 0,
                "new_model_calls": 0, "server_contacted": False, "optimizer_updates": 0,
                "planned_generations": 128, "maximum_generated_tokens": 98304,
                "prompt_tokens_per_model": sum(len(c["prompt_ids"]) for c in cases),
                "left_padded_prompt_tokens_per_model": sum(widths) * 8,
                "maximum_prompt_tokens": max(len(c["prompt_ids"]) for c in cases),
                "source_training_jsonl_sha256": sha256_file(raw_train),
                "official_test_read_during_preparation": False}
    INPUTS.mkdir()
    write_rows(INPUTS / "rows.jsonl", rows)
    dump(INPUTS / "cases.json", cases)
    dump(INPUTS / "cpu_evidence.json", evidence)
    dump(INPUTS / "manifest.json", {**source, "phase": "E016_INPUTS",
        "library_sources_sha256": library_sources(), "config_sha256": sha256_file(CONFIG),
        "files_sha256": {name: sha256_file(INPUTS / name) for name in ("rows.jsonl", "cases.json", "cpu_evidence.json")}})
    dump(RELEASE, {"phase": "E016_RELEASE", "manifest_sha256": sha256_file(INPUTS / "manifest.json")})
    return evidence


def load_release(tokenizer):
    release = json.loads(RELEASE.read_text())
    if release["phase"] != "E016_RELEASE" or sha256_file(INPUTS / "manifest.json") != release["manifest_sha256"]:
        raise ValueError("E016 release differs")
    manifest = json.loads((INPUTS / "manifest.json").read_text())
    if manifest["config_sha256"] != sha256_file(CONFIG) or set(manifest["source_files_sha256"]) != set(dependencies()):
        raise ValueError("Configuration/dependency set differs")
    for path, expected in manifest["source_files_sha256"].items():
        old = subprocess.check_output(["git", "show", manifest["source_commit"] + ":" + path])
        if sha256_file(path) != expected or hashlib.sha256(old).hexdigest() != expected:
            raise ValueError("Runtime/historical source differs: " + path)
    if manifest["library_sources_sha256"] != library_sources():
        raise ValueError("Installed generation/model implementation differs")
    for name, expected in manifest["files_sha256"].items():
        if Path(name).name != name or sha256_file(INPUTS / name) != expected:
            raise ValueError("Frozen input differs")
    rows = read_jsonl(INPUTS / "rows.jsonl")
    if validate_rows(rows, tokenizer) != json.loads((INPUTS / "cases.json").read_text()):
        raise ValueError("Raw prompt tokenization differs")
    return json.loads(CONFIG.read_text()), rows


def checkpoint_audit(folder, cfg):
    if sha256_file(CHECKPOINT_MANIFEST) != cfg["checkpoint_manifest_sha256"]:
        raise ValueError("E015 checkpoint manifest differs")
    folder = Path(folder).absolute()
    if any(p.is_symlink() for p in (folder, *folder.parents)):
        raise ValueError("Symlinked checkpoint path")
    manifest = json.loads(CHECKPOINT_MANIFEST.read_text())
    files = manifest["files"]
    if manifest["kind"] != "weights_only_not_optimizer_rng_resume" or len(files) != 12 or {p.name for p in folder.iterdir()} != set(files):
        raise ValueError("Complete exact E015 inventory required")
    for name, record in files.items():
        p = folder / name
        if Path(name).name != name or p.is_symlink() or not p.is_file() or p.stat().st_size != record["bytes"] or stream_hash(p) != record["sha256"]:
            raise ValueError("E015 checkpoint file differs: " + name)
    return {"all_files_verified": True, "file_count": 12, "bytes": sum(r["bytes"] for r in files.values()),
            "manifest_sha256": cfg["checkpoint_manifest_sha256"]}


def rental_window(start, now=None):
    start = datetime.fromisoformat(start.replace("Z", "+00:00"))
    if start.tzinfo is None:
        raise ValueError("Timezone-aware power-on timestamp required")
    age = ((now or datetime.now(timezone.utc)) - start).total_seconds()
    # 485 process + 120 compact export + 180 shutdown/slack, within 20 minutes.
    if not math.isfinite(age) or age < 0 or age > 415:
        raise ValueError("Insufficient whole-rental time; shut down without a model job")
    return {"power_on_at_utc": start.isoformat(), "elapsed_seconds": age,
            "whole_window_cap_seconds": 1200, "remaining_seconds": 1200-age,
            "required_at_admission_seconds": 785, "gpu_rate_cny_per_hour": 8,
            "planned_rental_ceiling_cny": 8/3}


def decisions(scores):
    summaries = {name: summarize(scores[name]) for name in ("base", "e015")}
    if any(s["n"] != 64 for s in summaries.values()):
        raise ValueError("No decision from a shortened calibration")
    base, tuned = summaries["base"], summaries["e015"]
    clean = lambda s: s["parse_status"].get("parsed", 0) >= 48 and s["truncated"] <= 8
    capable = base["clean_correct"] >= 8 and clean(base)
    retained = (capable and clean(tuned) and tuned["clean_correct"] >= 8
                and 4*tuned["clean_correct"] >= 3*base["clean_correct"]
                and base["clean_correct"]-tuned["clean_correct"] <= 8)
    lost = sum(b["clean_correct"] and not t["clean_correct"] for b, t in zip(scores["base"], scores["e015"]))
    gained = sum(not b["clean_correct"] and t["clean_correct"] for b, t in zip(scores["base"], scores["e015"]))
    return {"metrics": summaries, "base_nonfloor_gate": capable, "e015_retention_screen": retained,
            "paired_lost": lost, "paired_gained": gained, "paired_net_correct_change": gained-lost,
            "scientific_grid_authorized": False,
            "interpretation": "Operational screening thresholds, not a powered noninferiority test or proof of generalization. Fixed 32-parent overfit endpoint is not the final scientific training recipe."}


def worker(args, tokenizer):
    cfg, rows = load_release(tokenizer)
    out = Path("runs") / cfg["run_id"]
    if os.environ.get("CS294_BOUNDED_RUN_ID") != cfg["run_id"] or not out.is_dir() or (out / "run_manifest.json").exists():
        raise ValueError("Mandatory unique bounded wrapper required")
    source = provenance()
    preflight = json.loads(Path(args.preflight).read_text())
    if (preflight["phase"] != "E016" or preflight["source_commit"] != source["source_commit"]
            or preflight["release_sha256"] != sha256_file(RELEASE)
            or preflight["accounting"]["ledger_sha256"] != cfg["expected_ledger_sha256"]
            or not preflight["server"]["model"]["all_files_verified"]
            or not preflight["checkpoint"]["all_files_verified"]
            or preflight["checkpoint_path"] != str(Path(args.checkpoint).resolve())
            or preflight["snapshot_path"] != str(Path(args.tokenizer_dir).resolve())):
        raise ValueError("Matching source/weights/ledger preflight required")
    rental_window(preflight["rental"]["power_on_at_utc"])
    import torch
    from transformers import AutoModelForCausalLM
    torch.set_num_threads(8)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    tokenizer.pad_token = tokenizer.eos_token
    manifest = {**source, "phase": "E016", "status": "running", "config": cfg,
                "release_sha256": sha256_file(RELEASE), "preflight_sha256": sha256_file(args.preflight),
                "server": preflight["server"], "checkpoint": preflight["checkpoint"],
                "tokenizer": preflight["tokenizer"], "started_at_utc": datetime.now(timezone.utc).isoformat(),
                "optimizer_updates": 0, "checkpoint_write": False, "official_test_evaluation": False,
                "parameter_dtype": "float32", "autocast_dtype": "bfloat16", "attention": "sdpa", "tf32": False,
                "decoding": {"prompt": "Problem: {prompt}\nSolution:\n", "batch": 8, "max_new_tokens": 768,
                             "num_beams": 1, "do_sample": False, "extra_stop_strings": None}}
    dump(out / "run_manifest.json", manifest)
    scores, phases, generation_settings = {}, {}, {}
    start = time.monotonic()
    def stop(*_):
        raise TimeoutError("E016 watchdog stopped the finite calibration; no retry")
    signal.signal(signal.SIGTERM, stop)
    try:
        for name, snapshot in (("base", args.tokenizer_dir), ("e015", args.checkpoint)):
            torch.manual_seed(17); random.seed(17)
            tick = time.monotonic()
            model = AutoModelForCausalLM.from_pretrained(snapshot, dtype=torch.float32,
                      attn_implementation="sdpa", local_files_only=True).cuda()
            if any(p.dtype != torch.float32 for p in model.parameters()):
                raise ValueError("Endpoint parameter dtype differs")
            model.requires_grad_(False)
            torch.cuda.synchronize()
            phases[name + "_load"] = time.monotonic()-tick
            settings = effective_generation_config(model.generation_config, tokenizer, cfg)
            check_generation_settings(settings, cfg)
            if generation_settings and settings != generation_settings["base"]:
                raise ValueError("Effective decoding differs between endpoints")
            generation_settings[name] = settings
            dump(out / (name + "_generation_config.json"), settings)
            torch.cuda.reset_peak_memory_stats()
            tick = time.monotonic()
            predictions = generate(model, tokenizer, rows, cfg, out / (name + ".jsonl"))
            phases[name + "_generation"] = time.monotonic()-tick
            scores[name] = [score(r, r["text"], r["score"]["ended_with_eos"], r["score"]["truncated"]) for r in predictions]
            write_rows(out / (name + "_marked.jsonl"), [{"problem_id": r["problem_id"], "score": s}
                        for r, s in zip(rows, scores[name])])
            dump(out / (name + "_profile.json"), {"n": 64, "generation_seconds": phases[name + "_generation"],
                 "output_tokens": sum(r["generated_tokens"] for r in predictions),
                 "peak_allocated_mib": torch.cuda.max_memory_allocated()/1024**2,
                 "peak_reserved_mib": torch.cuda.max_memory_reserved()/1024**2})
            del model, predictions
            gc.collect(); torch.cuda.empty_cache()
        dump(out / "metrics.json", decisions(scores))
        manifest["status"] = "completed"
    except BaseException as exc:
        manifest.update(status="failed", exception_type=type(exc).__name__)
        raise
    finally:
        dump(out / "phase_timings.json", {"completed_phases_seconds": phases, "wall_seconds": time.monotonic()-start})
        manifest.update(finished_at_utc=datetime.now(timezone.utc).isoformat(), completed_models=list(scores))
        dump(out / "run_manifest.tmp", manifest)
        (out / "run_manifest.tmp").replace(out / "run_manifest.json")


def audit_run(tokenizer, run, out):
    cfg, rows = load_release(tokenizer)
    manifest = json.loads((run / "run_manifest.json").read_text())
    if manifest["status"] != "completed" or manifest["config"] != cfg or manifest["release_sha256"] != sha256_file(RELEASE):
        raise ValueError("Incomplete/different E016; retain failure records")
    scores, settings = {}, {}
    timings = json.loads((run / "phase_timings.json").read_text())["completed_phases_seconds"]
    for name in ("base", "e015"):
        predictions = audit_predictions(run / (name + ".jsonl"), rows, tokenizer, cfg)
        scores[name] = [score(r, r["text"], r["score"]["ended_with_eos"], r["score"]["truncated"]) for r in predictions]
        if read_jsonl(run / (name + "_marked.jsonl")) != [{"problem_id": r["problem_id"], "score": s} for r, s in zip(rows, scores[name])]:
            raise ValueError("Marked-answer records differ")
        settings[name] = json.loads((run / (name + "_generation_config.json")).read_text())
        check_generation_settings(settings[name], cfg)
        profile = json.loads((run / (name + "_profile.json")).read_text())
        if profile["n"] != 64 or profile["output_tokens"] != sum(r["generated_tokens"] for r in predictions):
            raise ValueError("Generation profile denominator/token count differs")
        for key in ("generation_seconds", "peak_allocated_mib", "peak_reserved_mib"):
            if type(profile[key]) not in (int, float) or not math.isfinite(profile[key]) or profile[key] <= 0:
                raise ValueError("Invalid generation profile measurement")
        if profile["generation_seconds"] != timings[name + "_generation"]:
            raise ValueError("Generation phase/profile timing differs")
    if settings["base"] != settings["e015"]:
        raise ValueError("Effective decoding differs between endpoints")
    if decisions(scores) != json.loads((run / "metrics.json").read_text()):
        raise ValueError("Aggregate or gate differs")
    receipt = json.loads((run / "resource_receipt.json").read_text())
    if (receipt["run_id"] != cfg["run_id"] or receipt["status"] != "completed" or receipt["exit_code"] != 0
            or type(receipt["charged_seconds"]) is not int or not 0 < receipt["charged_seconds"] <= 485):
        raise ValueError("Resource receipt differs")
    evidence = {"status": "passed_record_consistency_checks", "raw_token_streams_checked": 128,
                "new_model_calls": 0, "proofs_verified": False, "logits_recomputed": False,
                "result": decisions(scores), "resource_receipt_sha256": sha256_file(run / "resource_receipt.json")}
    dump(out, evidence)
    return evidence


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", nargs="?", default="inspect", choices=("prepare", "inspect", "launch", "worker", "audit"))
    p.add_argument("--tokenizer-dir", required=True, type=Path)
    p.add_argument("--raw-train", type=Path)
    p.add_argument("--checkpoint", type=Path)
    p.add_argument("--ledger", default=".local/resource_ledger.json")
    p.add_argument("--preflight")
    p.add_argument("--out", type=Path)
    p.add_argument("--power-on-at-utc")
    p.add_argument("--power-on-time-source", choices=("provider_timestamp", "owner_start_notification"))
    p.add_argument("--execute", action="store_true")
    a = p.parse_args()
    tokenizer, token_record = verified_tokenizer(a.tokenizer_dir)
    if a.action == "prepare":
        print(json.dumps(prepare(tokenizer, a.raw_train), indent=2)); return 0
    if a.action == "worker":
        worker(a, tokenizer); return 0
    cfg, _ = load_release(tokenizer)
    if a.action == "audit":
        print(json.dumps(audit_run(tokenizer, Path("runs") / cfg["run_id"], a.out), indent=2)); return 0
    source = provenance()
    resource = json.loads(Path("configs/resource_budget.json").read_text())
    accounting = check_ledger(cfg, a.ledger, resource)
    report = {"phase": "E016", "source_commit": source["source_commit"], "status": "not_run",
              "accounting": accounting, "release_sha256": sha256_file(RELEASE), "tokenizer": token_record,
              "generations": 128, "optimizer_updates": 0, "new_model_calls": 0}
    if a.action == "inspect" or not a.execute:
        print(json.dumps(report, indent=2)); return 0
    if not a.checkpoint or not a.power_on_at_utc or not a.power_on_time_source:
        raise ValueError("Explicit checkpoint, power-on time and evidence source required")
    report["rental"] = rental_window(a.power_on_at_utc)
    report["rental"]["time_source"] = a.power_on_time_source
    report["server"] = server_preflight(cfg, a.tokenizer_dir)
    if report["server"]["gpu"].split(",")[2].strip() != cfg["driver_version"]:
        raise ValueError("Pinned driver differs")
    report["checkpoint"] = checkpoint_audit(a.checkpoint, cfg)
    report["checkpoint_path"] = str(a.checkpoint.resolve())
    report["snapshot_path"] = str(a.tokenizer_dir.resolve())
    report["rental"].update(rental_window(a.power_on_at_utc))
    preflight = Path(".local") / ("e016_preflight_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f") + ".json")
    dump(preflight, report)
    check_ledger(cfg, a.ledger, resource)
    return subprocess.call([sys.executable, "-m", "scripts.run_bounded", "--run-id", cfg["run_id"],
        "--max-seconds", str(cfg["max_seconds"]), "--ledger", a.ledger,
        "--expected-ledger-sha256", cfg["expected_ledger_sha256"], "--require-full-cap", "--",
        sys.executable, "-m", "analyses.e016", "worker", "--tokenizer-dir", str(a.tokenizer_dir),
        "--checkpoint", str(a.checkpoint), "--preflight", str(preflight)])


if __name__ == "__main__":
    sys.exit(main())

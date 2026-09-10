"""CPU audit of already-observed E013 development outputs, not a new score claim."""
import argparse
import json
from pathlib import Path

from analyses.e014 import audit_predictions
from analyses.gsm8k_answer_audit import score, summarize, VERSION
from scripts.audit_family_matching import verified_tokenizer
from src.real_math_engineering import dump, git, load_frozen, write_rows
from src.sft_data import sha256_file


def audit(tokenizer, out):
    if out.exists():
        raise FileExistsError("Immutable C019 output already exists")
    if git("status", "--porcelain", "--untracked-files=no") or git("rev-parse", "HEAD") != git("rev-parse", "origin/main"):
        raise ValueError("Publish source before CPU audit")
    cfg, _, _, dev, _, _, _ = load_frozen(tokenizer)
    run = Path("runs/gsm8k_overfit_e013_r1")
    models, paired, paths = {}, [], []
    for name in ("base_dev", "final_dev"):
        path = run / (name + ".jsonl")
        paths.append(path)
        predictions = audit_predictions(path, dev, tokenizer, cfg)
        models[name] = [score(r, r["text"], r["score"]["ended_with_eos"], r["score"]["truncated"])
                        for r in predictions]
    for i, row in enumerate(dev):
        paired.append({"problem_id": row["problem_id"], "answer": row["answer"],
                       **{name: scores[i] for name, scores in models.items()}})
    report = {"phase": "C019", "status": "post_hoc_observed_development_only",
              "source_commit": git("rev-parse", "HEAD"), "scorer_version": VERSION,
              "source_sha256": {str(p): sha256_file(p) for p in paths + [
                  Path("analyses/gsm8k_answer_audit.py"), Path("analyses/c019_saved_capability.py")]},
              "raw_token_streams_reverified": 32, "historical_scores_modified": False,
              "historical_strict_correct": {"base_dev": 0, "final_dev": 0},
              "diagnostic_metrics": {name: summarize(scores) for name, scores in models.items()},
              "clean_base_successes_lost": sum(p["base_dev"]["clean_correct"] and not p["final_dev"]["clean_correct"] for p in paired),
              "clean_base_failures_gained": sum(not p["base_dev"]["clean_correct"] and p["final_dev"]["clean_correct"] for p in paired),
              "new_model_calls": 0, "server_contacted": False,
              "limits": "Scorer designed after seeing these outputs. Not an unbiased accuracy estimate, benchmark score, proof audit, or E015 development result. The original E013 scores remain authoritative for that run."}
    out.mkdir(parents=True)
    write_rows(out / "paired_answers.jsonl", paired)
    dump(out / "summary.json", report)
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--tokenizer-dir", required=True, type=Path)
    p.add_argument("--out-dir", required=True, type=Path)
    a = p.parse_args()
    tokenizer, _ = verified_tokenizer(a.tokenizer_dir)
    print(json.dumps(audit(tokenizer, a.out_dir), indent=2))


if __name__ == "__main__":
    main()

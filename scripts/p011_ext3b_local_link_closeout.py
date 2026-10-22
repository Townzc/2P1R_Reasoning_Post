"""One reviewed local continuation; original failed audit and payload stay intact.

The large cell stopped before its first state oracle/native decode. Reuse its
completed archive extraction, journal checks and first three input checks.
The small cell takes its first local oracle here. Scientific functions remain
the original functions; only endpoint-link verification and output locators differ.
"""
import argparse
import fcntl
import time
from pathlib import Path

from experiments.p011 import ext4b_path as path
from experiments.p011.ext4b_runtime_contract import LOCAL, INPUTS, SPEC, JOBS, review
from experiments.p011.owner_0205_common import create, read, sha, digest, utc
from experiments.p011.local_endpoint_link_verify import verify_inputs
from experiments.p011.ext4b_encoded import EncodedRows
from experiments.p011 import long_owner_evidence as evidence, long_transport, long_evaluation
from experiments.p011 import ext3b_math_scope as scope
from experiments.p011 import ext3b_math_scoring as scoring, ext3b_math_score_process as score_process
from experiments.p011.long_d2_scope import greedy_interval
from experiments.sft_allocation_midpoint.common import verify
from scripts.p011_ext4b_io import remaining_window

R = Path(".local/p011_20261020/r1")
RECOVERY = LOCAL / "local_endpoint_links_r1"
PRIOR_INPUTS = R / "ext4b_inputs_r1"
RECOVERY_SPEC = Path("reports/p011_20261020/ext3b_local_endpoint_links_preflight_v1/SPEC.json")
LARGE_ATTEMPT = JOBS[0] + "_attempt1"
SMALL_ATTEMPT = JOBS[1] + "_attempt1"


def admit(local_review):
    spec = read(RECOVERY_SPEC)
    for name, expected in spec["source_files"].items():
        if sha(name) != expected:
            raise ValueError("Exact local-continuation source changed: " + name)
    accepted = read(local_review)
    if (accepted.get("scope") != spec["scope"]
            or accepted.get("decision") not in ("PASS", "PASS-WITH-NOTES")
            or accepted.get("spec_sha256") != sha(RECOVERY_SPEC)
            or accepted.get("source_files") != spec["source_files"]
            or sha(accepted["local_report_path"]) != accepted["report_sha256"]
            or any(accepted.get(flag) is not True for flag in spec["required_flags"])):
        raise ValueError("Exact new Claude disposition and local-continuation CR required")
    return spec


def reuse_large_prefix(spec, dispatch, saved):
    old = LOCAL / "audit" / LARGE_ATTEMPT
    for name, binding in spec["failed_prefix_bindings"].items():
        p = Path(name)
        if p.stat().st_size != binding["bytes"] or sha(p) != binding["sha256"]:
            raise ValueError("Original failed-prefix evidence changed")
    failure = read(old / "FAILED.json")
    if (failure["type"] != "ValueError" or failure["message"] != "Artifact differs: ENDPOINT_GPU.json"
            or read(R / "EXT3B_R9072_FIRST_FULL_ORACLE_CLI_EXIT.json")["exit_code"] != 1
            or any((old / n).exists() for n in ("COMPLETE_PROOF.json", "SCORING_ROWS.json", "DECODED.json"))
            or read(saved / "COMPLETED.json")["receipt_sha256"] != spec["large_original_result_sha256"]
            or sha(dispatch / "RESULT.json") != spec["large_original_result_sha256"]):
        raise ValueError("Only the exact pre-science large-cell failure may continue")
    # The fixed original source reaches this failure only after extract,
    # identity/timing/ledger and journals checks returned successfully.
    # Project their saved ledger values without replaying those completed checks.
    ledger = read(saved / "DERIVED_LEDGER_VIEW.json")
    intent = read(dispatch / "INTENT.json")
    units = scope.expected_units(intent["job_spec"]["U"])
    attempted = {u: ledger[LARGE_ATTEMPT + "/unit/" + u] for u in units
                 if ledger[LARGE_ATTEMPT + "/unit/" + u] is not None}
    done = {u: ledger[LARGE_ATTEMPT + "/done/" + u] for u in units
            if ledger[LARGE_ATTEMPT + "/done/" + u] is not None}
    return old / "payload", attempted, done


def audit(out, attempt, spec):
    from transformers import AutoTokenizer
    dispatch = LOCAL / "dispatch" / attempt
    remaining_window(dispatch)
    intent = read(dispatch / "INTENT.json")
    job = intent["job_spec"]
    expected_job = JOBS[0] if attempt == LARGE_ATTEMPT else JOBS[1]
    if intent["job"] != expected_job or job != read(path.ACTUAL)["jobs"][expected_job]:
        raise ValueError("Exact original completed job and unchanged actual inputs required")
    saved = LOCAL / "collect" / attempt
    collected = read(saved / "COMPLETED.json")
    if not collected["original_worker_completed"]:
        raise ValueError("This narrow recovery covers the two completed original workers only")
    receipt = read(saved / "ORIGINAL_RESULT.json")
    ledger = read(saved / "DERIVED_LEDGER_VIEW.json")
    claim = ledger[attempt + "/claim"]
    reused = attempt == LARGE_ATTEMPT
    if reused:
        payload, attempted, done = reuse_large_prefix(spec, dispatch, saved)
    else:
        if (LOCAL / "audit" / attempt).exists():
            raise ValueError("Small-cell original oracle must never have been attempted")
        mapping = read(saved / "LEDGER_SOURCE_MAP.json")
        raw = read(saved / "ACTUAL_NAMED_RECORDS.json")
        if any(ledger[k] != raw[origin] for k, origin in mapping.items()) or raw[attempt + "/dispatch"] != intent:
            raise ValueError("Original source mapping changed")
        long_transport.extract(saved / "evidence.tar", out / "payload", receipt["artifact"], 64 * 1024**3)
        payload = out / "payload"
        identity = read(payload / "IDENTITY.json")
        timing = read(payload / "TIMING_POLICY.json")
        if (identity != intent["identity"] or read(payload / "CLAIM.json") != claim
                or read(payload / "ADMISSION.json") != intent
                or timing != path.timing(job, intent, claim["worker_start_epoch"])):
            raise ValueError("Original identity, admission or timing changed")
        attempted, done = scope.journals(payload, attempt, job["U"], ledger)
    identity = read(payload / "IDENTITY.json")
    timing = read(payload / "TIMING_POLICY.json")
    link_proof = verify_inputs(INPUTS, job["local_input_files"], PRIOR_INPUTS, reuse_passed_prefix=reused)
    model = Path(job["model"]["local_path"])
    verify(model, job["model"]["local_audit_asset_files"])
    config = read(model / "config.json")
    rows = EncodedRows(INPUTS / "ENCODED.jsonl", read(INPUTS / "ROW_METADATA.json"), job["questions"])
    plan = read(INPUTS / (job["logical_id"] + "_PLAN.json"))
    rates = read(INPUTS / "RATES_S-F15.json")
    trained = evidence.verify_training(payload, rows, plan, rates, "S-F15", config,
                                       identity, attempted, done, timing)
    tokenizer = AutoTokenizer.from_pretrained(model, local_files_only=True, trust_remote_code=False, use_fast=True)
    endpoint = scope.endpoint(payload, read(INPUTS / "ENDPOINT_LOCAL.json"), job["context"],
                              job["eos_token_ids"], tokenizer, config, attempted, done,
                              timing, trained["training_seconds"])
    if read(payload / "RESULT.json") != receipt["result"] or endpoint["outputs_decoded"] != 2500:
        raise ValueError("Returned complete MATH result differs")
    create(out / "SCORING_ROWS.json", endpoint.pop("scoring_rows"))
    create(out / "DECODED.json", endpoint.pop("decoded"))
    create(out / "PAYLOAD_REFERENCE.json", {"path": str(payload), "large_extraction_reused": reused,
           "old_payload_copied_or_reextracted": False, "original_failed_audit_erased": False})
    create(out / "COMPLETE_PROOF.json", {"utc": utc(), "passed": True, "job_sha256": digest(job),
           "training": trained, "endpoint": endpoint, "scoring_rows_sha256": sha(out / "SCORING_ROWS.json"),
           "private_binary_independently_reviewed": False, "original_training_native_scalar_functions_unchanged": True,
           "derived_resume_ledger_source_map": str(saved / "LEDGER_SOURCE_MAP.json"),
           "original_worker_completed": True, "actual_A3_accepted": False,
           "local_link_verification": link_proof, "failed_pre_science_prefix_reused": reused,
           "new_local_closeout_spec_sha256": sha(RECOVERY_SPEC), "original_failed_audit_preserved": True})


def score(out, attempt):
    dispatch = LOCAL / "dispatch" / attempt
    cap = min(7200, int(remaining_window(dispatch, 5) - 5))
    intent = read(dispatch / "INTENT.json")
    a = RECOVERY / "audit" / attempt
    proof = read(a / "COMPLETE_PROOF.json")
    if (proof["passed"] is not True
            or proof["new_local_closeout_spec_sha256"] != sha(RECOVERY_SPEC)
            or sha(a / "SCORING_ROWS.json") != proof["scoring_rows_sha256"]):
        raise ValueError("First complete state/native oracle required")
    rows = read(a / "SCORING_ROWS.json")
    binding = {"job_sha256": digest(intent["job_spec"]), "source_files": intent["source_files"],
               "oracle_sha256": sha(a / "COMPLETE_PROOF.json"), "source_review": intent["source_review"],
               "actual_review": intent["actual_review"]}
    result = score_process.supervise_once(out / "owned_score", rows, binding, cap)
    verified = scoring.verify_saved_scores(out / "owned_score/payload", rows, binding, cap)
    create(out / "COMPLETED.json", {"utc": utc(), "result": result, "saved_score_proof": verified,
           "score_cap_seconds": cap, "absolute_closeout_deadline_not_reset": True, "actual_A3_accepted": False})


def analyze(out):
    saved, bindings, deadline = [], {}, float("inf")
    actual = read(path.ACTUAL)
    for job, attempt in ((JOBS[1], SMALL_ATTEMPT), (JOBS[0], LARGE_ATTEMPT)):
        dispatch = LOCAL / "dispatch" / attempt
        intent = read(dispatch / "INTENT.json")
        if intent["job"] != job or intent["job_spec"] != actual["jobs"][job]:
            raise ValueError("Only exact matched-dose LARGE minus SMALL")
        deadline = min(deadline, time.time() + remaining_window(dispatch, 60))
        sf = RECOVERY / "score" / attempt / "COMPLETED.json"
        of = RECOVERY / "audit" / attempt / "COMPLETE_PROOF.json"
        s, o = read(sf)["saved_score_proof"], read(of)
        if (not s["passed"] or not o["passed"] or s["outputs"] != 2500
                or o["job_sha256"] != digest(intent["job_spec"])
                or o["new_local_closeout_spec_sha256"] != sha(RECOVERY_SPEC)):
            raise ValueError("Both original full MATH results and first score proofs required")
        saved.append(s)
        bindings[job] = {"attempt": attempt, "score_sha256": sha(sf), "oracle_sha256": sha(of)}
    sample = long_evaluation.paired_question_interval(*[s["endpoints"]["math500_sample"]["question_correct"] for s in saved])
    greedy = greedy_interval(*[s["endpoints"]["math500_greedy"]["question_correct"] for s in saved])
    if time.time() >= deadline:
        raise TimeoutError("Original extension result window elapsed")
    create(out / "COMPLETED.json", {"utc": utc(), "contrast": "LARGE_minus_SMALL", "sample": sample,
           "greedy": greedy, "descriptive_endpoints": {}, "bindings": bindings, "bootstrap_draws": 10000,
           "bootstrap_seed": 20261021, "single_training_seed": 17, "question_not_training_seed_population": True,
           "greedy_repeated_saved_bit_only_for_original_four_bit_interface": True,
           "A7_different_pool_descriptive_only_no_recomputed_contrast": True,
           "AIME_AMC": "NOT_RUN_BY_OWNER_OPTION2_SCOPE", "endpoint_scope_selected_by_completion_not_outcome": True,
           "actual_A3_accepted": False, "interpretation_written": False})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("audit", "score", "analysis"))
    parser.add_argument("--source-review", required=True)
    parser.add_argument("--actual-review", required=True)
    parser.add_argument("--local-review", required=True)
    parser.add_argument("--attempt-name", choices=(LARGE_ATTEMPT, SMALL_ATTEMPT))
    a = parser.parse_args()
    review(SPEC, a.source_review, a.actual_review)
    spec = admit(a.local_review)
    if a.mode != "analysis" and not a.attempt_name:
        raise ValueError("Exact original attempt required")
    out = RECOVERY / a.mode
    if a.mode != "analysis":
        out = out / a.attempt_name
    RECOVERY.mkdir(parents=True, exist_ok=True)
    with (LOCAL / "local_oracle.lock").open("a+") as lock:
        if a.mode == "audit":
            fcntl.flock(lock, fcntl.LOCK_EX)
        out.mkdir(parents=True, exist_ok=False)
        create(out / "ATTEMPT.json", {"utc": utc(), "mode": a.mode, "automatic_retry": False,
               "local_review_sha256": sha(a.local_review), "original_model_calls_added": 0})
        try:
            if a.mode == "audit":
                audit(out, a.attempt_name, spec)
            elif a.mode == "score":
                score(out, a.attempt_name)
            else:
                analyze(out)
        except BaseException as exc:
            create(out / "FAILED.json", {"utc": utc(), "type": type(exc).__name__,
                   "message": str(exc), "automatic_retry": False})
            raise


if __name__ == "__main__":
    main()

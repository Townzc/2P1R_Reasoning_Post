"""Finite A01-A10 orchestration of unchanged, reviewed Modal training/eval/scoring."""
from pathlib import Path
import copy
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import traceback
import zipfile

sys.dont_write_bytecode = True
sys.path.insert(0, ".")
sys.path.insert(0, ".local/p012_20261111/amendment7_v1")
from a7_ops import publish
from experiments.p012.evaluation import EvalConfig

LOCAL = Path(".local/p012_20261111")
PUBLIC = Path("reports/p012_20261111")
META = LOCAL / "amendment8_v1"
RUNS = LOCAL / "amendment8_modal_runs_v1"
MODAL = ".local/midpoint_20261011/venv/bin/modal"
PYTHON = ".local/p012_20261111/venv/bin/python"
ENV = dict(os.environ, MODAL_PROFILE="tangzhice", PYTHONPATH=".")
AUTHORITY = "5e1f9128180f1dcd222fc1e33fe691ec01030f38"
REVIEW = "ff567d06ba39fd1052a72c558e69dbe98f09dd24"
QUEUE = META / "A_QUEUE.json"
read = lambda p: json.loads(p.read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
utc = lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def verify_training_result(directory, request):
    assert read(directory / "result/STATUS.json")["success"]
    state = read(directory / "result/checkpoint/trainer_state.json")
    examples = [int(x.replace(",", "")) for x in re.findall(
        r"Num examples\s*=\s*([\d,]+)", (directory / "result/training.log").read_text())]
    assert examples and set(examples) == {request["dose"]["distinct_rows"]}, examples
    assert state["global_step"] == request["dose"]["expected_updates"]
    return {"global_step": state["global_step"], "expected_updates": request["dose"]["expected_updates"],
            "Num_examples": examples[-1], "expected_P_times_K": request["dose"]["distinct_rows"],
            "trainer_state_sha256": sha(directory / "result/checkpoint/trainer_state.json"),
            "training_log_sha256": sha(directory / "result/training.log"), "passed": True}


def main():
    assert not QUEUE.exists(), "Refuse duplicate controller"
    state = {"utc": utc(), "status": "running", "controller_pid": os.getpid(),
             "authority_commit": AUTHORITY, "accepted_review_commit": REVIEW,
             "automatic_retry": False, "events": []}
    def event(stage, **fields):
        row = {"utc": utc(), "stage": stage, **fields}
        state["events"].append(row)
        write(QUEUE, state)
        print(json.dumps(row), flush=True)
    children = {}
    first = read(META / "A01_LAUNCH.json")
    names = read(PUBLIC / "amendment8_A_admission_v1/LAUNCH_POLICY.json")["ordered_runs"]
    event("adopted_A01", **first)

    def start(directory, module):
        request = read(directory / "request.json")
        assert request["forecast"]["admitted"] and request["accepted_review_commit"] == REVIEW
        assert sha(Path(request["forecast"]["admission_file"])) == request["forecast"]["admission_sha256"]
        assert not (directory / "run.log").exists() and not (directory / "result").exists()
        for name, digest in request["source_sha256"].items():
            assert sha(Path("experiments/p012") / name) == digest
        with (directory / "run.log").open("x") as log:
            child = subprocess.Popen([MODAL, "run", "--detach", "-m", module,
                "--request", str(directory / "request.json"), "--output", str(directory / "result")],
                env=ENV, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                start_new_session=True)
        children[directory.name] = child
        event("launched", run_id=directory.name, pid=child.pid, request_sha256=sha(directory / "request.json"))

    def wait(directory):
        deadline = time.monotonic() + 8 * 3600
        while time.monotonic() < deadline:
            status = directory / "result/STATUS.json"
            text = (directory / "run.log").read_text(errors="replace")
            if status.exists():
                assert read(status)["success"], "Failed Modal call: " + directory.name
                child = children.get(directory.name)
                if (child is not None and child.poll() == 0) or "App completed." in text:
                    return
            assert "Traceback (most recent call last)" not in text, "Call failed: " + directory.name
            child = children.get(directory.name)
            if child is not None:
                assert child.poll() is None, "Child exited without artifacts: " + directory.name
            else:
                os.kill(first["pid"], 0)
            time.sleep(15)
        raise TimeoutError("Stop without retry: " + directory.name)

    try:
        for name in names:
            training = RUNS / name
            request = read(training / "request.json")
            if name != first["run_id"]:
                start(training, "experiments.p012.modal_train")
            wait(training)
            r2 = verify_training_result(training, request)
            write(training / "R2.json", r2)
            event("training_complete", run_id=name, **r2)
            evaluation = RUNS / name.replace("_s17_", "_s17_greedy_")
            evaluation.mkdir(exist_ok=False)
            r = read(LOCAL / "tier1_llama_v1/llama_base_gsm8k_p_s17_greedy_20261113_v1/request.json")
            r.update(run_id=evaluation.name, code_commit=request["code_commit"],
                     accepted_review_commit=REVIEW, prediction_commit=AUTHORITY,
                     authority="Owner-approved A8; reserved groupA greedy evaluation",
                     exploratory=True, excluded_from_H0_H3=True)
            r["config"].update(model="/p012/training/" + name + "/checkpoint", training_run_id=name,
                               checkpoint_manifest_sha256=sha(training / "result/CHECKPOINT_FILES.json"))
            r["forecast"] = dict(request["forecast"], forecast_usd=request["forecast"]["reserved_evaluation_usd"])
            r["source_sha256"] = {key: sha(Path("experiments/p012") / key) for key in r["source_sha256"]}
            EvalConfig(**r["config"]).validate()
            write(evaluation / "request.json", r)
            request_public = PUBLIC / "amendment8_evaluation_requests_v1"
            request_public.mkdir(exist_ok=True)
            rr = copy.deepcopy(r)
            rr.pop("input_jsonl")
            write(request_public / (evaluation.name + ".json"), rr)
            publish([request_public / (evaluation.name + ".json")], "P012 A8: bind reserved greedy request " + name)
            start(evaluation, "experiments.p012.modal_g0")
            wait(evaluation)
            prediction = {"utc": utc(), "prediction_commit": AUTHORITY, "accepted_review_commit": REVIEW,
                          "raw_sha256": sha(evaluation / "result/generation/raw.jsonl"),
                          "training_run_id": name, "prediction": request["prediction_binding"]["prediction"]}
            write(evaluation / "PREDICTION_BEFORE_SCORE.json", prediction)
            pred_public = PUBLIC / "amendment8_prescore_v1"
            pred_public.mkdir(exist_ok=True)
            write(pred_public / (name + ".json"), prediction)
            publish([pred_public / (name + ".json")], "P012 A8: record timestamped prediction before scoring " + name)
            subprocess.run([PYTHON, str(LOCAL / "amendment5_v1/score_endpoint.py"),
                            "amendment8_modal_runs_v1/" + evaluation.name], env=ENV, check=True)
            term = read(evaluation / "TERMINATION.json")
            output = PUBLIC / (name + "_results")
            output.mkdir(exist_ok=False)
            result = {"run_id": name, "group": "A", "cell": request["cell"], "model": request["model"]["repo"],
                      "seed": 17, "task": "gsm8k", "track": "A8_exploratory_full_finetuning",
                      "exploratory": True, "excluded_from_H0_H3": True, "dose": request["dose"],
                      "metrics": term["all"], "R2": r2, "prediction_before_score": prediction,
                      "data_sha256": request["dataset"]["sha256"], "accepted_source_review": REVIEW,
                      "training_run_id": name, "evaluation_run_id": evaluation.name,
                      "checkpoint_files_sha256": sha(training / "result/CHECKPOINT_FILES.json"),
                      "raw_sha256": prediction["raw_sha256"],
                      "labels_sha256": sha(evaluation / "score_v1/labels.jsonl"),
                      "independent_result_audit": "pending", "weights_retained_until_result_audit": True}
            write(output / "RESULTS.json", result)
            with zipfile.ZipFile(output / "evidence.zip", "x", zipfile.ZIP_DEFLATED) as archive:
                for root, prefix in [(training / "result", "training"), (evaluation / "result", "evaluation"),
                                     (evaluation / "score_v1", "scores")]:
                    for file in sorted(root.rglob("*")):
                        if file.is_file() and file.name != "artifacts.zip":
                            data = file.read_bytes()
                            assert b"/Users/" not in data
                            archive.writestr(prefix + "/" + str(file.relative_to(root)), data)
                archive.write(evaluation / "TERMINATION.json", "TERMINATION.json")
                archive.write(evaluation / "PREDICTION_BEFORE_SCORE.json", "PREDICTION_BEFORE_SCORE.json")
                archive.write(training / "R2.json", "R2.json")
            commit = publish([output], "P012 A8: publish full greedy and R2 evidence " + name)
            event("result_published", run_id=name, commit=commit, accuracy=term["all"]["accuracy"])
        state["status"] = "A_complete_B_C_storage_gate_pending_T_not_started"
        event("complete", endpoints=10)
    except Exception:
        state["status"] = "stopped_requires_inspection_no_retry"
        state["error"] = traceback.format_exc()
        write(QUEUE, state)
        raise


if __name__ == "__main__":
    main()

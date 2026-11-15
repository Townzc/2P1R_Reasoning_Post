"""CPU-only validation of archived A8 requests; no network or model execution."""
from pathlib import Path
import copy
import hashlib
import importlib.util
import json
import sys
import zipfile

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))
from experiments.p012 import training_config as original
from experiments.p012 import training_inputs as validator


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest = json.loads((HERE / "CANDIDATE_MANIFEST.json").read_text())
    assert sha(REPO / "experiments/p012/training_config.py") == manifest["base_training_config_sha256"]
    spec = importlib.util.spec_from_file_location("a8_review_candidate", HERE / "candidate/training_config.py")
    candidate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(candidate)
    assert sha(HERE / "candidate/training_config.py") == manifest["candidate_training_config_sha256"]
    validator.CELLS = candidate.CELLS
    validator.training_config = candidate.training_config
    results, requests = [], []
    with zipfile.ZipFile(HERE / "candidate_datasets.zip") as archive:
        for path in sorted((HERE / "request_templates").glob("*.json")):
            request = json.loads(path.read_text())
            assert request["forecast"]["admitted"] is False
            assert request["prediction_commit"] == manifest["authority_commit"]
            assert request["exploratory"] and request["excluded_from_H0_H3"]
            request["dataset"]["jsonl"] = archive.read(request["dataset"]["archive_member"]).decode()
            # Only this in-memory CPU fixture bypasses the admission guard.
            # Every persisted request remains admitted=False.
            request["forecast"]["admitted"] = True
            request["forecast"]["validation_only"] = True
            results.append(dict(run_id=request["run_id"], **validator.validate_training_request(request)))
            requests.append(request)
    assert len(requests) == 22
    largest = max(requests, key=lambda r: r["dataset"]["rows"])
    negative = {}

    def rejects(name, mutate):
        request = copy.deepcopy(largest)
        mutate(request)
        try:
            validator.validate_training_request(request)
        except ValueError as error:
            negative[name] = str(error)
        else:
            raise AssertionError("Invalid request accepted: " + name)

    rejects("wrong_epochs", lambda r: r["config"].update(num_train_epochs=3))
    rejects("max_samples_truncation", lambda r: r["config"].update(max_samples=10000))
    rejects("wrong_dataset_sha256", lambda r: r["dataset"].update(sha256="0" * 64))
    rejects("unadmitted_persisted_request", lambda r: r["forecast"].update(admitted=False))
    validator.CELLS = original.CELLS
    validator.training_config = original.training_config
    rejects("old_whitelist", lambda r: None)
    assert sha(REPO / "experiments/p012/training_config.py") == manifest["base_training_config_sha256"]
    print(json.dumps({"valid_requests": results, "negative_checks": negative,
                      "candidate_only": True, "new_model_calls": 0,
                      "live_source_unchanged": True}, indent=2))


if __name__ == "__main__":
    main()

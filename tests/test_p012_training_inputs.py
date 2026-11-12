import copy
import hashlib
import json

import pytest

from experiments.p012.training_config import CELLS, LI_COMMIT, training_config
from experiments.p012.training_inputs import validate_training_request


def request_fixture(cell=None, long_cot=False):
    count = CELLS[cell][0] * CELLS[cell][1] if cell else 1
    payload = (json.dumps({"problem": "1 + 1?", "solution": r"\boxed{2}"}) + "\n") * count
    digest = hashlib.sha256(payload.encode()).hexdigest()
    config = training_config("fixture/model", "1" * 40, "qwen", "fixture", "inputs", "output", cell=cell, long_cot=long_cot)
    return {"run_id": "synthetic_training_check", "code_commit": "0" * 40, "cell": cell, "long_cot": long_cot,
        "config": config,
        "model": {"repo": "fixture/model", "revision": "1" * 40, "family": "qwen",
                  "files": [{"path": "model.safetensors", "bytes": 1, "sha256": "2" * 64}]},
        "dataset": {"name": "fixture", "jsonl": payload, "rows": count, "sha256": digest},
        "length_report": {"dataset_sha256": digest, "rows": count, "model": "fixture/model",
            "revision": "1" * 40, "cutoff_len": config["cutoff_len"], "llamafactory_commit": LI_COMMIT,
            "maximum_full_tokens": 20, "over_cutoff_rows": 0, "preflight_sha256": "3" * 64},
        "forecast": {"admitted": True}}


def test_frozen_data_and_approved_r3_batch_fallback():
    request = request_fixture()
    assert validate_training_request(request)["rows"] == 1
    request = request_fixture(long_cot=True)
    request["config"].update(per_device_train_batch_size=1, gradient_accumulation_steps=8,
                             cutoff_len=16384)
    assert validate_training_request(request)["rows"] == 1


@pytest.mark.parametrize("mutation", ["data", "rows", "model", "batch", "forecast", "weights"])
def test_training_rejects_data_or_protocol_drift_before_remote_call(mutation):
    request = copy.deepcopy(request_fixture())
    if mutation == "data":
        request["dataset"]["jsonl"] += "\n"
    elif mutation == "rows":
        request["dataset"]["rows"] = 2
    elif mutation == "model":
        request["model"]["revision"] = "3" * 40
    elif mutation == "batch":
        request["config"]["gradient_accumulation_steps"] = 2
    elif mutation == "forecast":
        request["forecast"]["admitted"] = False
    else:
        request["model"]["files"] = []
    with pytest.raises(ValueError):
        validate_training_request(request)


@pytest.mark.parametrize("field,value", [("num_train_epochs", 3), ("learning_rate", 2e-5),
    ("save_strategy", "steps"), ("warmup_ratio", 0.1), ("seed", 42), ("template", "llama3"),
    ("unregistered_option", True)])
def test_grid_rejects_recipe_drift(field, value):
    request = request_fixture("P")
    assert validate_training_request(request)["rows"] == 4096
    request["config"][field] = value
    with pytest.raises(ValueError):
        validate_training_request(request)


def test_wrong_cell_dose_and_silent_truncation_are_rejected():
    request = request_fixture("L")
    request["cell"] = "K8"
    with pytest.raises(ValueError, match="P times K"):
        validate_training_request(request)
    request = request_fixture("L")
    request["length_report"]["maximum_full_tokens"] = 4097
    with pytest.raises(ValueError, match="silent truncation"):
        validate_training_request(request)
    request = request_fixture()
    request["config"].update(per_device_train_batch_size=1, gradient_accumulation_steps=8)
    with pytest.raises(ValueError, match="recipe"):
        validate_training_request(request)

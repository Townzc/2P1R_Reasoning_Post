import copy
import hashlib
import json

import pytest

from experiments.p012.training_config import training_config
from experiments.p012.training_inputs import validate_training_request


def request_fixture():
    payload = json.dumps({"problem": "1 + 1?", "solution": r"\boxed{2}"}) + "\n"
    return {"run_id": "synthetic_training_check", "code_commit": "0" * 40,
        "config": training_config("fixture/model", "1" * 40, "qwen", "fixture", "inputs", "output"),
        "model": {"repo": "fixture/model", "revision": "1" * 40,
                  "files": [{"path": "model.safetensors", "bytes": 1, "sha256": "2" * 64}]},
        "dataset": {"name": "fixture", "jsonl": payload, "rows": 1,
                    "sha256": hashlib.sha256(payload.encode()).hexdigest()},
        "forecast": {"admitted": True}}


def test_frozen_data_and_approved_r3_batch_fallback():
    request = request_fixture()
    assert validate_training_request(request)["rows"] == 1
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

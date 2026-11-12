import json
from dataclasses import replace
from pathlib import Path
import pytest
from experiments.p012.checkpoints import verify_checkpoint
from experiments.p012.evaluation import EvalConfig, sha256_file


def checkpoint_fixture(tmp_path):
    work = tmp_path / "r1_fixture"
    model = work / "checkpoint"
    model.mkdir(parents=True)
    for name in ("config.json", "tokenizer_config.json", "tokenizer.json", "generation_config.json", "model.safetensors"):
        (model / name).write_text("fixture bytes: " + name)
    (work / "STATUS.json").write_text(json.dumps({"run_id": work.name, "success": True}))
    (work / "MANIFEST.json").write_text(json.dumps({"run_id": work.name, "model": {"repo": "fixture/model", "revision": "1" * 40}}))
    entries = [{"path": p.name, "bytes": p.stat().st_size, "sha256": sha256_file(p)} for p in model.iterdir()]
    # Intermediate optimizer files are retained by R1 but are not loaded by evaluation.
    entries.append({"path": "checkpoint-1000/optimizer.pt", "bytes": 99, "sha256": "0" * 64})
    manifest = work / "CHECKPOINT_FILES.json"
    manifest.write_text(json.dumps(entries))
    return model, manifest


@pytest.mark.parametrize("mutation", [None, "corrupt", "missing", "extra", "manifest", "failed", "traversal"])
def test_verify_final_checkpoint_before_loading(tmp_path, mutation):
    model, manifest = checkpoint_fixture(tmp_path)
    bound = sha256_file(manifest)
    run_id = "r1_fixture"
    if mutation == "corrupt":
        (model / "model.safetensors").write_text("wrong")
    elif mutation == "missing":
        (model / "model.safetensors").unlink()
    elif mutation == "extra":
        (model / "other.safetensors").write_text("unexpected")
    elif mutation == "manifest":
        manifest.write_text(manifest.read_text() + "\n")
    elif mutation == "failed":
        (model.parent / "STATUS.json").write_text(json.dumps({"run_id": run_id, "success": False}))
    elif mutation == "traversal":
        run_id = "../r1_fixture"
    if mutation:
        with pytest.raises(ValueError):
            verify_checkpoint(str(model), run_id, bound, tmp_path)
    else:
        proof = verify_checkpoint(str(model), run_id, bound, tmp_path)
        assert proof["training_run_id"] == run_id
        assert proof["final_weights"][0]["sha256"] == sha256_file(model / "model.safetensors")
        assert len(proof["all_final_files_verified"]) == 5


def test_unbound_local_model_cannot_start():
    config = EvalConfig("/p012/training/r1/checkpoint", "1" * 40, "li_release_math500", "math", "qwen")
    with pytest.raises(ValueError, match="requires"):
        config.validate()
    config = replace(config, training_run_id="r1", checkpoint_manifest_sha256="2" * 64)
    config.validate()

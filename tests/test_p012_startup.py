"""The startup check must reject corrupted draws and real protocol violations."""
from dataclasses import asdict
import json
from types import SimpleNamespace

import pytest

from experiments.p012.evaluation import EvalConfig, sha256_file, stop_flags
from experiments.p012.g0_tools import check_startup
from experiments.p012.scoring import jsonl_bytes


def fixture(tmp_path, monkeypatch, corruption=None):
    import transformers
    tokenizer = SimpleNamespace(
        all_special_tokens=["<|im_end|>"],
        encode=lambda text, add_special_tokens: [1, 2],
        apply_chat_template=lambda messages, tokenize, **kwargs: [1, 2] if tokenize else "rendered",
    )
    monkeypatch.setattr(transformers.AutoTokenizer, "from_pretrained", lambda *a, **kw: tokenizer)
    rows = [{"id": str(i), "problem": "fixture"} for i in range(20)]
    inputs = tmp_path / "inputs.jsonl"
    inputs.write_bytes(jsonl_bytes(rows))
    config = EvalConfig("fixture", "fixed", "li_release_math500", "math", "qwen", n=4, temperature=0.7)
    raw = [{"id": r["id"], "draw": d, "prompt_token_ids": [1, 2], "token_ids": [10+d, 9],
            "text": f"output {d}", "finish_reason": "stop", "stop_reason": 9,
            **stop_flags([10+d, 9], {9}, "stop", 9, 16384)} for r in rows for d in range(4)]
    if corruption:
        corruption(raw)
    gen = tmp_path / "generation"
    gen.mkdir()
    (gen / "raw.jsonl").write_bytes(jsonl_bytes(raw))
    (gen / "MANIFEST.json").write_text(json.dumps({"config": asdict(config), "stop_token_ids": [9],
        "input_sha256": sha256_file(inputs), "code_commit": "a"*40}))
    (gen / "GENERATION_COMPLETE.json").write_text(json.dumps({"requests": 20, "draws": 80,
        "raw_sha256": sha256_file(gen / "raw.jsonl")}))
    return inputs, gen


def test_complete_startup_passes(tmp_path, monkeypatch):
    inputs, gen = fixture(tmp_path, monkeypatch)
    assert check_startup(inputs, gen, tmp_path)["passed"]


@pytest.mark.parametrize("mutation,reason", [
    (lambda raw: raw[0].update(stopped_on_terminator=False), "S1_saved_flags"),
    (lambda raw: raw[0].update(text="answer<|im_end|>"), "S3_special_tail"),
    (lambda raw: raw[0].update(prompt_token_ids=[1, 1, 2]), "S4_actual_prompt"),
    (lambda raw: [raw[d].update(token_ids=[10, 9]) for d in range(4)], "S2_identical_four_draws"),
])
def test_protocol_faults_fail(tmp_path, monkeypatch, mutation, reason):
    inputs, gen = fixture(tmp_path, monkeypatch, mutation)
    report = check_startup(inputs, gen, tmp_path)
    assert not report["passed"] and reason in report["errors"]


def test_duplicate_draw_rejected(tmp_path, monkeypatch):
    inputs, gen = fixture(tmp_path, monkeypatch, lambda raw: raw[0].update(draw=1))
    with pytest.raises(ValueError, match="repeated"):
        check_startup(inputs, gen, tmp_path)

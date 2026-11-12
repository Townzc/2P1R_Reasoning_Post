import json
from dataclasses import asdict

import pytest

from experiments.p012.evaluation import EvalConfig, sha256_file
from experiments.p012.scoring import (
    JUDGE_MODEL, judge_decision, jsonl_bytes, label_response, score_generation,
)


@pytest.fixture(autouse=True)
def synthetic_commit(monkeypatch):
    monkeypatch.setenv("P012_CODE_COMMIT", "0" * 40)


def save_generation(tmp_path, inputs, outputs, config, name="generation"):
    source = tmp_path / (name + "_inputs.jsonl")
    source.write_bytes(jsonl_bytes(inputs))
    directory = tmp_path / name
    directory.mkdir()
    raw = []
    for id_, draw, text in outputs:
        raw.append({"id": id_, "draw": draw, "text": text,
                    "prompt_token_ids": [1, 2], "token_ids": [3, 4, 99],
                    "native_eos": True, "length_capped": False,
                    "string_stop": False, "finish_reason": "stop"})
    (directory / "raw.jsonl").write_bytes(jsonl_bytes(raw))
    (directory / "MANIFEST.json").write_text(json.dumps({
        "config": asdict(config), "input_sha256": sha256_file(source)}))
    (directory / "GENERATION_COMPLETE.json").write_text(json.dumps({
        "requests": len(inputs), "draws": len(outputs),
        "raw_sha256": sha256_file(directory / "raw.jsonl")}))
    return source, directory


def test_sampled_accuracy_keeps_question_and_draw_identity(tmp_path):
    config = EvalConfig("fixture", "fixed", "omi2", "gsm8k", n=2, temperature=0.7)
    inputs = [{"id": "a", "problem": "2+0", "gold": "2"},
              {"id": "b", "problem": "1+1", "gold": "2"}]
    # Interleaved input IDs and draw order must not change the result.
    outputs = [("b", 1, r"\boxed{2}"), ("a", 0, r"\boxed{2}"),
               ("b", 0, r"\boxed{2}"), ("a", 1, "2, with no box")]
    source, directory = save_generation(tmp_path, inputs, outputs, config)
    summary = score_generation(source, directory, tmp_path / "scores")
    assert summary["accuracy"] == 0.75
    assert summary["format_compliance"] == 0.75
    assert summary["questions"] == 2 and summary["responses"] == 4
    assert summary["counts"]["completion_tokens"] == 12


def test_li_exact_and_judge_are_separate_and_missing_format_is_not_judged(tmp_path):
    config = EvalConfig("fixture", "fixed", "li_release_math500", "math")
    inputs = [{"id": "a", "problem": "A", "gold": r"\frac{1}{2}"},
              {"id": "b", "problem": "B", "gold": "3"},
              {"id": "c", "problem": "C", "gold": "4"}]
    outputs = [("a", 0, r"\boxed{0.5}"), ("b", 0, r"\boxed{2}"),
               ("c", 0, "Final Answer: 4")]
    source, directory = save_generation(tmp_path, inputs, outputs, config)
    first = score_generation(source, directory, tmp_path / "exact")
    assert first["accuracy"] == 1/3
    assert first["judge_requests"] == 1
    assert first["accuracy_with_judge"] is None
    pending = [json.loads(x) for x in (tmp_path / "exact/judge_inputs.jsonl").read_text().splitlines()]
    judge_config = EvalConfig(JUDGE_MODEL, "fixed", "li_judge", "math",
        max_tokens=20, temperature=0, top_k=1, dtype="float16", apply_chat_template=False)
    _, judge_dir = save_generation(tmp_path, pending, [(pending[0]["id"], 0, "True")],
                                   judge_config, name="judge")
    second = score_generation(source, directory, tmp_path / "with_judge", judge_dir)
    assert second["accuracy"] == 1/3
    assert second["accuracy_with_judge"] == 2/3
    assert second["judge_complete"]


@pytest.mark.parametrize("outputs", [
    [("a", 0, r"\boxed{2}")],
    [("a", 0, r"\boxed{2}"), ("a", 0, r"\boxed{2}")],
    [("a", 0, r"\boxed{2}"), ("unknown", 0, r"\boxed{2}")],
])
def test_missing_duplicate_or_unknown_answers_cannot_be_scored(tmp_path, outputs):
    config = EvalConfig("fixture", "fixed", "omi2", "gsm8k", n=2, temperature=0.7)
    source, directory = save_generation(tmp_path, [{"id": "a", "problem": "x", "gold": "2"}], outputs, config)
    with pytest.raises(ValueError):
        score_generation(source, directory, tmp_path / "invalid")
    assert not (tmp_path / "invalid").exists()


def test_changed_raw_output_is_rejected(tmp_path):
    config = EvalConfig("fixture", "fixed", "omi2", "gsm8k")
    source, directory = save_generation(tmp_path, [{"id": "a", "problem": "x", "gold": "2"}],
                                        [("a", 0, r"\boxed{2}")], config)
    with (directory / "raw.jsonl").open("a") as f:
        f.write("\n")
    with pytest.raises(ValueError, match="hash mismatch"):
        score_generation(source, directory, tmp_path / "invalid")


def test_released_gsm_metric_and_judge_rule_are_preserved():
    assert label_response("We had 7; now $12.00.", "work\n#### 12.00", "li_release_gsm", "gsm8k")["correct"]
    assert not label_response("Final Answer: 12.00", "12.00", "omi2", "gsm8k")["correct"]
    assert not label_response(r"\boxed{1.0}", "1", "li_release_gsm", "gsm8k")["correct"]
    assert judge_decision("True then False") is True
    assert judge_decision("true") is None

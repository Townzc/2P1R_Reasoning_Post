import json
from dataclasses import asdict

import pytest

from experiments.p012.evaluation import EvalConfig, sha256_file
from experiments.p012.scoring import (
    JUDGE_MODEL, judge_decision, jsonl_bytes, label_response, score_generation,
)
from experiments.p012.judge_collection import merge_queues


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
                    "stopped_on_terminator": True, "stop_token_id": 99, "length_capped": False,
                    "string_stop": False, "finish_reason": "stop"})
    (directory / "raw.jsonl").write_bytes(jsonl_bytes(raw))
    (directory / "MANIFEST.json").write_text(json.dumps({
        "config": asdict(config), "input_sha256": sha256_file(source)}))
    (directory / "GENERATION_COMPLETE.json").write_text(json.dumps({
        "requests": len(inputs), "draws": len(outputs),
        "raw_sha256": sha256_file(directory / "raw.jsonl")}))
    return source, directory


def test_sampled_accuracy_keeps_question_and_draw_identity(tmp_path):
    config = EvalConfig("fixture", "fixed", "omi2", "gsm8k", "qwen", n=2, temperature=0.7)
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
    config = EvalConfig("fixture", "fixed", "li_release_math500", "math", "qwen")
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
    judge_config = EvalConfig(JUDGE_MODEL, "fixed", "li_judge", "math", "qwen",
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
    config = EvalConfig("fixture", "fixed", "omi2", "gsm8k", "qwen", n=2, temperature=0.7)
    source, directory = save_generation(tmp_path, [{"id": "a", "problem": "x", "gold": "2"}], outputs, config)
    with pytest.raises(ValueError):
        score_generation(source, directory, tmp_path / "invalid")
    assert not (tmp_path / "invalid").exists()


def test_changed_raw_output_is_rejected(tmp_path):
    config = EvalConfig("fixture", "fixed", "omi2", "gsm8k", "qwen")
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


@pytest.mark.parametrize("answer,gold,correct,strict,format_ok,path", [
    ("18", "18", True, True, True, "strict_numeric"),
    (r"\$18", "18", True, False, True, "math_verify_fallback"),
    (r"\text{18}", "18", True, False, True, "math_verify_fallback"),
    (r"\sqrt{324}", "18", True, False, True, "math_verify_fallback"),
    (r"18\%", "18", True, False, True, "percent_stripped"),
    (r"18%", "18", True, False, True, "percent_stripped"),
    (r"18\%", "0.18", True, False, True, "math_verify_fallback"),
    ("18 dollars", "18", False, False, False, "invalid_format"),
    (r"\text{18 dollars}", "18", False, False, False, "invalid_format"),
    ("19", "18", False, False, True, "incorrect"),
])
def test_omi2_gsm_retains_both_score_paths(answer, gold, correct, strict, format_ok, path):
    label = label_response("\\boxed{" + answer + "}", gold, "omi2", "gsm8k")
    assert label["correct"] is correct
    assert label["strict_numeric_correct"] is strict
    assert label["format_compliant"] is format_ok
    assert label["score_path"] == path


def test_omi2_gsm_summary_reports_the_strict_and_fallback_difference(tmp_path):
    config = EvalConfig("fixture", "fixed", "omi2", "gsm8k", "qwen", chat_template_file="fixture.jinja")
    inputs = [{"id": str(i), "problem": "fixture", "gold": "18"} for i in range(5)]
    outputs = [(str(i), 0, "\\boxed{" + answer + "}") for i, answer in
               enumerate(["18", r"\$18", r"\text{18}", "18 dollars", r"18\%"])]
    source, directory = save_generation(tmp_path, inputs, outputs, config)
    summary = score_generation(source, directory, tmp_path / "f5_scores")
    assert summary["accuracy"] == summary["accuracy_with_percent_and_math_verify_fallback"] == 0.8
    assert summary["accuracy_strict_numeric"] == 0.2
    assert summary["fallback_gain_pp"] == 40
    assert summary["correct_by_path"] == {"strict_numeric": 1, "percent_stripped": 1, "math_verify_fallback": 2}
    assert summary["percent_stripped_gain_pp"] == 20
    assert summary["format_compliance"] == 0.8


def test_one_judge_load_preserves_colliding_question_ids_across_cells(tmp_path):
    config = EvalConfig("fixture", "fixed", "li_release_math500", "math", "qwen")
    parents, queues = {}, {}
    for cell in ("short", "long"):
        source, directory = save_generation(tmp_path,
            [{"id": "same_question", "problem": "fixture", "gold": "3"}],
            [("same_question", 0, r"\boxed{2}")], config, name=cell)
        queue = tmp_path / (cell + "_scores")
        score_generation(source, directory, queue)
        parents[cell] = (source, directory)
        queues[cell] = queue
    combined = tmp_path / "combined"
    assert merge_queues(queues, combined)["rows"] == 2
    rows = [json.loads(x) for x in (combined / "inputs.jsonl").read_text().splitlines()]
    assert rows[0]["id"] != rows[1]["id"]
    judge_config = EvalConfig(JUDGE_MODEL, "fixed", "li_judge", "math", "qwen",
        max_tokens=20, temperature=0, top_k=1, dtype="float16", apply_chat_template=False)
    _, judge_dir = save_generation(tmp_path, rows,
        [(rows[0]["id"], 0, "True"), (rows[1]["id"], 0, "False")], judge_config, name="combined_judge")
    for cell, expected in (("short", 1.0), ("long", 0.0)):
        result = score_generation(*parents[cell], tmp_path / (cell + "_judged"),
                                  judge_dir, combined / "inputs.jsonl", cell)
        assert result["accuracy_with_judge"] == expected
    with pytest.raises(ValueError, match="missing or extra"):
        score_generation(*parents["short"], tmp_path / "wrong_group", judge_dir,
                         combined / "inputs.jsonl", "unknown")
    # Even a self-consistent changed aggregate manifest must not replace the
    # original per-cell judge prompt with another problem/answer.
    rows[0]["prompt"] = "substituted prompt"
    (combined / "inputs.jsonl").write_bytes(jsonl_bytes(rows))
    manifest = json.loads((judge_dir / "MANIFEST.json").read_text())
    manifest["input_sha256"] = sha256_file(combined / "inputs.jsonl")
    (judge_dir / "MANIFEST.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="prompt differs"):
        score_generation(*parents["short"], tmp_path / "wrong_prompt", judge_dir,
                         combined / "inputs.jsonl", "short")

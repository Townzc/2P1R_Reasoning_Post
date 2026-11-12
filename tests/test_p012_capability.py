import copy
import hashlib
import json
from pathlib import Path

import pytest

from experiments.p012.capability import capability_config, conversation_rows, heldout_pass_metrics
from experiments.p012.capability_nll import aggregate_nll, validate_encoded, validate_nll_request
from experiments.p012.data_pool import normalized
from experiments.p012.evaluation import prompt_text


def test_four_shot_uses_frozen_turns_without_scoring_demo_answers():
    demos = [{"role": role, "content": str(i)} for i in range(4) for role in ("user", "assistant")]
    rows = [{"id": "heldout", "problem": "2+3?", "gold": "5"}]
    out = conversation_rows(rows, demos, 4)
    assert out[0]["messages"][:8] == demos
    assert out[0]["messages"][8] == {"role": "user", "content": prompt_text("2+3?", "omi2")}
    assert out[0]["gold"] == "5" and "messages" not in rows[0]
    assert len(conversation_rows(rows, demos, 0)[0]["messages"]) == 1
    with pytest.raises(ValueError, match="bare"):
        conversation_rows([dict(rows[0], prompt="legacy")], demos, 4)


def test_pass_estimators_and_missing_draw_rejection():
    ids = [str(i) for i in range(500)]
    # One question has all 8 correct, another has one, all others have zero.
    labels = [{"id": id_, "draw": draw, "correct": id_ == "0" or (id_ == "1" and draw == 3)}
              for id_ in ids for draw in range(8)]
    result = heldout_pass_metrics(labels, ids)
    assert result["pass_at_1"] == 9 / 4000
    assert result["pass_at_8"] == 2 / 500
    for bad in [labels[:-1], labels + [labels[0]]]:
        with pytest.raises(ValueError):
            heldout_pass_metrics(bad, ids)


def test_nll_masks_prompt_and_counts_response_eos_after_causal_shift():
    assert validate_encoded([4, 5], [6, 7, 2], [4, 5, 6, 7, 2], [-100, -100, 6, 7, 2]) == 3
    with pytest.raises(ValueError, match="masking"):
        validate_encoded([4, 5], [6, 2], [4, 5, 6, 2], [-100, 5, 6, 2])
    with pytest.raises(ValueError, match="never truncate"):
        validate_encoded([4] * 4096, [2], [4] * 4096 + [2], [-100] * 4096 + [2])


def test_nll_primary_is_token_weighted_not_mean_of_sequence_means():
    records = [{"parent_id": "a", "solution_hash": "1", "target_tokens": 2, "nll_sum": 2.0,
                "solution_chars": len("解答\n")},
               {"parent_id": "a", "solution_hash": "2", "target_tokens": 8, "nll_sum": 24.0,
                "solution_chars": len("answer ")}]
    result = aggregate_nll(records)
    assert result["mean_per_token_nll"] == 2.6
    assert result["mean_per_solution_nll"] == 2.0
    assert result["solution_chars"] == 10
    assert result["nll_per_char"] == 2.6
    assert result["cross_family_metric"] == "nll_per_char"
    with pytest.raises(ValueError):
        aggregate_nll(records + [records[0]])
    with pytest.raises(ValueError):
        aggregate_nll([dict(records[0], nll_sum=float("nan"))])


def fixture_request():
    rows = []
    for i in range(500):
        for k in range(2):
            solution = f"  {k}: \\boxed{{2}}  "
            rows.append({"parent_id": str(i), "task": "math", "raw_problem": "1+1?",
                         "problem": prompt_text("1+1?", "omi2"), "solution": solution,
                         "solution_hash": hashlib.sha256(normalized(solution).encode()).hexdigest()})
    payload = "".join(json.dumps(r) + "\n" for r in rows)
    return {"run_id": "synthetic_nll", "code_commit": "1" * 40, "task": "math",
            "model": {"repo": "Qwen/Qwen2.5-1.5B", "revision": "2" * 40, "family": "qwen",
                      "files": [{"path": "model.safetensors"}]},
            "dataset": {"jsonl": payload, "sha256": hashlib.sha256(payload.encode()).hexdigest()},
            "holdout_parent_ids": [str(i) for i in range(500)], "forecast": {"admitted": True}}


def test_nll_binds_holdout_and_rejects_model_or_data_drift():
    req = fixture_request()
    assert len(validate_nll_request(req)) == 1000
    for mutation in ("dataset", "parent", "model", "budget"):
        bad = copy.deepcopy(req)
        if mutation == "dataset":
            bad["dataset"]["jsonl"] += "\n"
        elif mutation == "parent":
            bad["holdout_parent_ids"][0] = "foreign"
        elif mutation == "model":
            bad["model"]["repo"] = "/p012/training/model/checkpoint"
        else:
            bad["forecast"]["admitted"] = False
        with pytest.raises(ValueError):
            validate_nll_request(bad)


@pytest.mark.parametrize("name,family", [("Qwen__Qwen2.5-1.5B", "qwen"),
    ("Qwen__Qwen2.5-1.5B-Instruct", "qwen"), ("meta-llama__Llama-3.2-1B", "llama3"),
    ("meta-llama__Llama-3.2-1B-Instruct", "llama3")])
def test_actual_tokenizers_use_identical_training_template_and_frozen_four_turns(name, family):
    from transformers import AutoTokenizer
    from experiments.p012.evaluation import EvalConfig, render_prompt_tokens
    root = Path(__file__).resolve().parents[1]
    assets = root / ".local/p012_20261111/assets" / name
    frozen = root / ".local/p012_20261111/c6_frozen_v1/math"
    if not assets.exists() or not frozen.exists():
        pytest.skip("Pinned C1/C6 local fixtures required")
    tok = AutoTokenizer.from_pretrained(assets, local_files_only=True)
    template = root / "experiments/p012/templates" / (family + ".jinja")
    tok.chat_template = template.read_text()
    held = json.loads(next((frozen / "holdout500.jsonl").open()))
    demos = json.loads((frozen / "FOUR_SHOT_MESSAGES.json").read_text())
    for shots in (0, 4):
        row = conversation_rows([held], demos, shots)[0]
        cfg = capability_config({"repo": name, "revision": "1" * 40, "family": family}, "math", "baseline4" if shots else "baseline0", str(template))
        ids = render_prompt_tokens(row, tok, EvalConfig(**cfg))
        assert ids == tok.apply_chat_template(row["messages"], tokenize=True, add_generation_prompt=True)
        assert len(ids) + 4096 <= 8192
        if family == "llama3":
            assert ids[0] == tok.bos_token_id and ids.count(tok.bos_token_id) == 1

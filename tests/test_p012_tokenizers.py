"""F1/F2/S4 checks against the four pinned, downloaded model tokenizers."""
import json
from pathlib import Path

import pytest
from transformers import AutoTokenizer

from experiments.p012.evaluation import (
    EvalConfig, LLAMA_G0_DATE, render_prompt_tokens, termination_tokens,
)

ASSETS = Path(__file__).resolve().parents[1] / ".local/p012_20261111/assets"
MODELS = [
    ("Qwen__Qwen2.5-1.5B", "qwen", {"<|im_end|>": 151645}),
    ("Qwen__Qwen2.5-1.5B-Instruct", "qwen", {"<|im_end|>": 151645}),
    ("meta-llama__Llama-3.2-1B", "llama3", {"<|eot_id|>": 128009, "<|eom_id|>": 128008}),
    ("meta-llama__Llama-3.2-1B-Instruct", "llama3", {"<|eot_id|>": 128009, "<|eom_id|>": 128008}),
]


def tokenizer(name):
    directory = ASSETS / name
    if not directory.exists():
        pytest.skip("Pinned C1 model assets are not bundled in the repository")
    return AutoTokenizer.from_pretrained(directory, local_files_only=True)


@pytest.mark.parametrize("name,family,expected", MODELS)
def test_all_four_template_terminators_are_stops(name, family, expected):
    tok = tokenizer(name)
    eos = json.loads((ASSETS / name / "generation_config.json").read_text())["eos_token_id"]
    result = termination_tokens(tok, eos, family)
    assert result["template_terminator_ids"] == expected
    assert set(expected.values()).issubset(result["stop_token_ids"])
    assert tok.eos_token_id in result["stop_token_ids"]


def test_llama_default_template_gets_a_fixed_date():
    tok = tokenizer("meta-llama__Llama-3.2-1B-Instruct")
    config = EvalConfig("fixture", "fixed", "li_release_math500", "math", "llama3")
    tokens = render_prompt_tokens({"problem": "1 + 1?"}, tok, config)
    assert "Today Date: " + LLAMA_G0_DATE in tok.decode(tokens)
    assert tokens == render_prompt_tokens({"problem": "1 + 1?"}, tok, config)


def test_pre_rendered_llama_requires_bos_and_never_adds_a_second_one():
    tok = tokenizer("meta-llama__Llama-3.2-1B")
    config = EvalConfig("fixture", "fixed", "li_release_math", "math", "llama3", apply_chat_template=False)
    with pytest.raises(ValueError, match="include its BOS"):
        render_prompt_tokens({"prompt": "Question: 1 + 1?"}, tok, config)
    text = "<|begin_of_text|>Question: 1 + 1?"
    ids = render_prompt_tokens({"prompt": text}, tok, config)
    assert ids == tok.encode(text, add_special_tokens=False)
    assert ids[0] == tok.bos_token_id and ids.count(tok.bos_token_id) == 1

"""Prevent silent prompt substitution in the standard base calibration path."""
from dataclasses import replace
import pytest
from experiments.p012.evaluation import EvalConfig, render_prompt_tokens


@pytest.mark.parametrize("protocol,task", [("lm_eval_minerva4", "math"), ("lm_eval_gsm4", "gsm8k")])
def test_base_uses_only_frozen_plain_prompt(protocol, task):
    config = EvalConfig("candidate", "fixed", protocol, task, "qwen", apply_chat_template=False,
                        max_tokens=2048, max_model_len=8192, batch_size=5000)
    config.validate()
    for overrides in ({"apply_chat_template": True}, {"chat_template_file": "template.jinja"},
                      {"task": "gsm8k" if task == "math" else "math"}, {"max_tokens": 16384},
                      {"max_model_len": 32768}):
        with pytest.raises(ValueError):
            replace(config, **overrides).validate()
    with pytest.raises(ValueError, match="pre-rendered"):
        render_prompt_tokens({"problem": "synthetic question"}, None, config)
    class Tokenizer:
        def encode(self, text, add_special_tokens):
            assert text == "four examples then synthetic heldout question"
            assert add_special_tokens is False
            return [10, 11]
    row = {"problem": "synthetic question", "prompt": "four examples then synthetic heldout question"}
    assert render_prompt_tokens(row, Tokenizer(), config) == [10, 11]

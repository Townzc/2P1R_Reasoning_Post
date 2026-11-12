"""Hand-authored parsing/termination fixtures, not benchmark samples."""
from fractions import Fraction
import pytest
from experiments.p012.evaluation import (
    EvalConfig, extract_answer, numeric_answer, prompt_text, score_answer, stop_flags,
)


@pytest.mark.parametrize("protocol,text,expected", [
    ("omi2", r"Thus \boxed{42}", "42"),
    ("omi2", r"\boxed{1} corrected \boxed{2}", "2"),
    ("omi2", r"\boxed{\frac{1}{2}}", r"\frac{1}{2}"),
    ("omi2", r"\fbox{-3}", None),
    ("omi2", r"\boxed{1} final \boxed{2", None),
    ("omi2", "The answer is 42", None),
    ("omi2", r"\boxed{}", None),
    ("omi2", r"\boxed{\{1,2\}}", r"\{1,2\}"),
    ("omi2", r"\boxed{\sqrt{9}}", r"\sqrt{9}"),
    ("omi2", r"work 9 \boxed { -2 }", "-2"),
    ("li_plan", "Final Answer: 42", "42"),
    ("li_plan", r"Final Answer: \boxed{42}", "42"),
    ("li_plan", "Final Answer: 1\nCorrection. Final Answer: 2", "2"),
    ("li_plan", "42", None),
    ("li_plan", "Final Answer: ", None),
    ("li_plan", "Final Answer: 2\nUnrelated afterword.", "2"),
    ("li_plan", r"Final Answer: \boxed{2", None),
    ("li_release_math500", "Final Answer: 42", None),
    ("li_release_math500", r"Final Answer: \boxed{42}", "42"),
    ("omi2", r"\boxed{a_{b_{c}}}", "a_{b_{c}}"),
])
def test_twenty_manual_extraction_examples(protocol, text, expected):
    assert extract_answer(text, protocol) == expected


def test_numeric_no_last_number_or_units_shortcut():
    assert numeric_answer("1,234.50") == Fraction(2469, 2)
    assert numeric_answer(r"\frac{1}{2}") == Fraction(1, 2)
    for value in ("1,2", "about 42", "42 apples", "1/0", "2 or 3"):
        assert numeric_answer(value) is None
    assert score_answer("0.5", r"\frac{1}{2}", "gsm8k")
    assert not score_answer(None, "0", "gsm8k")


def test_symbolic_equality_and_wrong_answer():
    assert score_answer(r"\frac{1}{2}", "0.5", "math")
    assert not score_answer("2", "3", "math")


def test_stop_reason_is_not_synonymous_with_eos():
    assert stop_flags([10, 11], {99}, "stop", "Problem:", 2) == {
        "stopped_on_terminator": False, "stop_token_id": None,
        "last_token_terminator_id": None, "length_capped": False,
        "at_token_limit": True, "string_stop": True}
    capped = stop_flags([10, 99], {99}, "length", None, 2)
    assert not capped["stopped_on_terminator"] and capped["length_capped"]
    assert capped["last_token_terminator_id"] == 99
    assert stop_flags([10], {99}, "stop", 99, 2)["stopped_on_terminator"]
    assert not stop_flags([10], {99}, "stop", None, 2)["stopped_on_terminator"]


def test_prompt_preserves_tex_and_literal_placeholders():
    assert prompt_text("x_{1}", "omi2").endswith("\n\nx_{1}")
    assert "\\boxed{}" in prompt_text("x", "omi2")
    assert "{your answer}" in prompt_text("x", "li_plan")
    assert prompt_text("x", "li_release_gsm") == "x"


def test_invalid_decode_contracts_fail_before_loading_model():
    for overrides in ({"revision": "main"}, {"n": 4}, {"max_model_len": 16384}):
        fields = {"model": "candidate", "revision": "fixed", "protocol": "omi2", "task": "math", "template_family": "qwen", "chat_template_file": "fixed.jinja"}
        with pytest.raises(ValueError):
            EvalConfig(**(fields | overrides)).validate()


@pytest.mark.parametrize("overrides", [
    {"chat_template_file": None}, {"apply_chat_template": False}, {"template_family": "none"},
])
def test_omi2_cannot_bypass_the_training_template(overrides):
    fields = {"model": "candidate", "revision": "fixed", "protocol": "omi2", "task": "math",
              "template_family": "qwen", "chat_template_file": "fixed.jinja"}
    EvalConfig(**fields).validate()
    with pytest.raises(ValueError, match="training-family"):
        EvalConfig(**(fields | overrides)).validate()

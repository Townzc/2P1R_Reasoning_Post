"""Frozen zero-shot Qwen prompt and explicit response-token boundaries (CPU only).

Prompt and response are encoded separately, without automatic BOS/EOS, then
concatenated. This preserves the actual generation prefix and gives full/blank
question forwards identical response tokens, including one assistant-end token.
"""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

QWEN_COMMIT = "a45202bd16f1ec06f433442dc1152d0074773465"
MODEL_REVISION = "4a83ca6e4526a4f2da3aa259ec36c259f66b2ab2"
CONTEXT_LIMIT = 4096
TRAIN_MAX_LENGTH = 2048
ASSISTANT_END_ID = 151645
EOS_ID = 151643
STOP_TOKEN_IDS = (ASSISTANT_END_ID, EOS_ID)
STOP_STRINGS = ("</s>", "<|im_end|>", "<|endoftext|>")
VENDOR = Path(__file__).parent / "vendor" / "qwen_math"


def _prompt_template() -> str:
    """Read the literal from byte-preserved upstream code without importing it."""
    manifest = json.loads((VENDOR / "PROVENANCE.json").read_text())
    expected = next(x["sha256"] for x in manifest["files"] if x["path"] == "utils.py")
    source = (VENDOR / "utils.py").read_bytes()
    if hashlib.sha256(source).hexdigest() != expected:
        raise ValueError("Qwen prompt source SHA mismatch")
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "PROMPT_TEMPLATES" for t in node.targets):
            return ast.literal_eval(node.value)["qwen-boxed"][0]
    raise ValueError("Missing frozen qwen-boxed template")


QWEN_BOXED_TEMPLATE = _prompt_template()


def qwen_boxed_prompt(question: str) -> str:
    if not isinstance(question, str):
        raise TypeError("question must be text")
    return QWEN_BOXED_TEMPLATE.format(input=question).strip(" ")


def encode_prompt(tokenizer, question: str) -> list[int]:
    return list(tokenizer.encode(qwen_boxed_prompt(question), add_special_tokens=False))


def validate_tokenizer(tokenizer) -> dict:
    for text, token_id in (("<|im_end|>", ASSISTANT_END_ID), ("<|endoftext|>", EOS_ID), ("<|im_start|>", 151644)):
        if tokenizer.encode(text, add_special_tokens=False) != [token_id]:
            raise ValueError(f"Unexpected token identity: {text}")
    if not getattr(tokenizer, "is_fast", False):
        raise ValueError("A fast tokenizer with exact character offsets is required")
    return {"model_revision": MODEL_REVISION, "actual_context_limit": CONTEXT_LIMIT,
            "tokenizer_advertised_limit": getattr(tokenizer, "model_max_length", None),
            "assistant_end_id": ASSISTANT_END_ID, "extra_eos_tokens": 0,
            "response_encoding": "separate_then_concatenate_shared_full_and_blank"}


def encode_training_pair(tokenizer, question: str, response: str, max_length: int = TRAIN_MAX_LENGTH) -> dict:
    if not isinstance(response, str) or not response.strip():
        raise ValueError("Empty or non-text reference")
    if max_length > TRAIN_MAX_LENGTH or max_length <= 0:
        raise ValueError("Training length must be within the frozen 2048-token cap")
    validate_tokenizer(tokenizer)
    prompt_ids = encode_prompt(tokenizer, question)
    blank_prompt_ids = encode_prompt(tokenizer, "")
    encoded = tokenizer(response, add_special_tokens=False, return_offsets_mapping=True)
    content_ids = list(encoded["input_ids"])
    special_ids = set(tokenizer.all_special_ids)
    if special_ids.intersection(content_ids):
        raise ValueError("Reference contains a special/control token; no silent stripping")
    response_ids = content_ids + [ASSISTANT_END_ID]
    offsets = [list(x) for x in encoded["offset_mapping"]] + [[len(response), len(response)]]
    input_ids = prompt_ids + response_ids
    blank_input_ids = blank_prompt_ids + response_ids
    if max(len(input_ids), len(blank_input_ids)) > max_length:
        raise ValueError("Complete reference exceeds max_length; truncation is forbidden")
    return {"prompt": qwen_boxed_prompt(question), "blank_prompt": qwen_boxed_prompt(""),
            "prompt_ids": prompt_ids, "blank_prompt_ids": blank_prompt_ids,
            "response_ids": response_ids, "response_offsets": offsets,
            "input_ids": input_ids, "labels": [-100] * len(prompt_ids) + response_ids,
            "blank_input_ids": blank_input_ids,
            "blank_labels": [-100] * len(blank_prompt_ids) + response_ids,
            "response_start": len(prompt_ids), "blank_response_start": len(blank_prompt_ids),
            "response_length": len(response_ids), "assistant_end_id": ASSISTANT_END_ID,
            "extra_eos_tokens": 0, "truncated": False,
            "response_encoding": "separate_then_concatenate_shared_full_and_blank"}


def validate_eval_context(tokenizer, question: str, max_new_tokens: int = 2048,
                          context_limit: int = CONTEXT_LIMIT) -> dict:
    if context_limit != CONTEXT_LIMIT or not 0 < max_new_tokens <= 2048:
        raise ValueError("Evaluation context/output cap differs from frozen protocol")
    ids = encode_prompt(tokenizer, question)
    if len(ids) + max_new_tokens > context_limit:
        raise ValueError("Prompt plus output budget exceeds model's actual 4096 context; freeze a legal shared rule first")
    return {"prompt_ids": ids, "prompt_tokens": len(ids), "max_new_tokens": max_new_tokens,
            "context_limit": context_limit, "truncated": False}


def trim_stop_text(text: str) -> str:
    """Match the official driver postprocessing without any execution branch."""
    for stop in STOP_STRINGS:
        text = text.split(stop)[0]
    return text.strip()

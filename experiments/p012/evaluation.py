"""Review candidate: literal prompts, auditable extraction, and vLLM raw output.

Production use requires the one-time Claude review described in P012 section 12.
The Li plan and released code have different prompt/extraction contracts. Keep
their names distinct; neither one's score is silently substituted for the other.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from fractions import Fraction
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import time
from typing import Any

from .vendor.li_math import last_boxed_only_string, remove_boxed


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def execution_commit() -> str:
    commit = os.environ.get("P012_CODE_COMMIT", "")
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("Set P012_CODE_COMMIT to the reviewed source commit")
    return commit


PROMPTS = {
    "lm_eval_minerva4": "{problem}",  # Required pre-rendered standard harness input.
    "lm_eval_gsm4": "{problem}",
    "li_plan": (
        "Solve the following math problem and present the final answer in the "
        "format: Final Answer: {your answer}\nProblem: {problem}\nAnswer:"
    ),
    "li_release_math500": (
        "Solve the following math problem. Present the final answer in the "
        "format: Final Answer: \\boxed{your_answer}.\nProblem: {problem}\nAnswer:"
    ),
    "li_release_math": (
        "Solve the following math problem and present the final answer in the "
        "format: Final Answer: \\boxed{your_answer}.\nProblem: {problem}\nAnswer:"
    ),
    "li_release_gsm": "{problem}",
    "li_judge": "{problem}",
    "omi2": (
        "Solve the following math problem. Make sure to put the answer "
        "(and only answer) inside \\boxed{}.\n\n{problem}"
    ),
}

TEMPLATE_STOP_WORDS = {
    "qwen": ("<|im_end|>",),
    "llama3": ("<|eot_id|>", "<|eom_id|>"),
    "none": (),
}
LLAMA_G0_DATE = "26 Jul 2024"


def termination_tokens(tokenizer: Any, generation_eos: int | list[int] | None,
                       template_family: str) -> dict:
    """F1: include training-template terminators even for base initializations."""
    if template_family not in TEMPLATE_STOP_WORDS:
        raise ValueError("Unknown template family")
    native_ids = set()
    for eos in (tokenizer.eos_token_id, generation_eos):
        native_ids.update(eos if isinstance(eos, list) else [eos])
    native_ids.discard(None)
    template_ids = {}
    for word in TEMPLATE_STOP_WORDS[template_family]:
        ids = tokenizer.encode(word, add_special_tokens=False)
        if len(ids) != 1 or ids[0] == tokenizer.unk_token_id:
            raise ValueError(f"Template terminator is not one known token: {word}")
        template_ids[word] = ids[0]
    return {"native_eos_ids": sorted(native_ids), "template_terminator_ids": template_ids,
            "stop_token_ids": sorted(native_ids | set(template_ids.values()))}


def prompt_text(problem: str, protocol: str) -> str:
    # Replace just this marker: TeX and literal answer placeholders are retained.
    return PROMPTS[protocol].replace("{problem}", problem)


def last_boxed(text: str) -> str | None:
    """OMI-2 contract: last balanced boxed expression; incomplete last box fails."""
    matches = list(re.finditer(r"\\boxed\s*\{", text))
    if not matches:
        return None
    start = matches[-1].end()
    depth = 1
    for i in range(start, len(text)):
        escaped = (len(text[:i]) - len(text[:i].rstrip("\\"))) % 2 == 1
        if not escaped and text[i] == "{":
            depth += 1
        elif not escaped and text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start:i].strip() or None
    return None


def extract_answer(text: str, protocol: str) -> str | None:
    if protocol in {"li_release_math500", "li_release_math"}:
        boxed = last_boxed_only_string(text)
        return remove_boxed(boxed) if boxed is not None else None
    if protocol == "li_release_gsm":
        # The release reports flexible-extract, not boxed-only GSM8K accuracy.
        matches = re.findall(r"(-?[$0-9.,]{2,})|(-?[0-9]+)", text)
        return next((x for x in matches[-1] if x), None) if matches else None
    if protocol == "li_judge":
        raise ValueError("Judge text has its own True/False rule")
    if protocol == "li_plan":
        if "Final Answer:" not in text:
            return None
        tail = text.rsplit("Final Answer:", 1)[1].strip()
        if re.search(r"\\(?:boxed|fbox)", tail):
            return last_boxed(tail)
        return tail.splitlines()[0].strip() if tail else None
    if protocol not in PROMPTS:
        raise ValueError(f"Unknown protocol: {protocol}")
    return last_boxed(text)


def numeric_answer(text: str | None) -> Fraction | None:
    """Strict, whole-answer numeric equality; never scrape the last number."""
    if text is None:
        return None
    value = text.strip().strip("$").strip()
    if re.fullmatch(r"[+-]?\d{1,3}(?:,\d{3})+(?:\.\d+)?", value):
        value = value.replace(",", "")
    latex = re.fullmatch(r"\\(?:d?frac)\{([+-]?\d+)\}\{([+-]?\d+)\}", value)
    if latex:
        value = f"{latex[1]}/{latex[2]}"
    if not re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:/[+-]?\d+)?", value):
        return None
    try:
        return Fraction(value)
    except (ValueError, ZeroDivisionError):
        return None


def gsm_numeric_scores(answer: str | None, gold: str) -> dict:
    """F5: retain strict equality and a separate numeric math-verify fallback."""
    a, b = numeric_answer(answer), numeric_answer(gold)
    strict = a is not None and b is not None and a == b
    result = {"strict_numeric_correct": strict, "math_verify_fallback_used": False,
              "math_verify_fallback_correct": None, "format_compliant": a is not None,
              "correct": strict, "score_path": "strict_numeric" if strict else "incorrect"}
    if strict:
        return result
    if answer is None:
        return result | {"score_path": "invalid_format"}
    from math_verify import LatexExtractionConfig, parse, verify
    kwargs = {"extraction_config": [LatexExtractionConfig()], "fallback_mode": "no_fallback"}
    parsed_gold = parse("$" + gold + "$", **kwargs)
    parsed_answer = parse("$" + answer + "$", **kwargs)
    # A boxed prose answer such as "18 dollars" may parse into a symbolic
    # product. GSM answers must be numeric scalars; symbols/text are invalid.
    numeric = bool(parsed_answer) and all(
        getattr(value, "is_number", False) is True or numeric_answer(str(value)) is not None
        for value in parsed_answer)
    fallback = bool(numeric and parsed_gold and verify(parsed_gold, parsed_answer))
    return result | {"math_verify_fallback_used": True,
        "math_verify_fallback_correct": fallback, "format_compliant": numeric,
        "correct": fallback,
        "score_path": "math_verify_fallback" if fallback else "incorrect" if numeric else "invalid_format"}


def score_answer(answer: str | None, gold: str, task: str) -> bool:
    if answer is None:
        return False
    if task == "gsm8k":
        return gsm_numeric_scores(answer, gold)["correct"]
    if task != "math":
        raise ValueError(task)
    from math_verify import LatexExtractionConfig, parse, verify
    kwargs = {"extraction_config": [LatexExtractionConfig()], "fallback_mode": "no_fallback"}
    parsed_gold = parse("$" + gold + "$", **kwargs)
    parsed_answer = parse("$" + answer + "$", **kwargs)
    return bool(parsed_gold and parsed_answer and verify(parsed_gold, parsed_answer))


def stop_flags(token_ids: list[int], stop_ids: set[int], finish_reason: str,
               stop_reason: str | int | None, max_tokens: int) -> dict:
    # Classify the actual finish event. The raw final token and stop_reason are
    # also retained, including a terminator emitted exactly at a length limit.
    last_terminator = token_ids[-1] if token_ids and token_ids[-1] in stop_ids else None
    terminator = stop_reason if isinstance(stop_reason, int) and stop_reason in stop_ids else None
    if stop_reason is None:
        terminator = last_terminator
    stopped = finish_reason == "stop" and terminator is not None
    return {"stopped_on_terminator": stopped,
            "stop_token_id": terminator if stopped else None,
            "last_token_terminator_id": last_terminator,
            "length_capped": finish_reason == "length",
            "at_token_limit": len(token_ids) >= max_tokens,
            "string_stop": finish_reason == "stop" and isinstance(stop_reason, str)}


@dataclass(frozen=True)
class EvalConfig:
    model: str
    revision: str
    protocol: str
    task: str
    template_family: str
    max_tokens: int = 16384
    max_model_len: int = 32768
    temperature: float = 0.0
    top_p: float = 1.0
    top_k: int = -1
    dtype: str = "bfloat16"
    n: int = 1
    seed: int = 17
    batch_size: int = 1024
    apply_chat_template: bool = True
    chat_template_file: str | None = None
    stop_strings: tuple[str, ...] = ()

    def validate(self) -> None:
        if self.protocol not in PROMPTS or self.task not in {"math", "gsm8k"}:
            raise ValueError("Unknown evaluation contract")
        if self.template_family not in TEMPLATE_STOP_WORDS:
            raise ValueError("template_family must be qwen, llama3 or none")
        if not self.revision or self.revision in {"main", "master"}:
            raise ValueError("Pin a model revision")
        if self.max_model_len <= self.max_tokens or self.batch_size < 1:
            raise ValueError("Reserve context space for prompts")
        if self.n < 1 or (self.temperature == 0 and self.n != 1):
            raise ValueError("Greedy has exactly one draw")
        if self.temperature < 0 or not 0 < self.top_p <= 1 or self.top_k == 0:
            raise ValueError("Invalid sampling parameters")
        if self.dtype not in {"bfloat16", "float16"}:
            raise ValueError("Use a registered precision")
        if self.protocol == "li_release_gsm" and self.task != "gsm8k":
            raise ValueError("Released GSM8K contract requires GSM8K")
        if self.protocol.startswith("lm_eval_") and (self.apply_chat_template or self.chat_template_file):
            raise ValueError("Standard base evaluation requires the frozen plain few-shot prompt")
        if self.protocol in {"lm_eval_minerva4", "lm_eval_gsm4"} and self.task != (
                "math" if self.protocol == "lm_eval_minerva4" else "gsm8k"):
            raise ValueError("Standard harness task and protocol disagree")
        if self.protocol == "omi2" and (
                not self.chat_template_file or not self.apply_chat_template
                or self.template_family == "none"):
            raise ValueError("OMI-2 requires an exported training-family chat_template_file")


def render_prompt_tokens(row: dict, tokenizer: Any, config: EvalConfig) -> list[int]:
    if config.protocol.startswith("lm_eval_") and "prompt" not in row:
        raise ValueError("Standard base evaluation requires its pre-rendered harness prompt")
    if "prompt" in row:
        if config.protocol == "omi2":
            raise ValueError("OMI-2 uses the frozen training template, not a pre-rendered override")
        if config.apply_chat_template:
            raise ValueError("Pre-rendered prompt requires chat template disabled")
        if config.template_family == "llama3" and not row["prompt"].startswith("<|begin_of_text|>"):
            raise ValueError("Llama pre-rendered few-shot prompt must include its BOS")
        return tokenizer.encode(row["prompt"], add_special_tokens=False)
    if config.apply_chat_template:
        messages = row.get("messages") or [{"role": "user", "content": prompt_text(row["problem"], config.protocol)}]
        kwargs = {"date_string": LLAMA_G0_DATE} if config.template_family == "llama3" and not config.chat_template_file else {}
        return tokenizer.apply_chat_template(messages, tokenize=True, add_generation_prompt=True, **kwargs)
    if config.template_family == "llama3":
        raise ValueError("Plain Llama input must be explicitly pre-rendered with BOS")
    return tokenizer.encode(prompt_text(row["problem"], config.protocol), add_special_tokens=False)


def run_vllm(config: EvalConfig, input_path: Path, output_dir: Path) -> None:
    """Generation only. Scores are a separate operation after raw bytes exist.

    Rows require stable id and problem. Optional messages are explicit frozen
    few-shot conversations; optional prompt is a complete pre-rendered plain
    completion. This wrapper does not choose examples from any test split.
    """
    config.validate()
    # Read the required export before paying to load a model.
    template_text = Path(config.chat_template_file).read_text() if config.chat_template_file else None
    if template_text is not None and not template_text.strip():
        raise ValueError("The exported training template is empty")
    code_commit = execution_commit()
    started = time.monotonic()
    rows = [json.loads(line) for line in input_path.read_text().splitlines() if line.strip()]
    if not rows or len({r["id"] for r in rows}) != len(rows):
        raise ValueError("Input IDs must be unique and nonempty")
    output_dir.mkdir(parents=True, exist_ok=False)
    from vllm import LLM, SamplingParams
    llm = LLM(model=config.model, revision=config.revision,
              tokenizer_revision=config.revision, dtype=config.dtype,
              generation_config="vllm",
              max_model_len=config.max_model_len, trust_remote_code=False,
              gpu_memory_utilization=0.85, seed=config.seed)
    tokenizer = llm.get_tokenizer()
    if template_text is not None:
        tokenizer.chat_template = template_text
    if config.apply_chat_template and not tokenizer.chat_template:
        raise ValueError("Supply the frozen training-family template for a base tokenizer")
    from transformers import GenerationConfig
    generation_config = GenerationConfig.from_pretrained(config.model, revision=config.revision)
    termination = termination_tokens(tokenizer, generation_config.eos_token_id, config.template_family)
    stop_ids = set(termination["stop_token_ids"])
    params = SamplingParams(n=config.n, temperature=config.temperature,
                            top_p=config.top_p, top_k=config.top_k, max_tokens=config.max_tokens,
                            seed=config.seed, stop=list(config.stop_strings) or None,
                            stop_token_ids=sorted(stop_ids), ignore_eos=False,
                            include_stop_str_in_output=False)
    manifest = {"config": asdict(config), "code_commit": code_commit,
                "input_sha256": sha256_file(input_path),
                "source_sha256": sha256_file(Path(__file__)),
                "input_rows": len(rows), **termination,
                "chat_template_date_string": LLAMA_G0_DATE if config.template_family == "llama3" and config.apply_chat_template and not config.chat_template_file else None,
                "model_load_seconds": time.monotonic() - started,
                "chat_template": tokenizer.chat_template,
                "chat_template_sha256": hashlib.sha256(template_text.encode()).hexdigest() if template_text is not None else None,
                "versions": {p: importlib.metadata.version(p) for p in ("vllm", "transformers", "torch")}}
    (output_dir / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    with (output_dir / "raw.jsonl").open("x") as raw:
        for start in range(0, len(rows), config.batch_size):
            batch = rows[start:start + config.batch_size]
            prompts = []
            for row in batch:
                tokens = render_prompt_tokens(row, tokenizer, config)
                if len(tokens) + config.max_tokens > config.max_model_len:
                    raise ValueError(f"Context would truncate input/output for {row['id']}")
                prompts.append({"prompt_token_ids": tokens})
            block_started = time.monotonic()
            generated = llm.generate(prompts, params, use_tqdm=False)
            block_seconds = time.monotonic() - block_started
            if len(generated) != len(batch):
                raise RuntimeError("Missing request output")
            for row, prompt, result in zip(batch, prompts, generated, strict=True):
                if len(result.outputs) != config.n:
                    raise RuntimeError("Missing sampled draw")
                if {c.index for c in result.outputs} != set(range(config.n)):
                    raise RuntimeError("Duplicate or invalid draw indices")
                for completion in result.outputs:
                    if completion.finish_reason not in {"stop", "length"}:
                        raise RuntimeError("Generation did not finish normally")
                    ids = list(completion.token_ids)
                    record = {"id": row["id"], "draw": completion.index,
                              "prompt_token_ids": prompt["prompt_token_ids"],
                              "token_ids": ids, "text": completion.text,
                              "finish_reason": completion.finish_reason,
                              "stop_reason": completion.stop_reason,
                              **stop_flags(ids, stop_ids, completion.finish_reason,
                                           completion.stop_reason, config.max_tokens)}
                    raw.write(json.dumps(record, ensure_ascii=False) + "\n")
                raw.flush()
            with (output_dir / "timing.jsonl").open("a") as timing:
                timing.write(json.dumps({"start": start, "requests": len(batch),
                    "seconds": block_seconds,
                    "prompt_tokens": sum(len(p["prompt_token_ids"]) for p in prompts),
                    "completion_tokens": sum(len(c.token_ids) for g in generated for c in g.outputs)}) + "\n")
            print(json.dumps({"completed_requests": start + len(batch), "total_requests": len(rows),
                              "block_seconds": block_seconds}), flush=True)
    (output_dir / "GENERATION_COMPLETE.json").write_text(json.dumps({
        "requests": len(rows), "draws": len(rows) * config.n,
        "elapsed_seconds": time.monotonic() - started,
        "raw_sha256": sha256_file(output_dir / "raw.jsonl")}) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run_vllm(EvalConfig(**json.loads(args.config.read_text())), args.inputs, args.output)


if __name__ == "__main__":
    main()

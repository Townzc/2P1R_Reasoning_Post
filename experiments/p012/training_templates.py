"""Export the pinned LLaMA-Factory templates and test their actual encoders.

This CPU check imports the real training package. It does not substitute a
locally reimplemented encoder for the reference implementation.
"""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
from pathlib import Path

from .evaluation import EvalConfig, prompt_text, render_prompt_tokens, sha256_file
from .training_config import LI_COMMIT


def export_and_check(assets: Path, models: list[dict]) -> dict:
    from llamafactory.data.template import get_template_and_fix_tokenizer
    from llamafactory.hparams import DataArguments
    from transformers import AutoTokenizer

    distribution = importlib.metadata.distribution("llamafactory")
    origin = json.loads(distribution.read_text("direct_url.json"))
    if origin.get("vcs_info", {}).get("commit_id") != LI_COMMIT:
        raise ValueError("The installed LLaMA-Factory source is not the frozen release")
    if importlib.metadata.version("transformers") != "4.49.0":
        raise ValueError("Template export must run in the pinned training environment")
    templates, checks = {}, []
    for model in models:
        directory = assets / model["directory"]
        tokenizer = AutoTokenizer.from_pretrained(directory, local_files_only=True)
        template = get_template_and_fix_tokenizer(
            tokenizer, DataArguments(template=model["family"]))
        # Native Instruct templates can survive fix_jinja_template(). Export the
        # training formatter directly, as required by F4, even in that case.
        exported = template._get_jinja_template(tokenizer)
        family = model["family"]
        if family in templates and templates[family] != exported:
            raise ValueError("Base and Instruct training-template exports differ")
        templates[family] = exported
        tokenizer.chat_template = exported
        for shots in (0, 4):
            messages = []
            for index in range(shots):
                messages.extend([
                    {"role": "user", "content": prompt_text(f"{index} + 1?", "omi2")},
                    {"role": "assistant", "content": "\\boxed{" + str(index + 1) + "}"},
                ])
            problem = r"Compute $\frac{1}{2} + \frac{1}{3}$."
            messages.append({"role": "user", "content": prompt_text(problem, "omi2")})
            training_ids, _ = template.encode_oneturn(
                tokenizer, messages + [{"role": "assistant", "content": r"\boxed{5/6}"}])
            config = EvalConfig(model["repo"], model["revision"], "omi2", "math", family,
                                chat_template_file=family + ".jinja")
            evaluation_ids = render_prompt_tokens({"problem": problem, "messages": messages},
                                                 tokenizer, config)
            if training_ids != evaluation_ids:
                raise AssertionError(f"Training/evaluation token mismatch: {model['repo']}, {shots} shots")
            checks.append({"model": model["repo"], "revision": model["revision"],
                "family": family, "shots": shots, "problem": problem, "messages": messages,
                "training_prompt_token_ids": training_ids,
                "evaluation_prompt_token_ids": evaluation_ids,
                "tokenizer_files": {p.name: sha256_file(p) for p in sorted(directory.iterdir()) if p.is_file()},
                "passed": True})
    return {"llamafactory_commit": LI_COMMIT, "installed_source": origin,
            "versions": {p: importlib.metadata.version(p) for p in
                         ("llamafactory", "transformers", "torch", "tokenizers", "flash-attn")},
            "templates": templates, "template_sha256": {
                k: hashlib.sha256(v.encode()).hexdigest() for k, v in templates.items()},
            "checks": checks, "all_passed": True, "model_execution": False}

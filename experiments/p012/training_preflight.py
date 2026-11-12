"""Measure frozen training rows with the actual pinned LLaMA-Factory encoder."""
from __future__ import annotations

from collections import Counter
import hashlib
import importlib.metadata
import json
from pathlib import Path

from .evaluation import EvalConfig, prompt_text, render_prompt_tokens, sha256_file
from .training_config import LI_COMMIT


def check_training_rows(payload: dict, assets: Path) -> dict:
    from llamafactory.data.processor.supervised import SupervisedDatasetProcessor
    from llamafactory.data.template import get_template_and_fix_tokenizer
    from llamafactory.hparams import DataArguments
    from transformers import AutoTokenizer

    origin = json.loads(importlib.metadata.distribution("llamafactory").read_text("direct_url.json"))
    if origin.get("vcs_info", {}).get("commit_id") != LI_COMMIT:
        raise ValueError("Preprocess with the pinned paper implementation")
    reports, checks = [], []
    for model in payload["models"]:
        tokenizer = AutoTokenizer.from_pretrained(assets / model["directory"], local_files_only=True)
        for dataset in payload["datasets"]:
            if model["repo"] not in dataset["model_repos"]:
                continue
            raw = dataset["jsonl"].encode()
            if hashlib.sha256(raw).hexdigest() != dataset["sha256"]:
                raise ValueError("Training payload differs from frozen input")
            rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
            if len(rows) != dataset["rows"]:
                raise ValueError("Training row count differs")
            args = DataArguments(template=model["family"], cutoff_len=dataset["cutoff_len"],
                                 packing=False, train_on_prompt=False)
            template = get_template_and_fix_tokenizer(tokenizer, args)
            if template.efficient_eos:
                raise ValueError("Revisit length accounting for an efficient-EOS template")
            exported = template._get_jinja_template(tokenizer)
            fixed = Path(__file__).parent / "templates" / (model["family"] + ".jinja")
            if exported != fixed.read_text():
                raise ValueError("The actual training template differs from the frozen export")
            tokenizer.chat_template = exported
            processor = SupervisedDatasetProcessor(template, tokenizer, None, args)
            histogram, source_total, target_total = Counter(), 0, 0
            for index, row in enumerate(rows):
                messages = [{"role": "user", "content": row["problem"]},
                            {"role": "assistant", "content": row["solution"]}]
                source_ids, target_ids = template.encode_oneturn(tokenizer, messages)
                histogram[len(source_ids) + len(target_ids)] += 1
                source_total += len(source_ids)
                target_total += len(target_ids)
                if index >= 3:
                    continue
                example = {"_prompt": [[messages[0]]], "_response": [[messages[1]]],
                           "_system": [""], "_tools": [""], "_images": [None],
                           "_videos": [None], "_audios": [None]}
                processed = processor.preprocess_dataset(example)
                ids, labels = processed["input_ids"][0], processed["labels"][0]
                untruncated = len(source_ids) + len(target_ids) <= dataset["cutoff_len"]
                if untruncated and (ids != source_ids + target_ids or
                                    labels != [-100] * len(source_ids) + target_ids):
                    raise AssertionError("Actual LF preprocessing differs from measured source/target")
                check = {"dataset": dataset["name"], "model": model["repo"], "row_index": index,
                         "source_tokens": len(source_ids), "target_tokens": len(target_ids),
                         "untruncated": untruncated, "actual_preprocess_passed": True}
                if dataset.get("omi2"):
                    if row["problem"] != prompt_text(row["raw_problem"], "omi2") or not untruncated:
                        raise ValueError("C6 rows need the OMI instruction and must fit without truncation")
                    config = EvalConfig(model["repo"], model["revision"], "omi2", row["task"],
                                        model["family"], max_tokens=4096, max_model_len=8192,
                                        chat_template_file=str(fixed))
                    evaluation_ids = render_prompt_tokens({"problem": row["raw_problem"]}, tokenizer, config)
                    if evaluation_ids != source_ids:
                        raise AssertionError("Real LF prompt differs from evaluation on the same bare problem")
                    # Verify the exact optimized two-segment counting method used
                    # by the all-candidate C5 scan against the reference encoder.
                    prefix = tokenizer.apply_chat_template(messages[:1], tokenize=False, add_generation_prompt=True)
                    marker = "__P012_RESPONSE_SENTINEL__"
                    rendered = tokenizer.apply_chat_template([messages[0], {"role": "assistant", "content": marker}],
                                                              tokenize=False, add_generation_prompt=False)
                    if not rendered.startswith(prefix + marker):
                        raise AssertionError("Cannot separate source and target")
                    suffix = rendered[len(prefix + marker):]
                    counted_source = tokenizer.encode(prefix, add_special_tokens=False)
                    counted_target = tokenizer.encode(row["solution"] + suffix, add_special_tokens=False)
                    if counted_source != source_ids or counted_target != target_ids:
                        raise AssertionError("Optimized full-row token count differs from actual LF")
                    check.update(evaluation_prompt_equal=True, length_counter_equal=True,
                                 source_token_ids=source_ids, target_ids_sha256=hashlib.sha256(json.dumps(target_ids).encode()).hexdigest())
                checks.append(check)
            reports.append({"dataset": dataset["name"], "dataset_sha256": dataset["sha256"],
                "rows": len(rows), "model": model["repo"], "revision": model["revision"],
                "template_sha256": sha256_file(fixed), "cutoff_len": dataset["cutoff_len"],
                "maximum_full_tokens": max(histogram), "over_cutoff_rows": sum(n for size, n in histogram.items() if size > dataset["cutoff_len"]),
                "source_tokens": source_total, "target_tokens": target_total,
                "histogram": dict(sorted(histogram.items())), "efficient_eos": False})
    return {"code_commit": payload["code_commit"], "llamafactory_commit": LI_COMMIT,
            "reports": reports, "checks": checks, "all_passed": True,
            "versions": {p: importlib.metadata.version(p) for p in ("llamafactory", "transformers", "tokenizers")},
            "source_sha256": sha256_file(Path(__file__))}

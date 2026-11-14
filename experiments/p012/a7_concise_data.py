"""A7 frozen same-teacher concise rewriting; posthoc full audit is required.

Training/generation/scoring implementations remain unchanged. This constructor
uses the existing renderer and answer scorer, and preserves every returned call.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import datetime
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path

from .evaluation import last_boxed, score_answer, sha256_file
from .tinker_lora import load_renderer, read_rows, rendered_datum, write_json

AUTHORITY = "2289056089f9ff3467d490efe93a92a07effb063"
TEMPLATE_SHA256 = "49ff0226bd8a455675c5440a25ab1b8b0ef7f176befeb4380038e57d3ee6b66f"
PLACEHOLDERS = ("{N}", "{raw_problem}", "{long_solution}")


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def target_words(solution):
    # Conventional half-up rounding, not Python round's ties-to-even rule.
    return max(20, ((len(solution.split()) + 5) // 10) * 10)


def literal_prompt(template, n, raw_problem, long_solution):
    values = dict(zip(PLACEHOLDERS, (str(n), raw_problem, long_solution), strict=True))
    locations = []
    for key in PLACEHOLDERS:
        if template.count(key) != 1:
            raise ValueError("Template must contain each literal placeholder once")
        locations.append((template.index(key), key))
    result, cursor = [], 0
    for index, key in sorted(locations):
        result.extend((template[cursor:index], values[key]))
        cursor = index + len(key)
    result.append(template[cursor:])
    return "".join(result)


def attempt_seed(row_number, attempt):
    if not 1 <= row_number <= 512 or not 1 <= attempt <= 4:
        raise ValueError("A7 row and attempt numbers are one-based")
    return 7000 + row_number * 4 + attempt


def strip_terminal_tokens(tokens, stop_ids):
    result = list(tokens)
    while result and result[-1] in stop_ids:
        result.pop()
    return result


def eligibility(solution, gold, finish_reason, special_tokens):
    boxed = last_boxed(solution)
    has_boxed = "\\boxed{" in solution and boxed is not None
    forbidden = sorted({s for s in special_tokens if s and s in solution} |
                       {s for s in ("<think>", "</think>") if s in solution})
    correct = has_boxed and score_answer(boxed, gold, "math")
    normal = finish_reason == "stop"
    return {"normal_termination": normal, "contains_boxed": has_boxed,
            "correct": bool(correct), "forbidden_special_tokens": forbidden,
            "eligible": bool(normal and correct and not forbidden)}


def fallback_limit_exceeded(count):
    return count > 26


def distribution(values):
    values = sorted(values)
    return {"n": len(values), "sum": sum(values), "mean": sum(values)/len(values),
            "min": values[0], "max": values[-1], "p10": values[int(.1*(len(values)-1))],
            "median": values[len(values)//2], "p90": values[int(.9*(len(values)-1))]}


def run(request, output):
    import tinker
    if request["authority_commit"] != AUTHORITY or request["prediction_commit"] != AUTHORITY:
        raise ValueError("A7 authority/prediction freeze missing")
    if not request["forecast"]["admitted"] or sha256_file(Path(__file__)) != request["source_sha256"]:
        raise ValueError("Prospective admission or constructor source binding missing")
    if request["model"] not in ("Qwen/Qwen3.5-9B", "Qwen/Qwen3.5-4B"):
        raise ValueError("Unregistered rewriting teacher")
    template_path = Path(request["template"]["path"])
    if sha256_file(template_path) != request["template"]["sha256"] or request["template"]["sha256"] != TEMPLATE_SHA256:
        raise ValueError("Frozen prompt template changed")
    template = template_path.read_text()
    long_rows = read_rows(request["long_dataset"])
    short_rows = read_rows(request["short_dataset"])
    if len(long_rows) != 512 or len(short_rows) != 512:
        raise ValueError("A7 requires all512 frozen rows")
    ids = [r["parent_id"] for r in long_rows]
    if len(set(ids)) != 512 or ids != [r["parent_id"] for r in short_rows]:
        raise ValueError("Frozen M512 parent order differs")
    for long, short in zip(long_rows, short_rows, strict=True):
        for key in ("problem", "raw_problem", "gold"):
            if long[key] != short[key]:
                raise ValueError("Paired frozen input differs: " + key)
    tokenizer, renderer = load_renderer(request)
    stop_ids = renderer.get_stop_sequences()
    if not all(isinstance(t, int) for t in stop_ids):
        raise ValueError("Expected reviewed integer termination contract")
    special_tokens = sorted(set(tokenizer.all_special_tokens) | {"<think>", "</think>"})
    prompts, word_targets = [], []
    for long, short in zip(long_rows, short_rows, strict=True):
        n = target_words(short["solution"]); word_targets.append(n)
        text = literal_prompt(template, n, long["raw_problem"], long["solution"])
        messages = [{"role": "user", "content": text}]
        prompt = renderer.build_generation_prompt(messages)
        hf = tokenizer.apply_chat_template(messages, add_generation_prompt=True,
            enable_thinking=False, return_dict=False)
        if prompt.to_ints() != hf or prompt.length + 2048 > 8192:
            raise ValueError("Rewrite renderer/context mismatch")
        prompts.append(prompt)
    output.mkdir(parents=True, exist_ok=False)
    write_json(output/"REQUEST.json", request)
    write_json(output/"VERSIONS.json", {p: importlib.metadata.version(p) for p in ("tinker", "tinker-cookbook", "torch", "transformers")})
    (output/"PROMPT_TEMPLATE.txt").write_bytes(template_path.read_bytes())
    write_json(output/"PREDICTION_FREEZE.json", {"prediction_commit": AUTHORITY, "utc": utc_now(),
        "template_sha256": TEMPLATE_SHA256, "scope": "All rewriting eligibility checks and later training endpoints"})
    usage = {"prefill_tokens_uncached_upper": 0, "completion_tokens": 0,
             "prompt_cache_hit_tokens": 0, "upper_token_cost_usd": 0.0, "returned_calls": 0, "submitted_calls": 0}
    prices = request["prices_per_million"]
    chosen, fallback, selections = {}, [], []
    service = tinker.ServiceClient(display_name=request["run_id"])
    try:
        # Base sampler, never a fine-tuned sampler path.
        sampler = service.create_sampling_client(base_model=request["model"]).result()

        def sample(i, attempt):
            seed = attempt_seed(i + 1, attempt)
            response = sampler.sample(prompts[i], num_samples=1, sampling_params=tinker.SamplingParams(
                max_tokens=2048, temperature=0.0 if attempt == 1 else .7, top_p=1.0, top_k=-1,
                seed=seed, stop=stop_ids)).result()
            if len(response.sequences) != 1:
                raise ValueError("Expected one independent sample")
            seq = response.sequences[0]
            if seq.stop_reason not in ("stop", "length"):
                raise ValueError("Unknown termination")
            return {"id": ids[i], "row_number": i+1, "attempt": attempt,
                "sampling_seed": seed, "temperature": 0.0 if attempt == 1 else .7,
                "target_words": word_targets[i], "text": tokenizer.decode(seq.tokens, skip_special_tokens=False),
                "token_ids": seq.tokens, "prompt_token_ids": prompts[i].to_ints(),
                "finish_reason": seq.stop_reason, "sequence_id": seq.sequence_id,
                "prompt_cache_hit_tokens": response.prompt_cache_hit_tokens}

        with (output/"raw.jsonl").open("x") as raw, (output/"ELIGIBILITY.jsonl").open("x") as labels, \
             (output/"PREDICTION_BEFORE_SCORE.jsonl").open("x") as freezes, ThreadPoolExecutor(max_workers=16) as pool:
            for begin in range(0, 512, 16):
                indices = list(range(begin, min(512, begin+16)))
                pending = indices[:]
                for attempt in range(1, 5):
                    if not pending:
                        break
                    mean_output = usage["completion_tokens"]/usage["returned_calls"] if usage["returned_calls"] else request["forecast"]["reference_mean_completion_tokens"]
                    expected = 1.5 * (sum(prompts[i].length for i in pending)*prices["prefill"] + len(pending)*mean_output*prices["sample"])/1e6
                    maximum = (sum(prompts[i].length for i in pending)*prices["prefill"] + len(pending)*2048*prices["sample"])/1e6
                    cap = request["forecast"]["generation_cap_usd"]
                    if usage["upper_token_cost_usd"] + max(expected, maximum) > cap:
                        raise ValueError("STOP: next rewriting wave exceeds admitted construction reservation")
                    write_json(output/f"ADMISSION_{begin:04d}_{attempt}.json", {"utc": utc_now(),
                        "used_usd": usage["upper_token_cost_usd"], "next_measured_x1_5_usd": expected,
                        "next_maximum_uncached_usd": maximum, "cap_usd": cap,
                        "row_numbers": [i+1 for i in pending], "attempt": attempt})
                    futures = {pool.submit(sample, i, attempt): i for i in pending}
                    usage["submitted_calls"] += len(futures)
                    returned, errors = {}, []
                    for future in as_completed(futures):
                        i = futures[future]
                        try:
                            record = future.result()
                        except Exception as exc:
                            errors.append({"row_number": i+1, "attempt": attempt, "error_type": type(exc).__name__})
                            continue
                        line = json.dumps(record, ensure_ascii=False) + "\n"
                        raw.write(line); raw.flush()
                        usage["prefill_tokens_uncached_upper"] += len(record["prompt_token_ids"])
                        usage["completion_tokens"] += len(record["token_ids"])
                        usage["prompt_cache_hit_tokens"] += record["prompt_cache_hit_tokens"]
                        usage["returned_calls"] += 1
                        usage["upper_token_cost_usd"] = (usage["prefill_tokens_uncached_upper"]*prices["prefill"] + usage["completion_tokens"]*prices["sample"])/1e6
                        returned[i] = (record, hashlib.sha256(line.encode()).hexdigest())
                    if errors:
                        write_json(output/"FAILED_CALLS.json", errors)
                        raise RuntimeError("SDK wave failed; all returned responses preserved; no automatic retry")
                    next_pending = []
                    for i in pending:
                        record, raw_hash = returned[i]
                        freezes.write(json.dumps({"prediction_commit": AUTHORITY, "utc": utc_now(),
                            "id": ids[i], "row_number": i+1, "attempt": attempt, "raw_record_sha256": raw_hash})+"\n"); freezes.flush()
                        solution = tokenizer.decode(strip_terminal_tokens(record["token_ids"], stop_ids), skip_special_tokens=False)
                        check = eligibility(solution, long_rows[i]["gold"], record["finish_reason"], special_tokens)
                        label = dict(id=ids[i], row_number=i+1, attempt=attempt, raw_record_sha256=raw_hash,
                            solution_sha256=hashlib.sha256(solution.encode()).hexdigest(), **check)
                        labels.write(json.dumps(label)+"\n"); labels.flush()
                        if check["eligible"]:
                            row = dict(long_rows[i], solution=solution, solution_hash=hashlib.sha256(solution.encode()).hexdigest(),
                                provenance={"teacher": request["model"], "construction": "A7 same-teacher concise rewrite",
                                    "source_long_solution_sha256": hashlib.sha256(long_rows[i]["solution"].encode()).hexdigest(),
                                    "row_number": i+1, "attempt": attempt, "sampling_seed": record["sampling_seed"],
                                    "sequence_id": record["sequence_id"]})
                            row.pop("training_tokens", None); chosen[i] = row
                            selections.append({"id": ids[i], "row_number": i+1, "selection": "rewrite", "attempt": attempt,
                                "raw_record_sha256": raw_hash, "solution_sha256": row["solution_hash"]})
                        else:
                            next_pending.append(i)
                    pending = next_pending
                for i in pending:
                    chosen[i] = dict(long_rows[i])
                    item = {"id": ids[i], "row_number": i+1, "selection": "original_long_fallback", "attempts": 4,
                            "solution_sha256": hashlib.sha256(long_rows[i]["solution"].encode()).hexdigest()}
                    fallback.append(item); selections.append(item)
                write_json(output/f"PROGRESS_{begin:04d}.json", {"processed_rows": begin+len(indices),
                    "fallback_rows": len(fallback), "returned_calls": usage["returned_calls"],
                    "upper_token_cost_usd": usage["upper_token_cost_usd"]})
                print(json.dumps({"processed": begin+len(indices), "fallback": len(fallback),
                    "cost_usd_upper": usage["upper_token_cost_usd"]}), flush=True)
                if fallback_limit_exceeded(len(fallback)):
                    write_json(output/"CONSTRUCTION_STOP.json", {"reason": "Fallback count exceeds26; no training",
                        "fallbacks": fallback, "selections": sorted(selections, key=lambda r:r["row_number"])})
                    raise ValueError("STOP: more than26 fallback rows")
        concise = [chosen[i] for i in range(512)]
        stats = []
        for i, row in enumerate(concise):
            for key in ("parent_id", "raw_problem", "problem", "gold"):
                if row[key] != long_rows[i][key]:
                    raise ValueError("Frozen question/answer identity changed")
            if not score_answer(last_boxed(row["solution"]), row["gold"], "math"):
                raise ValueError("Final concise/fallback answer failed existing scorer")
            datum, evidence = rendered_datum(row, tokenizer, renderer)
            stats.append({"full_tokens": len(evidence["input_token_ids"]),
                          "input_tokens": datum.model_input.length, "supervised_tokens": evidence["target_tokens"]})
        with (output/"concise.jsonl").open("x") as f:
            f.writelines(json.dumps(r, ensure_ascii=False)+"\n" for r in concise)
        write_json(output/"SELECTIONS.json", sorted(selections, key=lambda r:r["row_number"]))
        write_json(output/"FALLBACKS.json", fallback)
        write_json(output/"MANIFEST.json", {"authority_commit": AUTHORITY, "prediction_commit": AUTHORITY,
            "track": "tinker_lora", "exploratory": True, "excluded_from_H0_H3": True,
            "teacher": request["model"], "teacher_is_unfinetuned": True, "ordered_parent_ids": ids,
            "selected_rows": 512, "fallback_rows": len(fallback), "all_answers_correct": True,
            "same_frozen_question_order_and_answers": True, "no_per_row_length_selection_gate": True,
            "template_sha256": TEMPLATE_SHA256, "target_words": word_targets,
            "seed_numbering": "7000 + one_based_M512_row*4 + one_based_attempt",
            "tokens_teacher_tokenizer": {k: distribution([r[k] for r in stats]) for k in stats[0]},
            "files": {f: sha256_file(output/f) for f in ("concise.jsonl", "raw.jsonl", "ELIGIBILITY.jsonl", "SELECTIONS.json", "FALLBACKS.json", "PREDICTION_BEFORE_SCORE.jsonl", "PROMPT_TEMPLATE.txt")}})
        write_json(output/"USAGE.json", usage)
        write_json(output/"COMPLETE.json", {"success": True, "self_checks_passed": True,
            "training_not_started": True, "report_all_student_tokenizers_before_training": True})
        service.close(status="success").result()
    except BaseException:
        write_json(output/"PARTIAL_USAGE.json", usage)
        service.close(status="errored").result()
        raise


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True);args=parser.parse_args()
    if not os.environ.get("TINKER_API_KEY"):
        raise ValueError("Load private API key without printing it")
    run(json.loads(args.request.read_text()), args.output)


if __name__ == "__main__":
    main()

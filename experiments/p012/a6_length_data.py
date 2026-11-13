"""A6-2 sequential M512 selection; owner-approved data-path review exemption.

Original responses are written before scoring. All answer checks use the existing
OMI-2 scorer. Training and downstream evaluation use the unchanged Tinker runner.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import datetime
import hashlib
import json
import os
from pathlib import Path

from .data_pool import normalized, ngrams
from .evaluation import last_boxed, prompt_text, score_answer, sha256_file
from .tinker_lora import load_renderer, read_rows, rendered_datum, write_json

AUTHORITY = "18f64e2df34944da9b8fc6378609ccbdeed1c587"


def strip_terminal_tokens(tokens, stop_ids):
    result = list(tokens)
    while result and result[-1] in stop_ids:
        result.pop()
    return result


def distribution(values):
    values = sorted(values)
    return {"n": len(values), "sum": sum(values), "mean": sum(values) / len(values),
            "min": values[0], "max": values[-1],
            "p10": values[int(.1 * (len(values) - 1))],
            "median": values[len(values) // 2], "p90": values[int(.9 * (len(values) - 1))]}


def self_check(short, long, order, tests, tokenizer, renderer):
    ids = [r["parent_id"] for r in short]
    if len(ids) != 512 or len(set(ids)) != 512 or ids != [r["parent_id"] for r in long]:
        raise ValueError("A6 self-check1: short/long ordered question sets differ")
    positions = {p: i for i, p in enumerate(order["training4096"])}
    if any(p not in positions for p in ids) or [positions[p] for p in ids] != sorted(positions[p] for p in ids):
        raise ValueError("A6 training4096 selection order changed")
    held = set(order["holdout500"]) | set(order["demonstrations"])
    test_keys = {normalized(r["problem"]) for r in tests}
    test_grams = set().union(*(ngrams(r["problem"]) for r in tests))
    stats = {"short": [], "long": []}
    for s, l in zip(short, long, strict=True):
        if s["problem"] != l["problem"] or s["raw_problem"] != l["raw_problem"]:
            raise ValueError("Paired problem text changed")
        if s["parent_id"] in held or normalized(s["raw_problem"]) in test_keys or ngrams(s["raw_problem"]) & test_grams:
            raise ValueError("A6 self-check3: test/holdout contamination")
        if not score_answer(last_boxed(l["solution"]), l["gold"], "math"):
            raise ValueError("A6 self-check2: selected long answer is incorrect")
        if any(t in l["solution"] for t in ("<think>", "</think>", "<|im_end|>", "<|endoftext|>")):
            raise ValueError("A6 self-check2: selected answer contains thinking/end marker")
        for arm, row in (("short", s), ("long", l)):
            datum, evidence = rendered_datum(row, tokenizer, renderer)
            full_tokens = len(evidence["input_token_ids"])
            if arm == "long" and full_tokens > 2300:
                raise ValueError("Long training sequence exceeds2300 tokens")
            stats[arm].append({"full_tokens": full_tokens,
                               "input_tokens": datum.model_input.length,
                               "supervised_tokens": evidence["target_tokens"]})
    return {"all_three_self_checks_passed": True,
            "training4096_only": True, "test_5000_and_holdout_500_disjoint": True,
            "ordered_parent_ids": ids,
            "tokens": {arm: {key: distribution([r[key] for r in rows])
                              for key in rows[0]} for arm, rows in stats.items()}}


def run(request, output):
    import tinker
    from tinker_cookbook import renderers
    if request["authority_commit"] != AUTHORITY or request["prediction_commit"] != AUTHORITY:
        raise ValueError("A6 authority/prediction freeze missing")
    if not request["forecast"]["admitted"] or sha256_file(Path(__file__)) != request["source_sha256"]:
        raise ValueError("Prospective admission or pinned data source missing")
    if request["model"] not in ("Qwen/Qwen3.5-9B", "Qwen/Qwen3.5-4B"):
        raise ValueError("Unregistered A6 teacher")
    rows = read_rows(request["dataset"])
    order_path = Path(request["parent_order"]["path"])
    if sha256_file(order_path) != request["parent_order"]["sha256"]:
        raise ValueError("Frozen parent order changed")
    order = json.loads(order_path.read_text())
    if [r["parent_id"] for r in rows] != order["training4096"]:
        raise ValueError("P rows differ from training4096 order")
    tests = read_rows(request["test_exclusion"])
    if len(tests) != 5000:
        raise ValueError("Full MATH test exclusion required")
    tokenizer, renderer = load_renderer(request)
    stop_ids = renderer.get_stop_sequences()
    if not all(isinstance(x, int) for x in stop_ids):
        raise ValueError("Expected the reviewed integer end-token contract")
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "REQUEST.json", request)
    write_json(output / "PREDICTION_BEFORE_SCORE.json", {
        "prediction_commit": AUTHORITY, "utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "scoring_scope": "A6 training-candidate eligibility and later paired-arm results"})
    service = tinker.ServiceClient(display_name=request["run_id"])
    usage = {"prefill_tokens_uncached_upper": 0, "completion_tokens": 0,
             "prompt_cache_hit_tokens": 0, "upper_token_cost_usd": 0.0}
    recovered = {}
    if request.get("resume_raw"):
        saved = read_rows(request["resume_raw"])
        for r in saved:
            key = (r["question_number"] - 1, r["attempt"])
            if key in recovered or r["id"] != rows[key[0]]["parent_id"]:
                raise ValueError("Recovered attempts are duplicated or mismatched")
            if r["sampling_seed"] != 17 + (key[0] + 1) * 4 + key[1]:
                raise ValueError("Recovered attempt seed differs")
            recovered[key] = r
        # A resumption is permitted only when every previously submitted call was saved.
        if len(saved) != request["resume_raw"]["submitted_calls_verified"]:
            raise ValueError("Cannot resume with missing original responses")
    selected, skipped, attempts = [], [], []
    prices = request["prices_per_million"]
    try:
        sampler = service.create_sampling_client(base_model=request["model"]).result()
        def sample(item):
            i, attempt = item
            if item in recovered:
                return recovered[item]
            row = rows[i]
            messages = [{"role": "user", "content": row["problem"]}]
            if row["problem"] != prompt_text(row["raw_problem"], "omi2"):
                raise ValueError("Frozen prompt is not single-wrapped OMI-2")
            prompt = renderer.build_generation_prompt(messages)
            hf = tokenizer.apply_chat_template(messages, add_generation_prompt=True,
                enable_thinking=False, return_dict=False)
            if prompt.to_ints() != hf or prompt.length + 4096 > 8192:
                raise ValueError("Generation renderer/context mismatch")
            # Numbering is explicitly one-based, matching the amendment's question/attempt wording.
            seed = 17 + (i + 1) * 4 + attempt
            response = sampler.sample(prompt, num_samples=1, sampling_params=tinker.SamplingParams(
                max_tokens=4096, temperature=0.0 if attempt == 1 else .7,
                top_p=1.0, top_k=-1, seed=seed, stop=stop_ids)).result()
            if len(response.sequences) != 1:
                raise ValueError("Expected one independent sample")
            seq = response.sequences[0]
            if seq.stop_reason not in ("stop", "length"):
                raise ValueError("Unknown stop reason")
            return {"id": row["parent_id"], "question_number": i + 1, "attempt": attempt,
                    "sampling_seed": seed, "temperature": 0.0 if attempt == 1 else .7,
                    "text": tokenizer.decode(seq.tokens, skip_special_tokens=False),
                    "token_ids": seq.tokens, "prompt_token_ids": prompt.to_ints(),
                    "finish_reason": seq.stop_reason, "sequence_id": seq.sequence_id,
                    "prompt_cache_hit_tokens": response.prompt_cache_hit_tokens}

        with (output / "raw.jsonl").open("x") as raw, (output / "ELIGIBILITY.jsonl").open("x") as labels, \
             ThreadPoolExecutor(max_workers=16) as pool:
            cursor = 0
            while len(selected) < 512 and cursor < len(rows):
                indices = list(range(cursor, min(len(rows), cursor + min(16, 512 - len(selected)))))
                pending, accepted = indices[:], {}
                for attempt in range(1, 5):
                    if not pending:
                        break
                    new_calls = sum((i, attempt) not in recovered for i in pending)
                    expected = request["forecast"]["measured_cost_per_sample_usd"] * 1.5 * new_calls
                    prior_paid = request.get("resume_raw", {}).get("prior_cost_usd", 0)
                    if max(prior_paid, usage["upper_token_cost_usd"]) + expected > request["forecast"]["teacher_generation_cap_usd"]:
                        raise ValueError("STOP: next measured-token x1.5 batch exceeds teacher generation reservation")
                    write_json(output / f"ADMISSION_{cursor:04d}_{attempt}.json", {
                        "used_usd": usage["upper_token_cost_usd"], "next_buffered_usd": expected,
                        "cap_usd": request["forecast"]["teacher_generation_cap_usd"],
                        "question_numbers": [i + 1 for i in pending]})
                    next_pending = []
                    records = list(pool.map(sample, [(i, attempt) for i in pending]))
                    # Persist the complete returned wave before any eligibility checks.
                    for record in records:
                        raw.write(json.dumps(record, ensure_ascii=False) + "\n"); raw.flush()
                    for record in records:
                        i = record["question_number"] - 1
                        usage["prefill_tokens_uncached_upper"] += len(record["prompt_token_ids"])
                        usage["completion_tokens"] += len(record["token_ids"])
                        usage["prompt_cache_hit_tokens"] += record["prompt_cache_hit_tokens"]
                        usage["upper_token_cost_usd"] = (usage["prefill_tokens_uncached_upper"] * prices["prefill"] +
                                                         usage["completion_tokens"] * prices["sample"]) / 1e6
                        solution = tokenizer.decode(strip_terminal_tokens(record["token_ids"], stop_ids), skip_special_tokens=False)
                        long_row = dict(rows[i], solution=solution,
                            solution_hash=hashlib.sha256(solution.encode()).hexdigest(),
                            provenance={"teacher": request["model"], "sequence_id": record["sequence_id"],
                                        "question_number": i + 1, "attempt": attempt, "sampling_seed": record["sampling_seed"]})
                        long_row.pop("training_tokens", None)
                        # Measure before applying the training helper's4096-token guard:
                        # overlong generated candidates are rejected, not training rows.
                        mi, _ = renderer.build_supervised_example(
                            [{"role": "user", "content": long_row["problem"]},
                             {"role": "assistant", "content": solution}],
                            train_on_what=renderers.TrainOnWhat.LAST_ASSISTANT_MESSAGE)
                        full_tokens = mi.length
                        correct = score_answer(last_boxed(solution), rows[i]["gold"], "math")
                        eligible = record["finish_reason"] == "stop" and correct and full_tokens <= 2300
                        label = {"id": record["id"], "question_number": i + 1, "attempt": attempt,
                                 "normal_termination": record["finish_reason"] == "stop", "correct": correct,
                                 "full_training_tokens": full_tokens, "eligible": eligible}
                        labels.write(json.dumps(label) + "\n"); labels.flush(); attempts.append(label)
                        if eligible:
                            if any(t in solution for t in ("<think>", "</think>", "<|im_end|>", "<|endoftext|>")):
                                raise ValueError("A6 self-check2 failed before freezing")
                            accepted[i] = long_row
                        else:
                            next_pending.append(i)
                    pending = next_pending
                for i in indices:
                    if i in accepted:
                        selected.append((rows[i], accepted[i]))
                    else:
                        skipped.append({"question_number": i + 1, "id": rows[i]["parent_id"]})
                cursor = indices[-1] + 1
                print(json.dumps({"processed": cursor, "selected": len(selected), "skipped": len(skipped),
                                  "cost_usd_upper": usage["upper_token_cost_usd"]}), flush=True)
        if len(selected) != 512:
            raise ValueError("STOP: training4096 exhausted before512 eligible questions")
        short, long = map(list, zip(*selected))
        check = self_check(short, long, order, tests, tokenizer, renderer)
        for arm, values in (("short", short), ("long", long)):
            with (output / f"{arm}.jsonl").open("x") as f:
                f.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in values)
        manifest = dict(check, authority_commit=AUTHORITY, prediction_commit=AUTHORITY,
            track="tinker_lora", exploratory=True, excluded_from_H0_H3=True, teacher=request["model"],
            processed_questions=cursor, selected_questions=512, qualifying_question_rate=512 / cursor,
            eligible_attempt_rate=sum(x["eligible"] for x in attempts) / len(attempts),
            skipped_questions=skipped, chosen_attempts=[r["provenance"] for r in long],
            seed_numbering="17 + one_based_question_number*4 + one_based_attempt_number",
            files={f: sha256_file(output / f) for f in ("short.jsonl", "long.jsonl", "raw.jsonl", "ELIGIBILITY.jsonl")})
        write_json(output / "MANIFEST.json", manifest)
        write_json(output / "USAGE.json", usage)
        write_json(output / "COMPLETE.json", {"success": True, "self_checks_passed": True})
        service.close(status="success").result()
    except BaseException:
        write_json(output / "PARTIAL_USAGE.json", usage)
        service.close(status="errored").result()
        raise


def main():
    p = argparse.ArgumentParser(); p.add_argument("--request", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True); args = p.parse_args()
    if not os.environ.get("TINKER_API_KEY"):
        raise ValueError("Load the private API key without printing it")
    run(json.loads(args.request.read_text()), args.output)


if __name__ == "__main__":
    main()

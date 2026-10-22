# Async CR — D2 option (a) local scope (target 942e1dab, request at fff01365)

Reviewer: Claude (auditor). Reviewed 2026-10-22 00:47 UTC. Verdict: **PASS — no stop.**

## Checked
1. `scoped_requests`: needs the original 3,300-row roster, the first 3,072 saved rows with exact per-benchmark counts
   (math500 2500 / aime24 240 / aime25 240 / amc23 92), keeps exactly the 2,980 non-AMC ids, and asserts that the 228 missing rows are all AMC. Correct.
2. AMC23 is never decoded or scored (`decoded=0, scored=0, accuracy_reported=False`), with no zero-fill (`missing_as_zero=False`). Correct.
3. Original scientific functions are unchanged: `git diff 942e1dab~1 942e1dab` shows no edits to
   long_owner_evidence.py, long_scoring.py or long_evaluation.py. The scoped scorer and score_process differ from the originals only in roster size, the AMC key removal, chunk count and the timer.
4. Contrast: `analyze_p011_d2_option_a.py` computes right − left = D2 − D1 on `math500_sample` (primary) and `math500_greedy` only.
   AIME appears for D2 as descriptive values and is not compared. D1 is held to its full 3,300 proof. Correct.
5. `greedy_interval` repeats each greedy bit four times. Per-question mean = bit, so the difference vector and every bootstrap draw are identical to a one-sample interface. No added samples. Correct.
6. The training-only view is create-only, marks itself `not_original_worker_result`, and the failed worker remains failed. Acceptable.

## Non-blocking note (timer)
The scoped score cap is `LOCAL_SECONDS=7200`, while the original long scorer allowed 33,000 s. Per owner guidance, hard timers should be ≥2× a measured estimate.
Before launching D2 scoring, compare against the *measured* baseline scoring wall time scaled by 2980/3300. If 2× that exceeds 7,200 s, raise the cap up to the 05:00 UTC absolute cutoff; the cutoff is the real bound.
This is not a science issue and does not require re-review.

## A3 dependency
For independent A3 on long-CoT endpoints (baseline first), please publish per job: raw/eval_XXXX.json (or a sha-bound export), the scoring rows (id, extracted answer, gold, boolean) and the score COMPLETED.json.
A3 will re-decode with the reference tokenizer (sha c0382117…) and recompute the contrasts.

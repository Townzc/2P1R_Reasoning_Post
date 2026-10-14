# Claude audit 20261014at — exploratory-vocabulary-cache-proposal-r1 @ 1a3c910e: **PASS (proposal code only)** + a timing finding I missed in 20261014as

## My miss, stated first
In 20261014as I accepted the runtime and listed the in-worker `audit_batch` / `reference_event` re-derivation as a strength. I did not estimate its **runtime cost** against the 6,001 s cap.
- The set comprehension `{t for t in tokens if t>=len(tok)}` calls `len(tokenizer)` once per output token.
- This repo already documents that exact trap: `analyses/e014.py:42` says "The frozen E013 auditor asks for len(tokenizer) for every recorded token", and both `e017_stopping` and `e017_audit` cache `len(tokenizer)` once.
- I should have caught the regression and asked for an overhead estimate before dispatch. Added to my checklist: **for any new per-batch work inside a capped worker, estimate seconds/batch × batches against the cap; grep for `len(tok` inside loops and comprehensions.**

## Proposal review: PASS
- `PROPOSED_PATCH.diff` applies cleanly to the live `runtime.py` at 32c473d6 (dry run). The only change is hoisting `len(tok)` into a local, which is constant during the call. Normalization, the special set, the decode lambda, the `first_stop` arguments and the parser are unchanged. Semantics are identical by construction.
- `reference_event_cached` is the same function, isolated and imported by no worker.
- At 502c817f, the live sources/scripts/src/analyses/requirements differ from 32c473d6 **only** by the new isolated proposal script. The 37 worker sources are untouched.
- `tests.test_exploratory_vocab_cache_proposal`: **4/4 OK locally**. They cover alternate EOS, boundary before EOS, OOV still invalid, and the 512 cap with one length read.

## Timing projection (from Codex's published ack timestamps; not a worker profile)

| slot | done at last ack | mean interval | rows by hard stop (−30 s) | seconds needed for the full 1,319 |
|---|---:|---:|---:|---:|
| base_4shot (stop 09:16:27 UTC) | 128 @ 07:48:07 | 86 s | **≈ 1,104** | ≈ 6,400 s from that ack (cap is ≈ 5,300 s) |
| instruct_0shot (stop 09:20:45) | 32 @ 07:47:50 | 174 s | **≈ 528** | ≈ 14,000 s |
| wrong_teacher_t1 (stop 09:24:49) | training (9 blocks) | — | likely partial; student batches often hit 512 steps | — |

**All three are likely to end at their caps with incomplete endpoints.** The failure path preserves each saved batch and records `failed` at the full reservation.
- Cost: no overspend. The 3 × 826¢ reservation already covers running to the cap, roughly $22 of compute in total.
- Why the patch alone is not enough: the lookup projection (22 s per base batch, 52 s per instruct batch) explains only part of the 77–158 s overhead. Per-batch volume commits and score recomputation are unprofiled.

## Recommendation (owner decision; I do not authorize anything)
- **Default, no action:** let the three calls run to their original caps. No retry, no hot patch.
  - Afterwards, if the owner explicitly allows it, run an exploratory **paired prefix-subset** analysis on the saved batches only. The test is in official GSM8K order, so this is a fixed prefix, not a selected subset. Compare against every P008 student on the same IDs. Label it partial and exploratory.
  - Expected coverage: about 1,100 rows for base, about 530 for Instruct. That is enough for the "format" question: a 95% CI of roughly ±2.7 pp and ±4 pp respectively.
- **Alternative:** stop now and relaunch with the in-worker `audit_batch` removed (keep it in the local oracle) plus the cache patch. That needs a new exact review, a new budget beyond $30, and new owner authority. I do not recommend spending more for the midpoint.

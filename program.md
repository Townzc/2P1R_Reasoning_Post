# Bounded research workflow

Read AGENTS.md and docs/NEXT_SESSION.md first. This file describes this project's
finite research loop; it is not permission to rent hardware or exceed the ledger.

**Current phase (2026-09-10 UTC):** P005 literature-guided planning and C018
local CPU analysis are complete. Read `docs/NEXT_SESSION.md`,
`docs/experiments/P005_literature_guided_next_phase.md` and
`docs/RENTAL_WALL_CLOCK.md`. No server/model call or new reservation occurred.
Finish papers, code, CPU validation and transfer preparation with the rental off.
Budget the whole power-on-to-confirmed-stop interval, not just GPU processes.

E014 is complete; E013 remains failed. Preserve all adverse endpoints and the
18-receipt ledger: **6,467 process seconds used, 733 remaining**, no reservations.
Original checkpoint/ledger backups remain independent. The next review-only
repair holds 256 updates fixed and changes terminal LR decay; 512-update E015
is a fallback, with no automatic launch or continuation. The proposed repair
cap is 360+15 seconds, but storage, implementation, rate/money cap and a safe
whole-rental window remain prerequisites.

A minimum three-arm allocation comparison, followed conditionally by selection,
curriculum or small-model/objective checks, replaces an automatic full grid.
The entire scientific phase needs a usable recipe, held-out capability check,
complete budget and owner review. It does not fit the existing balance.
No startup request exists; E012 stays paused.

**Historical phase (2026-09-09 UTC):** E010's identity-absent Paths/GCM seed31 pair
is complete. Do not replay it or seed17/23. Matched greedy is7/64 versus5/64,
complete traces4/64 each, and broader expression/trace0/64 versus2/64. Both
full doses and all800 saved outputs passed independent CPU audits. Read
`reports/ABSENT_BOUNDARY_SEED31_RESULTS.md` and `docs/NEXT_SESSION.md`.

At that historical milestone the ledger was **5740 seconds charged,1460 remaining**,15 reconciled
receipts and zero reservations. No new GPU phase is queued. The remaining
allowance cannot reserve another2130-second pair at the present caps. Complete
independent checkpoint preservation and normal shutdown, then work on CPU-only
task/estimand design for owner review. A clone is not a fresh budget and starting
an instance must not launch a completed queue. Retain all adverse endpoints and
selection limitations. Do not evaluate the reserved holdout.

## Inspiration and scope

Reference: [karpathy/autoresearch](https://github.com/karpathy/autoresearch/tree/228791fb499afffb54b46200aca536f79142f117),
inspected 2026-09-08. Its small experiments, fixed evaluation, and compact run log
are useful organizational ideas. No upstream code or data is imported here.

Our research question requires equal supervised tokens and optimizer updates.
Runtime is a resource ceiling, not the treatment-matching criterion. Preserve
every attempt and its source revision, including failed and negative results.
Commit compact results to Git so another instance can continue.

## Fixed for pilot v1

- Pinned Qwen2.5-1.5B base, full FP32 trainable parameters, BF16 autocast, AdamW.
- Immutable split allocation, verified equations, tokenizer, data manifest,
  paired schedule, loss normalization, four arm definitions, and evaluator.
- One shared seed (17), four complete training cycles, common decoding settings.
- No holdout model evaluation, automatic seed grid, architecture search, or RL.

## Historical pilot-v1 finite loop (completed)

1. Prepare and audit on CPU. Publish code, configurations, data hashes and plan.
2. When the owner supplies an A800, restore the current ledger and inspect the
   actual clone contents. Verify pinned weights, environment and free storage.
   Do not upload old overfit checkpoints for new training from the base model.
3. Run the calibration phase through the queue and cumulative budget guard.
   It is capped at 900 process-seconds and does not automatically start comparison.
4. Record calibration metrics and raw outputs in Git. Check the complete-dose
   development gate and the measured cost. A failure returns to diagnosis; do
   not modify data or decoding per arm to improve one result.
5. If calibration passes and the whole comparison fits, run the four paired
   arms, each capped at 1050 process-seconds. Stop on any failure/timeout. Keep
   failed artifacts; a rerun requires a fresh run ID and the same shared ledger.
6. Generate a new results snapshot with scripts/report_pilot.py, review raw
   failures, and publish. One seed cannot establish a general ordering.
7. Back up any newly retained checkpoints and the latest ledger before declaring
   the instance disposable. Update docs/NEXT_SESSION.md and stop.

Queue commands and dataset details: docs/PILOT_V1.md.

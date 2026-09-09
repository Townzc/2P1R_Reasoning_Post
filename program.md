# Bounded research workflow

Read AGENTS.md and docs/NEXT_SESSION.md first. This file describes this project's
finite research loop; it is not permission to rent hardware or exceed the ledger.

**Current phase (2026-09-09 UTC):** Pilot v1 is complete. Use the prepared
seed23 pair in docs/PILOT_REPLICATION_PROPOSAL.md and the commands in
docs/NEXT_SESSION.md when the owner supplies an instance for that phase.
Restore the 3712-second ledger. Reuse the completed calibration receipt;
do not rerun the historical calibration/four-arm sequence below.
The new pair is a stability check. The larger ICLR roadmap requires a
substantive design and separate resource review, not autonomous search.

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

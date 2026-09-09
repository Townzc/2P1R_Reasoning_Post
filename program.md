# Bounded research workflow

Read AGENTS.md and docs/NEXT_SESSION.md first. This file describes this project's
finite research loop; it is not permission to rent hardware or exceed the ledger.

**Current phase (2026-09-09 UTC):** Both seed17 and seed23 GPU phases are
complete; do not replay their queues. C010 retained a CPU deadline failure;
C011/C012/C013 complete the feasibility/selection work. The next finite pair is
`configs/absent_boundary_seed31/queue.json`:128 fixed questions, Paths/GCM,
seed31/eval17,1024 updates and277760 response tokens per arm. Read
`docs/ABSENT_BOUNDARY_TRAINING.md` and `docs/NEXT_SESSION.md` before startup.

Restore the verified **4716-second** ledger with2484 remaining. The new queue
requires2130 seconds for both jobs and reuses the completed calibration with
the unchanged recipe. It is prepared, not running; the server was last verified
shut down. Wait for the owner to start/provide tomorrow's A800, verify its
published code/model/ledger/environment and18GiB free, then execute only this
pair under the later launch instruction. No automatic rental, budget reset,
main grid or holdout evaluation is implied. Selection and numerical residuals
limit the boundary interpretation; retain all failed and adverse outcomes.

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

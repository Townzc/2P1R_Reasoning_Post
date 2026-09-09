# E009 — Fixed same-problem Paths/GCM replication at seed23

**Registration date:** 2026-09-09. **Status at entry:** CPU preparation complete;
owner authorized execution on a supplied A800; **results pending**.
**Hypothesis timing:** fixed after seed17 and its post-hoc audits, before seed23 outputs.
This is a repository preregistration record, not an external preregistration claim.

## Question and motivation

Does the seed17 primary direction survive a new GCM assignment and presentation
order on the same selected problems? A null or reversal would weaken the case
for expanding a positive within-problem-diversity claim.

## Competing explanations and design

The first result may depend on a particular path assignment/order rather than a
stable allocation effect. Independently initialize both arms from the same pinned
Qwen2.5-1.5B base. Joint assignment/order/training seed **23**, evaluation seed
**17**. Preserve the same 256 train and both 64-problem dev sets, optimizer,
1024 updates, 4096 presentations and 267456 EOS-inclusive supervised tokens.
No seed17 checkpoint resume, new pool, holdout evaluation or dose tuning.

Primary: Paths minus GCM matched-dev **greedy final-expression correctness** at
the full dose. Secondary: broader greedy, sampled pass@1/2/4, parse/truncation,
fixed trace rules and fixed descriptive identity strata. Do not promote pass@4
to primary because seed17's result looked larger. Two seeds remain descriptive.

## Frozen evidence and execution envelope

- [Protocol and stopping rules](../PILOT_REPLICATION_PROPOSAL.md).
- [Queue](../../configs/pilot_replication_seed23/queue.json) and
  [CPU-prepared data](../../runs/pilot_replication_seed23_20260909_r1/).
- [CPU verification](../../reports/pilot_replication_cpu_verification_20260909.json)
  and [before-GPU snapshot](../../reports/pilot_replication_seed23_before_gpu/results.json).
- Planned IDs: `pilot_replication_paths_seed23_r1`, `pilot_replication_gcm_seed23_r1`.
- Entry-time ledger: **3712/7200 seconds used**, **3488 remaining**. Whole phase
  reserves **2130 seconds** (1050+15 per arm); runtime is not yet measured here.

Complete both arms without efficacy-based stopping. A technical failure, timeout
or invariant violation stops the queue and keeps the receipt. Any retry needs a
fresh ID and explicit accounting. Publish either sign, then pause before an
additional scientific phase; do not search seeds until the contrast is positive.

## Results and analysis — pending completion

No seed23 correctness, runtime, conclusion or checkpoint availability is asserted
by this entry. On completion append: both exact run directories and source commit;
official and secondary outcomes per seed; paired counts; dose/receipt audits;
all failures; final cumulative accounting; independent checkpoint/ledger backup
verification; the publication milestone and next decision. Keep the registration
above intact. Server provisioning alone is not an experimental result.

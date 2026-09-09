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

## Completion appended — 2026-09-09 UTC

Both planned jobs completed on their first attempt from source
`6128e4266d62f14f063585d4c8e94dbe3ad8c711`. The entry above was published in
`3fb43907c0fb8c951b50adfad6dabcc1bfde6403` before GPU execution. No training,
endpoint, stratum or stopping-rule revision was made after outcomes.

| Endpoint | Paths | GCM |
|---|---:|---:|
| Primary matched greedy expression | 22/64 | 17/64 |
| Matched complete trace | 18/64 | 16/64 |
| Broader greedy expression | 1/64 | 1/64 |
| Broader complete trace | 0/64 | 1/64 |
| Sampled pass@1 / pass@2 / pass@4 | .3515625 / .47135417 / .546875 | .2421875 / .3046875 / .375 |
| Correct sampled draws | 90/256 | 62/256 |
| Complete sampled traces | 70/256 | 55/256 |
| Charged process-seconds | 500 | 504 |

Matched paired final-expression counts: 11 both correct, 11 Paths only,
6 GCM only, 36 neither. Both official and secondary outcomes were recomputed
from all 800 saved predictions. Each arm completed the fixed 1024 updates,
4096 presentations and 267456 EOS-inclusive supervised tokens. Both measured
26836.27 MiB peak allocated memory. No technical failure, retry or extra inference
occurred in this phase. See [result and analysis report](../../reports/PILOT_REPLICATION_SEED23_RESULTS.md),
[Paths raw run](../../runs/pilot_replication_paths_seed23_r1/),
[GCM raw run](../../runs/pilot_replication_gcm_seed23_r1/) and
[fixed trace/stratum audit](../../reports/pilot_replication_seed23_after_gpu_audit/summary.json).

The primary net difference repeats seed17's five problems. The complete-trace
gap shrinks from seven to two, broader transfer remains unsupported, and the
identity stratum contributing the greedy gap changes. Two seeds on the same
selected pool support a narrow stability observation; they do not identify a
mechanism, a population effect or paper readiness. Preserve pass@4 as secondary.

**Decision:** retain the fixed-pool finding and move to CPU definition/shared-support
checks for a legal-path-family intervention before another GPU phase. Do not
remove input 1 and attribute a changed task distribution to a mechanism. The
current stored four-path inventory cannot supply two paths from each identity
category on any problem; see [C007](C007_identity_family_inventory_failure.md).

This phase charged 1004 seconds, bringing the original allowance to **4716/7200
used, 2484 remaining**. All 13 receipts match the independently saved private
ledger, with no unresolved reservation; see
[ledger proof](../../reports/replication_seed23_ledger_verification.json).
At this results milestone, both new checkpoint downloads are still pending;
preserve the instance until the separate backup completion record is verified.

## Independent preservation completed

Both new checkpoints are independently retained and all 24 files
(12,381,607,162 bytes) passed SHA-256 verification. The compact experiment record
was published at `a4edae0817c72c11481ce0f7536952500a8e1e02`. The current private
ledger is independently reconciled with 13 receipts, 4716 seconds used and no
reservation. See [backup summary](../../reports/replication_seed23_checkpoint_backup_summary.json)
and [server idle check](../../reports/replication_seed23_final_server_check.json).
Weights remain outside Git and do not include optimizer/RNG/sampler resume state.
This replaces the pending preservation status at the earlier results milestone.

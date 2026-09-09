# Fixed next-phase proposal — paired Paths/GCM seed 23

**Prepare one two-arm replication on the existing task before spending on a
larger study.** This is a low-cost stability check of the seed17 pilot, not an
ICLR contribution or a main-grid launch. The specifications below are the
reviewable next phase. CPU preparation and the pinned-tokenizer verification
have passed; the [verification report](../reports/pilot_replication_cpu_verification_20260909.json)
and [queue snapshot](../reports/pilot_replication_seed23_before_gpu/results.json)
record the exact artifacts. Both new jobs remain not_run. No server connection,
rental, or GPU execution occurred during preparation.

## Evidence motivating this narrow phase

The [completed seed17 pilot](../reports/PILOT_V1_RESULTS.md) scored Paths 23/64
versus GCM 18/64 on matched-development greedy final-expression correctness:
11 both correct, 12 Paths only, 7 GCM only, and 34 both wrong. The sampled
per-draw scores are much closer, 72/256 versus 70/256, although at least one of
four samples succeeds on 33 versus 22 problems. Broader-development greedy
scores are only 4/64 versus 1/64. Four samples per problem, one trained model per
arm, and 16 selected development blocks do not establish a population effect.

Two independent post-hoc CPU audits clarify the risk:

- The [trace audit](../reports/pilot_v1_trace_audit_20260909/FINDINGS.md) finds
  21/64 versus 14/64 matched outputs with fully verified calculations, legal input
  consumption, and an exact connection to the final expression. Broader-dev
  fully verified traces are 1/64 in both arms. Correct final expressions can
  accompany false intermediate equations. This diagnostic does not replace the
  official final-expression endpoint.
- The [structure audit](../reports/pilot_v1_structure_bias_20260909/summary.json)
  finds identity operations in 695/1024 selected training paths and 168/256
  matched-development reference paths. Input 1 occurs in 32/64 matched-dev
  problems but only 5/64 broader-dev problems. The sampled any-success advantage
  is concentrated among input-1 problems (22 versus 12 successes); without input
  1 it is 11 versus 10. Conversely, the greedy difference lies in the 16 problems
  whose selected references contain no identity operation (8 versus 3); the
  other 48 problems are tied at 15 each. These endpoint-dependent, post-hoc
  strata cannot identify a causal shortcut effect or justify selecting a
  favorable subset.

The [literature positioning audit](../reports/ICLR_POSITIONING_20260909.md)
identifies close prior work directly comparing per-problem with global diversity.
A second positive seed alone would establish neither novelty nor readiness for
ICLR. The broader intervention and evidence gates are specified in
[ICLR_EXPERIMENT_ROADMAP.md](ICLR_EXPERIMENT_ROADMAP.md).

## Frozen scientific scope

| Component | Specification for both arms |
|---|---|
| Conditions | Within-Problem Paths and Global-Coverage Matched only |
| Data preparation directory | `runs/pilot_replication_seed23_20260909_r1` |
| Queue specification | `configs/pilot_replication_seed23/queue.json` |
| Training problems | Same 256 problems and 64 shared-structure blocks as `runs/pilot_v1_20260908_r3` |
| Development | Same 64 matched and 64 broader problems; unchanged text and problem order |
| Data-assignment/order seed | 23, jointly regenerate GCM assignments and paired presentation schedules |
| Training seed | 23 |
| Evaluation seed | Explicitly fixed at 17, independent of training/assignment seed |
| Initialization | Independently initialize each arm from pinned `Qwen/Qwen2.5-1.5B` base, revision `8faed761d45a263340a0528343f099c05c9a4323` |
| Adaptation | Full FP32 trainable parameters, BF16 autocast, AdamW, LR 5e-5, weight decay 0.01, clip 1, SDPA and gradient checkpointing |
| Batch | Effective batch 4, microbatch 2 |
| Dose | 1024 updates, 4096 presentations, 267456 supervised response tokens including EOS per arm |
| Processing | 472832 prompt-plus-response nonpadding tokens, zero training padding; no packing or truncation |
| Checkpoint | Full common final dose only; no best-checkpoint selection or resumed seed17 weights |

A different training RNG alone is insufficient: the original GCM assignment and
order also used seed17. Regenerate the paired seed23 assignment/order without
changing the selected problems, path support, or reference wording. This measures
joint sensitivity to training, assignment, and order randomness; it does not
isolate these sources and does not replicate the training-pool selection.
Holding evaluation seed17 controls one source of sampling variability but does
not make generations from different models identical or independent trials.

Before GPU work, the CPU preparation must prove the same problem identities,
unchanged development bytes, exact EOS-inclusive token budgets, four Paths paths
versus one assigned GCM path per problem, and equal Paths/GCM structural exposure
at every optimizer update. Freeze data, source, config, and tokenizer hashes in
Git. Preserve all seed17 artifacts. If matching fails, report the failure and
stop preparation; do not relax tolerances or change the selected pool silently.

## Endpoints and interpretation fixed before seed23 outputs

The primary contrast is **Paths minus GCM matched-development greedy
final-expression correctness at update 1024**. Report each seed separately with
problem-paired both-correct, Paths-only, GCM-only, and both-wrong counts. Any
cross-seed average must remain descriptive: two seeds on one fixed training
pool do not support a strong seed-level uncertainty claim.

Preserve the existing decoding: greedy maximum 384 new tokens; matched dev also
has four samples per problem at temperature 0.7 and top-p 0.95, with macro
pass@1/2/4. Report broader-dev greedy correctness, parsing and truncation, output
lengths, reference NLL, the fixed 16-example train diagnostic, runtime, and memory.
Do not switch the primary endpoint to pass@4 because it looked more favorable
in seed17. Extra sampling, a larger evaluation set, or a new seed would be a
separate phase.

Apply the frozen arithmetic trace-audit rules as a secondary diagnostic to the
new saved outputs: locally true equations, legal resource derivation, and final
expression connection are separate fields. Unknown syntax is unverifiable, not
correct. The strict connection rule can leave an algebraically equivalent
expression unverified; publish that limitation. The prepared
`scripts/audit_replication_outputs.py` checks both completed runs, frozen
development and stratum hashes, full dose and matching code/configuration before
writing its immutable audit. Report the already-defined
input-1 and selected-reference-identity strata descriptively, without changing
the denominator or claiming a causal effect.

## Decision and stopping rules

- Complete both full-dose arms if technical checks and the whole-phase budget
  permit. There is no efficacy-based early stopping between arms.
- If the primary contrast vanishes or reverses, publish that outcome and pause
  expansion of a positive within-problem-diversity claim. Diagnose the changed
  assignments and error distribution; do not search seeds until one is positive.
- If the direction persists, treat it as a limited stability signal. Proceed
  first to the CPU design of a substantive controlled intervention, not directly
  to a large training grid or a claim that ICLR requirements are met.
- If a timeout, invalid source/data state, failed invariant, or unresolved ledger
  reservation occurs, stop the queue and retain its receipts. Any retry needs a
  fresh run ID and explicit accounting; do not substitute a shorter or altered
  arm to fit the balance.

No sealed holdout is inspected. The existing reserved raw-group pool remains
untouched; a final benchmark and access policy must be frozen in a later design.

## A800 execution and migration envelope

The current shared ledger is **3712/7200 process-seconds used, 3488 remaining**.
Two 1050-second job caps with 15-second guards reserve **2130 seconds**, leaving
1358 seconds of reservation headroom. This phase fits the remaining allowance;
another four-arm phase at the existing caps would require 4260 seconds and does
not fit. The earlier two relevant arms took roughly 17 process-minutes together,
but the new server's runtime is not guaranteed. Instance startup, downloads,
backup transfer, and idle billing are separate; no A800 hourly rate is assumed.

Use one A800 80GB. The unchanged recipe previously peaked near 26.21 GiB allocated
GPU memory; a larger GPU is unnecessary for this phase. Require at least
**18 GiB free on the run filesystem after the base cache and environment are
ready**, sufficient for both FP32 weight sets (approximately 12.4 GB total) plus
headroom. Check the actual free space rather than relying on the advertised disk
size. A new instance and a verified clone follow the same checks.

When the owner starts or supplies the next instance for this fixed phase:

1. Fetch the published source and frozen CPU artifacts. Verify the pinned base
   model/tokenizer and environment; reuse valid cache files from a clone.
2. Restore the latest complete 3712-second ledger with no unresolved reservation.
   Older 1173- or 1719-second backups are stale and must be rejected.
3. Run the meaningful correctness checks and queue dry run; verify both-job
   reservation, free disk, and immutable fresh run IDs before training starts.
4. Execute only the declared finite pair under the persistent timeout/ledger
   wrapper. Never auto-launch training merely because a server booted or cloned.
5. Publish compact records, raw predictions and analysis; independently back up
   both checkpoints with SHA-256 verification and the final ledger. Declare the
   server disposable only after publication, backup verification, and GPU-idle
   checks are complete.

The larger roadmap is not authorized to launch by these preparation steps. The
owner can decide startup or replacement once the completed CPU preparation and
this concrete phase are ready for review.

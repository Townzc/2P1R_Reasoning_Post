# Next-session handoff — C009 capped join recorded; no GPU needed next

## Current state — 2026-09-09 UTC

C009's bounded CPU attempt is recorded. All 256 original questions were checked:
131 admit disjoint AC 4+4,67 retain common response length and 66 also retain
four structures per family. Key search hit the frozen 2,000,000-pair ceiling;
681 discovered keys involve seven questions, with one valid four-question block.
This is incomplete global discovery, not proof that only one block exists.
See [C009 analysis](../reports/FAMILY_MATCHING_20260909.md),
[scientific review](../reports/C009_SCIENTIFIC_REVIEW.md), and
[receipt](../reports/family_matching_20260909_r1/summary.json).

**Do not open a GPU server for the next step.** Freeze a complete CPU join with
safe support-mask grouping and independent small-fixture equivalence tests;
then measure complete support, packing limits and selection. Do not increase
C009's caps or overwrite its failure, change K, alter targets, create another
pool, train the tiny witness, or evaluate holdout. The family labels still do
not isolate semantic strategies. The full256 four-cell design is already
infeasible under the declared support rule.

**The project A800 was shut down and the authenticated provider console showed
“已关机” at 07:37 UTC on 2026-09-09.** The automatic backstop is now **paused**.
See the [shutdown/recovery receipt](../reports/c009_shutdown_closeout.json).
C009 results were verified on GitHub at `f52d7228fe18bd9667030725348234c790cc7883`
before shutdown. The later closeout publication records the stopped state.
The old server remains at prior GPU closeout `fc96885c`; new CPU artifacts are
local and in GitHub. A future instance must fetch the latest verified Git history;
do not assume a clone has C009 or let old completed queues auto-launch.

Both seed23 backups remain verified: 24 files,12,381,607,162 bytes. No new weights
were produced. The latest ledger remains 4716/7200 process-seconds, 2484 remaining,
13 receipts and zero reservations. A fresh remote check confirmed no GPU/training
processes and 29.61 GiB free; no expansion was necessary.

Read [STATUS](../reports/STATUS.md), the
[result analysis](../reports/PILOT_REPLICATION_SEED23_RESULTS.md),
[result snapshot](../reports/pilot_replication_seed23_after_gpu/results.json),
[complete-pair audit](../reports/pilot_replication_seed23_after_gpu_audit/summary.json)
and [research journal](RESEARCH_JOURNAL.md). The
[replication proposal](PILOT_REPLICATION_PROPOSAL.md) records the frozen design;
the [roadmap](ICLR_EXPERIMENT_ROADMAP.md) identifies later decisions.

| Endpoint | Paths seed23 | GCM seed23 |
|---|---:|---:|
| Matched-dev greedy final expression | 22/64 | 17/64 |
| Broader-dev greedy final expression | 1/64 | 1/64 |
| Matched-dev complete trace | 18/64 | 16/64 |
| Broader-dev complete trace | 0/64 | 1/64 |
| Matched-dev sampled pass@1 / pass@4 | 35.16% / 54.69% | 24.22% / 37.50% |

The seed17 matched primary contrast was 23/64 versus 18/64. Both pairs use the
same restricted training/development problems; two seeds do not establish a
population effect, a semantic mechanism or general arithmetic improvement.
Keep final-expression correctness, displayed trace verification and sampled
success coverage distinct. Preserve the adverse broader-development outcomes.

## Completed run identities and budget

- Runs: `pilot_replication_paths_seed23_r1` and
  `pilot_replication_gcm_seed23_r1`; both are completed and must not be rerun.
- Execution source: `6128e4266d62f14f063585d4c8e94dbe3ad8c711`.
- Journal/preflight publication before outputs:
  `3fb43907c0fb8c951b50adfad6dabcc1bfde6403`.
- Seed23 result publication: `a4edae0817c72c11481ce0f7536952500a8e1e02`.
  Final closeout publication/alignment is a separate check; no unverified final
  commit is assumed here.
- Data: `runs/pilot_replication_seed23_20260909_r1`; manifest SHA-256
  `0959c217feb4b0c51aebf85c1f08e341e1b6c8034657ee028acb263a2ee18ad4`.
- Same 256 training problems, two 64-problem dev sets, pinned Qwen2.5-1.5B base,
  full-parameter recipe, 1024 updates and 267456 supervised tokens per arm.
- Assignment/order/training seed23; evaluation seed17. The seed change jointly
  varies assignment, ordering and training randomness, not the training pool.
- Phase runtime: Paths 500 seconds, GCM 504; **1004 seconds total**.
- Current cumulative ledger: **4716/7200 process-seconds used; 2484 remaining**.
  The latest private ledger is retained locally and exactly reconciled against
  all **13 receipts**, with **zero unresolved reservations**. The
  [verification report](../reports/replication_seed23_ledger_verification.json)
  records ledger SHA-256
  `995d1ec3d484671bb391f3997640712201d6341b97a00e1feafed5378b22633e`.
- Preflight: all 96 Linux tests and pinned model/data/budget checks passed.
  The final frozen pair audit independently checked all 800 saved predictions.

The earlier 1173-, 1719- and 3712-second ledgers are historical. A new or cloned
instance does not reset compute allowance. The previous 2130-second queue
reservation was a ceiling for this now-completed phase, not its actual charge.

## Recovery sources and historical GPU closeout

| State | Recovery source / current status |
|---|---|
| Source, configs, frozen inputs and historical compact records | Published GitHub history; verify the actual fetched commit |
| New seed23 predictions, receipts and audit | Published at `a4edae0817c72c11481ce0f7536952500a8e1e02`; independently CPU-verified |
| Four seed17 scientific weights | Independent local SHA-256 backups; all 48 files reverified before redundant remote weights were removed |
| Paths seed23 scientific weights | Independent local copy: all 12 files SHA-256 verified; see ARTIFACTS.md |
| GCM seed23 scientific weights | Independent local copy: all 12 files SHA-256 verified; see ARTIFACTS.md |
| Complete legal-solution census | Public compact counts/hashes; private compressed 25,846-record solution stream outside Git |
| Three earlier engineering checkpoints | Previously verified local copies outside Git |
| Cumulative private ledger | Retained locally at 4716 seconds; exactly reconciled against all 13 receipts, zero reservations |
| Base model and environment | Pinned model lock/bootstrap plus recorded A800 preflight; reconstruct only when a later reviewed job requires it |

See [ARTIFACTS](../reports/ARTIFACTS.md). Removing the verified duplicate seed17
remote weight directories restored 41.16 GiB free on the existing 50 GB data
disk; no storage expansion was needed. It did not remove their local backups
or compact run histories. No old checkpoint is needed for the next CPU phase.
Weights do not contain optimizer/RNG/sampler state for exact training resume.

The [backup summary](../reports/replication_seed23_checkpoint_backup_summary.json)
and [server check](../reports/replication_seed23_final_server_check.json) verify
both independent copies, no active training/GPU process and zero reservations.
Retain those copies and the reconciled private ledger. GPU compact closeout
was published and synchronized at `fc96885c` in the preceding round. C009 is
local CPU work and does not require uploading its inventory to an idle server.
A future clone must fetch the latest verified Git commit; old GPU queue files
remain completed historical records and must not auto-launch.
Connection information and live ledger contents remain outside Git. Use
[MIGRATION](MIGRATION.md) for authenticated transfer or verified Git bundles;
a clone is a convenience, not proof that its state is current.

## CPU reproduction of existing outputs

These commands rescore saved artifacts; they do not launch models. Use fresh
output paths because generated reports are immutable. Run from the repository
root in the prepared Python environment.

```bash
python -m scripts.verify_pilot_outputs \
  --run runs/pilot_replication_paths_seed23_r1 \
  --out reports/new_paths_seed23_output_check.json
python -m scripts.verify_pilot_outputs \
  --run runs/pilot_replication_gcm_seed23_r1 \
  --out reports/new_gcm_seed23_output_check.json
python -m scripts.audit_replication_outputs \
  --queue configs/pilot_replication_seed23/queue.json \
  --out reports/new_seed23_pair_audit
python -m scripts.report_pilot \
  --queue configs/pilot_replication_seed23/queue.json \
  --out reports/new_seed23_results
```

The pair audit requires matching completed runs, frozen development bytes and
stratum labels, source/config identities and full-dose receipts. Preserve all
raw generations and both signs of descriptive differences. The holdout remains
reserved and unevaluated.

## Historical C008 census and now-measured C009 gate

[C008](experiments/C008_complete_ordered_support_census.md) ran after the GPU
phase from prepublished source `b504cb7b604847b2155bb71dd2bb2c3602d9f371`.
Use that commit for original protocol snapshots; the journal subsequently appends
completion. It completed all 256 fixed training questions with 1,966,080 attempts,
25,846 legal ordered solutions and recovery of all 1,024 stored references.
Disjoint-AC support is 132 problems for 2+2 and 131 for 4+4. There are 112
mixed-label AC classes on 56 problems. No new model result, development/holdout
access, GPU charge or storage expansion occurred. See the
[census analysis](../reports/LEGAL_SUPPORT_CENSUS_20260909.md) and
[immutable summary](../reports/legal_support_census_20260909_r1/summary.json).

Do not rerun enumeration as the next scientific step. C009 has completed the
fixed token and per-question structure checks. Its global key search remains
incomplete; the complete-join proposal in the current scientific review is the
next CPU work. Keep the immutable C008/C009 inputs, hashes and pre-execution
source commits, including the unsuccessful capped search. No GPU work is queued.

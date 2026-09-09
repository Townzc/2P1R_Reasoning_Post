# Next-session handoff — seed23 complete; next work is CPU design

## Current state — 2026-09-09 UTC

Both frozen seed23 jobs completed. **Checkpoint backups are pending; the
instance must remain available until independent SHA-256 verification and
publication are complete. The private ledger is already reconciled.** No further GPU job or
holdout evaluation is scheduled. The completed seed17 and seed23 queues are
historical execution records, not a next-session launch plan.

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

## Recovery and outstanding closeout

| State | Recovery source / current status |
|---|---|
| Source, configs, frozen inputs and historical compact records | Published GitHub history; verify the actual fetched commit |
| New seed23 predictions, receipts and audit | Retrieved and CPU-verified locally; include in the completion publication |
| Four seed17 scientific weights | Independent local SHA-256 backups; all 48 files reverified before redundant remote weights were removed |
| Two seed23 scientific weights | Saved server copies; independent local download and SHA-256 verification pending |
| Three earlier engineering checkpoints | Previously verified local copies outside Git |
| Cumulative private ledger | Retained locally at 4716 seconds; exactly reconciled against all 13 receipts, zero reservations |
| Base model and environment | Pinned model lock/bootstrap plus recorded A800 preflight; reconstruct only when a later reviewed job requires it |

See [ARTIFACTS](../reports/ARTIFACTS.md). Removing the verified duplicate seed17
remote weight directories restored 41.16 GiB free on the existing 50 GB data
disk; no storage expansion was needed. It did not remove their local backups
or compact run histories. No old checkpoint is needed for the next CPU phase.
Weights do not contain optimizer/RNG/sampler state for exact training resume.

Finish the two new checkpoint transfers and verify every file against its run
manifest. Retain the reconciled private ledger, publish the compact completion
milestone, verify the fetched Git ref, and check no GPU job or unresolved
reservation remains. Only then tell the owner the instance can be stopped.
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

## Next scientific decision, while the server is off

Define legal path families and test shared problem support on CPU before
proposing another training phase. Every Countdown input must be consumed once:
multiplication/division by one may be essential to a legal solution. Numerical
simplification must retain input provenance and cannot automatically equate
these paths with Surface changes or invalid strategies.

The [training-exposure audit](../reports/PAIRING_SEED_SEMANTIC_AUDIT_20260909.md)
shows that exact canonical-structure matching does not establish equality of
all numerical features or per-problem exposure. State the path-allocation
estimand, manipulated property and required controls before constructing a new
comparison; do not adjust away treatment components after viewing outcomes.

Prior work already covers the broad per-problem/global-diversity idea. A useful
next study needs an explicit, falsifiable relation to that work, an audited
construction and credible uncertainty. The current results do not authorize
another seed, a main grid, changed tuning, more sampling, a holdout experiment,
a larger rental or a budget increase. Present concrete CPU feasibility and the
exact proposed jobs before the next resource/design decision.

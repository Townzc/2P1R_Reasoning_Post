# Artifact inventory and migration limits

## 2026-09-10 — E015 implementation and rental authorization

- `analyses/e015.py`, `e015_core.py`, `e015_audit.py`, `verify_e015_inputs.py`: isolated one-factor runner, reference measurements and independent audits.
- `analyses/e015_storage.py`, `e015_export.py` and focused tests: verified duplicate reclamation and bounded streaming backup; no server actions during CPU preparation.
- `configs/real_math_e015/terminal_decay.json` and `configs/rental_budget_20260910.json`: original-dose256-step repair and owner-supplied CNY8/hour, CNY3000 ceiling.
- `real_math_e015_local_preservation.json`: freshly verified12-file independent E013 backup and unchanged18-receipt ledger.
- `docs/experiments/E015_terminal_decay.md`, `docs/E015_STORAGE_AND_RENTAL.md`: fixed run, stop conditions,40/45-minute rental/export plan.

Source publication precedes input release and readiness evidence. No new weights,
model results, process receipts, server connection or provider stop claim exists.

## 2026-09-10 — P005 and C018, local CPU only

- `LITERATURE_NEXT_EXPERIMENT_20260910.md` and `literature_next_20260910_sources.json`: eleven primary-paper methods/limits, official venues and PDF hashes; full text stays private.
- `REAL_MATH_C018_SELECTION_AUDIT.md` and `real_math_c018_selection_audit_r1/`: immutable post-hoc counts and selections from existing C017/E013 artifacts, with independent verification.
- `analyses/c018_selection_audit.py`: reproducible, model-free audit with hash checks and overwrite refusal.
- `docs/experiments/P005_literature_guided_next_phase.md`, `docs/RENTAL_WALL_CLOCK.md`, and `configs/diagnostics/real_math_terminal_decay_proposal.json`: review-only staged plan, separate rental accounting and unimplemented repair.

No model weights, teacher outputs, GPU run, process receipt or additional
allowance was created. Historical E015512 proposal and experiment data remain
unchanged. Latest checkpoint and 18-receipt ledger recovery copies remain private.

**Current E014 completion, 2026-09-10 UTC:** all compact raw outputs and CPU
verification are retained in `runs/gsm8k_generation_e014_r1` and
`reports/real_math_e014_execution_r1`. No new checkpoint was written. All12 E013
checkpoint files (6,190,803,414 bytes) remain independently backed up and pass
post-run server hashes. The latest private ledger backup matches all18 receipts:
**6467 used /733 remaining,zero reservations**. Its SHA256 is
`8813caaa4a3661900f874033fac68b802b3e856bc9c449f28f1fff3983b4aae9`.
The older17-receipt snapshot is retained as history, not a recovery balance.
Read [results](REAL_MATH_E014_RESULTS.md) and [handoff](../docs/NEXT_SESSION.md).

**Historical workflow pause, 2026-09-10 UTC:** the current task is the proposed P004 framing
and deliverable discussion. E012's ready artifacts remain preserved; no model
job has run. The personally addressed reply is retained privately outside Git,
and [P004](../docs/experiments/P004_cost_aware_sft_allocation_proposal.md) contains
only the scientific proposal. No checkpoint, ledger or migration state changed.

**Historical E012 ready milestone, 2026-09-10 UTC:** execution source and immutable
release are published; clean-checkout checks and default inspection passed.
See [ready report](RELATION_E012_READY.md) and
[verification](relation_e012_fresh_checkout_verification.json). No E012 model
has run; there are no new weights or GPU receipts. C016's seven-file 203769-byte
input bundle remains fully public and unchanged. The latest private ledger
remains 5971 used / 1229 remaining, 16 receipts, zero reservations; both public
aggregate summaries now agree. E011's 12 independently verified checkpoint
files / 6190803414 bytes remain retained. No checkpoint was loaded, changed
or removed in this CPU phase.

Git contains source, configuration, data hashes, environment inventory, compact predictions/history, metrics and failure receipts. It does **not** contain model weights or the live private resource ledger.

| Artifact | Current retained copies | Verification / reproduction |
|---|---|---|
| Pinned 0.5B and 1.5B base snapshots | Reproducible from pinned sources; current A800 main cache verified before pilot | `model_verified_debug.json`, `model_verified_main.json`; re-download exact revisions and verify against official file digests. |
| Higher-LR debug checkpoint (`r2`, gate failed) | Verified independent local backup outside Git; historical server copy | `checkpoint_r2_local_verified.json`, plus the run's checkpoint manifest. |
| Passing debug checkpoint (`r3`, 31/32) | Verified independent local backup outside Git; historical server copy | `checkpoint_r3_server_verified.json` and `checkpoint_r3_local_verified.json`; all ten files verified on both copies. |
| Shared runtime ledger | Independently retained current private backup:6467 seconds, zero reservations; all18 receipts reconciled | [E014 ledger proof](real_math_e014_execution_r1/ledger_verification.json). Older16/17-receipt balances are historical. A replacement keeps the same approved budget. |
| E013 failed GSM8K checkpoint |12 files /6,190,803,414 bytes, independently retained; server copy must be rechecked at startup | [Backup proof](real_math_e013_checkpoint_backup.json), [post-run hashes](real_math_e014_execution_r1/checkpoint_preservation.json). E014 reads these weights, not a fresh base snapshot. |
| E014 active input release | Public configs/real_math_e014 and reports/real_math_e014_inputs_r2; r1 retained | [r2 release](../configs/real_math_e014/release_r2.json), [independent checks](real_math_e014_execution_r1/input_verification_r2.json). Case/evidence bytes match r1. |
| E014 completed diagnostic | Local and public compact run records,42 free generations and32 full-reference records | [Both audits and resource proof](REAL_MATH_E014_RESULTS.md);170-second receipt. No new weights. |
| Main A800 checkpoint (32/32 overfit) | Verified independent local backup outside Git, all 12 files; historical A800 copy | `checkpoint_main_a800_server_verified.json` and `checkpoint_main_a800_local_verified.json` are identical. Weights-only checkpoint; no exact optimizer resume. |
| Raw run records | GitHub, local checkout and training server | See `run_registry.json` and each run's recorded code commit; one launch is explicitly invalidated. |

Checkpoint files contain model weights and tokenizer, **not** optimizer/RNG/sampler state. The current runner does not provide exact optimizer resume. Copy the checkpoint separately when needed and run:

```bash
python scripts/verify_artifact.py \
  --manifest runs/<run-id>/checkpoint_manifest.json \
  --directory /path/to/transferred/checkpoint \
  --out reports/new_checkpoint_verification.json
```

A Git clone plus the pinned base model can reproduce the experiment from initialization. It does not recover an interrupted optimizer trajectory. Do not delete a server's unique artifacts before a destination copy is verified; see `docs/MIGRATION.md` for the bundle path when direct GitHub access is unavailable.
## Pilot v1 weights — 2026-09-08

All four final FP32 checkpoints were saved on A800. Independent transfer status:

| Arm | Independent local copy | Verification report |
|---|---|---|
| repeat | All 12 files verified; 6190803581 bytes | [pilot_v1_repeat_seed17_r1_checkpoint_backup.json](pilot_v1_repeat_seed17_r1_checkpoint_backup.json) |
| surface | All 12 files verified; 6190803581 bytes | [pilot_v1_surface_seed17_r1_checkpoint_backup.json](pilot_v1_surface_seed17_r1_checkpoint_backup.json) |
| paths | All 12 files verified; 6190803581 bytes | [pilot_v1_paths_seed17_r1_checkpoint_backup.json](pilot_v1_paths_seed17_r1_checkpoint_backup.json) |
| gcm | All 12 files verified; 6190803581 bytes | [pilot_v1_gcm_seed17_r1_checkpoint_backup.json](pilot_v1_gcm_seed17_r1_checkpoint_backup.json) |

The exact per-file SHA-256 values are in each run's checkpoint_manifest.json.
Backups remain outside Git. All raw predictions, logs, training histories,
metrics and the sanitized compute-accounting summary belong to the published
experiment milestone. At the seed17 milestone the private ledger recorded 3712 seconds used and
3488 remaining; those balances are historical. Calibration did not save another
checkpoint. On 2026-09-09 all 48 seed17 backup files were reverified locally
before only the redundant remote weight directories were removed, restoring
41.16 GiB free on the 50 GB data disk. The independent local copies and all
compact run records remain retained; see
[storage cleanup](replication_seed23_storage_cleanup_20260909.json).


## Seed23 replication weights — 2026-09-09, independent backups complete

| Run | Saved source | Independent local backup status |
|---|---|---|
| `pilot_replication_paths_seed23_r1` | Final server checkpoint and run manifest | All 12 files independently verified; [backup report](pilot_replication_paths_seed23_r1_checkpoint_backup.json) |
| `pilot_replication_gcm_seed23_r1` | Final server checkpoint and run manifest | All 12 files independently verified; [backup report](pilot_replication_gcm_seed23_r1_checkpoint_backup.json) |

Both jobs completed from source
`6128e4266d62f14f063585d4c8e94dbe3ad8c711`. Their raw compact records and
[800-output CPU audit](pilot_replication_seed23_after_gpu_audit/summary.json)
are published at `a4edae0817c72c11481ce0f7536952500a8e1e02`. Both additional
FP32 checkpoints are now independently verified: **24 files, 12,381,607,162
bytes**. Weights remain outside Git. The
[backup summary](replication_seed23_checkpoint_backup_summary.json) records the
per-run verification reports and sizes.

The new private ledger has been retrieved: **4716/7200 seconds used, 2484
remaining, zero reservations**. All **13 receipts** have been reconciled exactly;
see [ledger verification](replication_seed23_ledger_verification.json), which
records SHA-256
`995d1ec3d484671bb391f3997640712201d6341b97a00e1feafed5378b22633e`.
The [server check](replication_seed23_final_server_check.json) records no active
training/GPU process and zero reservations. **Recovery material is complete;
after final closeout publication and Git alignment the instance can be stopped.**
That final alignment is separate from the recorded idle check. No more training
or holdout evaluation is scheduled.


## Complete legal-support census — local CPU artifact, 2026-09-09

The [census](LEGAL_SUPPORT_CENSUS_20260909.md) executed from prepublished source
`b504cb7b604847b2155bb71dd2bb2c3602d9f371`, separate from the seed23 GPU source.
Its [immutable summary](legal_support_census_20260909_r1/summary.json) and
[per-problem records](legal_support_census_20260909_r1/per_problem.jsonl) retain
all 256 completed IDs, 1,966,080 attempts, 25,846 legal ordered solutions,
class witnesses and source/protocol hashes. Disjoint-AC 2+2 support is 132
problems, 4+4 is 131; 56 problems contain 112 mixed-label classes.

The complete 25,846-record solution archive remains **outside Git**. Its gzip
SHA-256 is `42c00622cdf8e9953d50f4a5c781b28e054198dff72915524577fe5a6407f5ef`;
the uncompressed stream SHA-256 is
`fa0563f030ffaa810f23e4eb5e9c63a2e12096f2dc675128a9bd9a9362c338d8`.
Use the recorded execution commit and fresh output paths in the census report
if reconstructing it; later journal completion text is not the original
protocol snapshot.

This is a mathematical inventory, not a frozen training dataset or a model
result. EOS-token, global-structure and shared-block matching remain untested;
the next gate is a separately fixed CPU matching-loss diagnostic. The census
added no GPU process-seconds and required no storage expansion.


## C009 token/structure/block feasibility — 2026-09-09

Execution source: `cb2bcedce36f78ae593ce979677e4199aeda26ee`. All 256 questions
have complete per-question checks (131→67→66); global key discovery is capped,
not exhaustive. The [summary](family_matching_20260909_r1/summary.json),
per_problem.jsonl, policy_emulations.json and block_witnesses.json retain
provenance, all stage IDs/counts, residuals and explicit accounting schedules.
The independent verification receipt records which claims were checked.

The 72,820,255-byte full shared-key JSON is retained locally and as a private
gzip. Git contains a **lossless 904,602-byte catalog with 260 unique records**,
plus a compact key index and storage manifest. Expansion of record indices
restores the original object and exact byte hash recorded by the summary.
The complete tokenized 25,846-row inventory remains outside Git with compressed
and uncompressed SHA-256 digests in the public summary; recreate from C008 and
the pinned original tokenizer if necessary. No trained model/checkpoint was
created by C009. See [analysis/reproduction](FAMILY_MATCHING_20260909.md).

The preceding GPU recovery was synchronized at `fc96885c`. Repeated local
verification of the two seed23 backups again passed all 24 files. The latest
server check has unchanged ledger SHA-256
`995d1ec3d484671bb391f3997640712201d6341b97a00e1feafed5378b22633e`,
4716 seconds charged,13 receipts,zero reservations and no active training/GPU
process. CPU publication can be fetched on a replacement server; no new server
or disk expansion is needed now. The user authorized normal provider shutdown
after this round; the handoff records its verified completion separately.


### C009 shutdown completion — 2026-09-09 07:37 UTC

After C009 result publication at `f52d7228fe18bd9667030725348234c790cc7883`
and local/Git tree verification, the owner-authorized normal shutdown was
confirmed in the authenticated provider console as “已关机”. The instance
identity matched the previous run and the confirmation dialog. A fresh remote
check immediately before shutdown found no active GPU/training process, no
reservation and the unchanged 4716-second ledger. No instance was deleted or
started. The task heartbeat backstop was then paused; no further GPU job is
queued. See [closeout receipt](c009_shutdown_closeout.json).


## 2026-09-09 CPU completion and new128-question training artifacts

The authoritative current handoff is docs/NEXT_SESSION.md. C010's incomplete
witness stream remains private (614821423-byte gzip; public hashes and partial
receipts), with no need to copy it to a GPU disk. C013 fully completes the old
finite grid; every compact key is retained in six public base64 parts. Its
storage.json verifies assembly of the2571804-byte original gzip, and public
compressed catalog/support-group files reconstruct original JSON bytes.

C011 has a byte-exact gzip/base64 diagnostic archive. C012 has a lossless slot
catalog restoring its79406557-byte repeated join JSON; independent fresh-clone
archive checks passed. Original C009 tokenized inventory remains private with
public digests and source reproduction. CPU search archives are unnecessary
for training because its verified witness rows are materialized in Git.

All new training bytes are in `runs/absent_boundary_seed31_20260909_r1`, including
128-question blocks, four compatibility datasets, actual paired schedule,
selection/exclusion audit, token budgets and unchanged development/split files.
Manifest SHA256: `cd9a72d187dbb18f2b75b743ccc0cf85c94951ee574c07e55ed8ddf1f4a1ab97`.
New configs are in `configs/absent_boundary_seed31`; both GPU run IDs are not_run.
Independent data audit: `reports/absent_boundary_cpu_verification_20260909.json`.

No new checkpoint exists; all six old scientific checkpoint backups remain
retained outside Git. The same independently reconciled ledger remains4716
used/2484 remaining with13 receipts and no reservation. Do not reset it on a
clone. Restore the pinned base and current source/data only; require18GiB free
for the later two-checkpoint phase. No storage expansion or server access was
needed for this CPU turn.

## E010 identity-absent seed31 — execution and compact preservation complete

Both complete run directories and independent800-output audit are retained
locally and in the result milestone. Each run saved12 checkpoint files outside
Git. Both have independent SHA256-verified backups:24 files,12,381,607,162 bytes.
See [the summary](absent_boundary_seed31_checkpoint_backup_summary.json),
[Paths receipt](absent_boundary_paths_seed31_r1_checkpoint_backup.json) and
[GCM receipt](absent_boundary_gcm_seed31_r1_checkpoint_backup.json). The fresh
server check is idle with zero reservations; preservation is complete. Normal
shutdown request and provider-state confirmation remain separately recorded.

The new ledger has5740/7200 charged,1460 remaining,15 reconciled receipts and
zero reservations; the old4716 balance is historical. Its SHA256 is
`1d674f211298aee5eb8bdd1936cab6d68d2d545392b42b9f63a013ebfc11a4c6`.
The original13 jobs are unchanged. All earlier engineering and six scientific
checkpoint backups remain independently retained. No current-round cleanup or
disk expansion was needed. [Analysis and recovery state](ABSENT_BOUNDARY_SEED31_RESULTS.md).


## E011 relation engineering — complete failed gate, preserved artifacts

All compact records are tracked in `runs/relation_overfit_e011_r1`. The
12-file checkpoint totals6190803414 bytes and has an independent local
SHA256-verified backup; see `relation_e011_checkpoint_backup.json`. It saves
weights/tokenizer only,not optimizer/RNG resume state. Previous backups remain.
All16 receipts match the current ledger:5971 used/1229 remaining,zero
reservations,SHA256`664a177b847b678d41d52fe7dbb62667630256db70f416b11b4facbbb9c82cb5`.
Do not replay E011 or restore the historical5740 ledger as current. No disk
expansion or artifact deletion was needed. Normal shutdown is confirmed
separately after publication; follow `docs/NEXT_SESSION.md`.


## Relation diagnosis artifacts — C016 and E012

C016: `runs/relation_diagnostics_c016_r1` holds all288 rows, exact assignments,
update schedules, supervised-field masks/budgets and exposed-fact audit. Read
[CPU findings](RELATION_C016_CPU_READY.md),
[release identities](../configs/diagnostics/relation_c016_release.json) and
[fresh-checkout verification](relation_c016_fresh_checkout_verification.json).
No new weights or live-ledger copy belong in Git.

E012 source: `configs/relation_diagnostics_e012/execution.json` and
[registration](../docs/experiments/E012_relation_diagnostic_ladder.md) define
three conditional runs. The execution release will be frozen after source
publication. Do not label planned stages as completed or add fictitious
receipts/checkpoints. Every actual stage must preserve all raw token records,
teacher-forced token measurements, history, manifests, metrics and its resource
receipt. Weights require independent per-file hashing; compact backup proof
uses `reports/<run_id>_checkpoint_backup.json` with the schema in E012.

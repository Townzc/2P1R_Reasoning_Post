# Artifact inventory and migration limits

Git contains source, configuration, data hashes, environment inventory, compact predictions/history, metrics and failure receipts. It does **not** contain model weights or the live private resource ledger.

| Artifact | Current retained copies | Verification / reproduction |
|---|---|---|
| Pinned 0.5B and 1.5B base snapshots | Reproducible from pinned sources; current A800 main cache verified before pilot | `model_verified_debug.json`, `model_verified_main.json`; re-download exact revisions and verify against official file digests. |
| Higher-LR debug checkpoint (`r2`, gate failed) | Verified independent local backup outside Git; historical server copy | `checkpoint_r2_local_verified.json`, plus the run's checkpoint manifest. |
| Passing debug checkpoint (`r3`, 31/32) | Verified independent local backup outside Git; historical server copy | `checkpoint_r3_server_verified.json` and `checkpoint_r3_local_verified.json`; all ten files verified on both copies. |
| Shared runtime ledger | Current A800 and independently retained local private copy: 4716 seconds, zero reservations; all 13 receipts reconciled exactly | [Ledger verification](replication_seed23_ledger_verification.json) records the retained copy hash. Older 1173-, 1719- and 3712-second ledgers are historical. A replacement keeps the same approved budget. |
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

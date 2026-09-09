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


## Seed23 replication weights — 2026-09-09, backup pending

| Run | Saved source | Independent local backup status |
|---|---|---|
| `pilot_replication_paths_seed23_r1` | Final server checkpoint and run manifest | Download/SHA-256 verification pending |
| `pilot_replication_gcm_seed23_r1` | Final server checkpoint and run manifest | Download/SHA-256 verification pending |

Both jobs completed from source
`6128e4266d62f14f063585d4c8e94dbe3ad8c711`. Their raw compact records and
[800-output CPU audit](pilot_replication_seed23_after_gpu_audit/summary.json)
are available locally for publication. The two additional FP32 checkpoints are
about 12.4 GB combined; weights remain outside Git. A partially downloaded file
is not a verified backup.

The new private ledger has been retrieved: **4716/7200 seconds used, 2484
remaining, zero reservations**. All **13 receipts** have been reconciled exactly;
see [ledger verification](replication_seed23_ledger_verification.json), which
records SHA-256
`995d1ec3d484671bb391f3997640712201d6341b97a00e1feafed5378b22633e`.
Completion still requires both new checkpoint manifests to verify at the
independent destination and the compact milestone to be published. **The instance is not yet
ready to discard.** No more training or holdout evaluation is scheduled.

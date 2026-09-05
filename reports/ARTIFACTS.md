# Artifact inventory and migration limits

Git contains source, configuration, data hashes, environment inventory, compact predictions/history, metrics and failure receipts. It does **not** contain model weights or the live private resource ledger.

| Artifact | Current retained copies | Verification / reproduction |
|---|---|---|
| Pinned 0.5B and 1.5B base snapshots | Training server cache | `model_verified_debug.json`, `model_verified_main.json`; re-download exact revisions and verify against official file digests. |
| Higher-LR debug checkpoint (`r2`, gate failed) | Training server and local backup outside Git | `checkpoint_r2_local_verified.json`, plus the run's checkpoint manifest. |
| Passing debug checkpoint (`r3`, 31/32) | Training server and local backup outside Git | `checkpoint_r3_server_verified.json` and `checkpoint_r3_local_verified.json`; all ten files verified on both copies. |
| First-session runtime ledger | Training server and local private backup | Public summary in `compute_accounting.json`; transfer the private ledger to continue the same approved budget. |
| Main A800 checkpoint (32/32 overfit) | A800 verified; local weight transfer in progress | `checkpoint_main_a800_server_verified.json` and the run's 12-file SHA-256 manifest. Keep the sole verified copy until destination verification completes. |
| Raw run records | GitHub, local checkout and training server | See `run_registry.json` and each run's recorded code commit; one launch is explicitly invalidated. |

Checkpoint files contain model weights and tokenizer, **not** optimizer/RNG/sampler state. The current runner does not provide exact optimizer resume. Copy the checkpoint separately when needed and run:

```bash
python scripts/verify_artifact.py \
  --manifest runs/<run-id>/checkpoint_manifest.json \
  --directory /path/to/transferred/checkpoint \
  --out reports/new_checkpoint_verification.json
```

A Git clone plus the pinned base model can reproduce the experiment from initialization. It does not recover an interrupted optimizer trajectory. Do not delete a server's unique artifacts before a destination copy is verified; see `docs/MIGRATION.md` for the bundle path when direct GitHub access is unavailable.

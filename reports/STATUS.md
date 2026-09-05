# Verified status — 2026-09-05 UTC

## First engineering session complete
- CPU arithmetic fixtures reproduced byte-for-byte; token/loss/isolation and budget tests pass.
- Both Qwen base checkpoints and tokenizers are pinned; all nine files for each role match official expected digests.
- 32-example overfit gate PASSED with debug Qwen2.5-0.5B: 31/32 greedy train correctness and exact trace reproduction, NLL 0.000996 after 300 updates, LR 5e-5.
- Development: 0/16 greedy correctness; 0/64 sampled correct with four samples per problem. This is a software check and provides no positive generalization evidence.
- Debug throughput: 645 supervised response tokens/s (100 measured updates after 10 warmups); peak allocated 8779 MiB, reserved 10062 MiB.
- Main Qwen2.5-1.5B with FP32 parameters, BF16 autocast and standard AdamW failed at the first optimizer-state allocation on the 4090. No optimizer update completed; no valid main-model throughput estimate exists. Keep the adaptation recipe fixed when profiling a larger GPU. This is not a claim that all 1.5B training methods require more than 24 GB.
- Runtime charged: **737 / 7200 seconds** (12.28 minutes); **6463 seconds remain**. Includes a conservative 120-second aborted provenance attempt and 17-second main-model OOM. Idle instance billing is separate.

The higher-LR debug run failed its overfit gate; the uncommitted-source attempt is explicitly invalidated. All raw predictions, histories, manifests and failure receipts are retained in `runs/` and indexed in `run_registry.json`. Large checkpoints remain outside Git; see ARTIFACTS.md and ../docs/MIGRATION.md.

## Next three work items
1. Re-profile the identical 1.5B recipe on a larger-memory GPU selected by the owner, then calibrate base performance using development data. No new machine has been rented automatically.
2. Implement and audit candidate selection for the proposed exact matching construction (or review declared residual tolerances). Freeze an eligible arithmetic pilot split before treatment comparisons. Existing fixture GCM matching is mathematically impossible at the proposed tolerance.
3. Run one paired-seed SFT pilot only after the control definitions and measured cost are settled; inspect failures before expanding seeds, task families or models.

See ../docs/PILOT_PROPOSAL.md, ../docs/CLOSEST_WORK.md, VALIDATION.md, environment_4090.json and compute_accounting.json.

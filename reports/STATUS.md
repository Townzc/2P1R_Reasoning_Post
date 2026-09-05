# Verified status — 2026-09-05 UTC

## A800 engineering continuation complete
- Main Qwen2.5-1.5B base and tokenizer: nine files match pinned official digests. Python/PyTorch/Transformers match the 4090 environment; the new driver is recorded separately.
- All 40 server tests passed, including three new exact-matching selection tests.
- Identical main-model profile completes: 110 updates, 280.60 supervised tokens/s at batch 1; peak allocated 25396.92 MiB, reserved 27886 MiB.
- Main 32-example overfit gate PASSED after 500 updates at LR 5e-5: 32/32 greedy correctness and exact reference trace, train NLL 0.000263.
- Main batch 4 / microbatch 2 throughput: 642.51 supervised tokens/s; peak allocated 26837.74 MiB, reserved 28996 MiB.
- Main development: 0/16 greedy and 0/64 sampled both before and after overfit. Formatting/termination improved; dev NLL increased from 0.630177 to 0.741163. No generalization improvement is established.
- CPU matching search found 64 disjoint blocks / 256 candidate problems. One proposed cycle has exactly 68608 supervised tokens and 256 updates in every arm; Within-Paths/GCM structure TV is zero at each update. Surface diversity currently only changes step labels and selection bias is material; no final scientific split has been frozen.
- A800 added 436 process-seconds. Cumulative runtime: **1173 / 7200 seconds**; **6027 seconds remain**. Idle billing is separate and A800 hourly price is unknown.

See A800_SESSION.md, main_a800_output_integrity.json, exact_matching_candidate_integrity.json, environment_a800.json and compute_accounting.json. GPU work has ended; artifact backup status is in ARTIFACTS.md.

## Retained earlier evidence
The 0.5B debug gate passed with 31/32 train correctness, while development was also zero. Its higher-LR attempt failed the gate; an earlier uncommitted-source attempt was invalidated and conservatively charged. The original 1.5B 4090 OOM occurred before any optimizer update. All failures and both debug checkpoints' verified backups are retained. See run_registry.json.

## Next scientific work
1. Review the exact shared-block candidate design, measured selection bias, and a stronger or explicitly narrow surface-rendering control; freeze group-disjoint train/dev/holdout construction before augmentation.
2. Prepare matched arm schedules and a measured cost proposal within the remaining shared budget. Engineering fixtures and candidate audits are not final scientific datasets.
3. After design review, run a single paired-seed pilot and inspect failures before expanding seeds, tasks or model families.

See ../docs/PILOT_PROPOSAL.md. No four-arm treatment comparison has been launched.

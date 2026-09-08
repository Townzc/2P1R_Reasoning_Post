# Verified status — 2026-09-08

## Approved pilot complete; no further GPU work scheduled

- All four arms completed 1024 updates, 4096 presentations and 267456 response tokens.
- Matched dev: Repeat 14/64, Surface 12/64, Paths 23/64, GCM 18/64.
- Broader dev: 2/64, 0/64, 4/64 and 1/64 respectively.
- Matched Paths/GCM: 11 both correct, 12 Paths only, 7 GCM only, 34 both wrong.
- All raw predictions and full-dose accounting independently verified on CPU.
- Four-arm phase charged 1993 seconds; cumulative 3712/7200 used, 3488 remaining.
- Final private ledger independently retained with no unresolved reservation.
- See PILOT_V1_RESULTS.md and pilot_after_comparison_r1/results.tsv.
- Weight transfer verification is tracked in ARTIFACTS.md. Shutdown readiness
  is recorded in ../docs/NEXT_SESSION.md after publication and complete backups.
- One paired seed, restricted selection, development only. Review another paired
  replication before any more GPU work; no holdout evaluation or main grid.

## Calibration milestone (superseded by completed comparison)

The full-dose feasibility gate passed with 14/64 matched dev, 2/64 broader dev
and 12/16 train diagnostic. All 50 Linux tests passed. It charged 546 seconds,
bringing the then-current ledger to 1719; scientific Repeat was trained separately.
See PILOT_CALIBRATION.md. Historical balances below are not the current ledger.

## Historical CPU preparation — before the calibration

- CPU-only preparation completed; no new GPU process-seconds or server connection.
- Immutable dataset: runs/pilot_v1_20260908_r3; 256 train, 64 matched dev,
  64 broader dev, 2048 unsolved holdout-reserved number groups.
- Raw groups assigned before solving/path augmentation; split and reference
  integrity checked separately. Two unsuccessful preparations remain recorded.
- Four arms: 1024 updates, 4096 presentations, 267456 response tokens,
  472832 processed nonpadding tokens and zero training padding per arm.
  Exact per-example token equality and per-update Paths/GCM structure equality.
- Surface uses four complete sentence frames with unchanged equations/order;
  selection remains restrictive (train target TV .25952, dev .49170).
- Queue defaults to dry run, rejects stale ledgers and insufficient full-phase
  budget, and requires a completed development calibration gate for comparison.
- Original ledger remains 1173 used / 6027 seconds remaining. Planned total
  maximum reservations are 5175 seconds, leaving 852 seconds headroom.
- Local verification: 48 tests passed; two GNU-timeout integration tests must
  run on the replacement Linux server. Full artifact verification and both
  queue dry runs passed. GPU timing remains unmeasured for this pilot.
- Source, commands, budget, stopping rules and limitations: ../docs/PILOT_V1.md.
  No scientific treatment result or calibrated GPU timing exists yet.

The following sections are the retained 2026-09-05 historical status.

## A800 engineering continuation complete
- Main Qwen2.5-1.5B base and tokenizer: nine files match pinned official digests. Python/PyTorch/Transformers match the 4090 environment; the new driver is recorded separately.
- All 42 server tests passed, including five exact-matching selection/operator tests.
- Identical main-model profile completes: 110 updates, 280.60 supervised tokens/s at batch 1; peak allocated 25396.92 MiB, reserved 27886 MiB.
- Main 32-example overfit gate PASSED after 500 updates at LR 5e-5: 32/32 greedy correctness and exact reference trace, train NLL 0.000263.
- Main batch 4 / microbatch 2 throughput: 642.51 supervised tokens/s; peak allocated 26837.74 MiB, reserved 28996 MiB.
- Main development: 0/16 greedy and 0/64 sampled both before and after overfit. Formatting/termination improved; dev NLL increased from 0.630177 to 0.741163. No generalization improvement is established.
- The initial exact-matching pool was additive-only. A stricter 4096-group CPU audit found 64 blocks / 256 problems with a multiply/divide path in every block: 66416 supervised tokens and 256 updates per arm per cycle, with exact per-update Within-Paths/GCM structural equality. Only 6.25% of candidates are selected and Surface only changes step labels; no final scientific split is frozen.
- A800 added 436 process-seconds. Cumulative runtime: **1173 / 7200 seconds**; **6027 seconds remain**. Idle billing is separate and A800 hourly price is unknown.

See A800_SESSION.md, main_a800_output_integrity.json, exact_matching_candidate_integrity.json, environment_a800.json and compute_accounting.json. GPU work has ended. All 12 main checkpoint files are verified on A800 and in a separate local backup; see ARTIFACTS.md.

## Retained earlier evidence
The 0.5B debug gate passed with 31/32 train correctness, while development was also zero. Its higher-LR attempt failed the gate; an earlier uncommitted-source attempt was invalidated and conservatively charged. The original 1.5B 4090 OOM occurred before any optimizer update. All failures and both debug checkpoints' verified backups are retained. See run_registry.json.

## Historical next-work proposal (superseded by pilot v1)
1. Review the exact shared-block candidate design, measured selection bias, and a stronger or explicitly narrow surface-rendering control; freeze group-disjoint train/dev/holdout construction before augmentation.
2. Prepare matched arm schedules and a measured cost proposal within the remaining shared budget. Engineering fixtures and candidate audits are not final scientific datasets.
3. After design review, run a single paired-seed pilot and inspect failures before expanding seeds, tasks or model families.

See ../docs/PILOT_PROPOSAL.md for the earlier proposal. The completed comparison
and current next decision are described above.

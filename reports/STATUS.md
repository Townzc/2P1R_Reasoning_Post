# Verified status — 2026-09-09 UTC

## Seed23 pair complete; checkpoint backups pending

- Both frozen runs completed from source
  `6128e4266d62f14f063585d4c8e94dbe3ad8c711`:
  `pilot_replication_paths_seed23_r1` and `pilot_replication_gcm_seed23_r1`.
- Matched-development greedy final-expression correctness: Paths **22/64**,
  GCM **17/64**. Paired counts: 11 both correct, 11 Paths only, 6 GCM only,
  36 both wrong. Both broader-dev scores are **1/64**, on the same problem.
- Complete-trace verification: matched **18/64 versus 16/64**; broader
  **0/64 versus 1/64**. Correct final expressions and verified displayed
  derivations remain distinct endpoints.
- Matched sampled pass@1/2/4: Paths **35.16% / 47.14% / 54.69%**;
  GCM **24.22% / 30.47% / 37.50%**. Four draws share each problem; they are
  not independent experimental units. All final sets have zero truncations.
- Both arms used 1024 updates, 4096 presentations, 267456 EOS-inclusive
  supervised response tokens and 472832 processed tokens. The frozen
  evaluation seed is 17; training/assignment/order seed is 23.
- Both saved runs passed independent CPU scoring and dose checks; the frozen
  complete-pair audit covers all **800 predictions**, development identities
  and prespecified descriptive strata. All **96 Linux preflight tests** passed.
- Paths charged 500 seconds and GCM 504: **1004 seconds this phase**.
  Cumulative **4716/7200 process-seconds used; 2484 remaining**. The latest
  private ledger is independently retained and reconciled exactly against all
  **13 receipts**, with **zero unresolved reservations**. See the
  [ledger verification](replication_seed23_ledger_verification.json).
- Both new checkpoint downloads and independent SHA-256 verification are
  **pending**. Do not declare the instance disposable until backups and
  publication have both been verified. Ledger reconciliation is complete.
- The old four seed17 checkpoints were reverified locally (48 files) before
  only their redundant remote weight directories were removed. Preflight free
  space was 41.16 GiB on the existing 50 GB data disk; no expansion was needed.
- No further GPU phase or holdout evaluation is scheduled. Next work is CPU
  definition and feasibility testing of legal path families with shared problem
  support. Numerical identity operations can be required to consume each input
  legally; they are not automatically Surface variants or invalid strategies.
- Two paired seeds on the same selected pool do not establish a population
  effect, a reasoning mechanism or ICLR readiness. The broad question overlaps
  existing work; retain the adverse broader-development results.

Results: [analysis report](PILOT_REPLICATION_SEED23_RESULTS.md),
[snapshot](pilot_replication_seed23_after_gpu/results.json),
[complete-pair audit](pilot_replication_seed23_after_gpu_audit/summary.json),
[training-exposure audit](PAIRING_SEED_SEMANTIC_AUDIT_20260909.md), and
[handoff](../docs/NEXT_SESSION.md). The research journal was published at
`3fb43907c0fb8c951b50adfad6dabcc1bfde6403` before the pair's outputs;
this is repository provenance, not external preregistration.

## Historical CPU preparation — 2026-09-09, before seed23 execution

- Fixed next phase: Paths/GCM, seed23 assignment/order/training, evaluation seed17.
- Frozen data: runs/pilot_replication_seed23_20260909_r1; manifest SHA-256
  `0959c217feb4b0c51aebf85c1f08e341e1b6c8034657ee028acb263a2ee18ad4`.
- Parent training blocks, selection audit, split allocation and both development
  files are byte-identical. No new solving or holdout model evaluation occurred.
- Both original and new artifacts passed the real-tokenizer CPU verifier;
  1024 updates, 4096 presentations, 267456 EOS-inclusive response tokens,
  472832 processed tokens, zero padding. Per-update Paths/GCM structures match.
- The new seed changes GCM assignments on 196/256 problems and presentation
  order on all 1024 updates; the Paths exposure set is unchanged.
- Queue: configs/pilot_replication_seed23/queue.json. Its dry run confirms
  3712 used, 3488 remaining and a 2130-second whole-phase reservation.
- No GPU process, server connection, new rental or budget extension this session.
  Both new scientific run IDs remain not_run. Existing checkpoint backups and
  the latest private ledger remain the recovery sources.
- A800 80GB is sufficient for the measured recipe. Require 18 GiB free after
  environment/base-cache setup; previous completed calibration is reused.
- Post-hoc CPU audits verified all 4224 frozen references and rescored 1600
  predictions. Full matched trace verification is Paths 21/64 vs GCM 14/64;
  broader full traces are 1/64 for each. Original primary scores stay unchanged.
- Matched-dev input-1 and reference-identity proportions differ markedly from
  broader dev. These descriptive strata are fixed for the next pair; they do
  not identify a causal effect or justify selecting a favorable subset.
- Close prior work already studies per-problem vs global diversity. See
  ICLR_POSITIONING_20260909.md and ../docs/ICLR_EXPERIMENT_ROADMAP.md.
  The pair is a stability gate, not an ICLR contribution or a main-grid approval.
- Final local suite: 96 tests, 94 passed and two GNU-timeout checks skipped on
  macOS; these are mandatory on the supplied Linux server. Both historical
  audit source-hash sets verified (25 trace / 24 structure inputs/dependencies).
- The prepared replication-output audit passed real seed17 regression tests and
  rejects missing seed23 outputs, changed labels/data, mismatched recipes/code,
  score corruption and output overwrite. It does not invent results for not_run.

Verification reports: pilot_replication_cpu_verification_20260909.json,
pilot_original_cpu_verification_20260909.json and
pilot_replication_seed23_before_gpu/results.json. Current recovery and CPU reproduction
commands are in ../docs/NEXT_SESSION.md.
The test log and final checks are in pilot_replication_tests_20260909.log and
pilot_replication_release_verification_20260909.json.

## Completed seed17 pilot — retained evidence from 2026-09-08

- All four arms completed 1024 updates, 4096 presentations and 267456 response tokens.
- Matched dev: Repeat 14/64, Surface 12/64, Paths 23/64, GCM 18/64.
- Broader dev: 2/64, 0/64, 4/64 and 1/64 respectively.
- Matched Paths/GCM: 11 both correct, 12 Paths only, 7 GCM only, 34 both wrong.
- All raw predictions and full-dose accounting independently verified on CPU.
- Four-arm phase charged 1993 seconds; cumulative 3712/7200 used, 3488 remaining.
- Final private ledger independently retained with no unresolved reservation.
- See PILOT_V1_RESULTS.md and pilot_after_comparison_r1/results.tsv.
- All four weights (48 files, 24.8 GB) have independent SHA-256-verified backups.
  At the seed17 shutdown milestone, the instance had no GPU job or unresolved
  reservation. See pilot_checkpoint_backup_summary.json and
  pilot_final_server_check.json. This historical check does not cover the new
  seed23 checkpoints, whose backups are pending above.
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

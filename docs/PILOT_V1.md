# Pilot v1 — completed on 2026-09-08

The approved calibration and four-arm comparison completed at the frozen dose.
Read ../reports/PILOT_V1_RESULTS.md for outcomes and ../reports/ARTIFACTS.md
for recovery. Current budget: 3712/7200 process-seconds used, 3488 remaining.
No further seed, grid or holdout evaluation is authorized. The protocol below
records the original design; preparation estimates are labeled historical.

## Question and operational limits

Does exposing each problem to four canonical arithmetic structures help relative
to one fixed structure per problem, when exposure-weighted global structures and
supervision are matched? This is a restricted arithmetic SFT pilot. Canonical
syntax is not a cognitive-strategy label. One seed and development scores cannot
establish a population effect or general ordering.

## Immutable data

Directory: `runs/pilot_v1_20260908_r3`. Its manifest pins every artifact and the
exact original Qwen tokenizer. CPU preparation records the parent commit,
dirty-worktree flag and individual source SHA-256 values; it ran during local
development, not from a falsely claimed clean commit. The published source
hashes must match those records. GPU runs require committed clean source/data.

Before solving any group, shuffle all four-distinct-number combinations from
1..40 with seed 20260908 and allocate 4096 train, 2048 development and 2048
reserved holdout candidate groups. Each solved candidate receives one seeded
eligible target in 10..100. The final 2048 groups remain unsolved and are not
read for model evaluation. This is a reserved holdout pool, not a completed
test benchmark or an access-control mechanism.

- Train: 64 shared-structure blocks, 256 problems, four paths per problem.
- Matched development: 16 independently selected blocks, 64 problems.
- Broader development: first 64 eligible, nonselected development groups; this
  complements the restricted split but does not establish IID or compositional OOD.
- No number group overlaps between train, either development set, and holdout.

Selection retains 6.25% of train candidates and 3.125% of development candidates.
Selected-versus-candidate target TV is 0.25952 and 0.49170 respectively. These
are substantial restrictions, especially on the small development set. Report
both development slices; do not present either as representative of arithmetic
in general. The exact search considers the first 12 complete structures at each
token length. Every block supports at least one multiply/divide structure.

## Four conditions and exact controls

| Arm | Paths per problem | Texts per problem | Presentations per problem over four cycles |
|---|---:|---:|---:|
| Repeat | 1 | 1 | 16 |
| Surface | same anchor as Repeat | 4 | 16 |
| Within-Problem Paths | 4 | 4 | 16 |
| Global-Coverage Matched | 1 assigned path | 1 | 16 |

Repeat anchors are selected with seed 17 within each block. GCM uses a seeded
permutation of its four structures and repeats each problem's assigned path.
Paths uses a Latin-square rotation. Both see the same global structure counts
at every update. Block/round order and sample order are shared across conditions.

Surface keeps equations, calculation order, and final expression unchanged.
It varies full sentence frames: `Step {i}:`, `We now calculate:`, `Next, we obtain`,
and `This calculation gives us`. All four tokenizations are verified per example.
This is a controlled sentence-frame variation, not arbitrary rich paraphrasing.

Measured **per arm**: 1024 updates, 4096 presentations, **267456 response tokens
including EOS**, 472832 processed nonpadding tokens, zero training padding.
Maximum training sequence length is 119 tokens. All per-example token counts
match; Paths/GCM structure TV is zero at every update. No truncation or packing.

## Calibration and comparison

Pinned main Qwen2.5-1.5B base; full FP32 parameters with BF16 autocast, AdamW,
LR 5e-5, weight decay 0.01, gradient clip 1, batch 4 / microbatch 2, seed 17.
All jobs start independently from the same base model, never an overfit checkpoint.

Calibration uses Repeat at the full common four-cycle dose. Its initial 16 dev
prompts are greedily generated up to 384 tokens; score the same sequences at
192 and 384 to diagnose the previous truncation problem without changing prompts.
Development checkpoints occur at updates 256 and 512; final evaluation follows
1024 updates. There is no best-checkpoint or per-arm early stopping.

The feasibility gate requires at least 4/64 matched dev greedy successes,
at most 10% parse failures and at most 5% truncation at the full dose. This is
an operational gate, not a statistical-power calculation. If it fails, stop and
inspect predictions; any next calibration is a separate documented decision.

The comparison uses the same four cycles and greedy cap of 384 in every arm.
Final evaluation includes both 64-problem dev sets and 16 unique train examples;
on matched development, also draw four samples per problem at temperature 0.7,
top-p 0.95 and report problem-macro pass@1/2/4. Holdout evaluation stays closed.
The calibration run is not reused as the scientific Repeat result.

## Original cost plan and finite queue (before calibration)

Pre-calibration cumulative ledger: 1173/7200 seconds used, **6027 seconds remain**.
The earlier engineering rate of 642.51 response tokens/s extrapolates to about
416 seconds of training per arm and 27.8 minutes for four arms, excluding load,
decoding and checkpoint costs. This is an estimate, not a new-GPU measurement.

| Phase | Jobs | Per-job process cap | Reservation including 15-second guard per job |
|---|---:|---:|---:|
| Calibration | 1 | 900 s | 915 s |
| Comparison | 4 | 1050 s | 4260 s |
| Total | 5 | — | **5175 s** |

This leaves **852 seconds** beyond the planned maximum reservations. Instance
startup/download/idle billing is separate; no hourly A800 price is assumed.
After calibration, review measured throughput and decoding time before comparison.
Timeout or failure stops the queue; never shorten one arm to fit the budget.

## Recorded execution commands (completed run IDs cannot be reused)

First follow MIGRATION.md: fetch the latest published commit, verify the pinned
base and environment, restore the current ledger, and run tests. A clone can
reuse valid files. Four saved FP32 checkpoints need about 24.8 GB; the comparison
queue requires at least 30 GiB free on the run filesystem for write headroom.
Calibration does not save another checkpoint. Back up all scientific weights
before declaring a server disposable.

```bash
# Read-only preflight; missing/stale ledger is rejected.
python -m scripts.run_pilot_queue --phase calibration
# Explicit bounded calibration only; comparison never auto-starts afterward.
python -m scripts.run_pilot_queue --phase calibration --execute
python -m scripts.report_pilot --out reports/pilot_after_calibration_r1
# After checking the gate, actual cost and Git publication:
python -m scripts.run_pilot_queue --phase comparison
python -m scripts.run_pilot_queue --phase comparison --execute
python -m scripts.report_pilot --out reports/pilot_after_comparison_r1
```

The queue's default is a dry run. Both phases use the shared persistent budget
guard; neither creates a new budget. Reusing a recorded run ID is rejected.
Results snapshots include not-run, failed and completed jobs and are committed.

## Preparation failures retained

`pilot_v1_20260908` stopped before solving because a checkpoint-resaved tokenizer
had a different serialization hash from the official original. Original tokenizer
files were then downloaded at the pinned revision, without model weights.
`pilot_v1_20260908_r2` stopped because 1024 dev candidates yielded only 14 of 16
requested blocks. The final preparation expanded raw allocation before solving;
no matching tolerance or model-outcome criterion was changed.

Workflow inspiration and its bounded adaptation are recorded in `program.md`.

## Historical validation before GPU execution

50 tests ran: 48 passed, two GNU-timeout integration tests were skipped on
macOS and must run on the A800 before training. Real pinned-tokenizer matching,
post-freeze tamper rejection, prefix/EOS scoring, cumulative ledger checks and
token-normalized gradient accumulation passed. The full pilot artifact verifier
and both queue dry runs passed. GPU-specific execution and timing remain to be
verified on the replacement A800; no CUDA training is claimed by these checks.

See reports/pilot_v1_tests_local.log, reports/pilot_v1_integrity.json and
reports/pilot_v1_before_gpu/results.tsv.

## Completed validation and execution

All 50 Linux preflight tests passed before training. Calibration passed at the
full dose. Four independent scientific arms then completed from the same source
commit and base model, charging 1993 additional process-seconds. Saved text was
rescored on CPU and every update/exposure budget reconciled. After reporting
changes, 48 local tests passed with two Linux-only skips. Final results and
paired counts are in ../reports/pilot_after_comparison_r1/results.json.

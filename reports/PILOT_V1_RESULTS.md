# Pilot v1 results — one paired seed, development only

All four independently initialized arms completed the frozen 1024-update dose
on 2026-09-08. On matched development, Paths scored 23/64
and GCM scored 18/64. This is the prespecified
contrast beyond global structural coverage. The restricted, single-seed result
is descriptive; it does not establish a general advantage or seed-level effect.

## Results

| Arm | Matched dev greedy | Broader dev greedy | Sampled pass@1 | pass@2 | pass@4 | Train sample | Process seconds |
|---|---:|---:|---:|---:|---:|---:|---:|
| Repeat | 14/64 (21.88%) | 2/64 (3.12%) | 18.75% | 25.00% | 32.81% | 12/16 | 496 |
| Surface | 12/64 (18.75%) | 0/64 (0.00%) | 13.67% | 19.27% | 25.00% | 10/16 | 500 |
| Within-Problem Paths | 23/64 (35.94%) | 4/64 (6.25%) | 28.12% | 40.10% | 51.56% | 9/16 | 499 |
| Global-Coverage Matched | 18/64 (28.12%) | 1/64 (1.56%) | 27.34% | 30.73% | 34.38% | 14/16 | 498 |

Each dev split has 64 distinct problems. Sampled metrics use four generations per
matched-dev problem (temperature 0.7, top-p 0.95), the standard finite-sample
pass@k estimator, and problem-level averaging. Sampled pass@1 is not greedy
accuracy. All final greedy and sampled sets terminated with EOS, with zero
384-token truncations. The train diagnostic has only 16 unique examples.

For matched greedy Paths versus GCM: 11 both correct,
12 Paths only, 7 GCM only, and 34
both wrong. On broader development: 0 both correct,
4 Paths only, 1 GCM only, and 59
both wrong. These paired counts preserve overlap that marginal percentages hide.

Repeat independently reproduced the calibration's greedy output files byte for
byte on the train diagnostic and both dev splits. It was trained again from the
pinned base; the calibration run/checkpoint was not reused as a scientific arm.

## Controls and provenance

- Training source for all four arms: `c4f4038f0d1582dc3586802af9d5f22fbfaa13c2`.
- Model and tokenizer: Qwen/Qwen2.5-1.5B base, revision
  `8faed761d45a263340a0528343f099c05c9a4323`.
- Frozen data: `runs/pilot_v1_20260908_r3`; 256 shared train problems,
  64 matched dev, 64 broader dev; number groups allocated before solving.
- Per arm: 1024 updates, 4096 presentations, 267456 supervised response tokens
  including EOS, 472832 processed nonpadding tokens, zero training padding.
- Exact per-example token equality across arms and exact per-update Paths/GCM
  structural exposure counts were verified. The generic per-run budget flag
  does not itself claim cross-condition matching; the separate matching audit does.
- Full FP32 parameters, BF16 autocast, AdamW LR 5e-5, weight decay .01,
  gradient clipping 1, microbatch 2 / effective batch 4, SDPA, checkpointing.
- Seed 17, shared presentation schedule, four complete cycles, common decoding.
  No selected best checkpoint, per-arm early stopping or optimizer substitution.

Measured profiling throughput is about 693.3–698.7
supervised tokens/s; peak allocated memory is about
26.21 GiB (reserved 28.27 GiB).
Later runs overlap network checkpoint backup activity. Wall times are budget
records, not an isolated hardware or arm-speed benchmark.

## Error audit and interpretation

| Arm / greedy split | Correct | Parse failure | Wrong input multiset | Wrong target | Division by zero |
|---|---:|---:|---:|---:|---:|
| Repeat / matched | 14 | 5 | 19 | 26 | 0 |
| Repeat / broader | 2 | 1 | 29 | 32 | 0 |
| Surface / matched | 12 | 3 | 27 | 22 | 0 |
| Surface / broader | 0 | 3 | 38 | 23 | 0 |
| Within-Problem Paths / matched | 23 | 1 | 6 | 34 | 0 |
| Within-Problem Paths / broader | 4 | 2 | 14 | 44 | 0 |
| Global-Coverage Matched / matched | 18 | 5 | 14 | 27 | 0 |
| Global-Coverage Matched / broader | 1 | 5 | 23 | 35 | 0 |

Each generated final expression was rescored locally against its frozen prompt,
input multiset and exact target. Categories are mutually exclusive: parsing first,
then correct, then wrong input multiset, then arithmetic target/division errors.
Intermediate generated calculation steps are not independently checked by this
metric. Final-expression correctness is not evidence that every rationale step
is valid.

The selection retains only 6.25% of train candidates and 3.125% of dev candidates;
target total-variation shifts are .25952 and .49170. Both dev slices are restricted;
neither is a representative arithmetic benchmark or a demonstrated compositional
OOD test. Canonical expression structure is an operational proxy. Surface varies
sentence frames with unchanged equations/order, not arbitrary paraphrases.

Reference dev NLL is available in the machine-readable results, but measures one
canonical textual reference. Its rendering and chosen path favor some trained
texts; it is not a substitute for expression correctness or the primary contrast.
Four samples give a sparse estimate of output diversity. One paired seed and
16 matched-dev selection blocks do not justify population or significance claims.
The 2048 reserved holdout groups remain unsolved and unevaluated.

## Runtime, verification and recovery

The four-arm phase charged **1993 process-seconds**. Including calibration and
all earlier engineering/failed jobs, the shared ledger is **3712/7200 used,
3488 remaining**. Instance startup, transfer, idle time and storage are billed
separately; no A800 hourly price is assumed. No further GPU job is launched.

All four saved-output audits reproduce scoring and full training accounting.
All 50 Linux preflight tests passed. Post-comparison local verification ran the
same 50 tests: 48 passed, with two Linux-only timeout tests skipped on macOS.
Checkpoint backup state is recorded in ARTIFACTS.md and the individual
`pilot_v1_*_checkpoint_backup.json` verification reports. A Git clone restores
code and compact records; weights and the current private ledger are transferred
separately. The weights do not contain optimizer/RNG/sampler resume state.

Machine-readable snapshot: `pilot_after_comparison_r1/results.json` and
`results.tsv`. Immutable raw records: `runs/pilot_v1_{arm}_seed17_r1`.
Run `python -m scripts.verify_pilot_outputs --run runs/<run-id> --out <new-report>`
to reproduce the CPU output audit. Use a new output path for immutable snapshots.

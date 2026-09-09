# E007 — The full common pilot dose passes the feasibility gate

**Work date:** 2026-09-08. **Status:** completed calibration; gate passed.
**Hypothesis timing:** gate and dose fixed in the pilot protocol before this run.

## Question and motivation

Before running four conditions, verify that the intended model/dose yields a
nondegenerate development signal within the runtime envelope.

## Competing explanations and design

Use the Repeat calibration at the common 1024-update dose. Require at least 4/64
matched-dev correct, <=10% parsing failures and <=5% truncation at the final dose.
Interim checkpoints diagnose learning; they do not select a best scientific dose.

## Evidence and result

[pilot_v1_calibration_seed17_r1](../../runs/pilot_v1_calibration_seed17_r1/)
charged **546 seconds**. Matched greedy was **11/64 at 256 updates**, **16/64 at
512**, and **14/64 at 1024**; final parse failures were 5/64 and truncations zero.
Broader dev was **2/64**; train diagnostic **12/16**. No checkpoint was requested.
See [calibration report](../../reports/PILOT_CALIBRATION.md) and
[CPU output verification](../../reports/pilot_calibration_output_integrity.json).

## Interpretation and next decision

The operational gate passed; it is not a power analysis or treatment result.
Proceed to the full independently initialized four-arm comparison at the same
final dose, even though the interim 512-update score was higher. Cumulative
runtime after calibration was **1719 seconds**.

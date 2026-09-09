# C006 — Freeze shared data and the full four-arm pilot dose

**Work date:** 2026-09-08. **Status:** completed CPU preparation.
**Hypothesis timing:** design frozen before pilot model outcomes.

## Question and motivation

Make the within-problem/global-allocation contrast concrete under exact common
supervision and update budgets, after the earlier feasibility failures.

## Competing explanations and design

Allocate raw groups before solving/augmentation; select 256 train, 64 matched
dev and 64 broader dev problems. Preserve 2048 unsolved reserved groups. Use
four complete Surface sentence frames, paired seed17, four cycles, no packing,
exact per-example tokens and per-update Paths/GCM structure matching.

## Evidence and result

[Frozen data](../../runs/pilot_v1_20260908_r3/) and
[integrity audit](../../reports/pilot_v1_integrity.json) establish **1024 updates,
4096 presentations, 267456 supervised tokens including EOS, 472832 processed
nonpadding tokens and zero training padding per arm**. Selected fractions are
6.25% train and 3.125% matched dev; target TV shifts are **0.25952/0.49170**.
See [frozen protocol](../PILOT_V1.md), including retained preparation failures.

## Interpretation and next decision

This is a deliberately restricted pilot, not IID/OOD benchmark validation.
Exact controls address budget confounding, not selection or semantic equivalence.
Proceed to the bounded calibration gate [E007](E007_pilot_calibration.md);
the scientific queue remains conditional on that full-dose gate.

# C002 — Multiply/divide constraint sharply reduced selection support

**Work date:** 2026-09-05. **Status:** completed CPU sensitivity audit.
**Hypothesis timing:** follow-up to C001's observed operator collapse.

## Question and motivation

Can the existing candidate-pool size supply the intended 256 problems once
every selected block must contain a multiply/divide structure?

## Competing explanations and design

Require an explicit multiply/divide structure while retaining full canonical
signatures and exact exposure/token controls. The search limit is a feasibility
heuristic, not a proof that other matching constructions are impossible.

## Evidence and result

[exact_matching_muldiv_20260905](../../runs/exact_matching_muldiv_20260905/)
selected **64 of 1024 problems** (6.25%), with **34 complete structures**,
**16592 supervised tokens per arm/cycle**, target TV **0.44238**.
See [operator sensitivity](../../reports/matching_operator_sensitivity.json).
This was CPU only, not a model experiment.

## Interpretation and next decision

The candidate search supplies fewer problems than intended. Increase the
candidate pool in [C003](C003_muldiv_larger_pool.md), retaining the constraint
rather than reporting this restricted subset as a broad benchmark.

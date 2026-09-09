# C001 — Exact controls were feasible but selected additive paths

**Work date:** 2026-09-05. **Status:** completed CPU candidate audit.
**Hypothesis timing:** retrospective design-feasibility summary; no model outcomes used.

## Question and motivation

Can four conditions share problems, supervised tokens and per-update global
structure counts while differing in within-problem path exposure?

## Competing explanations and design

A nominally diverse set might differ in budget or collapse to easy structures.
Search 1024 number groups in 1..40 for four-problem/four-structure equal-length
blocks; use a Latin-square allocation and an explicit tokenizer audit.

## Evidence and result

[exact_matching_candidates_20260905](../../runs/exact_matching_candidates_20260905/)
yielded **64 blocks / 256 problems / 1024 reference paths**. One cycle gave
**68608 supervised tokens** and 256 updates per arm. Selection was 25%, target
TV **0.25098**. However all paths used only addition/subtraction: **1376 additions,
1696 subtractions**. Surface changed step labels only. See
[A800 session](../../reports/A800_SESSION.md) and
[operator audit](../../reports/matching_operator_sensitivity.json).

## Interpretation and next decision

Exact matching is possible, but this selected operator distribution does not
represent the intended task. No GPU result exists for this candidate artifact.
Add an explicit multiply/divide requirement in [C002](C002_muldiv_small_pool.md),
while treating structure syntax as a proxy and reporting selection losses.

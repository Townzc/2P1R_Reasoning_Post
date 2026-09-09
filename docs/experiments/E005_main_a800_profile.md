# E005 — Unchanged main-model profile fits A800

**Work date:** 2026-09-05. **Status:** completed GPU profile.
**Hypothesis timing:** retrospective engineering summary.

## Question and motivation

Determine whether sufficient memory resolves E004 while retaining the intended
model and optimization recipe.

## Competing explanations and design

Reuse pinned Qwen2.5-1.5B base, FP32 parameters, BF16 autocast and standard AdamW.
Run **110 updates**, with 10 warmups and 100 measured updates, batch/microbatch 1/1.
Carry the cumulative ledger across the hardware replacement.

## Evidence and result

[profile_main_a800_20260905_r1](../../runs/profile_main_a800_20260905_r1/) completed:
**280.60 supervised tokens/s**, **25396.92 MiB peak allocated**, **7016 supervised
tokens**, **32 charged seconds**. Source commit and verified environment are in
[A800 session](../../reports/A800_SESSION.md).

## Interpretation and next decision

Optimizer allocation succeeds under the unchanged recipe. This profile does not
test generalization or establish a hardware speed ratio. Proceed to the
main-model [32-example gate](E006_main_a800_overfit.md) at effective batch 4.

# E004 — Main-model FP32 AdamW exceeded 4090 memory

**Work date:** 2026-09-05. **Status:** failed GPU profile.
**Hypothesis timing:** retrospective engineering summary.

## Question and motivation

Can the intended Qwen2.5-1.5B base use the selected full-parameter recipe on 24 GB?

## Competing explanations and design

Model loading alone does not establish training feasibility: optimizer state and
gradients also require memory. Run the actual FP32-parameter/BF16-autocast AdamW
profile rather than silently changing precision, optimizer or adaptation method.

## Evidence and result

[profile_main_20260905_r1](../../runs/profile_main_20260905_r1/) failed with
`OutOfMemoryError` at AdamW state allocation, **before completing any update**.
The receipt charges **17 seconds**. See
[memory analysis](../../reports/main_memory_analysis.json) and the
[run registry](../../reports/run_registry.json).

## Interpretation and next decision

This rejects this specific recipe/hardware fit, not the model's learning ability
or every possible 4090 implementation. Preserve the recipe on the supplied A800
for [E005](E005_main_a800_profile.md); no LoRA or optimizer-precision substitution
was made to disguise the memory failure.

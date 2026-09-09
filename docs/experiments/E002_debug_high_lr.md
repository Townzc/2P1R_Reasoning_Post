# E002 — Initial debug learning rate failed the memorization gate

**Work date:** 2026-09-05. **Status:** completed; engineering gate failed.
**Hypothesis timing:** retrospective summary of the recorded gate.

## Question and motivation

Can Qwen2.5-0.5B base learn 32 fixed examples with the initial SFT implementation?

## Competing explanations and design

Low teacher-forced NLL can coexist with incorrect free generation. Require the
recorded >=95% train-correctness gate rather than accepting loss alone. Use the
published source, full FP32 parameters, BF16 autocast, AdamW LR **2e-4**, effective
batch 4/microbatch 2, seed17 and 400 updates. This is not a treatment contrast.

## Evidence and result

[Run E002](../../runs/overfit_debug_20260905_r2/) completed **400 updates**, processing
**101950 supervised tokens** and charging **342 seconds**. Train correctness was
**25/32**, reference NLL **0.011995**; dev was **0/16 greedy**, **0/64 sampled**.
See [validation](../../reports/VALIDATION.md) and its retained raw predictions.

## Interpretation and next decision

The software gate failed despite low NLL. Oscillation motivated a lower-LR
engineering retry, not a relaxed correctness parser or a scientific conclusion.
[E003](E003_debug_lower_lr.md) changes LR and maximum duration; it is not a
controlled estimate of an isolated LR effect.

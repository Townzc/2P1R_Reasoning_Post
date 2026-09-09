# E006 — Main model memorizes examples without dev generalization

**Work date:** 2026-09-05. **Status:** completed; engineering gate passed.
**Hypothesis timing:** retrospective summary of the recorded engineering gate.

## Question and motivation

Verify the main model can learn the exact task serialization before attributing
later differences to data allocation.

## Competing explanations and design

Use 32 fixed examples, main base, LR 5e-5, batch 4/microbatch 2 and seed17;
apply the same >=95% correctness/<0.2 NLL engineering gate. Memorization and
termination improvements must be separated from held-out correctness.

## Evidence and result

[overfit_main_a800_20260905_r1](../../runs/overfit_main_a800_20260905_r1/) passed
at **500 updates**, **32/32 train** and exact reference traces, NLL **0.000263**.
Both before and after adaptation, dev was **0/16 greedy**, **0/64 sampled**;
dev NLL rose **0.630177 to 0.741163**. It used **127448 supervised tokens**,
charged **404 seconds**, and peaked at **26837.74 MiB** allocated. See
[A800 session](../../reports/A800_SESSION.md) and
[independent output audit](../../reports/main_a800_output_integrity.json).

## Interpretation and next decision

The software gate passed; generalization did not. Heavy base truncation also
limits interpretations of its zero score. After E005/E006 the cumulative ledger
was 1173 seconds. Develop reviewed coverage and budget controls on CPU before
any treatment comparison; retain the negative development result.

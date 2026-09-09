# E003 — Lower-LR debug run passed the engineering gate

**Work date:** 2026-09-05. **Status:** completed; engineering gate passed.
**Hypothesis timing:** retrospective summary of the recorded follow-up.

## Question and motivation

After E002, test whether a less aggressive recipe can satisfy the same
memorization requirement without weakening final-expression verification.

## Competing explanations and design

Use the same 0.5B base, 32 examples, serialization, batch and seed, with LR **5e-5**
and a maximum 800 updates. Stop on the engineering gate (>=95% train correctness,
reference NLL <0.2). This adapts an engineering recipe after a failure; it is not
a preregistered scientific comparison or a development-based checkpoint search.

## Evidence and result

[Run E003](../../runs/overfit_debug_20260905_r3/) passed at **300 updates**:
**31/32 train**, NLL **0.000996**, **76466 supervised tokens**, **258 charged seconds**.
Development remained **0/16 greedy** and **0/64 sampled**. Raw outputs and
[trace summary](../../reports/overfit_debug_20260905_r3_trace_summary.json) are retained.

## Interpretation and next decision

Memorization is feasible, but no development generalization is established.
Move to the intended 1.5B base with the unchanged FP32 AdamW approach; the next
constraint was [memory feasibility](E004_main_4090_memory_failure.md).

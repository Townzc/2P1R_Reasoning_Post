# E001 — First debug launch lacked reproducible source provenance

**Work date:** 2026-09-05. **Status:** invalidated GPU attempt.
**Hypothesis timing:** retrospective engineering summary.

## Question and motivation

Establish a reproducible 32-example software gate before scientific comparisons.
The first launch used the 0.5B debug base and the initial engineering configuration.

## Competing explanation and control

An apparent training outcome could reflect unrecorded source rather than the
published implementation. Source/configuration identity must therefore pass
before interpreting losses or generated answers.

## Evidence and result

Run: [overfit_debug_20260905_r1](../../runs/overfit_debug_20260905_r1/).
The registry marks `aborted_provenance_check`, `evidence_valid: false`.
The attempt was stopped and conservatively charged **120 seconds**. No train/dev
score from it is accepted. See [validation](../../reports/VALIDATION.md) and
[AI use log](../../AI_USE_LOG.md).

## Interpretation and next decision

This is a provenance failure, not evidence for or against learning. Add the
Git-tracked-source/configuration guard, synchronize published history and use a
fresh run ID. The valid restart is [E002](E002_debug_high_lr.md).

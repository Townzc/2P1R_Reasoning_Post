# C000 — Supported environment and reproducible CPU/bootstrap checks

**Work date:** 2026-09-05. **Status:** environment setup completed after failures.
**Hypothesis timing:** retrospective engineering summary, not a treatment hypothesis.

## Question and motivation

Can the arithmetic parser, split construction, supervision masks and training
environment be reproduced before interpreting model behavior?

## Competing explanations and design

An unsupported interpreter, wrong working directory or altered model bytes can
look like a task/implementation failure. Use the supported Python environment,
run correctness checks and verify downloaded model bytes against pinned official
digests. Changing a download route must not change the expected model identity.

## Evidence and result

[Validation](../../reports/VALIDATION.md) records an initial wrong-directory/
Python 3.9 attempt failing on unsupported `int.bit_count`; it was corrected under
Python **3.12.14**, where the original **20 local tests passed**. The expanded
training-server suite later passed 35 tests. Direct model access failed; mirror
bytes were checked against expected official digests before accepted execution.
Actual environments and model verification are retained in
[4090 environment](../../reports/environment_4090.json),
[debug model verification](../../reports/model_verified_debug.json) and
[main model verification](../../reports/model_verified_main.json).

## Interpretation and next decision

These are environment/provenance corrections, not learning results. No separate
GPU experiment or model-performance charge is inferred from setup time; counted
GPU attempts have individual receipts. Proceed to bounded model gates while
keeping parser/task semantics and expected model revisions unchanged.

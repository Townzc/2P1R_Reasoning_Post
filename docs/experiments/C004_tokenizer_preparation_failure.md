# C004 — Pilot preparation rejected a reserialized tokenizer

**Work date:** 2026-09-08. **Status:** CPU preparation failed before solving.
**Hypothesis timing:** retrospective provenance check.

## Question and motivation

Ensure token matching uses the exact original tokenizer rather than assuming a
saved checkpoint's tokenizer serialization is identical.

## Competing explanations and design

Equivalent-looking tokenizer files can have different serialized bytes. Require
the pinned original Git blob before freezing a dose; do not relax provenance
merely because tokenization appears plausible.

## Evidence and result

[failure.json](../../runs/pilot_v1_20260908/failure.json) records
`CPU_PREPARATION_FAILED_BEFORE_SOLVING`: the checkpoint tokenizer serialization
differs from the pinned original blob. **Zero GPU seconds**; no scientific data
or model outcome resulted.

## Interpretation and next decision

Acquire and verify the original tokenizer, retain the failed directory, and use
a new preparation ID. This is a file-identity failure, not evidence that the
mathematical matching design is infeasible. The next attempt is
[C005](C005_development_support_failure.md).

# C003 — Larger candidate pool restores the intended matched training size

**Work date:** 2026-09-05. **Status:** completed CPU sensitivity audit.
**Hypothesis timing:** follow-up to C002's limited support.

## Question and motivation

Can 4096 candidates support 256 matched problems under the same operator constraint?

## Competing explanations and design

Expand candidate search rather than weakening exact structural/token matching.
Continue checking selected distributions because increased candidate count does
not remove eligibility bias or strengthen the step-label Surface control.

## Evidence and result

[exact_matching_muldiv_4096_20260905](../../runs/exact_matching_muldiv_4096_20260905/)
selected **256/4096 problems**, **31 complete structures**, **66416 supervised
tokens per arm/cycle**, target TV **0.22876**. Its 1024 binary programs contain
**636 multiplications, 348 divisions, 860 additions and 1228 subtractions**.
See [A800 session](../../reports/A800_SESSION.md) and
[candidate verification](../../reports/exact_matching_candidate_integrity.json).

## Interpretation and next decision

The intended candidate size is feasible at 6.25% selection. These are not frozen
scientific train/dev/test splits, and multiply/divide does not guarantee
nontrivial operations. Prepare presolver-disjoint splits and a stronger Surface
rendering before the pilot; do not train on this feasibility artifact.

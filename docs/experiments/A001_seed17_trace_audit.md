# A001 — Correct final expressions can accompany false displayed calculations

**Work date:** 2026-09-09. **Status:** completed post-hoc CPU analysis.
**Hypothesis timing:** formulated after observing seed17; not an original primary endpoint.

## Question and motivation

Does final-expression correctness also imply a valid displayed derivation?

## Competing explanations and design

A model may output a correct expression while displaying false equations,
reusing unavailable operands or presenting an unrelated trace. Independently
check local equations with exact rationals, enumerate input-consumption
provenance, and require connection to the final expression. Keep inconsistent,
unverifiable and fully verified outcomes separate; support all frozen Surface
frames. Audit saved predictions only, leaving official primary scores intact.

## Evidence and result

[Trace findings](../../reports/pilot_v1_trace_audit_20260909/FINDINGS.md) and
[summary](../../reports/pilot_v1_trace_audit_20260909/summary.json) cover **1600
stored predictions**. Fully verified matched greedy traces are **21/64 Paths vs
14/64 GCM**, compared with final-expression scores 23/64 and 18/64. Broader
fully verified traces are **1/64 for both**, compared with final-expression
scores 4/64 and 1/64. No new inference or GPU time was used.

## Interpretation and next decision

Displayed arithmetic must be distinguished from final-answer success and hidden
reasoning faithfulness. The strict ordered-tree connection may leave equivalent
forms unverifiable; publish that limitation. Retain the frozen rules as a
secondary seed23 diagnostic, without replacing its original primary endpoint.

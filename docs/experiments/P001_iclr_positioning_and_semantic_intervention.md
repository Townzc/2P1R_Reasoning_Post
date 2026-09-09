# P001 — Positioning audit and proposed semantic intervention

**Date:** 2026-09-09. **Status:** literature audit completed; intervention and
larger scientific study **proposed, not executed**.
**Hypothesis timing:** motivated by prior work and seed17 post-hoc findings.

## Question and motivation

What substantive question remains beyond showing that within-problem diversity
can differ from globally distributed diversity? The closest inspected paper
already compares globally balanced NL/code diversity allocated within versus
across problems: [Why Do Reasoning Models Lose Coverage?](https://arxiv.org/html/2605.17026v2),
Section 4.2.1. Our tighter arithmetic accounting alone is not sufficient novelty.
The [positioning audit](../../reports/ICLR_POSITIONING_20260909.md) records scope,
other close comparisons and verified conference planning sources.

## Competing explanations and falsifiable proposal

An allocation advantage might require genuinely different computational choices;
alternatively, neutral operations, algebraic rewrites or changes in success
concentration might suffice. A candidate intervention crosses allocation
(within-problem versus globally matched) with path type (substantive alternatives
versus neutral/algebraic rewrites). Failure to preserve comparable problems,
difficulty, structure exposure and supervision would block a causal reading.

## Design status and evidence

This is **not a frozen experiment**. Operational semantic equivalence, eligible
pool construction, matching residuals, sample sizes, seeds and compute envelope
remain to be specified and reviewed. Removing input 1 alone is inadequate:
intermediate expressions can create 1 or 0. Existing evidence is the
[trace audit](A001_seed17_trace_audit.md), [identity audit](A002_seed17_identity_and_success_audit.md)
and [roadmap](../ICLR_EXPERIMENT_ROADMAP.md), not intervention outcomes.
**Results: pending; no intervention model trained.**

## Interpretation and next decision

Finish the bounded seed23 stability check while designing the semantic boundary
on CPU. A paper-quality extension needs a falsifiable intervention, independent
pools and prespecified seeds, a meaningful generalization boundary and credible
uncertainty. A second model/task must test a stated limit. Venue ambition does
not determine the outcome or authorize a main grid, extra GPU budget or submission.

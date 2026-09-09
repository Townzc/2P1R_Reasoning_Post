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

## Design refinement and evidence update — 2026-09-09 UTC

An independent design critique before inspecting seed23 outcomes identified a
problem in the provisional wording above: numerically neutral does not mean
invalid, useless or a Surface rewrite. Countdown requires every input once.
For `[1,2,3,4]` and target 24, `(1*2)*(3*4)` and `(2*3)*(4/1)` are legal ways to
consume all inputs, as is `(1+3)*(2+4)`. Simplification can be an analysis
projection, but removing the neutral operation from a training example may
violate input-use rules. Retain the legal expression and input provenance.

The refined question asks whether within-problem allocation's benefit depends
on different numerical calculation structures, or can also arise from different
legal ways of consuming required inputs. Define the families and their equivalence
relation before constructing data. Fix problems and audit stated difficulty
proxies; do not claim all difficulty is controlled. Numerical exposure differences
can be part of the intervention and should not automatically be adjusted away.

[C007](C007_identity_family_inventory_failure.md) rules out a naive 2+2 reuse of
the current four-path inventory: no problem has two references in each identity
category. It does not establish mathematical impossibility beyond that inventory.
The proposal remains unexecuted. Shared support, matching residuals and retention
must be established before freezing an experiment or renting more GPU time.

After the critique, [E009](E009_seed23_paired_replication.md) completed with the
same primary net difference of five problems, a smaller complete-trace gap and
no broader greedy advantage. The result supports continued CPU design work,
not an already established semantic mechanism or approval to expand training.

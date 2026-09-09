# A002 — Identity-path selection and heterogeneous success concentration

**Work date:** 2026-09-09. **Status:** completed post-hoc CPU analysis.
**Hypothesis timing:** after seed17 outcomes; descriptive strata, not a causal test.

## Question and motivation

Does canonical structural diversity include many neutral operations, and where
are the greedy and sampled differences concentrated?

## Competing explanations and design

Different syntax need not encode distinct computational choices. Traverse the
four selected reference paths with exact rational arithmetic, marking x*1, x/1,
x+0 and x-0, including intermediate values. Separate input 1 from these events;
0-x, 1/x and x*0 are not identity events. Rescore all four arms' saved dev outputs,
retain fixed problem IDs and report all 16 selection-block contrasts.

## Evidence and result

[Summary](../../reports/pilot_v1_structure_bias_20260909/summary.json) and
[384 per-problem records](../../reports/pilot_v1_structure_bias_20260909/per_problem.jsonl)
contain source hashes. **695/1024 training paths** and **168/256 matched-dev
reference paths** contain identity operations. Input 1 occurs in **96/256 train,
32/64 matched dev and 5/64 broader dev**.

Among 48 matched problems with any selected identity path, Paths/GCM greedy is
**15 vs 15**; among the other 16 it is **8 vs 3**. Four-sample success-count
histograms for c=0..4 are Paths **[31,11,11,5,6]**, GCM **[42,4,2,2,14]**:
72 vs 70 correct generations cover 33 vs 22 problems. Input-1 sampled coverage
is **22 vs 12**; without input 1 it is **11 vs 10**.

## Interpretation and next decision

The endpoint-dependent strata do not identify a causal shortcut explanation.
Labels concern selected references, not every solution a problem admits; strata
also differ in difficulty/support. Freeze these descriptive labels for seed23,
then design an intervention before making a semantic-path mechanism claim.
No GPU work, holdout access or primary-endpoint change occurred.

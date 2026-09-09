# C008 — Complete ordered-expression support census on the fixed training pool

**Entry date:** 2026-09-09 UTC. **Status at entry:** implementation preparation;
real-pool enumeration not started. **Timing:** after published seed23 results,
before this census's outcomes. This is a bounded local CPU diagnostic under
[P002](P002_legal_support_enumeration_design.md), not another GPU experiment.

## Question and motivation

Does C007's zero 2+2 support arise from the four selected references, or does the
same problem pool lack enough paths even after complete enumeration under the
declared binary grammar? A zero remains a useful result. Finding more legal
paths is not evidence that they are different semantic strategies or that a
four-cell training design is feasible.

## Fixed design and competing explanations

Read only the 256 original problem IDs, input numbers, targets and stored paths
in `runs/pilot_v1_20260908_r3/train_blocks.json`, SHA-256
`e15857122ad9148a1a209cce7c8ef4c107ff0de27bcfe11b97ba6fce6b7a2cea`.
Keep inputs and targets unchanged. Enumerate all five full binary-tree shapes,
24 input orders and 64 operator assignments per problem using exact fractions,
rejecting division by zero. There are 1,966,080 construction attempts in total.
Do not use the AC-deduplicating solver as an exhaustive identity-family oracle.

Use two CPU workers with a 600-second wall-time ceiling. A timeout or invalid
reference recovery yields an incomplete/failed report, never zero support.
Reconcile all attempted expressions, independently verify every retained legal
answer and recover all four stored paths. Save fresh compact per-problem results,
stream hashes and optional complete compressed solution records outside Git.

Report ordered-solution family counts and numeric-leaf AC classes, including
classes containing both identity labels. Predeclare K=2 and K=4 diagnostics:
each family's class count and explicit disjoint-class assignment feasibility.
An AC-mixed class may fill only one slot in the disjoint assignment. Record
witnesses and the gap from the stored inventory without choosing K from whichever
result looks favorable. The identity label describes an evaluated trajectory;
it is not an invariant semantic-strategy category.

## Scope and decision rule

This attempt covers **enumeration completeness and family/class support only**.
Tokenizer length equality, Surface eligibility, global/per-update structural
matching, statistical design and GPU feasibility are not tested here. P002's
later matching-loss diagnostics remain proposals after this census.

- Failure or timeout: preserve progress and identify an incomplete computation.
- Complete zero support: reject the specified construction on this pool/grammar.
- Added ordered support but no disjoint-class support: report that distinction.
- Added class support: selection limited the stored inventory, but no training
  design is approved until its remaining matching/size constraints are checked.

The fixed pool is already strongly selected. A support result cannot establish
representativeness, difficulty matching, a mechanism or model performance. Do
not read or solve reserved holdout groups, recruit new questions, change target
values or infer an allocation effect from this mathematical census.

## Results — pending

Append the exact execution source, runtime/completeness receipt, output hashes,
all support counts and interpretation. Preserve the design above. This local CPU
attempt does not consume additional GPU process-seconds or extend that allowance.

## Completion appended — 2026-09-09 UTC

The complete census ran from prepublished source
`b504cb7b604847b2155bb71dd2bb2c3602d9f371`, with two CPU workers and a measured
1.640-second elapsed time. All 256 problems completed, all 1,024 stored ordered
references were recovered, and recorded source files stayed unchanged. There
was no timeout or retry. The 1,966,080 attempted expressions partition into
1,176 undefined divisions, 1,939,058 wrong-target programs and 25,846 legal
ordered solutions. The complete private solution stream and public compact
records have SHA-256 digests in the [summary](../../reports/legal_support_census_20260909_r1/summary.json).

| Prespecified support rule | Problems |
|---|---:|
| Ordered 2+2 | 134/256 |
| Ordered 4+4 | 132/256 |
| Disjoint-AC 2+2 | 132/256 |
| Each family has four AC classes, overlap allowed | 131/256 |
| Disjoint-AC 4+4 | 131/256 |

There are 112 mixed-label AC classes across 56 problems. Stored-four selection
therefore hid class support on part of the pool. Yet 125 problems fail disjoint
4+4 even before tokenizer/structure constraints, so the complete 256-problem
four-cell design is not feasible under that declared rule. Do not silently use
K=2 or reduce the problem set. Neither category is a semantic-strategy label.

**Decision:** the next step can be a fixed CPU matching-loss diagnostic, with
explicit cardinality/class-overlap rules and disclosed retention. Tokenizer,
global/per-update structural matching, difficulty proxies, sample size and GPU
work remain untested/unapproved. See the [full interpretation](../../reports/LEGAL_SUPPORT_CENSUS_20260909.md).

Independent archive verification subsequently rechecked all 25,846 solutions,
all stream hashes, original reference counts and 1,576 allocation witnesses with
an independent AST/Fraction evaluator and separate Hall-condition support test.
It confirmed all reported counts without rerunning enumeration or inspecting
model/development/holdout outputs. See
[independent proof](../../reports/legal_support_census_20260909_r1/independent_verification.json).

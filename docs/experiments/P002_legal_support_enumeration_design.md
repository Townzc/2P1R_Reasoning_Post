# P002 — Distinguish selected-inventory limits from legal path-family support

**Work date:** 2026-09-09 UTC. **Status at entry:** proposed CPU design from code review;
not executed. **Hypothesis timing:** follows A003/C007 and the existing pilot
outcomes; it is not an earlier registration of the pilot or a main-GPU protocol.
This entry used code/schema review without new solving, model inference, holdout
access or data construction. Published aggregate seed23 outcomes were already
known to the coordinator; the independent code reviewer did not inspect new
model predictions. The arithmetic example below is a hand-worked property
counterexample, not a new experimental result.

## Question and motivation

[C007](C007_identity_family_inventory_failure.md) found zero problems with two
identity-containing and two identity-free paths among their four stored
references. Does this reflect the selected inventory, or do the same public
training questions lack sufficient legal support under a declared path-family
and distinctness rule? Resolve that narrower uncertainty before considering a
new candidate pool or a four-cell GPU design.

[A003](A003_pairing_seed_semantic_exposure_audit.md) also showed that numerical
identity exposure is not determined by canonical structure. Code review adds a
specific limitation: `solve_all` retains one representative per AC-canonical
expression at each dynamic-programming subset. That is consistent with its
stated canonical-expression representation, but it cannot exhaustively audit a
property that varies among representatives of the same class.

## A legal counterexample to identity invariance under AC deduplication

Both expressions use the distinct inputs **1, 2, 3, 20 exactly once** and produce
the valid target **20** under the current four-input binary-operation grammar:

| Ordered expression | Nonroot calculations | Root calculation | Identity event under the existing definition |
|---|---|---|---|
| `((1 - 3) + 2) + 20` | `1 - 3 = -2`; `-2 + 2 = 0` | `0 + 20 = 20` | Yes, addition of zero |
| `(1 - 3) + (2 + 20)` | `1 - 3 = -2`; `2 + 20 = 22` | `-2 + 22 = 20` | No |

Both have the same current numeric-leaf AC path ID, `+(-(1,3),2,20)`.
The old solver's representative choice can therefore hide an identity-free or
identity-containing rendering within a class. It would be incorrect to infer
absence of all legal family support by counting only that one representative.
It would also be incorrect to call these two AC-equivalent rebracketings two
demonstrated semantic strategies. The example is not claimed to be a member of
the frozen training set.

## Proposed bounded input and enumeration

Start with exactly the **256 already public training problems** in
`runs/pilot_v1_20260908_r3/train_blocks.json`. Retain each problem's numbers,
target and identity. Sort by problem ID for deterministic enumeration. Do not
call `candidate()`, which would select an eligible target again; do not expand
the range, choose another target, read split-allocation holdout groups or use new
candidates. This first attempt diagnoses the existing selected pool only.

For four distinct numbers there are five ordered full binary-tree shapes
(Catalan number C3), 4! = 24 input permutations and 4^3 = 64 assignments of
`+`, `-`, `*`, `/` to the three internal nodes. Thus the direct search has exactly
**5 × 24 × 64 = 7680 construction attempts per problem**, or **1,966,080 attempts
for 256 problems**, before filtering. This is an upper bound on retained legal
solutions, not their count. The grammar has exactly four input leaves and three
binary operations; it excludes extra constants, unary operators, powers and
repeated inputs.

Evaluate every attempted tree with exact `Fraction` arithmetic and reject any
division whose evaluated denominator is zero, including nested divisions.
Retain every ordered tree that reaches the original target. Do not merge by AC
class while traversing or saving this first inventory. A full-ordered-tree DP
would also be possible, but the explicit five-shape enumeration makes the search
bound and completeness scope easier to check independently.

Before reporting support, independently verify every retained expression's
input multiset and target, and verify that all four stored reference expressions
are recovered. Reconcile attempted, undefined, wrong-target and retained counts
per problem. Store deterministic expression identities, class labels and source
hashes; save progress in fresh immutable output paths. Proposed operational
ceiling: two CPU workers and 600 seconds wall time, without GPU or network use.
That is a bound to review, not a measured runtime estimate. A timeout produces
**incomplete enumeration**, never a zero-support conclusion.

## Taxonomy and support levels to report

Retain the existing numerical identity definition: evaluated `x * 1`, `x / 1`,
`x + 0` and `x - 0` in their allowed operand orientations. It is a numerical
path classification, not a proof of semantic strategy equivalence, invalidity,
or difficulty. In CountDown, using every number once is compulsory; an identity
operation may legitimately incorporate a supplied one or a computed zero/one.
Identity-containing solutions are not invalid examples and are not the Surface
arm, which changes wording while retaining calculations.

For every fixed problem, report the following layers without selecting on model
outcomes:

1. Its original four-reference family counts and the complete ordered-solution
   family counts.
2. Distinct numeric-leaf AC classes represented in each family, and classes
   whose ordered representatives occur in both families. Preserve this
   **AC-mixed** category instead of assigning a class a single arbitrary label.
3. Support when the selected references must come from distinct AC classes.
   If a design requires disjoint class identities across families, solve and
   record that explicit assignment constraint; do not count one mixed class as
   two distinct path identities. Report operator-only structure diversity
   separately from numeric-leaf path diversity.
4. Nonroot fractional/negative/zero/one values, depth and relevant magnitude
   summaries, retaining ordered representations. Counts of identity events and
   other numerical properties remain incomplete descriptions of a path.

A **2×2 factorial design means two experimental factors, not automatically two
paths per family**. If Within-Problem uses K = 4 alternatives within each of the
two families, a same-problem construction needs at least **four qualifying paths
per family**, plus the declared distinctness and matching constraints. The
weaker 2+2 support checked in C007 would not suffice. If K = 2 is proposed instead,
it is a different allocation design and needs its own exposure/dose controls;
it cannot silently inherit the original four-path interpretation.

For this census, predeclare reporting support for **both K = 2 and K = 4** under
each stated distinctness rule. Do not choose the main-study K afterward merely
because one threshold yielded more candidates. The eventual family cardinality,
class-overlap rule and four-cell construction must be fixed in a reviewed
protocol before any GPU experiment.

## Matching-loss diagnostics after the legal-support census

Keep the complete solution inventory separate from the matching procedure. The
current preparation applies several additional filters: exact tokenizer
serialization, equal-length Surface support, one representative per
response-length/operator-structure key, a first-12-structures-per-length search
cap, then four-structure shared-block selection. Each can reduce support. The
current four stored paths are not simply the first four mathematical solutions.

Using the pinned original tokenizer and canonical training response format,
measure the loss of qualifying problems at each separately declared layer:
legal support, chosen class rule, required family cardinality, common
EOS-inclusive supervised length, operator-structure support and shared-problem
block matching. Retain all family-relevant representatives for this diagnosis;
reusing `setdefault(structure_id, row)` can erase one family before it is counted.
A deterministic matching search must report whether it was exhaustive or capped;
a capped search failure is not a proof that no matching exists.

For a candidate four-cell design, verify allocation comparisons within each
family: identical questions, intended P/T/R exposures, supervised tokens,
optimizer updates and required global/per-update structural coverage. Separately
report cross-family operator/length/difficulty changes and numerical-feature
residuals. A purported identity-only mechanism claim requires a design that
addresses those other changes rather than attributing any interaction to
identity by default. No exact token or block match is asserted before it is
actually computed; truncation and meaningless padding are not repairs.

Do not automatically require equality of each problem's entire numerical
property distribution. Some distributional differences can be components or
consequences of allocation; eliminating them may remove the intended treatment.
State which properties are manipulated, held fixed or left as measured residuals,
and how that changes the estimand. An eventual correlation with a model endpoint
would not by itself establish a mechanism.

## Falsifiable go/no-go conditions and next decision

- **Completeness failure:** timeout, count reconciliation failure, missing stored
  references or invalid retained expressions means no valid support conclusion.
  Preserve the failure and diagnose the enumerator; do not treat it as an empty
  mathematical inventory.
- **Complete census, zero support:** reject the specified K/family/distinctness
  construction for these 256 fixed questions under this exact binary grammar.
  This is a stronger result than C007's stored-four failure, but still says
  nothing about other problems, grammars or semantic taxonomies.
- **Raw support but no distinct-class support:** the extra inventory consists
  only of insufficient class diversity or AC-mixed rearrangements under the
  requested rule. Report the distinction; do not advertise semantic strategy
  support from ordered syntax counts alone.
- **Class support but matching failure:** distinguish inventory-selection loss
  from length/structure/block constraints. Report the surviving number of
  problems and search completeness. Do not silently relax matching, reduce the
  intended training size or recruit new questions.
- **All declared CPU checks pass:** proceed only to a concrete four-cell
  protocol, required sample size, uncertainty plan and resource proposal. This
  does not launch GPU training. A same-size, same-pool 256-problem design needs
  all required problems and block constraints to qualify; a smaller subset or
  a new candidate pool is a separate reviewed design with disclosed selection.

No counts from this proposed complete enumeration exist yet. No new generator,
main-study registration, GPU phase or spending authorization is created by this
entry. The immediate decision is whether to implement and run the bounded CPU
census on the already public training questions.

## Inspected source provenance

These hashes identify the code and schema inspected for this proposal; they are
not receipts for a new solver execution. The training manifest preserves the
existing split/selection history; its holdout groups were not read or solved.

| Inspected source | SHA-256 |
|---|---|
| `src/countdown_smoke.py` | `2249e313c60090958d5ddfe474dc44f2dff6337dbccc79a6ee48498254531058` |
| `scripts/audit_exact_matching.py` | `320ec558efcbdbd12c2e28b91f34a5f76650b1437cfb84aff43f19f7932c1e30` |
| `scripts/prepare_pilot.py` | `76f5096548d319c0ccfb293595c51894441f287fcf473427bfe95aed006e6e55` |
| `src/pilot_data.py` | `9b72c83c1dcc5c55fa38c3132e7c99075ff2e056bc97465e854e19be75a9d714` |
| `runs/pilot_v1_20260908_r3/train_blocks.json` | `e15857122ad9148a1a209cce7c8ef4c107ff0de27bcfe11b97ba6fce6b7a2cea` |
| `runs/pilot_v1_20260908_r3/manifest.json` | `45c51cec657eff48e271a67d99439b5f390bc661562fab3bd3d920c450c03e6b` |

## Subsequent execution of the census portion

[C008](C008_complete_ordered_support_census.md) completed the bounded enumeration
and support census after the proposal/code publication. Disjoint-AC support is
132/256 for 2+2 and 131/256 for 4+4; all stored references were recovered. This
establishes an inventory-selection limitation on part of the existing pool,
not a ready matched training design. The tokenizer/structure/block diagnostics
and any later GPU protocol above remain proposals. The original entry is retained;
see [the census report](../../reports/LEGAL_SUPPORT_CENSUS_20260909.md) for outcomes.

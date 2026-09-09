# Complete training-pool census: selected paths hide support, but the full pool is not ready

**Completed 2026-09-09 UTC, local CPU only.** Complete enumeration of the original
256 public training questions found **132 problems with disjoint-AC 2+2 support**
and **131 with disjoint-AC 4+4 support** for the defined identity-present/absent
trajectory categories. The stored four-reference inventory had zero 2+2 support.
Selection therefore hides legal class support on part of this fixed pool. This
does not make the original 256-problem four-cell experiment feasible and does not
identify semantic strategies, a mechanism or any model-performance effect.

## Reason for the attempt and fixed protocol

[C007](../docs/experiments/C007_identity_family_inventory_failure.md) rejected a
naive reuse of the four stored paths. [P002](../docs/experiments/P002_legal_support_enumeration_design.md)
identified a further issue: identity events can differ between AC-equivalent
ordered expressions, so the existing AC-deduplicating solver cannot establish
all identity-family support. [C008](../docs/experiments/C008_complete_ordered_support_census.md)
fixed the census scope before its outputs. Protocol and execution code were
published at `b504cb7b604847b2155bb71dd2bb2c3602d9f371`; the worktree was clean
at launch and all recorded sources remained unchanged during execution.

Keep the original numbers, targets and IDs. Enumerate 24 input permutations,
five ordered full binary trees and 64 operator assignments per problem with
exact Fraction arithmetic. Do not call `candidate()` or `solve_all`, alter the
target, select new questions, inspect development/holdout data or run a model.
Evaluate identity events before grouping concrete-number expressions into AC
classes. Each class can fill at most one slot in a disjoint-class assignment.
Both K=2 and K=4 were specified; neither is selected as the next study's K here.

The run used two local CPU workers, a 600-second ceiling, fresh immutable output
paths and explicit failure/timeout states. Its observed elapsed time was
**1.640 seconds**, not a GPU charge. Eleven focused tests passed before execution,
including complete unique enumeration on a toy problem, overlapping-class
matching, the AC identity counterexample, retained timeout status and gzip-stream
ordering/hash checks. An independent code review preceded execution.

## Complete counts and support rules

| Enumeration account | Count |
|---|---:|
| Completed fixed problems | 256/256 |
| Ordered construction attempts | 1,966,080 |
| Undefined divisions | 1,176 |
| Defined but wrong target | 1,939,058 |
| Legal ordered solutions | 25,846 |
| Stored ordered references recovered | 1,024/1,024 |

The three expression categories sum exactly to the attempted count. Every
retained expression passes an independent parse/input-multiset/target check,
and the identity walker agrees on its exact value. The complete feature stream
is retained as a private compressed JSONL artifact, with public SHA-256 digests.

| Support rule on each fixed question | Eligible problems |
|---|---:|
| At least two ordered expressions per family | 134/256 |
| At least four ordered expressions per family | 132/256 |
| Two per family drawn from four distinct AC classes | 132/256 |
| Each family has four AC classes, allowing cross-family overlap | 131/256 |
| Four per family drawn from eight distinct AC classes | 131/256 |

**56 problems contain 112 AC classes in total that admit both identity labels.**
One such class cannot count as two distinct classes in a joint assignment. The
per-problem report preserves witnesses, stored-reference recovery, original
family counts, mixed-class examples and complete feature-stream hashes. These
counts are mathematical properties of the stated grammar and selected inputs;
they are not sample estimates of model success or semantic strategy diversity.

## Interpretation and next decision

The stored-inventory failure was not evidence of universal mathematical absence:
complete enumeration recovers disjoint class support for many of the same
questions. However, **125 of the original 256 questions fail the 4+4 rule even
before token/structure matching**. Keeping K=4 in both path families therefore
cannot silently reuse the entire fixed problem pool. K=2, a smaller subset or
a newly sampled pool would each be a new design with disclosed eligibility and
its own sample-size/uncertainty argument.

Identity-present/absent remains a property of an evaluated legal trajectory.
An identity step may consume a required input; absence of an identity step does
not prove nontrivial reasoning. Because the property varies inside AC classes,
it cannot be presented as a clean partition of semantic strategies. The census
tests inventory support, not the causal scientific question.

**Next CPU gate:** use a separately frozen matching diagnostic to measure
EOS-inclusive token length, operator-structure and shared-block losses from this
complete inventory, retaining representatives relevant to both families. State
the class-overlap rule, path cardinality and permitted residuals before searching.
Do not count a capped search failure as proof of infeasibility, require per-problem
feature equality that eliminates allocation itself, or repair matching by
truncating responses/adding meaningless padding. No tokenizer matching, new
training dataset, independent-pool study, model run or GPU authorization follows
from the current support counts.

## Evidence and reproduction

- [Immutable summary](legal_support_census_20260909_r1/summary.json) records the
  exact execution commit, source/protocol snapshot hashes, runtime and counts.
- [Per-problem records](legal_support_census_20260909_r1/per_problem.jsonl)
  contain class-allocation witnesses and source-reference recovery evidence.
- [Independent verification](legal_support_census_20260909_r1/independent_verification.json)
  rechecks all 25,846 archived solutions with an independent AST/Fraction walker,
  all stream hashes and 1,576 allocation witnesses. Its separate Hall-condition
  calculation confirms every positive and negative disjoint-class support result;
  runtime was not remeasured and full enumeration was not rerun.
- [Census implementation](../scripts/audit_legal_support.py) and
  [focused tests](../tests/test_legal_support.py) implement the bounded scope.
- Complete solution-stream SHA-256:
  `fa0563f030ffaa810f23e4eb5e9c63a2e12096f2dc675128a9bd9a9362c338d8`.
  Compressed archive SHA-256:
  `42c00622cdf8e9953d50f4a5c781b28e054198dff72915524577fe5a6407f5ef`.

Use the recorded execution commit for the original protocol snapshots; journal
entries may later append results. Reproduce with fresh output paths:

```bash
python -m scripts.audit_legal_support \
  --out reports/new_legal_support_census --workers 2 --max-seconds 600 \
  --solutions-out .local/new_legal_support_census/solutions.jsonl.gz
```

The full solution archive stays outside Git. Compact evidence and its hashes are
published. This is an additional CPU result after the seed23 GPU phase; it does
not change that phase's frozen data, primary endpoint or reported outcomes.

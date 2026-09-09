# C009 — Exact token matching removes substantial family support; block search remains incomplete

**Bounded CPU attempt, 2026-09-09 UTC.** The complete per-problem checks retain
66 of the original 256 training questions. The shared-key search reached its
predeclared two-million-pair ceiling. It found valid witnesses, but did not
establish total block capacity. No model was trained or evaluated in this round.

## Motivation and prior failures

C007 found no 2+2 family allocation among the four stored paths. C008 recovered
hidden support by enumerating all ordered legal solutions: 131 questions admit
eight distinct numeric AC classes, four per identity category. Those findings
separate inventory selection from mathematical support. C009 asks which of
those candidates survive the remaining exact matching requirements.

Earlier engineering failures matter here. C004 required original tokenizer
bytes, not a reserialized checkpoint tokenizer. C001/C002/C005 showed that
apparently strict matching can create a narrow selected task or fail to supply
enough blocks. Accordingly, this attempt preserves the original inputs and
targets, verifies tokenizer bytes, measures each loss separately, and does not
lower K or enlarge the pool after seeing outcomes.

## Frozen design and provenance

The [protocol](../docs/experiments/C009_token_structure_block_matching.md),
[configuration](../configs/diagnostics/family_matching_v1.json), matching code
and 18 passing synthetic tests were published at
**`cb2bcedce36f78ae593ce979677e4199aeda26ee` before execution**. Use that commit
for the pre-outcome protocol; later journal text appends results. Recorded source
bytes remained unchanged through the execution.

The input is the C008 archive of 25,846 ordered legal solutions on the same
256 training questions. Original Qwen2.5-1.5B tokenizer files at revision
`8faed761d45a263340a0528343f099c05c9a4323` passed pinned Git-blob and size checks.
The exact original prompt and canonical trace include supervised terminal EOS,
with a 384-token sequence ceiling and no truncation. All 25,846 rows encoded.

Each retained question must support four different AC classes in each family,
eight different classes jointly, four structures within each family, and one
common supervised response length for all eight paths. Different questions may
have different lengths. A four-question block shares the same pair of family
structure tuples. Four accounting cells combine family and Paths/GCM allocation.
These cells are not a new approved GPU experiment.

## Measured retention

| Completed per-problem stage | Retained / original 256 | Loss from preceding stage |
|---|---:|---:|
| Raw disjoint AC 4+4 | 131 | 125 lack the initial support |
| Encodable disjoint AC 4+4 | 131 | 0 |
| Common EOS-inclusive length within question | 67 | 64 |
| Four distinct structures per family plus eight distinct classes | 66 | 1 |

Ordered 4+4 support alone is 132/256 and is not interchangeable with the
131/256 disjoint-AC count. The archive contains 10,155 problem/AC classes,
including 112 mixed-label classes. The per-problem stages are complete;
the subsequent global search is not.

The 66 survivors are an upper bound on shared-key participation under these
constraints. Even ideal packing could use at most 64 of them in four-question
blocks. The original 256-question design remains infeasible under fixed K=4.
This is not permission to train on a newly reduced dataset.

## Bounded shared-key search

Complete frequent-tuple enumeration produced 24,324 identity-present and 1,991
identity-absent tuples: a Cartesian grid of 48,429,084 pairs. The search checked
exactly **2,000,000 pairs** and stopped with `key_pair_checks_cap`. It used
75,126 structure-search nodes, examined 206,387 exact slot assignments and
retained 681 fully checked keys. The source reports
`incomplete_shared_key_search`, not exhausted or infeasible.

Those discovered keys collectively involve **seven questions**. Greedy packing
constructed **one four-question block**. Seven is a discovered lower bound on
participation, not its total or upper bound; the greedy block is a constructive
lower bound on packing, not a maximum. Lexicographic truncation can distort
which questions are found. The two-million checks cover only 4.13% of the
Cartesian grid; neither wall-time headroom nor a positive witness justifies
silently increasing the prespecified cap within C009.

The full attempt took **23.081 local CPU wall seconds**: 20.617 for input
verification/tokenization, 0.455 for per-problem/policy checks and 0.826 for
key search; the remainder includes serialization and output preparation.
Actual timings are measured here, not estimates of a larger search.

## Policy emulations and what they resolve

| Prespecified inventory policy | Ordered rows | Problem/AC classes | Mixed-label classes | Common-length questions | Structure-feasible questions |
|---|---:|---:|---:|---:|---:|
| Full inventory | 25,846 | 10,155 | 112 | 67 | 66 |
| Surface eligibility alone | 25,846 | 10,155 | 112 | 67 | 66 |
| First representative alone | 11,706 | 7,906 | 53 | 64 | 64 |
| First 12 structures alone | 23,093 | 8,713 | 112 | 57 | 56 |
| Surface → first representative | 11,706 | 7,906 | 53 | 64 | 64 |
| Surface → first representative → first 12 | 10,128 | 6,681 | 53 | 56 | 56 |

The first-representative policy also reduces raw disjoint support from 131 to
88 questions. The policy has a large effect before token matching but only a
two-question additional structure loss relative to the already token-selected
full inventory. These nested quantities answer different questions.

Surface eligibility causes **no additional loss on this complete inventory**.
It should not be blamed for C009's observed narrowing. The first-12 structure
cap removes ten of the 66 structure-feasible questions. Policies are deterministic
controlled emulations on the same complete inventory, not a replay of the old
solver's first-found ordering. Serial losses are conditional, not additive
independent causal contributions.

## Schedule witnesses, residuals and selection

The single constructed block has four updates and 16 presentations per cell,
1,024 supervised tokens, 1,824 processed nonpadding tokens, and zero padding.
Within each family, each update has identical Paths/GCM structure coverage.
Each question sees four AC-distinct paths in Paths and one repeated path in GCM.
The four cells share question order and token budgets. These tiny schedules
prove an accounting construction only; there is no accuracy or training result.

The two families have different operator distributions and numerical features.
For example, the identity-present witness has 0.25 negative nonroot operation
results per scheduled presentation and mean operation depth 2.75; the absent
family has zero and depth 3. The absent family still computes intermediate ones
(including division of equal expressions), so the declared identity label does
not establish nondegenerate reasoning or distinct semantic strategies.

Selection is material: all target values at least 41 disappear at the common-
length stage. Of 131 raw-support questions, 41 had targets at least 41; all 67
length-matched survivors have targets at most 40. All seven discovered questions
and all four preview questions contain input one, versus 15/66 complete
structure-feasible questions. The latter is partly a truncated-search selection,
not evidence that input one is mathematically necessary. See the
[independent scientific review](C009_SCIENTIFIC_REVIEW.md).

## Independent verification

A separate verifier rechecked all **25,846 expressions and their exact token
serialization**, all 256 questions' Hall/NetworkX flow stages, all six policy
variants, all **4,491 question-level eight-slot witnesses** across 681 discovered
keys, and the four-cell block schedules. It passed in **21.554 seconds**; see
[the immutable verification receipt](family_matching_20260909_r1/independent_verification.json).
All 37 focused synthetic tests (14 matching, four orchestration and 19 independent
verification) passed. The verifier uses an independent bounded AST/Fraction evaluator and a separate
flow implementation. It did not re-enumerate the global key grid and therefore
does not turn C009's incomplete search into a complete result.

The first verification-adapter attempt rejected an execution-source whitelist
entry before checking inventory; the adapter was corrected and the successful
run followed. This is a verifier integration failure, not a failed scientific
matching run. Neither original outputs nor search caps were changed.

## Decision and next step

Do not open a GPU server or train this four-question preview. The current result
identifies **exact per-question token matching as the largest measured additional
loss**, while the truncated key join leaves total group support unresolved.

A separate CPU-only attempt should freeze a complete key-join method and its
work bounds, compare it against exhaustive small fixtures, retain per-question
support and selection summaries, and distinguish complete key coverage from
maximum disjoint packing. Grouping identical problem-support masks and skipping
provably disjoint pairs can avoid repeating equivalent intersections. A changed
search is a new engineering attempt with its own source and receipt, not a new
scientific mechanism or a retroactive completion of C009.

Only after that result should a concrete design address sample size, retained
population, numerical residuals, a defensible path-family concept and uncertainty.
No additional seed/model grid repairs the present selection and concept gaps.
Earlier seed17/23 findings and adverse broader-dev outcomes remain unchanged.
The reserved holdout stays untouched. GPU accounting remains **4716/7200 used,
2484 remaining**; this CPU attempt adds zero GPU process-seconds and requires
no storage expansion.

## Artifacts and reproduction

- [Immutable summary and provenance](family_matching_20260909_r1/summary.json)
- [Per-question retention](family_matching_20260909_r1/per_problem.jsonl)
- [Policy emulations](family_matching_20260909_r1/policy_emulations.json)
- [Block schedules and full records](family_matching_20260909_r1/block_witnesses.json)
- [Discovered-key index](family_matching_20260909_r1/shared_key_index.json)
- [Lossless key/record catalog](family_matching_20260909_r1/shared_key_catalog.json)
- [Catalog reconstruction and original-byte hashes](family_matching_20260909_r1/shared_key_storage.json)

The original 72,820,255-byte shared-key JSON repeats full records. Its
904,602-byte public catalog interns 260 unique records and reconstructs the
original object and exact sorted/indented bytes; the original hash is retained.
The full local JSON and its private gzip are preserved outside Git tracking.
The private tokenized inventory has published hashes and can be reproduced
from the fixed census plus the official tokenizer. Neither weights nor private
connection details belong in this repository.

Run the frozen diagnostic in a fresh output directory:

```bash
python -m scripts.audit_family_matching \
  --archive <C008-solutions.jsonl.gz> --tokenizer <official-snapshot> \
  --out <fresh-report-dir> --private-out <fresh-private-dir>
```
Never overwrite C009's actual incomplete attempt or silently rerun it with
higher limits. The independent verification receipt records its own scope;
verification of discovered witnesses does not prove exhaustive key discovery.

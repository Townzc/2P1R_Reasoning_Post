# C013 — Compact exact occurrence-mask completion

**Registered 2026-09-09 UTC before C013 real-inventory execution.** This is a
new CPU algorithmic attempt to finish the unchanged C009 common-length question.
The C012 identity-absent training candidate is already fixed separately; C013
does not select its family, dataset tier, or outcome using a new yield.

## Observed failure and fixed question

[C010](C010_complete_support_join.md) ran at
`21090e3511243d45b4ad605e924c730ff4b480eb` and stopped at its 600-second deadline.
Its [summary](../../reports/complete_join_20260909_r1/summary.json) and
[join receipt](../../reports/complete_join_20260909_r1/join.json) record:

- 48,429,084 total candidate pairs; 37,104,680 conservatively pruned plus
  10,653,296 exact decisions, leaving 671,108 pairs unrepresented.
- 528,669 valid keys, 53 exact-support groups and 53 participating questions
  among the completed decisions; these are different units despite the equal
  last two numbers.
- A 7,697,969,832-byte uncompressed key stream and 614,821,423-byte gzip archive.
  Each key repeated its question/path witnesses. The twelve-block packing and
  bound apply only to discovered groups; global optimality was not established.

C013 changes the computation and representation, keeping the **600-second**
join deadline. C010's code, limit, output, partial counts and archive remain
unchanged. This is not a higher-cap retry inside C010 or new scientific evidence
about model learning. Its question is the complete feasible-key inventory and
packing capacity of the original construction.

Use the same verified C009 tokenized archive of 25,846 ordered solutions,
original 256 training questions/targets, tokenizer, renderer, identity labels,
and K=4. Reuse the complete per-problem flow-eight necessary filter, reproducing
**5,774 records and 66 questions**, with the same eligible common supervised
lengths. The archive byte digests and original training-input digest remain
those registered in C010. Do not retokenize, recruit questions, change targets,
or consult model/development/holdout outcomes. Different questions may still
have different L_i; all eight paths for one question must share L_i.

## Exact reduction and a checked precondition

Implement the new producer in
[`src/path_family_matching_compact.py`](../../src/path_family_matching_compact.py)
and run it through
[`scripts/run_compact_join.py`](../../scripts/run_compact_join.py).

Before using the reduction, verify across the supplied fixed matching inventory
that every `(problem ID, numerical AC class)` maps to **one operator-only
structure**. Reject the attempt if this property fails; do not treat it as zero
support or use the shortcut without its precondition.

With four distinct structures in each family, each structure appears in at
most two of the eight slots. The checked property prevents an AC class from
competing between different structures. Thus the matching graph decomposes
into components of one slot or two slots. A single slot needs a nonempty class
set. Two slots for a shared structure require nonempty family sets and a union
containing at least two classes, the complete two-slot Hall condition.

Index occurrences by `(problem ID, supervised length)`. For each family and
structure build its occurrence bitset. For each structure shared by the families,
precompute the occurrence bitset where the two class sets satisfy the two-slot
condition. A structure-pair key's **exact** feasible-occurrence bitset is the
intersection of its eight slot-presence masks and all compatibility masks for
its shared structures. This replaces repeated general matching with integer
intersections; it preserves eight-class distinctness and same-length support.
Different lengths never create additional problem identities.

Project each exact occurrence bitset to its complete participating-problem set
and lowest feasible L_i per problem. A cache keyed by this exact bitset is safe;
a conservative support mask alone is not an exact-feasibility cache key.
Use fixed 65,536-entry limits for optional overlap/projection caches; after a
cache fills, uncached decisions are still computed. These limits affect runtime,
not search completeness or retained keys.

## Finite enumeration, completeness and witnesses

Enumerate each family's four-structure tuples using sorted structure IDs and
safe conservative problem masks. Group tuples by these masks only to count and
prune whole group products with fewer than four possible distinct problems.
All other tuple pairs receive the exact occurrence-mask calculation above.
Tuple IDs are their positions in the complete lexicographic tuple catalogs;
mask groups use increasing integer masks and tuple IDs use increasing order
within each group.

The same finite grid must contain 24,324 identity-present tuples and 1,991
identity-absent tuples. Require:

```
pruned_pairs + exact_pairs = represented_pairs = 48,429,084
unrepresented_pairs = 0
```

Count a valid key only after its compact output callback completes; an
interrupted decision must not be counted twice. Retain stop stage, cursor and
counters. A cursor is an audit position, not a standalone resumable state.
The deadline covers indexing, enumeration, synchronous key output and final
representative-witness construction. Report actual elapsed time; pure-Python
checks cannot preempt one atomic operation already in progress.

After classifying the full grid, choose the lexicographically smallest
structure-pair key for each exact-support set. Construct its explicit eight-path
witnesses using the prior augmenting matcher, independently cross-checking the
mask classification for every representative problem. A disagreement fails
the attempt. Set overall `complete` only after both the grid and these witnesses
finish within the bound. If a stop leaves representatives unavailable, preserve
their tuple/length-signature identifiers and mark them unavailable; skip the
planned global packing rather than fabricate paths.

## Compact output contract

Every valid distinct key remains represented in a fresh private JSONL gzip
stream, but each line is only:

```
[identity_tuple_id,nonidentity_tuple_id,length_signature_id]
```

The producer's `compact_key_bytes` defines the exact ASCII JSON-array/newline
bytes. Preserve compressed and uncompressed SHA-256 digests and byte counts.
Publish `catalog.json` containing sorted problem and structure IDs, each family's
tuple catalog as four structure indices, and length signatures as sorted
`[problem_catalog_index, lowest_common_length]` pairs. Together these tables and
the stream recover every key's structures, exact support and lowest lengths.
The immutable tokenized inventory supplies its candidate records; no solution
or support is discarded by omitting repeated full responses.

Publish `support_groups.json` with each exact support set's total valid-key count,
smallest key, and explicit representative witnesses using canonical record
SHA-256 references. Support-set counts are not structural-key counts. Only
representatives need repeated slot metadata; all other witnesses can be
reconstructed from the frozen inventory, catalogs and declared matcher.
Publish compact join, packing and selection receipts separately. Refuse existing
output paths and check all declared source bytes before and after execution.
Record the new prepublished commit; neither earlier commit is C013 provenance.

## Checks, packing and interpretation

At registration preparation, **13 synthetic compact-core tests passed**, including
ten randomized small complete grids against the original naive matcher. Checks
cover shared-class conflicts, different per-problem L_i, cross-length false
support, violated AC-to-structure functionality, product accounting, decoded
catalog/stream equality, deterministic representatives, deadline receipts and
the explicit augmenting-witness cross-check. C013 real-inventory execution and
independent complete-output verification are still pending.

After a complete join, use the existing `pack_support_groups` with **SciPy 1.18.0**
and a separate **60-second** limit. The C010 binary question/group assignment
and integer block-count formulation is unchanged: each question is used at
most once and each group's assignments equal four times its block count.
Preserve and validate primal solutions, dual bounds, gaps and solver status.
Do not report global optimality after an incomplete join or a solver outcome
without the required certificate. Expand record references only for the
explicit chosen blocks and validate their common lengths.

Describe original, raw, common-length, flow-eight, complete shared-support and
packed populations using the fixed selection descriptors. A complete population
can still be restricted by target, input 1, templates or operator composition.
The numerical identity families remain trajectory properties, not semantic
strategies. Neither faster enumeration nor larger support demonstrates a model
effect or removes these selection concerns. No GPU job, server connection or
change to C012's already registered training gate occurs in C013.

**Execution commit, complete real-inventory counts, compact archive receipts,
independent verification and packing outcome: pending.** Append actual results
after the new source is published and executed, preserving this registration.

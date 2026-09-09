# C010 — Complete the original shared-support join

**Entry date:** 2026-09-09 UTC. **Status at entry:** implementation and registration
preparation, before C010 real-inventory execution. **Type:** CPU algorithmic
completion of the fixed C009 question; no model training or evaluation.

## Question, motivation, and competing explanations

[C009](C009_token_structure_block_matching.md) completed the per-problem checks
but stopped its shared-key search at its prespecified 2,000,000-pair cap.
Its [saved summary](../../reports/family_matching_20260909_r1/summary.json)
contains 681 discovered valid keys, seven participating problems, and one
four-problem schedule preview. These findings do not establish total support.

C009 already enumerated 24,324 identity-present structure tuples and 1,991
identity-absent tuples, giving **48,429,084** candidate tuple pairs. Thus its
checked prefix was 4.13% of a known finite grid. The remaining uncertainty is
whether the small discovered population reflects genuinely sparse shared
support, unvisited keys, or both. Separately, even a complete support inventory
may admit more disjoint blocks than a greedy construction finds.

C010 tests these computational alternatives without changing the family
definition, eligible inputs, K, token matching, or structural constraints. More
keys or a larger packing would be a feasibility result, not a new learning
effect, a semantic mechanism, or evidence that the new population is unbiased.
The [C009 scientific review](../../reports/C009_SCIENTIFIC_REVIEW.md) motivates
this distinction and the accompanying selection descriptions.

## Fixed inputs and unchanged matching rule

Use the same 256 original training questions, targets, and prompts from
`runs/pilot_v1_20260908_r3/train_blocks.json`, SHA-256
`e15857122ad9148a1a209cce7c8ef4c107ff0de27bcfe11b97ba6fce6b7a2cea`.
The full C008 inventory contains **25,846** legal ordered solutions. Its
compressed SHA-256 is
`42c00622cdf8e9953d50f4a5c781b28e054198dff72915524577fe5a6407f5ef`;
its uncompressed stream SHA-256 is
`fa0563f030ffaa810f23e4eb5e9c63a2e12096f2dc675128a9bd9a9362c338d8`.

C009 executed at `cb2bcedce36f78ae593ce979677e4199aeda26ee`. Reuse its verified
tokenized inventory with compressed SHA-256
`ba890778096197a3f9683cf6d6b4a4675dcc930ff41c5e8ec977ab84611c8ed0`
and stream SHA-256
`4302986b7f74c390ed740720715326e3e3db422649031204ab131dae55e0e58e`.
Keep the pinned Qwen/Qwen2.5-1.5B base tokenizer revision
`8faed761d45a263340a0528343f099c05c9a4323`, canonical trace renderer,
response-only supervision including terminal EOS, and 384-token sequence limit.
Verify immutable source/input/tokenizer provenance rather than accepting a
similarly named local file.

Apply the same complete per-problem necessary filter as C009: retain only
problem/length options admitting flow eight, with four different operator-only
structures per family and eight numerical AC classes distinct across families.
C009 already recorded **5,774 retained records from 66 problems**. Reproduce
and assert that filter before joining; a mismatch invalidates this attempt
rather than authorizing a different pool. This is a reuse of a complete necessary
condition, not a selection based on C010 outcomes.

Run `complete_supported_key_join(..., length_mode="common")` from
[`src/path_family_matching_complete.py`](../../src/path_family_matching_complete.py).
Each problem's eight selected responses must have the same supervised length
L_i. Different problems may have different L_i. Each family uses four distinct
operator-only structures, the two families may have different structure tuples,
and all eight selected numerical AC classes remain distinct. A shared key fixes
the two structure tuples across at least four distinct problems. Numerical
identity labels retain the original exact evaluated-tree definition; they are
not semantic-strategy labels.

## Complete finite join and accounting

The new algorithm groups each family's frequent four-tuples by identical
conservative problem-support masks. A mask unions a feature's support across
lengths and therefore only bounds possible support. Generate frequent tuples
with the same safe at-least-four-problem pruning as C009. Sort problem IDs,
structure IDs, and structure tuples lexicographically. Sort mask groups by
their nonnegative integer mask; visit identity groups, absent groups, identity
tuples, and absent tuples in that fixed nested order.

For a pair of groups whose mask intersection contains fewer than four distinct
problems, prune its whole Cartesian product and add that product's multiplicity
to `pruned_pairs`. For every other distinct tuple pair, test each candidate
problem at its lengths in ascending order using the exact eight-slot AC
assignment. Retain its lowest feasible common length and the deterministic
C009 class witness. Equal masks alone never justify reusing another tuple
pair's AC feasibility result.

Count only completed tuple-pair decisions in `exact_pairs`, including decisions
that no valid key exists. A pair interrupted during exact verification is not
counted or emitted. The complete result must satisfy:

```
represented_pairs = pruned_pairs + exact_pairs
represented_pairs = 24,324 * 1,991 = 48,429,084
unrepresented_pairs = 0
```

Record family tuple counts, mask-group counts, structure-prefix nodes, group-pair
checks, pruned group products, begun/completed exact decisions, slot-assignment
checks, all valid-key counts, and timing. This accounting is necessary for
completeness; finding many keys is not a substitute.

Allow **600 seconds** for this join, including its indexing/grouping work and
synchronous key output. There is **no C009 2,000,000-pair limit** in C010. Do not
initiate new checks or output commits after the deadline. An atomic matching or
output operation cannot be preempted by the pure-Python core; report actual
elapsed time and mark a detected overrun incomplete. Preserve a stop reason,
counters, and deterministic audit cursor. The cursor is not a self-contained
resume checkpoint: earlier stream/state must also be retained. Do not quietly
retry a capped run or present partial support as an upper bound.

This is a separately published algorithm and registration. C009's program,
config, two-million cap, and output remain unchanged. Record C010's own
prepublished execution commit and hashes; the C009 commit above is input
provenance, not a claim that C010 already ran there.

## Compact outputs and independent checks

Stream **every valid distinct structure-pair key** into a new private JSONL gzip
archive. Serialize each line with the module's `canonical_json_line`: sorted-key,
ASCII-escaped JSON, UTF-8 bytes, one final newline. Preserve the complete stream
and publish its uncompressed SHA-256, compressed SHA-256, byte sizes, valid-key
count, and source/input hashes. Use fresh paths and refuse to overwrite prior
artifacts. I/O or archive-validation errors invalidate the affected output.

Each compact witness identifies its problem, common supervised length, and eight
family/structure/AC slots. A slot's `record_ref` is `record_reference(record)`:
SHA-256 of that validated record's canonical JSON without a final newline.
Resolve references against the verified tokenized inventory before constructing
any schedule. Do not duplicate full responses for every key.

Group keys by their **exact sorted participating-problem tuple**, storing the
number of valid keys and the lexicographically smallest structure-pair key with
its witnesses per group. These support groups are not the number of distinct
structural keys; keep both counts. Every valid key remains in the full stream.
Under the current hard constraints, two keys with the same exact support set
offer the same possible four-problem subsets, so one representative preserves
packing possibilities. This equivalence does not assert that their numerical
or linguistic features are interchangeable for science.

At registration preparation, **30 synthetic tests passed**: 16 tests in
`tests.test_path_family_matching_complete` plus 14 existing C009 matching-core
tests, run with:

```
python3 -m unittest tests.test_path_family_matching_complete tests.test_path_family_matching -q
```

They include equality with complete naive C009 keys on small inventories,
different L_i across problems, cross-length false support, mixed AC conflicts,
identical masks with different AC feasibility, full group-product accounting,
stream hashing, deterministic representatives, and interrupted-pair accounting.
This is an implementation check, not an executed real-inventory C010 result.
Record any subsequent wrapper, source-integrity, or independent-verifier checks
with their actual commands and outcomes; none are presumed complete here.

## Disjoint packing: a separate bounded optimization

Only after complete key generation, formulate exact packing over its distinct
exact support groups with **SciPy 1.18.0** MILP. Record the observed library and
solver environment. Keep the declared support-descending/lexicographic greedy
packing as a reproducible constructive comparison.

For each group g and supported question q, introduce binary assignment x_gq.
For each group introduce integer block count b_g, with
`0 <= b_g <= floor(|support_g| / 4)`. Require:

```
for every q:  sum_g x_gq <= 1
for every g:  sum_q x_gq = 4 * b_g
maximize:    sum_g b_g
```

Set a separate **60-second MILP time limit**. This formulation permits multiple
blocks under the same key and forbids reusing a question across groups. Sort
each group's assigned questions and partition them into groups of four for
explicit witness validation. Report the primal objective/assignment when
available, solver status, dual bound, MIP gap, elapsed time, and whether a limit
was reached. Independently check integrality, all constraints, distinctness,
and the resolved eight-path witnesses before accepting any primal solution.

A feasible time-limited primal solution is a lower bound; its verified dual
bound is an upper bound. Do not label the packing maximum without an appropriate
optimality certificate. If support generation is incomplete, defer this planned
global packing conclusion; any calculation restricted to discovered groups
must be labeled accordingly. The earlier flow-eight stage already supplies the
necessary ceiling of 16 blocks/64 selected problems, not a guarantee that they
can all be packed.

## Selection descriptions and subsequent decisions

Describe the original 256-question pool and every matching stage, the complete
shared-support population, and the actual selected blocks. Include problem IDs,
retention denominators, input-1 frequency, target distribution, consecutive-pair
and preview-template concentration, and available operator/intermediate-value
features. Distinguish witness-level and scheduled-presentation distributions.
These are descriptive selection diagnostics; do not change the matching rule
after seeing them to remove an inconvenient residual.

The current four-problem preview remains a CPU accounting witness with no model
outcome. Neither one block nor a large count of overlapping keys justifies a
GPU experiment. A training proposal must separately state the target population,
independent question/block count, paired seeds, dose, primary outcome, and
remaining confounds.

C011 is a separate **per-problem 2×2 diagnostic** of length equality and
structure requirements. Although the new module's `per_family` join branch has
synthetic tests, **no full per-family shared-key join is planned in this attempt**.
The prospective C012 identity-absent Paths/GCM comparison addresses a single
within-family allocation effect; it need not require another four identity-
present paths for the same problem. That candidate must have its own registration
and feasibility checks. C010 must not be repurposed after execution to choose
which family or model result looks favorable.

## Execution and result record

**C010 execution commit, real-inventory outputs, complete support counts,
packing certificate, and interpretation: pending.** Append the actual outcome
and links after execution, retaining the pre-outcome design above. An invalid
artifact, deadline, or solver cap is a result to preserve, not permission to
rewrite the limits or declare mathematical impossibility.

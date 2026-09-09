# C009 — Token, structure and shared-block matching loss

**Entry date:** 2026-09-09 UTC. **Status at entry:** protocol preparation,
before this diagnostic's real-inventory matching outcomes. Earlier pilot,
seed23 and C008 outcomes motivated this entry. This is a local CPU diagnostic
under [P002](P002_legal_support_enumeration_design.md), not a training dataset
release, GPU registration or authorization to change the problem pool.

## Question and scope

How much of C008's legal path-family support survives exact supervised-token,
within-family operator-structure and four-problem Latin-block constraints?
Separately, how much support would three explicitly specified inventory-selection
policies discard? A complete negative result is useful; a search limit is not a
negative result.

C008 already established that only **131/256** original training problems have
disjoint numeric-AC 4+4 support, before token or structural matching. The full
256-problem four-cell design is therefore infeasible under this fixed rule;
131 is an upper bound on candidate problems, not a ready training set. Even
before later filters, at most 128 of those problems can fill disjoint four-problem
blocks. This entry measures the additional losses without silently reducing K,
changing targets or recruiting replacement problems.

## Fixed inputs and tokenizer validation

Use only the 256 original training questions, prompts, targets and identities
in `runs/pilot_v1_20260908_r3/train_blocks.json`, with SHA-256
`e15857122ad9148a1a209cce7c8ef4c107ff0de27bcfe11b97ba6fce6b7a2cea`.
Use all **25,846** ordered legal solution records from C008's complete private
archive, not just its allocation witnesses or one AC representative. Before
matching, reconcile problem coverage and record counts, and verify both archive
digests against [C008's summary](../../reports/legal_support_census_20260909_r1/summary.json):

| Archive representation | SHA-256 |
|---|---|
| Compressed bytes | `42c00622cdf8e9953d50f4a5c781b28e054198dff72915524577fe5a6407f5ef` |
| Uncompressed bytes | `fa0563f030ffaa810f23e4eb5e9c63a2e12096f2dc675128a9bd9a9362c338d8` |

The census executed at prepublished source
`b504cb7b604847b2155bb71dd2bb2c3602d9f371`; this is C008 provenance, not the
future C009 execution commit. Record C009's own prepublished commit, clean/dirty
state and hashes of its protocol, config, implementation and inputs when it runs.

Use the official **Qwen/Qwen2.5-1.5B base** tokenizer at
`8faed761d45a263340a0528343f099c05c9a4323`, as pinned by
`configs/models.lock.json`. Before using tokenizer output, validate the complete
local `tokenizer.json`, `tokenizer_config.json`, `vocab.json` and `merges.txt`
bytes against the pinned sizes and Git blob identities. Record ordinary SHA-256
digests as well. A file's name or apparent vocabulary size is not byte validation.
No model weights or inference are needed.

Use the original training prompt and `src.sft_data.encode_row` serialization:
`Problem: {prompt}\nSolution:\n`, canonical `render_trace(tree)` response,
response-only labels and one supervised terminal EOS. Preserve prompt/response
boundary validation. The total sequence limit is **384 tokens**; do not truncate,
add meaningless tokens or change rendering to repair a mismatch. Count any
length exclusions explicitly. A tokenizer, archive, label, input-resource or
target-validation failure makes the affected diagnostic invalid/incomplete;
it must not be interpreted as absent mathematical support.

## Fixed family, distinctness and block constraints

The four cells are `identity_present_paths`, `identity_present_gcm`,
`identity_absent_paths` and `identity_absent_gcm`. They are not the old
Repeat/Surface/Paths/GCM four arms.

Keep the existing identity convention: multiplication with an evaluated operand
one, division with denominator one, addition with an evaluated operand zero,
or subtraction with right operand zero. Evaluate the ordered tree with exact
fractions before AC grouping. Numerical identities can legally consume a
required input or a computed zero/one in Countdown. These families are not
semantic-strategy labels, and identity-present is not equivalent to Surface.

For every retained problem require all of the following simultaneously:

1. **K=4 paths per family**, from **eight different numeric-leaf AC classes**
   across the two families. A mixed-label AC class can occupy only one slot.
   Concrete-number AC IDs flatten/sort only associative/commutative `+` and `*`.
2. Each family's four paths have **four different canonical operator-only
   structures**. This is the existing AC structure representation, not the full
   ordered execution tree or a semantic strategy taxonomy.
3. All eight canonical responses have the same EOS-inclusive supervised length
   **L_i for that problem**. Different problems may have different L_i. Do not
   add the old matcher's stronger common-length-across-problems restriction.
4. Each four-problem block shares a pair of structure four-tuples
   **(S_identity, S_noidentity)**. The two tuples may differ. Both families use
   exactly the same four problem identities; their feasible L_i may differ
   between problems, but never between cells for the same problem.

Keep a representative for every `(problem, family, L_i, structure, numeric AC
class)` option. Within that exact key, deterministic expression ordering may
choose a witness because all hard constraints in this diagnostic are unchanged;
the complete ordered inventory remains available. Never reduce the main
inventory to one row per structure before testing family support. Additional
numerical attributes are measured residuals, not additional matching keys here.

## Nested matching-loss sequence

Report denominators and problem IDs at each stage, retaining both original-pool
and previous-stage denominators. Separate a fully checked infeasible problem
from one whose computation is incomplete.

| Stage | Required support |
|---|---|
| Raw disjoint 4+4 | Eight distinct AC classes assignable to the two families; reproduce C008's 131/256. Report ordered 4+4 separately, without substituting it for this rule. |
| Common L_i | At some supervised length, eight different AC classes can still fill four slots per family; no four-structure requirement yet. |
| Flow eight | At some L_i, four distinct structures per family and eight distinct AC classes are simultaneously assignable. |
| Exact shared key | A feasible pair `(S_identity, S_noidentity)` is shared by at least four distinct problems. Report all discovered keys and participating problem IDs, with completeness status. |
| Greedy disjoint blocks | Select explicit four-problem blocks from these feasible keys without reusing a problem. This is a constructive lower bound on maximum packing. |

The per-problem structure check can use an integral maximum-flow network:
source to each family (capacity four), family to its structure nodes (capacity
one), structure nodes to eligible numeric AC class nodes, and each class to the
sink (capacity one). Only rows at that L_i create edges. Flow eight supplies an
actual eight-class witness; the shared class capacity handles AC-mixed conflicts.
Run the complete check for each finite candidate length before calling a problem
infeasible. Equivalent complete matching implementations must preserve these
constraints and provide independently checked witnesses.

Generate feasible structure-pair keys using deterministic, sorted candidate
orders. Before building support masks, discard only problem/length pairs that
failed the complete flow-eight check; no true shared key can use such a pair.
Record this necessary-filter input size separately from the full inventory. A key must retain valid per-problem lengths and eight-path witnesses;
intersecting separate family support counts is insufficient. Different lengths
for one problem do not create different problem identities. A key's support
counts each problem once. Complete generation with no key supported by four
problems proves no block under this specified construction. Partial generation
can certify a found block but cannot prove absence.

Greedy packing visits feasible structure-pair keys by descending static support
count, breaking ties by lexicographic `(S_identity, S_noidentity)` order. For
each key, take groups of four unused problem IDs in ascending order and mark
them used; leave any remainder available to later keys. Do not dynamically
re-sort keys after each selection. Use a deterministic valid witness for each
selected problem/key. A greedy
shortfall is not proof that a larger packing is impossible, even if the key
inventory is complete. Report candidate-key support/participation separately
from selected block counts and unselected IDs.

## Search limits and schedule checks

The frozen config is
[`configs/diagnostics/family_matching_v1.json`](../../configs/diagnostics/family_matching_v1.json).
The execution wrapper must load and strictly enforce all of its keys, including
schema version, instead of silently replacing settings with runtime defaults.
For the main key search, allow at most **2,000,000 structure-DFS nodes**,
**2,000,000 key-pair checks** and **600 seconds**. The two work counters apply
cumulatively across the entire key search, not separately to every problem.
Record counter definitions, counts, elapsed time and the exact stopping reason.
Reaching a limit before exhaustion means `incomplete`; do not retry with higher
limits inside this entry. Tokenizer/inventory validation and complete per-problem
checks have separate recorded timings; the 600-second limit is for key search.

For every constructed block, verify **one cycle of four updates**, four problems
per update, **microbatch size two**, with **assignment seed 17**. Sort each
structure tuple and the block's problem IDs before seeded assignment. Within
each family, choose a permutation assigning one structure index to each problem;
use the same seeded index assignment across the two families. Paths rotates
indices across the four rounds while GCM repeats the assigned path. Thus each
family's Paths and GCM have the same one-of-each-structure histogram at every
update, while each problem sees four distinct paths versus one repeated path.

All four cells must have the same ordered problem sequence, per-example
supervised tokens, presentation counts, update counts and microbatch boundaries.
Audit processed nonpadding and padding tokens too: identical prompt and response
lengths for corresponding examples make these budgets identical across cells.
Do not assume padding is zero when L_i differs between problems. One cycle gives
16 presentations per block in each cell; it is an accounting witness, not a
chosen GPU training duration or published training dataset.

## Prespecified inventory-policy loss simulations

These CPU simulations measure selection loss, not four additional model arms.
Do not impose their restrictions on the main full-inventory diagnostic. Report
each policy separately against the full encoded inventory and also report the
fixed cumulative sequence **Surface → first representative → first 12**.
Rerun only the complete per-problem stages above for these alternatives; do not
repeat block search or choose a policy using its observed yield.

- **Surface eligibility:** retain a canonical row only if all four existing
  `src.pilot_data.SURFACE_FRAMES` renderings meet the sequence limit and have
  exactly the same supervised length as its canonical response. This tests the
  old eligibility requirement; Surface is not a cell of this proposed design.
- **First representative:** for each `(problem ID, L_i, structure)`, keep the
  first row sorted by `(numeric AC class, expression)`, without conditioning
  this choice on family. This deliberately tests the old selector's potential
  to discard family/class options; it is not the main inventory representation.
- **First 12 structures:** for each `(problem ID, L_i)`, retain only the first
  12 lexicographically sorted structures and all rows belonging to them in that
  simulation's input. Apply the same rule independently and at its stated
  cumulative position, and do not select a different cap after seeing yield.

Report retained ordered-row, class and per-problem support counts, including
AC-mixed options lost by each policy. The serial losses are conditional on prior
filters, not independent causal contributions. The policies' complete checks
can establish feasibility or failure under that policy; a loss relative to the
full inventory is a selection effect within this fixed encoded dataset.

## Numerical residuals and interpretation

Describe selected witnesses and actual scheduled presentations separately.
Report identity-event counts, nonroot intermediate zero/one/negative/fractional
counts, ordered-tree depth, maximum absolute nonroot intermediate magnitude,
and operator histograms. The two nonroot operation results exclude input leaves
and the final target; fractional means a reduced denominator other than one;
depth counts operation levels with leaves at zero. Keep exact rational values
where applicable. If no block is found, mark scheduled residuals unavailable
rather than filling them with zero.

Within each family, Paths/GCM operator-structure coverage is controlled at every
update. Cross-family structural/numerical differences are measured and disclosed,
not automatically matched. The identity-present family can also differ in the
number and position of identity events. These residual descriptions do not make
the between-family contrast an identity-only causal intervention, establish
model difficulty equality or demonstrate a mechanism. Some path-property
differences can be part of the allocation treatment; do not add post hoc
constraints merely to remove a measured residual.

## Decision and completion record

- Invalid bytes, tokenizer/source mismatch, witness verification failure or
  incomplete search: preserve the failure and bounded evidence; do not declare
  mathematical impossibility or silently relax constraints.
- Complete absence at a stage: reject that construction on this fixed pool,
  exact serialization and grammar. State which earlier stage still had support.
- Found blocks: record validated witnesses, retention and residuals; proceed
  only to a separate concrete sample-size/selection/uncertainty and resource
  proposal. Finding one block is engineering feasibility, not statistical
  adequacy or authorization to train.

Do not read new model predictions, development or reserved holdout results;
launch GPU work; alter K, targets, the tokenizer or the selected problems; or
increase storage for this local diagnostic. Existing model outcomes motivated
the design and remain distinct from this CPU feasibility evidence. Preserve
fresh immutable attempt outputs, exact source/config/input hashes, environment
versions, validation checks, all limits, failures and realized accounting.

**Results at entry: pending.** Append the executed source commit, completeness,
stage counts, selection-policy losses, block witnesses and interpretation after
the run. Do not overwrite the pre-outcome design above.

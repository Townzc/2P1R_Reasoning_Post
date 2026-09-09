# Scientific review of C009

**Review date:** 2026-09-09. **Recommendation:** finish the finite CPU support
search and characterize selection before reserving another GPU. C009 establishes
that a precisely controlled four-problem schedule can be constructed. It does
not yet establish the size of the available block pool, a training effect, or a
semantic mechanism.

This review reads the saved [summary](family_matching_20260909_r1/summary.json),
[per-problem records](family_matching_20260909_r1/per_problem.jsonl),
[policy emulations](family_matching_20260909_r1/policy_emulations.json), and
[block witnesses](family_matching_20260909_r1/block_witnesses.json). It does not
read the large `shared_keys.json` archive, rerun the search, inspect model
predictions, or access development/holdout data. Independent computational
verification is separate from this scientific interpretation.

## What the saved evidence establishes

C009 ran at source commit `cb2bcedce36f78ae593ce979677e4199aeda26ee` on the fixed
256 training questions and all 25,846 legal ordered solutions. All 25,846 records
were encodable, with no sequence-length exclusions. The complete per-problem
checks and incomplete shared-key search must be interpreted separately.

| Stage | Problems | Meaning |
|---|---:|---|
| Original selected training pool | 256 | Fixed input population, already selected by the earlier pilot construction |
| Disjoint numerical AC 4+4 support | 131 | Eight different AC classes can fill the two families |
| Common supervised length within each problem | 67 | Some length permits disjoint 4+4 support |
| Exact family/structure flow of eight | 66 | At some length, each family also has four distinct structures |
| Shared-key support discovered before the cap | 7 | Certified participation among the checked keys; not total available support |
| Explicit greedy block | 4 | One four-problem accounting preview |

The main **complete** additional loss is the common-length requirement: 64 of
131 raw-eligible problems fail it. Adding the structure/AC flow requirement
removes one further problem, `485b8fd4720d0b74b81b`, with inputs
`[10, 26, 27, 36]`, target 26, and common length 67. These are consequences of
this grammar, tokenizer, serialization, and exact matching rule on this pool;
they do not show that the excluded questions are harder for a model.

Both family tuple enumerations completed: 24,324 identity-present tuples and
1,991 identity-absent tuples. Their Cartesian product contains **48,429,084**
key pairs. The frozen 2,000,000-pair limit examined **4.13%** of that ordered
grid; it stopped on the pair cap, not the 600-second deadline. The recorded
search used 75,126 structure-prefix nodes, retained 15,060 coarse pair
intersections, attempted 206,387 per-problem/length slot assignments, and found
681 valid keys whose union contains seven problems. A key count is not a sample
size: these 681 keys largely reuse the same questions.

The seven discovered problems can fit at most one disjoint four-problem block,
and one is witnessed. Thus the current one-block count is already optimal
**within that seven-problem discovered universe**, regardless of greedy quality.
It is not the optimum of the unsearched universe. The complete flow stage gives
a separate necessary upper bound of 66 candidate problems, hence at most
16 four-problem blocks/64 selected problems, before shared-key restrictions.

## Selection and interpretation risks

The per-problem records show substantial distribution changes:

| Population | Contains input 1 | Target range | Targets at least 41 |
|---|---:|---:|---:|
| Original 256 | 96/256 | 10–88 | 105 |
| Raw disjoint 4+4 | 19/131 | 10–76 | 41 |
| Common length | 15/67 | 10–40 | 0 |
| Flow eight | 15/66 | 10–40 | 0 |
| Discovered shared support | 7/7 | 12–34 | 0 |
| Four-problem preview | 4/4 | 12–34 | 0 |

The common-length construction therefore excludes every original target above
40. The all-input-1 pattern of the currently discovered keys has an additional
qualification: these keys come from a lexicographic prefix, not a complete or
random sample of feasible keys. It cannot establish that shared support without
input 1 is absent. Increasing the work cap and finding other questions would
resolve a computation limit; it would not demonstrate a new model phenomenon.

The four selected problems also share a conspicuous arithmetic template: an
input 1, a consecutive pair, and a remaining number whose successor is the
target. This is a post hoc observation of the preview, not a preregistered
selection criterion. It reinforces the need to measure formula-template
concentration before treating retained questions as independent task diversity.

The identity label describes an evaluated numerical trajectory. It is not a
semantic-strategy label, and distinct numerical AC classes do not by themselves
certify distinct reasoning strategies. For example, the saved problem with
inputs `[1, 19, 20, 33]` and target 34 has identity-absent witness
`33 + ((1 + 19) / 20)`: it constructs 1 through `20 / 20` and then adds 33.
That division is correctly identity-absent under the fixed rule, because its
denominator is 20 rather than 1. Nevertheless, it contains an algebraic
cancellation. The family contrast is not equivalent to useful reasoning versus
redundant reasoning, nor to the presence versus absence of constants.

All four preview cells have 16 presentations, four updates, 1,024 supervised
tokens, 1,824 processed nonpadding tokens, and zero padding tokens. Their four
problem witnesses happen to use length 64; the design correctly allows other
problems to have their own common lengths. These are CPU accounting results,
with **zero GPU process seconds and no model outcome**.

Cross-family operator distributions remain very different. Over 16 scheduled
presentations, either identity-present cell has `* = 16, + = 12, - = 20`, whereas
either identity-absent cell has `/ = 16, + = 24, - = 8`. Mean depth is 2.75 versus
3.0; mean negative-intermediate count is 0.25 versus 0. The within-family
Paths/GCM control is valuable, but a later difference between those allocation
effects across families would still be compatible with operator/trajectory
composition as well as identity events. The preview is not an identity-only
causal intervention.

## What the inventory-policy comparisons add

These complete checks isolate selection behavior within the saved inventory:

| Policy | Retained ordered rows | Raw disjoint | Common length | Flow eight |
|---|---:|---:|---:|---:|
| Full canonical inventory | 25,846 | 131 | 67 | 66 |
| Surface eligibility | 25,846 | 131 | 67 | 66 |
| First representative | 11,706 | 88 | 64 | 64 |
| First 12 structures | 23,093 | 131 | 57 | 56 |
| Surface → first representative → first 12 | 10,128 | 88 | 56 | 56 |

Surface eligibility causes no measured loss here. Choosing one representative
discards many raw family options, but most of those lost problems also fail
later full-inventory requirements: its flow-stage loss is two problems, not 43.
The first-12 policy loses ten flow-eligible problems. These losses overlap and
must not be added as independent contributions. They support preserving all
class/family options during matching. They are controlled policy emulations,
not a reconstruction of historical solver traversal and not evidence about
model performance.

## Next CPU experiment: complete the same finite question

Create a separately versioned follow-up; preserve C009 and its original limits
and outputs. Keep the same pool, feature archive, tokenizer, K, family definition,
length rule, and per-problem exact checks. Its outcome should answer **how many
problems/blocks this construction actually supports**, rather than optimize a
model score or seek a favorable family split.

1. **Make the join complete and compact.** Group each family's already finite
   structure tuples by identical conservative problem-support masks. Intersect
   each pair of masks once; if fewer than four distinct problems remain, prune
   the entire Cartesian product of those groups. For surviving group pairs,
   enumerate their distinct tuple pairs and perform the original same-length,
   eight-class assignment checks. Equal support masks alone do **not** permit
   reusing an exact AC assignment: different structure tuples can have different
   class bottlenecks. A cache must identify the actual candidate graph.
2. **Account for exhaustion.** Record group multiplicities and require that
   pruned plus explicitly evaluated pair counts cover all 48,429,084 original
   pairs. Check optimized results against the existing simple implementation on
   exhaustive toy inventories and deterministic small shards, including
   cross-length false positives and mixed-class conflicts. Predeclare a bounded
   CPU deadline and persist a deterministic cursor if unfinished. A capped
   follow-up remains incomplete; do not keep increasing limits inside C009.
3. **Separate support from packing.** Save compact key/support records and
   per-problem witnesses by reference/hash rather than repeating full responses
   for every key. For packing, keys with identical *exact* problem-support sets
   are interchangeable under the current hard constraints; one deterministic
   representative can preserve their packing possibilities, while a separate
   count/hash records all keys. Compare the declared greedy packing with a
   bounded exact set-packing formulation or a certified upper bound only after
   complete support generation. Report gaps rather than calling greedy optimal.
4. **Audit the resulting population before training.** Report retention by
   input 1, target, consecutive-pair/template patterns, operator composition,
   and intermediate-value features at each stage. Keep the current matching
   requirements fixed. A new renderer, K, target range, or population would be
   a distinct design change requiring its own rationale and baseline, rather
   than a repair to be silently selected for higher yield.

This is an algorithmic completion and design-feasibility experiment. Faster
joins, larger support counts, and a larger packing would not themselves provide
the scientific contribution needed for ICLR.

## GPU and paper decision

**Do not open a new GPU server for this four-problem preview.** First obtain
complete support/selection results and the independent witness-verification
outcome. Even the current necessary upper bound is only 16 training blocks,
so a defensible next training proposal must state the population to which it
applies and justify its number of independent blocks and seeds. Repeating
presentations, solutions, keys, or training cycles cannot substitute for new
independent problems or independent training runs.

If enough diverse blocks survive, preregister the within-family Paths-minus-GCM
effects, their between-family interaction, full-trace correctness, and suitable
coverage/concentration diagnostics with paired training seeds and matched dose.
The interaction alone would still concern these measured trajectory families;
to attribute it to identity operations specifically, define a falsifiable
mechanism contrast that separates identity from cancellation, operator mix,
and template effects, and first check its feasibility on CPU. If exact support
is sparse or dominated by the preview template, propose a new controlled
population/contrast explicitly before spending GPU time. Two more runs of the
same narrow allocation comparison would not resolve that identification gap.

# Design review after E010: select a falsifiable allocation question

**Status: reviewed proposal, not a new training protocol. 2026-09-09 UTC.**
The owner requested an immediate review of task construction and controls.
Three independent reviews cover [causal identification](../reports/DESIGN_REVIEW_CAUSAL_20260909.md),
[construction](../reports/DESIGN_REVIEW_CONSTRUCTION_20260909.md), and
[closest prior work](../reports/DESIGN_REVIEW_NOVELTY_20260909.md).
This document reconciles their recommendations into one decision. No new
dataset, model output, holdout result, GPU charge or completed novelty claim
is produced by this review. The original arithmetic registrations stay intact.

## Decision and what changed

**Stop adding arithmetic seeds to the current design. Develop one CPU-only
falsification prototype for evidence-route allocation.** Do not call it a
demonstration of different semantic strategies, a new benchmark already
validated, or evidence of ICLR readiness. If a strategy-level contribution is
essential, the proposed task does not meet that requirement.

The candidate question is:

> At fixed questions, available evidence, primitive computation, supervision
> and optimizer updates, does distributing supervision over several valid
> evidence routes per question improve verified reasoning when some evidence
> becomes unavailable, compared with repeatedly supervising one assigned route?

The clean-input effect is retained and reported. The evidence-removal question
is prospective for a **different task**, motivated by an identifiable
intervention. It does not replace E010's endpoint or repair E010 retroactively.
An effect here would concern learning from redundant evidence under a defined
distribution shift, not broad reasoning transfer or a discovered mechanism.

| Completed evidence | Implication for the redesign |
|---|---|
| C009: 131 raw 4+4-support questions become 67 after equal-token and 66 after structure constraints. C013: completed global matching supports only 63 questions, with 15 disjoint blocks. | Exact controls can select the population. A faster search resolves computation, not selection bias. New support should be guaranteed before sampling question values. |
| C012 removes unnecessary present-family restrictions but still selects 128 questions; depth differs for 120/128 and negative-intermediate exposure for 52/128 across arms. | Shared questions and matched batch structures do not imply all numerical path properties match. Do not label the contrast difficulty-free. |
| E010: primary 7/64 vs 5/64; complete traces 4/64 each; broader 0/64 vs 2/64. Earlier seeds used a different population and repetition dose. | A small favorable primary count does not justify scaling; the changed-population comparison does not identify identity removal. Lack of a robust benefit is not proof of zero effect. |
| Forks already contrasts within-problem versus global diversity and includes graph experiments. | Moving to graphs and matching updates are not sufficient novelty. A different evidence intervention plus a supported explanatory boundary would still need a closest-work comparison. |

Sources: [matching completion](../reports/MATCHING_COMPLETION_AND_TRAINING_20260909.md),
[E010](../reports/ABSENT_BOUNDARY_SEED31_RESULTS.md),
and the linked independent reviews. This is a post-E010 design decision;
none of the new predictions is represented as preregistered before E010.

## Candidate selection and explicit rejections

1. **Do not expand planted arithmetic identities now.** AC rewrites collapse
   many alleged alternatives; distributivity changes the task, operation
   counts and numerical exposure. Integer feasibility can recreate rejection
   sampling. No reviewed construction supplies four equally controlled,
   substantively different algorithms on a broad arithmetic population.
2. **Reject all-positive planted reachability.** If every query has a planted
   path, always answering yes solves the final-answer task. A certificate
   requirement helps assess proof generation but does not repair the trivial
   final-answer label distribution.
3. **Select permutation relation transport for CPU scrutiny.** It gives
   several disjoint supporting fact sets and a nonconstant answer. Its routes
   all execute the same algorithm; this limitation is part of the selection.
4. **Defer mixed AND/OR or heterogeneous proof algorithms.** They could support
   a stronger claim, but proof length, branching, information and operation
   difficulty are coupled. Do not switch to them automatically if the simpler
   candidate fails, or call an unimplemented possibility a solution.

## One precise construction to implement first

Use five state symbols and hidden independent uniform permutations
`h_v in S5`. A directed edge `u -> v` exposes the complete lookup table
`pi_uv = h_v composed with inverse(h_u)`. The question supplies source `s`,
source state `x`, drawn uniformly and independently of all potentials, and
target `t`; the answer is
`y = h_t(inverse(h_s)(x))`.

Construct four internally vertex-disjoint source-to-target chains, each with
four edges, initially all written forward. Add four disconnected four-edge
distractor chains, with independently sampled potentials. These supply a
predeclared irrelevant-evidence deletion control; they are shared across
training arms and are part of the proposed population. Random opaque node/edge
names and fact order are independent of potentials and the answer. No path
slot, construction order, latent potential or gold metadata enters the prompt.
Tables denote bijections: both forward lookup and inverse lookup are legal.
The initial four gold routes traverse their written edges forward. The solver
and certificate checker must honor the same bidirectional semantics.

Use IID semantic draws for the first scientific population: answer probability
is exactly one fifth in the population, not necessarily equal in a finite
sample. A separately quota-balanced implementation fixture is permitted but
must not be described as IID. Do not reject repeated states, identity maps or
neutral transitions. Those filters would change the generator and can create
missing-symbol or related shortcuts. Report their frequencies instead.

The telescoping product makes every route consistent with the same unique
answer, so every drawn question has four valid certificates. Equal length
fixes the number of table lookups, not every conceivable learning difficulty.
Permutations are noncommutative, but noncommutativity does not turn four chains
into four algorithms.

There is a useful exact limit on local shortcuts. For any **fixed** observed
edge subset that leaves `s` and `t` disconnected in the underlying **undirected**
observed graph, right-compose all latent
permutations in the target's observed component with a common permutation.
Observed tables remain unchanged while the target state ranges over all five
values. Under the stated IID law, the answer is uniform conditional on these
observations and `x`. This includes any fewer-than-four-edge subset here.
It does not cover a bag-of-all-tables probe, arbitrary compressed full-prompt
statistics, a label-dependent selector of edges, or a modified filtered law.
The mathematical statement is not an audit of an implementation.

All four task chains are isomorphic. Relabeling nodes, reversing a written
edge while inverting its table, or changing its position does not establish
semantic strategy diversity. New random tables on this fixed topology are
IID instance generalization, **not topology generalization**. A future
topology/depth extension needs a separate specification and evaluation stratum.

## Minimum allocation control and a concrete matching schedule

Use two independently initialized copies of the same pinned base model and
identical SFT settings. Each sees exactly the same question prompts, including
all four useful routes and the same distractors.

| Arm | Per question in a four-round cycle | Intended interpretation |
|---|---|---|
| **Route-multi** | Each of four valid certificates once | Within-question evidence-route supervision |
| **Route-repeat** | One assigned certificate four times | Equal-dose exact repetition of a fixed evidence route |

Avoid the name GCM for this new task: every route has the same inference
schema. Balancing arbitrary route slots is bookkeeping, not a substantive
control for global strategy coverage.

For each block of four questions, draw one label-independent permutation
`a_i` of route slots `0,1,2,3`, before any model result. At round `r`, Route-multi
uses `(a_i + r) mod 4`; Route-repeat always uses `a_i`. Each update includes
the same four questions in the same order, and one instance of every route
slot in both arms. After four rounds, every question has four exposures.
Repeat complete cycles only. Do not redraw Route-repeat's assignment each
epoch: that would give it within-question route diversity too.

The realized supervised table, intermediate-state and neutral-transition
histograms need not match, despite fixed primitive counts and route slots.
Audit these residuals at question, update and arm levels. Label-independent
assignment defines an average over assignments; it does not make each paired
realization nuisance-equal. Do not select a seed because its residuals or model
scores are favorable. This is a procedural allocation effect, not an effect
beyond every global semantic or computational exposure difference.

Use one canonical response renderer initially. Establish a finite symbol/ID
codebook whose **actual full serialization on the pinned tokenizer** makes
each route target the same length including EOS. Check prompt masks, target
normalization, padding and sequence limits. Equal characters do not establish
equal tokens. If a generated question fails the token contract, fail the
construction version; do not discard that question to rescue matching.
Changing the renderer before the next immutable attempt is allowed and logged.

Target multiplicity, reduced exact repetition and the changed question-to-fact
association are intended treatment components. The two-arm result cannot
identify a unique latent mechanism or rule out a generic benefit from multiple
targets. Training NLL is diagnostic and is not a matched reasoning outcome:
the conditional reference distributions differ between arms.

For a later claim **beyond surface variation**, add an explicitly reviewed
2-by-2 allocation design (four versus one route; four versus one equivalent
renderer), not a vague paraphrase baseline. An exact combinatorial schedule
exists: index 16 questions by `(a,b)` in `Z4 x Z4`; for each of 16 rounds
`(u,v)`, use route `a+u` or `a`, and renderer `b+v` or `b`, depending on the
arm, with addition modulo four. Assign actual questions to these indices
randomly, independently of tables and answers. This requires all 16 examples
in one effective optimizer update, possibly using gradient accumulation;
it cannot inherit a four-example update. Every update has the same joint
route/renderer histogram; every question
has 16 exposures. Full serialization and optimizer-dose feasibility remain
unverified. The four arms are **not queued** by this proposal, and different
numbers of distinct targets remain part of the factorial treatment.

## Evaluation that could disprove the hypothesis

The prospective central endpoint is the **paired difference in greedy fully
verified certificate accuracy after useful-evidence deletion**. A certificate
must use only present facts, have correct intermediate states, connect the
requested endpoints and give the correct final state. Final-state accuracy,
clean-input certificate accuracy, error categories and sampled coverage are
secondary; they cannot replace an unfavorable primary. The exact sample size,
training dose, decoding cap and seed list must be frozen before a GPU proposal.

For each evaluation parent, create these views before any model output:

- **Clean:** all four useful and four distractor routes remain.
- **Useful deletion:** uniformly choose one useful route to retain. On each
  of the other three, remove one of its two internal edges, selected by a
  fixed seeded randomization. One complete route remains and the answer is
  unchanged. There are three fewer facts; the invalidated routes are dead ends.
- **Irrelevant deletion:** remove one internal edge from each of three
  preselected distractor chains. Delete exactly three facts with the same
  serialization budget and coupled deletion-position policy. All useful
  routes remain. Match rendered positions where feasible by construction;
  report residual positions instead of post-hoc question filtering.

Equal removed-fact counts do not prove equal token costs. The CPU gate must
tokenize the entire reserialized views, including changed boundaries, and
verify prompt/response budgets under the same tokenizer.

The irrelevant control addresses prompt shortening and fact deletion generally;
it does not match the semantic effect of destroying useful certificates.
The contrast between allocation effects under useful and irrelevant deletion
is a prespecified specificity check. Report the clean effect and
`Delta_useful - Delta_clean` as well. All denominators include every assigned
question, not just questions the model solved cleanly. Do not choose a removed
route by inspecting a generated proof, and do not describe this as observing
the model's hidden preferred route.

The stronger availability-specific claim requires both a supported positive
primary `Delta_useful` and a supported positive key-secondary
`Delta_useful - Delta_irrelevant`, under prespecified uncertainty and practical
effect criteria. A primary improvement alone does not pass that claim gate.

Within each split, create two additional counterfactual diagnostics: change
source state according to a fixed policy; and change `h_t` to `rho composed
with h_t`, for a fixed derangement `rho` such as a five-cycle, updating **all**
incident tables and the gold answer coherently. This guarantees `rho(y) != y`.
Changing only one edge can create inconsistent evidence and is a solver
negative fixture, not a valid answer-changing evaluation example. Freeze
sampling of these diagnostics before model results and report them separately.

The predicted pattern worth investigating is a repeatable advantage in valid
proofs under useful deletion, beyond any change seen under irrelevant deletion,
without relying solely on guessed final states. Null, reversed, or highly
seed-dependent effects are meaningful outcomes. A clean-only improvement,
the same advantage after irrelevant deletion, or frequent use of deleted edges
does not support the proposed evidence-availability explanation. No single
one of these outcomes establishes an internal routing mechanism.

## CPU gates before discussing a server

Prepare a new immutable CPU attempt with source and configuration published
**before** materialization. The following are acceptance requirements, not
claims that they have passed:

1. **Independent correctness.** A lifted `(node,state)` graph solver reads
   only serialized tables; a separate trace checker uses direct table lookup,
   not generator composition code. Exhaustive finite permutation/inverse
   fixtures and corrupted, disconnected, inconsistent and counterfactual cases
   must pass. Any unexplained disagreement blocks the task.
2. **Full support and no hidden selection.** A fixed audit of 10,000 semantic
   instances, grouped under 100 prespecified seeds, must retain every instance
   and verify four length-four task routes, no shorter connecting route,
   consistent unique answers and all planned view invariants. This is a
   proposed engineering audit size, not a model-effect power calculation.
3. **Token and schedule contract.** Verify every exact response, EOS, mask,
   update total, padding count and seeded schedule independently. No length-
   based omission, meaningless proof padding or truncation is acceptable.
4. **Shortcut challenge.** Register fixed CPU probes for label priors,
   query state, ID/order/degree features, radius-one endpoint neighborhoods, all-table
   bags and template retrieval. Split parents before fitting probes. Freeze
   probe hyperparameters, rejection thresholds, multiplicity correction and
   a separate audit set in the CPU registration; they are still to be
   implemented. Above-chance prediction must be investigated by feature
   ablations and coherent counterfactuals. Passing finite probes is not proof
   that every shortcut is absent. An exact path solver is a valid algorithm,
   not an illicit shortcut. The union of radius-two neighborhoods from both
   endpoints can already contain complete length-four routes; success with
   that information is not a violation of the disconnected-information null.
5. **Leakage and scope.** Group each world/query family, renaming, reorder,
   inverse rewrite and counterfactual orbit into one split before augmentation.
   Check semantic duplicate orbits under rooted graph isomorphism and global
   state relabeling with exact witnesses. Do not demand disjoint bare topology
   for the single-topology pilot and then pretend relabeling satisfied it.
6. **Claim and resource gate.** If support or matching needs selective
   deletion, the version fails. If only evidence routes survive semantic
   quotienting, retain the narrow claim. A new GPU phase needs the completed
   CPU receipts, an engineering overfit/profile plan, and a reviewed cost
   envelope. Existing arithmetic performance does not calibrate this task.

For later training, separate training-pool seeds, allocation seeds, optimization
seeds and decoding randomness. Pair arms within each complete replicate.
Models, not generation samples, are the treatment units; question/view
clusters determine paired evaluation uncertainty. Several seeds on one pool
do not establish population robustness, and many decode samples do not replace
training replication. Select uncertainty targets and practical effect bounds
before final sample size; do not convert a conventional seed count into a
power claim. Do not inspect the existing reserved arithmetic holdout.

## Novelty and execution decision

The [bounded primary-source comparison](../reports/DESIGN_REVIEW_NOVELTY_20260909.md)
finds substantial overlap: Forks already studies allocation and graph choices;
ProofWriter, PrOntoQA and ProsQA already provide controlled proof tasks. The
useful-evidence intervention differs from merely reordering the same facts,
but this is a **candidate incremental distinction**, not a verified novelty
claim. A defensible extension would require the controls above, independent
replications, a nontrivial boundary, and comparisons faithful to the closest
work. If the only result is a small IID final-answer gain on four symmetric
chains, do not scale it or pitch it as a broad strategy-diversity contribution.

The next authorized work is implementation and CPU falsification of this
single candidate. GPU work is not ready. No server needs to be started for
this review or its CPU follow-up. The cumulative budget remains 5740/7200
process-seconds, with 1460 remaining and no reservations; no extra spending
is implied. Decide whether a new training plan is worth the cost only after
the CPU gates yield concrete evidence.

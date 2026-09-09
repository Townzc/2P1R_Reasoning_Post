# Training-design candidates after C009

**Decision memo, 2026-09-09 UTC.** Written after C009 and before inspecting any
C010/C011 result. This review uses existing protocols, C009's saved reports,
the frozen training recipe and the resource ledger. It runs no matching,
creates no new problem pool, reads no new model/development/holdout outputs,
and performs no server operation. All candidate support counts below are
unknown unless explicitly attributed to C009.

**Recommendation fixed before new support results:** use **C012, absent-only
exact matching**, for the prospective identity-absent Paths/GCM pair. Its input
population is all 256 original training questions; no identity-present support
or cross-family eight-class assignment is required. Those restrictions do not
identify the absent-only contrast and would unnecessarily select its population.
C010 completes the original finite question, while C011's two-family length
diagnostic remains a separate study of the older design; neither one's yield
chooses the training family. Reserve 2,130 of the remaining 2,484 GPU
process-seconds for one complete absent pair, conditional on C012's gates.
Do not launch four models or a tiny preview.

## What needs fixing, and what the experiment can identify

[C009](../reports/FAMILY_MATCHING_20260909.md) completely checked 131 raw
disjoint-AC 4+4 questions, 67 with a common eight-response length, and 66 with
the required structures. Its capped join found seven participating questions
and one block; these are lower bounds, not final capacity. The completed
per-question token filter removed all targets above 40. Surface eligibility
removed no rows. These are observed selection effects of a specific construction,
not evidence about problem difficulty or model learning.

The question for the next pair is narrower than a four-cell mechanism test:
**Does allocating four legal paths within each training question improve the
prespecified development endpoint over repeating one globally structure-matched
path, when all training paths lack the already defined identity events?**
The controlled contrast is between two fully specified allocation procedures on
a frozen eligible population, at the same within-pair dose. A favorable result
would challenge the claim that those particular identity events are necessary
for the allocation benefit. A null, reversal or uncertain result supplies no
such evidence; it would not prove identity events are necessary.

Identity-absent still permits `x / x` when the denominator is not one. The
observed C009 example `33 + ((1 + 19) / 20)` uses every input legally, creates
one by cancellation, and is correctly absent under the existing convention.
Keep this label unchanged. Neither absent nor present means nontrivial versus
redundant reasoning; numerical AC distinctness also does not define semantic
strategies. Cancellation, intermediate constants and input-resource use remain
separate descriptors. Do not delete required neutral computations or rename
the family after seeing a favorable result.

The [existing primary-source review](../reports/ICLR_POSITIONING_20260909.md)
already identifies direct overlap with
[Forks in the Road](https://arxiv.org/html/2605.17026v2), which studies
per-problem versus dataset-level diversity at fixed global mode balance.
Another positive seed alone does not distinguish this project. A useful
extension would connect exact structural/budget controls, their measured
population-selection costs, and a falsifiable arithmetic boundary that survives
independent evidence. The next pair could support that investigation; it cannot
by itself establish a semantic mechanism, transfer or ICLR readiness.

## Three concrete candidates

| Candidate | Hard matching and estimand | Main limitation | Decision |
|---|---|---|---|
| **A. Joint support, family-specific length (C011)** | Same questions; each family has four distinct structures/classes; eight distinct numeric AC classes jointly. Four paths share length L_i,f inside family f, but L_i,present may differ from L_i,absent. Exact Paths/GCM questions, tokens, updates and per-update structures within either family. | The two family-specific effects occur at different response doses and numerical/operator compositions. Their difference is not an identity-only interaction. Joint support still selects questions. | **CPU diagnosis of the older two-family design.** Its support is not a prerequisite for tomorrow's single-family comparison. |
| **B. Absent-only exact matching (C012)** | On all original 256 questions, require only four absent AC classes, four absent structures and a common L_i,absent, then four-question shared-structure blocks. Preserve all exact within-pair controls. | A newly eligible, still selected population; no same-question present/absent interaction is identified. It cannot be compared directly with A or the old pilot as if only one factor changed. | **Recommended training candidate, chosen before new support results.** Removing an unused family requirement follows the absent-only estimand, not a higher observed yield or model score. |
| **C. Randomized GCM with variable path lengths** | Keep four paths and uniform block-level permutation assignment. Paths sees all four; GCM keeps one path per question. Match questions, updates and structural histograms; total response tokens match in expectation over assignments. | Per-realization and per-update tokens need not match. One or two convenient seeds do not guarantee balance. Token-normalized SFT is nonlinear in the realized batches; expected token equality is not optimizer equivalence. | **Do not use for tomorrow's fixed-budget pair.** It requires a separately registered randomization/uncertainty and compute plan. |

These are prospective alternatives motivated by completed selection evidence.
They do not repair C009 retroactively. Complete C010 under C009's original
constraints before interpreting its capacity; evaluate A and B in separate,
versioned CPU attempts. B is already selected for the training question, regardless
of A's outcome. Do not run all alternatives and select whichever later
produces the best development score.

## C011/C012 CPU constraints and exact accounting

Retain the original training bytes, all 25,846 verified ordered solutions,
official pinned tokenizer, canonical rendering, EOS supervision, no truncation,
maximum sequence length 384, K=4 and the current identity/AC definitions.
For **C011** only, consider every feasible pair `(L_i,present, L_i,absent)`.
Each family's four slots use only rows at its own length. Enforce a single
capacity-one numeric-AC class constraint across all eight slots, including
mixed-label classes. Independent family feasibility is not enough to prove
their joint eight-class assignment.

Retain each `(question, family, length, structure, AC class)` option with a
deterministic ordered witness. Enumerate shared structure-pair keys completely
or mark the attempt incomplete. A four-question block must support the same
present and absent structure tuples, with its own valid length pair for every
question. Different questions need not share lengths. Reuse C010's independently
verified complete-join method only with proof that its pruning/cache identities
remain valid for two family lengths. Save exact witnesses, original and encoded
stream hashes, limits, completeness counters and independent verification.

For **C012**, start from every one of the original 256 questions and the same
complete ordered inventory. Select only rows labelled identity-absent, preserving
all `(question, length, structure, AC class)` options. At each finite length,
require four different structures and four different numeric AC classes jointly;
then completely enumerate shared four-structure keys supported by at least four
questions. Each question can use its own L_i. No present-family row, mixed-class
cross-family conflict or joint-support qualification can remove an otherwise
eligible C012 question. Produce complete support groups, a verified disjoint
packing, concrete path/schedule witnesses and independent verification before
freezing the training subset. Preserve capped or failed attempts explicitly.

For B blocks and C complete Latin cycles, with four questions per block:

- Unique training questions: **P = 4B**.
- Updates per arm: **U = 4BC**; presentations: **16BC**.
- Every question appears **4C** times. Paths presents each of its four paths C
  times; GCM presents its single assigned path 4C times.
- Supervised response tokens in either arm of family f:
  **T_f = 4C × sum_i L_i,f**, including one EOS per presentation.

Within each family, use the same problem ordering, microbatch boundaries and
Latin assignment/order seeds for Paths and GCM. Every update has one instance
of each of the four shared structures. Per-example and per-update response
tokens, processed nonpadding tokens and padding are equal across the pair;
padding need not be zero. Preserve the existing update loss normalization by
the actual total supervised response targets.

There is no requirement that `T_present = T_absent`. Common update counts do
not supply common response budgets across families. Do not add cycles to one
family to equalize its tokens while still claiming equal updates or exposures.
No cross-family equal-dose or pure-interaction claim accompanies tomorrow's
absent-only pair. The exact new T_absent is computed and frozen on CPU; it is
not assumed to equal the old pilot's 267,456 tokens.

## Minimum scale and the 1,024-update schedule

Set **64 distinct training questions in 16 verified disjoint blocks** as the
minimum operational gate. This prevents a four-question accounting example
from becoming an excessively repeated training experiment. It is **not** a
power calculation or evidence of statistical adequacy. Training-question count
does not determine evaluation precision, and shared templates reduce effective
diversity. Report the complete retained population, input-one frequency,
target distribution, consecutive-pair/template concentration, operator counts,
and numerical descriptors before choosing the training subset. New descriptors
of already observed C009 data are post hoc; describe them as such.

To retain exactly **1,024 updates**, all questions equally exposed and complete
four-round cycles, `4BC = 1024`, so **B must divide 256** and `C = 256/B`.
Do not add a partial cycle or oversample a few questions to fill a remainder.

C011 has at most 131 raw-eligible questions, but C012 is not restricted to that
subset. For tomorrow's bounded pilot, preselect **64 or 128 training questions**
even if C012 supports more; this is a training-size policy, not a claim that the
selected set represents all 256 originals. Freeze this rule before C012 outcomes:

| Verified disjoint blocks available | Training blocks B | Questions P | Cycles C | Presentations per question |
|---|---:|---:|---:|---:|
| At least 32 | 32 | 128 | 8 | 32 |
| 16–31 | 16 | 64 | 16 | 64 |
| Fewer than 16 | No GPU run | — | — | — |

Use the independently verified complete-key inventory and documented deterministic
packing. A greedy packing is a lower bound; if it supplies fewer than 16 blocks
while a larger packing remains possible, describe an unresolved packing gate,
not mathematical impossibility. Save any certified upper bound separately.
For budget-compatible downselection, canonically sort the verified disjoint
blocks by their question-ID tuples, then use a fixed local `Random(31)` shuffle
to select B blocks. Record selected and omitted IDs. The assignment/order RNG
is separate from this subset RNG. Do not select by a model output, favorable
numerical residual or preferred target value. Report the resulting subset's
descriptors again; random downselection does not undo prior eligibility bias.

If C012 fails this floor, explain exactly whether absent legal support, tokens,
structures, shared keys or unresolved packing blocked it. Do not train a smaller
set or switch family. The concrete next CPU alternative is the block-update-total
length constraint described below: it preserves equal updates, total/update
response tokens and global structure coverage while relaxing question-level
token equality. Its changed estimand and residuals require a separate reviewed
protocol before training. A new population/task is another explicit proposal;
no new pool is constructed by this memo.

These schedules change per-question repetition relative to the old 256-question,
four-cycle pilot. Matching holds within the new pair. An old-versus-new effect
difference would also reflect training population, repetition and token dose;
it must not be presented as an isolated identity intervention.

## Why expected length balance is a separate design

For a four-question block, let `l_i,s` be the length of question i's path at
structure index s. One Paths cycle uses
`T_P = sum_i sum_s l_i,s`. A fixed GCM assignment permutation pi uses
`T_G(pi) = 4 sum_i l_i,pi(i)`. Under a uniform permutation, each question selects
each structure with probability 1/4, so `E[T_G] = T_P`. Every update still has
one of each structure, but a particular assignment can overshoot or undershoot.

Prestratifying by length/operator features and randomizing within strata can
make a randomization estimand clearer. It does not make realized budgets exact.
Selecting one short and one long GCM seed is not enough: their deviations must
be demonstrated to cancel under the actual sampling weights. Four balanced
assignment permutations can balance each question's total exposure across a
run ensemble, while each individual GCM model still sees one path. That is a
multi-run estimand, not exact matching for a single pair, and averaging models
does not reproduce training one Paths model. Changing the GCM path inside a run
would also remove the intended fixed-single-path treatment.

One could instead freeze a constraint on block update sums: require all four
Paths Latin rounds to have the same token sum as the fixed GCM round. This is
weaker than per-example length equality and preserves the update normalizer,
but changes the controlled unit: question-level token allocations and padding
can differ. It would need its own complete CPU feasibility and residual audit,
not a claim that candidate A's exact per-example control was preserved. It is
a possible later alternative, not an unregistered fallback tomorrow.

## GPU recipe, resource gate and evaluation

Use fresh **Qwen/Qwen2.5-1.5B base** weights at the already pinned revision in
both arms, not continued adaptation from a seed23 checkpoint. Keep full FP32
trainable parameters, BF16 autocast, AdamW, learning rate 5e-5, weight decay 0.01,
clip 1.0, batch four, microbatch two, SDPA and gradient checkpointing. Freeze
data/config/schedule hashes before execution. Selection seed and the paired
assignment/order/training seed are **31**, using separate RNG instances for
selection and scheduling; evaluation seed remains **17**. Preserve the existing
evaluation decoding and greedy final-expression
primary for development continuity, with full-trace correctness and sampled
coverage kept as separate diagnostics. Do not substitute a metric because it
was more favorable previously. Existing development sets remain development
evidence; no fresh final holdout is opened here.

The ledger is **4,716/7,200 seconds charged; 2,484 remain**. The old pair's
measured 500 + 504 seconds is a runtime observation, not a new reservation
limit. Retain **1,050 seconds per arm plus 15 seconds per-arm guard overhead**:
`2 × (1050 + 15) = 2130`, leaving **354 seconds**. Any new GPU profile or
calibration must be charged within that remainder, and the full 2,130-second
pair reservation must still fit after it. Four arms at these bounds require
4,260 seconds and do not fit. Data-dependent throughput, evaluation and saving
must be included in the prospective complete-phase estimate. No automatic
retry, reduced dose or truncated second arm is authorized by unused observed
runtime in a previous run.

Before opening a server, the coordinator needs only the following blocking
information: verified eligible and packed counts; selected P/B/C and exact
per-arm token/update/padding audits; selection/template descriptors and stated
scope; an immutable paired configuration with primary/secondary endpoints and
stopping rules; and a complete-phase reservation that fits the live ledger.
Checkpoint backup/free-space needs must be measured on the actual replacement
instance, without assuming a storage purchase or an available old instance.

One paired training seed can support a limited development boundary check;
it cannot estimate training-seed variation. Report paired per-question outcomes
and uncertainty that respects evaluation grouping, and disclose that limitation.
The 64-question training floor does not guarantee a conclusive confidence interval.
Keep all unfavorable, invalid and interrupted outcomes. A stronger paper claim
requires independent pools/seeds and a meaningful generalization boundary after
this controlled core, with an additional explicit resource plan.

**Decision fixed before new matching outcomes:** C011 diagnoses the two-family
design; C012's absent-only construction is the training candidate. Prepare the
identity-absent pair only after C012's complete CPU and minimum-scale gates pass.
Otherwise report the precise blocker and the explicit block-total alternative;
never switch to identity-present merely because it yields more rows or a better
score, and do not automatically infer a future between-family interaction.

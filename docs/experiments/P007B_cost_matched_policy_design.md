# P007B: test the procurement decision under equal acquisition caps

Internal experiment design, October12 2026. Prepared, not dispatched. P007A must
finish and pass independent verification first. The exact numerical wallet caps
and execution ledger are frozen afterward using the calibration rule below,
before any P007B student outcome. TuesdayOct13 evening is the evidence target;
proposed hard closeout October14 02:00UTC (Tuesday19:00PDT). No main deadline changes.

## What the existing evidence does and does not say

The original two-seed bank experiment holds student targets and updates constant.
Solutions beats exact-answer Repeat by10.79 percentage points. Breadth minus
Solutions is−0.81 points with conditional paired-question interval[−3.71,2.20].
This is uncertain, not equivalence. The source bank's acquisition history is
unknown, so no cost-optimal rule follows. P007A estimates usable-answer supply and
cost from another fixed teacher; attaching that price to old bank results would
combine incompatible sources. P007B therefore acquires and trains on the new
teacher's own outputs.

Prior P/R comparisons already exist, including OpenMathInstruct-2 §2.2.4 and
When Does Generating More Help?. The remaining contribution is a tested decision
under explicit prices and resources, including rejected acquisition work, rather
than merely another fixed-pair ratio. Difficulty-aware retry allocation itself
is also established by DART-Math.

## Primary question and minimum decisive comparison

At one common acquisition spending cap, does a breadth policy (one usable answer
per problem) or a depth policy (up to four distinct usable answers) produce the
better SFT student, and does that ranking change when obtaining a new problem is
more expensive? The preregistered interaction is
(depth−breadth at positive problem price) minus
(depth−breadth at zero problem price). Also report both within-price contrasts;
a positive interaction alone does not establish that either policy wins.

Four procurement cells: breadth/depth × problem-price scenarios0 and4m.
Here m is a frozen calibration unit computed from the complete P007A generation
and checker time × the same GPU/host rate, divided by1024 attempts. It includes
wrong and duplicate attempts; it is not cost per accepted response. Both policies
receive an acquisition cap B=1024m at each price. If the pilot indicates that the
finite size/time gate is infeasible, amend this design explicitly before any
student output rather than silently tuning B or the prices to get a winner.
The positive problem price is a stated scenario, not a measured human price.
Zero price is the public-benchmark-access case. Keep obtaining a problem plus its
checking reference distinct from buying a worked demonstration; do not charge a
reference as though it were an additional purchased training solution.

Use the1024 GSM8K parents in the already-frozen fresh_draw_reserved order; zero
parents overlap the pilot or main audit_draw. Check exact/group disjointness and
restore all source bytes. The complete pool is a hard maximum, not a promise to
spend all budget after exhausting it. No replacement of unsolved parents, no
selecting parents by known teacher success. A second procurement draw is reserved
for a later confirmation; two student seeds on the first draw do not replace it.

## Acquisition contract: an actual capped policy run

Same teacher/revision/prompt/checker/duplicates/precision as P007A. The same GPU
class and a fixed16-slot batching policy apply to all four cells. Breadth retires
a parent after its first usable answer; depth retires it after four. Both retire
unsuccessful parents after eight attempts and keep them in the denominator.
Acquire the next frozen parent only when its scenario price can be paid. No
retries beyond the cap or filling quotas with extra free work. Different P, R and
retained N are outcomes, not extra controls forced equal.

The actual model/host time while the policy is active is charged at the locked
rate, including generation, checking and persistence. Every batch is charged once;
per-candidate shares may describe cost but never replace the actual batch bill.
Record asset/setup overhead separately and include its allocated share in an
all-in sensitivity analysis and actual total experiment spend. Pilot expense is
included in any end-to-end savings claim, with any reuse/amortization explicit.

The implementation must enforce a wallet with pre-admitted worst-case bounded
batch time, a watchdog and measured settlement. It must never start an action
whose maximum reserved charge exceeds the remaining wallet. It stops at the
same B and reports unspent budget and exhausted-pool/time censoring. If indivisible
batch slack exceeds5% of B in any cell, do not describe results as an exact-spend
comparison: report the cap comparison and expense imbalance, and resolve this
engineering limitation before a stronger dollar-efficiency conclusion. No
counterfactual prorated fixed-tape bill is substituted for executing the policy.
A capped or interrupted candidate costs resources and is unusable/unknown;
completed or ambiguous work is never replayed.

A separate overall dollar reservation includes platform startup, failures and all
four cells. It is distinct from the hypothetical scientific wallet. Maximum two
GPU workers total, finite individual calls, no resident service. Freeze numerical
batch reservations and exact attempt/time maxima after observing only P007A
throughput, without seeing P007B accuracy.

## Student and evaluation contract

Fresh Qwen2.5-1.5B base from the original locked revision, one LoRA/loss/LR recipe,
seeds17/23 in all four cells: eight student runs, no best-checkpoint selection.
Target256 optimizer updates and524288 supervised targets per run, whole answers,
prompt/pad masked, no truncation/packing. Audit processed tokens, answer lengths,
quality/stop selection, repeats and parent weights separately. If exact complete-
answer schedules cannot be constructed for every cell, reconcile the common dose
before any student training; never alter only one cell after observing outcomes.
A final-answer pass does not establish correct reasoning. Do not interpret a
policy contrast as a pure structural-diversity effect.

Primary student outcome: terminal greedy exact-answer accuracy on a frozen
held-out roster, same decoder/inference cap for every cell. The431 main dev
questions can support fast exploratory continuity but are already observed; they
cannot supply a fresh confirmation claim. The separate standard GSM8K roster is
now all1,319 official test questions, frozen before new P007B outcomes; use it only
at the chosen final terminal
recipe. Historical exposure audit on October12 found that the September public-
math study evaluated all1,319 official GSM8K test questions. Consequently this is
an existing, research-team-observed standard benchmark, not a pristine or newly
unseen test set. It can evaluate a locked new acquisition comparison without
P007B test-driven tuning; it cannot establish fresh researcher-level confirmation.
The new procurement pool is fresh with respect to this study, which is a separate
claim. Do not invent a benchmark or conceal the previous test exposure. Unknown
model pretraining contamination remains a limitation even on this split.
Prepared roster SHA256:
`ea61d5f11ee2b0605cfd031f840621aa7ee7015be5750d0eeb8ac3a9c7ebd9a1`;
raw official test file:
`3730d312f6e3440559ace48831e51066acaca737f6eabec99bccb9e4b3c39d14`.
All1,319 question/reference byte pairs agree with the pinned source; their1,319
groups have zero overlap with the1,024 fresh procurement groups. This is a
source/group check, not a guarantee of semantic or pretraining independence.
There have been zero new P007B test generations. Eight complete endpoints would
require10,552 generations; avoid adding a second development endpoint or choosing
checkpoints from this test. The exact execution limits remain unadmitted.
Compute inference resources and compare correctness under a common inference
contract; sampled pass@k is not required for the midpoint minimum.

Report both training seeds, paired question gains/losses, the interaction, policy
P/usableR/N, all attempt costs, unused wallet, and any failure. Bootstrap intervals
condition on these models and this procurement draw; they do not establish seed
or procurement robustness. With two prices and one budget, at most a local
conditional decision is supported, not an optimal price frontier or universal
threshold. A non-significant difference is not noninferiority.

## Decision and finite delivery scope

P007A is the immediate admitted-by-owner follow-up after main verification. Before
P007B execution, publish its exact numerical caps and roster hashes, check the
remaining total budget against450USD, and make the eight-run plan concrete. The
owner's standing execution authorization covers a finite justified follow-up;
this design is not permission to expand to more teachers, seeds or endless tuning.
Prioritize the four policy cells and two student seeds over another arbitrary
P/R grid. Reserve a fresh procurement draw plus a new price/budget for confirmation
after the midpoint if they cannot be completed by Tuesday's freeze.

A negative or inconclusive result is informative: it can show that answer supply,
quality, training exposure or uncertainty prevents a defensible purchasing rule.
Do not spend Wednesday finding a preferred result; use it for user-led rehearsal
and correcting verified artifacts. No AI-generated slides or assignment prose.

Primary references:
- [OpenMathInstruct-2](https://arxiv.org/abs/2410.01560)
- [When Does Generating More Help?](https://arxiv.org/abs/2607.01727)
- [DART-Math](https://arxiv.org/abs/2407.13690)

# Falsifiable proposals and their course provenance

September 29, 2026. Discussion designs, not execution protocols or confirmed
novelty. The [deep review](POSTTRAINING_DEEP_REVIEW_20260929.md) remains valid:
the original renamed-code Q1 is withdrawn; the revised Q1 below is a narrower
explanatory follow-up, not a revival of that proposal. Q2 remains conditional.
No new experiment or GPU use occurred in this design turn.
[Source and reading-depth record](POSTTRAINING_PROPOSAL_SOURCES_20260929.json).

## Course origin and contribution standard

The [syllabus](https://www.sewonmin.com/courses/cs294_288/) explicitly includes
data-constrained scaling and synthetic-data critiques. These proposals are our
extensions of readings, not two of the instructor's six suggested project titles.
The supplied topic document allows follow-ups to course readings, but excludes
simply improving reasoning models or agents without a course-relevant question.

| Proposal | Direct curricular starting point | Boundary |
| --- | --- | --- |
| Q1: durability of repeated solution data | September 10: [Scaling Data-Constrained Language Models](https://arxiv.org/abs/2305.16264); September 24: [Rephrasing the Web](https://arxiv.org/abs/2401.16380) | Related to the motivation of Topic 1, but not its Internet-data-supply forecasting task. A new LoRA optimizer would weaken the data-centric connection. |
| Q2: value of weak-supervision history after correction | September 22 Option B: [Spurious Rewards](https://arxiv.org/abs/2506.10947) and [Reasoning or Memorization?](https://arxiv.org/abs/2507.10532) | Study what training signals do and what evaluation can establish. Not Topic 4 distillation detection, and not a new agent benchmark. |

The webpage lists alternative September 22 readings; it alone does not verify
which option was discussed in class. Reading-list alignment does not establish
that the instructor has approved either specific design.

## Q1. Is the durability cost of repetition sensitive to adapter continuation?

**Scientific question.** For fixed problem exposure, does the additional
later-stage forgetting caused by repeatedly training on the same correct
solutions change under an intervention that preserves each trained model's
initial function but balances its LoRA factor scales?

**Why this matters.** If the data-recipe ranking depends substantially on how
the next stage updates an adapter, endpoint accuracy and data diversity alone
do not determine durable data value. A company deciding whether to purchase more
validated solutions needs to know the scope of a repeated-data penalty. This
experiment would qualify that penalty, not estimate procurement ROI or prove
that collecting new solutions is unnecessary.

### Similar work and the exact remaining claim

[Fine Until Fine-Tuned](https://arxiv.org/html/2609.33559v1) already tests fixed
versus fresh solutions to repeated problems and their later-stage durability.
[LoRA-RITE](https://arxiv.org/html/2410.20625v2) already establishes that ordinary
optimizers depend on the factorization of an unchanged effective LoRA matrix.
[Early Data Exposure](https://arxiv.org/html/2605.12705v1) and
[Overtrained Language Models](https://arxiv.org/html/2503.19206v1) already relate
training history to susceptibility to later updates. None of these inspected
comparisons directly establishes the particular data-history-by-factor-scale
interaction proposed here. Their conjunction is not, by itself, a novelty proof.

The remaining hypothesis is specific: **repeated-solution checkpoints are
disproportionately vulnerable to their inherited factor-scale configuration**.
An across-the-board optimizer improvement, or a repeat-versus-fresh score table,
does not support that claim. No new optimizer is proposed.

### Smallest informative design

Use a verified pair of the published repeated-solution (D) and fresh-solution
(P) handoff checkpoints and the frozen data/rendering contract. D/P is a whole
data-recipe contrast: solution lengths and strategies can differ. It does not
isolate surface wording at a matched acquisition-token budget. For each pair:

| Prior data | Original factors | Deterministically balanced factors |
| --- | --- | --- |
| D: same correct solution repeated | D-original | D-balanced |
| P: fresh correct solutions to the same problems | P-original | P-balanced |

For a LoRA update BA, transform A to cA and B to B/c, with
`c = sqrt(||B||_F / ||A||_F)` fixed from that layer's norms. This preserves BA
in exact arithmetic and equalizes the two norms. Preserve the module's existing
LoRA multiplier. Declare handling of zero factors and numerical tolerance before
execution; reject an invalid transformation rather than silently clipping it.
Verify effective weights and logits before any update. The function equality is
within a checkpoint across interventions, not between D and P.

All four branches start with fresh optimizers and the same published ordinary
instruction-tuning stage. Start with the realistic No Robots schedule rather
than choosing the stress schedule that makes the largest gap. The initial
diagnostic uses the paper's existing math evaluation and a proposed held-out
No Robots response-NLL check, after revision and overlap verification. The latter
measures instruction-objective learning, not complete user-facing quality. This
design does not create a benchmark or claim new mathematical ability. Its near-ceiling
base performance and possible contamination limit generalization claims.

Let F(H,C) be the pre-to-post loss of reasoning accuracy for history H and
continuation C. The primary contrast is

`I = [F(D,original)-F(P,original)] - [F(D,balanced)-F(P,balanced)]`.

Fix the training dose and endpoint before observing results. Also report the
retention/adaptation trajectory: an intervention that simply learns less of the
instruction task is not a useful solution. Post-hoc equal-score checkpoint
selection is not an additional causal control.

| Observation | Supported interpretation |
| --- | --- |
| Reproducible positive I with meaningful instruction learning | Factor scale conditions the *extra* repeated-data penalty in this setting. |
| Both histories improve equally | Generic optimization benefit; insufficient contribution for this proposal. |
| I indistinguishable from zero | No resolved scalar-scale interaction; does not exclude all adapter geometry or prove a textual-memory mechanism. |
| Protection disappears when accounting for instruction learning | Reduced adaptation is an alternative explanation; do not claim durable knowledge. |

Use independent upstream D/P training histories for confirmation. More decoding
samples or continuation seeds do not create independent upstream histories.
One available checkpoint pair permits a local diagnostic only. Four continuation
jobs per pair are required; recreating a pair adds two upstream training jobs.

**Practical gate:** the author's states are request-only, and a faithful local
trainer port is unverified. Without accessible matching states or an affordable
faithful reproduction, this exact diagnostic stops. Switching to a smaller model
would test a different regime, not reproduce the published mechanism. A later
code/generalization study on a frozen temporal LiveCodeBench window would be a
separate extension, not an automatic cheap validation.

## Q2. Does repaired supervision retain a harmful training history?

**Scientific question.** After replacing a weak public code-test reward with a
specified stronger public suite, does retaining the weakly trained model state
have negative value relative to returning to a pre-weak checkpoint under the
same future training procedure? Can this be separated from missed stronger-
supervision learning and optimizer-state dependence?

**Why this matters.** Data cleaning after training has begun changes future
labels, but it need not undo all effects of past labels. The concrete industrial
decision is whether to retain or discard already trained state after fixing
tests. The output should be a bounded decision contrast and an explanation that
survives obvious controls, not a claim that rollback is universally better.

### Similar work and one additional collision

[PRIME §4.3](https://arxiv.org/html/2606.09711v1) already studies reward switching
and residual history. [Delay, Plateau, or Collapse §4.6](https://arxiv.org/html/2605.02909v2)
already interleaves oracle verification. [Gradient Starvation](https://arxiv.org/html/2605.07689v1)
already explains loss of group-relative learning signal.

This turn also identified [Near-Future Policy Optimization](https://arxiv.org/html/2604.20733v1).
Its §§3.1–3.3 really roll back training checkpoints and guide earlier policies
with later successful outputs; this is not inference-time trajectory repair.
It does not test repairing a natural weak verifier under a common remaining
budget. Nevertheless, rollback, guided rescue and adaptive timing are unavailable
as standalone novelty claims. We do not propose another such method.

[When the Reward Suite Is Leaky](https://arxiv.org/html/2607.11022v1) supplies
the closest natural-error setting and substantial evidence against assuming
universal accumulating harm. Any recovery thesis must take that negative
evidence seriously.

### Concrete starting configuration and counterfactuals

Candidate implementation: the inspected Qwen2.5-Coder-1.5B-Instruct, full-model
GRPO/Adafactor setup and frozen MBPP split from the natural-suite study. It is
not a LoRA trainer. Use base tests for the weak phase, and explicitly pin the
official base-plus-extra union as the stronger condition on training tasks.
That union is a changed treatment relative to the paper's extra-only arm;
document it and do not label it a perfect semantic oracle.

Starting at S0, train two histories of T updates: W under weak tests and C under
the stronger suite. At a predeclared correction time, run the same stronger-
supervision continuation for a fixed K update opportunities and prompt groups:

| Future branch | Purpose |
| --- | --- |
| W-keep: W with full saved optimizer state | Actual current-state continuation policy |
| W-reset: W with fresh optimizer | Isolate optimizer carryover at W |
| C-reset: C with fresh optimizer | Same-duration stronger-supervision reference |
| R-reset: S0 with fresh optimizer | Value of discarding the weak phase |

Use a common phase-local LR schedule. Save optimizer counters/factored statistics,
sampler/RNG states and rollout model versions, not just weights. Literal full-state
rollback and an optimizer interaction across histories require additional arms.

**Most informative unobserved prediction:** W performs at least as well as S0
at correction time, yet W-reset later falls behind R-reset under the common
stronger-suite continuation. This sign reversal would show why current endpoint
quality can miss a future cost. It is a hypothesis, not an observed effect or a
new name for established plasticity phenomena.

**Discriminating results:**

- `W-reset < C-reset` but `W-reset >= R-reset`: weak training missed some useful
  learning, yet retaining it is beneficial or neutral. Calling this damage
  requiring rollback would be wrong.
- `W-reset < R-reset` at a meaningful, resolved margin: the weak phase has net
  negative value for this specified future procedure. It does not prove
  irreversible capability loss.
- W-keep loses while W-reset does not: the operational failure depends on
  retained optimizer state. A claim of *weak-history-specific* optimizer harm
  additionally needs C-keep versus C-reset (and, where relevant, S0 controls).
- Rankings change with future budget: report a finite-horizon tradeoff, not a
  universal policy. A boundary needs replication and prospective validation;
  one crossover is not a learned decision rule.

### A correction to the earlier screening logic

No immediate W/C gap at the end of the weak phase is **not** a sufficient reason
to conclude that subsequent recovery behavior is identical. If this is the
question, the phenomenon screen must include at least W-reset and R-reset under
a common short stronger-supervision continuation. Lack of power is inconclusive.
A sufficiently resolved null for the future decision contrast is a useful stop
for that setting. If the budget only covers prefixes, it cannot test this claim.

### What to measure and what would count as progress

Freeze an official held-out code evaluation separately from training tests.
Record stronger-suite pass rate, base/extra disagreement and per-task training
group composition. Do not turn all-fail samples into a claim of zero support or
all extra-test failures into semantic wrongness. A temporal LiveCodeBench window
after the model's release is an existing external evaluation option, but its
task overlap, test errata, sample size and small-model score floor must first
support the planned effect resolution. It is not a new benchmark.

Match future update/group dose for the causal comparison, and report actual
generated tokens, test execution costs and GPU time separately. Equal updates
do not imply equal compute. An actual budget decision additionally needs
performance at a common resource cap. Keep sunk historical costs visible.
Training-group informativeness is a useful diagnostic, but correlation with the
future gap does not identify its cause; known starvation alone is not a new
mechanism. The comparison includes weight-mediated changes in subsequent
on-policy data, rather than isolating them from parameter history.

Count `n_paired_history_replicates * (2T + 4K)` update opportunities for independent
paired histories
and these four continuations, plus evaluation and diagnostic generation. If a
state-interaction claim needs C-keep, add K per history. More correction times
expand the design; none is authorized here. Three seeds are not automatically
adequate power, and repeated tasks across seeds are not independent new tasks.

A valuable result requires a replicated contrast or a failure of a specific
existing explanation. If only known optimizer resets or generic starvation
account for the outcome, this remains a useful replication rather than the
desired new paper. If natural errors do not cause a meaningful future penalty,
preserve that result and stop rather than engineering stronger exploits.

## Sequence and decision

First finish the offline asset/measurement checks, including reuse of published
records and a declared effect-resolution target. These designs require no
teacher API or invented benchmark. Q1 additionally depends on obtaining usable
trained states; Q2 requires implementing full-state save/resume before execution.
Neither prerequisite has been completed by this document.

Take both cards to Office Hour with **Q2 first** because supervision reliability
is directly data-centric and operationally concrete. Ask whether its remaining
counterfactual is substantive enough after the listed prior work. Present Q1 as
a narrow interpretation study whose course fit and asset cost may rule it out.

Only one should advance to a separately scoped, measured pilot if its scientific
and engineering gates pass. No A100-hour completion estimate is available.
The 1,000-hour total ceiling remains a ceiling, not a target or an allocation to
each proposal. The previous 40-hour figure is not a verified experiment duration.

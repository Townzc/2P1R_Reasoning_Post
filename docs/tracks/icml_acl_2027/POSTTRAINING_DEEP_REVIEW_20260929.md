# Deep review of two post-training data questions

September 29, 2026. Literature, methods and public-source review only. This
supersedes the recommendation in [the initial discussion card](POSTTRAINING_QUESTIONS_20260929.md).
No model experiment was conducted. A missing exact paper is not proof of novelty.

## Decision

| Candidate | Current judgment | Reason |
| --- | --- | --- |
| Stable versus changing solution text under repeated SFT | Withdraw as the main project | A September 27 paper already compares fixed versus fresh correct solutions to the same problems at matched exposure. Pure renaming leaves a narrow augmentation question. |
| Repetition history interacting with subsequent LoRA optimization | Unadmitted diagnostic, not a replacement project | Potentially separates explanations of an existing result, but parameterization sensitivity is established and necessary trained states are not publicly downloadable. Course fit weakens if it becomes optimizer research. |
| Continue versus roll back after repairing code-test supervision | Conditional Office Hour question; not experiment-ready | Operationally consequential, but recovery, history effects and sampling starvation all have direct precedents. Natural-error harm, valid measurement and full-state recovery are unresolved prerequisites. |

Neither original card presently warrants a main GPU study. Q2 deserves a
focused discussion with an expert, not a claim of an untouched research direction.

## What changed after reading methods and appendices

| Primary source and inspected material | Consequence for our proposal |
| --- | --- |
| [Fine Until Fine-Tuned, 2609.33559v1](https://arxiv.org/html/2609.33559v1), methods, results, limitations and appendices K/M/N | Same-problem fresh solutions and later fine-tuning are already the central experiment; source of the remaining mechanism question, not evidence that our original question is novel. |
| [Early Data Exposure, 2605.12705v1](https://arxiv.org/html/2605.12705v1), §§3–5 and training details | Exposure history can affect later retention despite similar immediate performance; fixed target-data budget and retention/adaptation tradeoffs already matter. |
| [Overtrained Language Models, 2503.19206v1](https://arxiv.org/html/2503.19206v1), §3 and Appendix D | Training-induced sensitivity to later updates is established; local curvature does not fully explain finite-update forgetting. |
| [Retaining by Doing, 2510.18874v1](https://arxiv.org/html/2510.18874v1), §4 and Appendix A.4 | Refreshing self-generated training data and on-policy explanations of retention are established, although this differs from measuring vulnerability to a later stage. |
| [PRIME, 2606.09711v1](https://arxiv.org/html/2606.09711v1), §4.3 | Corrected rewards suppress observed exploitation; subsequent faulty rewards can reveal a persistent history effect. Neither switching nor residual history is new. |
| [Delay, Plateau, or Collapse, 2605.02909v2](https://arxiv.org/html/2605.02909v2), especially §4.6 | Interleaving accurate verification already mitigates some error regimes; v2 moves the relevant experiment into the main text. |
| [When the Reward Suite Is Leaky, 2607.11022v1](https://arxiv.org/html/2607.11022v1), methods, long runs, adjudication and author code | Natural test disagreement need not produce growing harm. Stronger tests are not an infallible semantic oracle. |
| [Gradient Starvation, 2605.07689v1](https://arxiv.org/html/2605.07689v1), §§3.1, 3.3 and 4.3 | Per-prompt success probability, degenerate reward groups and group-size rescue already have analysis and experiments. Logging them is a diagnostic, not a new mechanism. |
| [Reward Specification and Benchmark Reliability, 2608.17804v1](https://arxiv.org/html/2608.17804v1), §§4.1, 5.4–5.5 | Separates reward specification from availability of reinforceable behaviors; SFT warm-up and active-group logging already exist. |
| [When RL Fails after SFT, 2606.09932v1](https://arxiv.org/html/2606.09932v1), methods and intervention ablations | Overtraining, output concentration, later trainability and fusion/reset interventions are crowded territory. |
| [Robust RL for Small-Scale LM Agents, 2607.25091v1](https://arxiv.org/html/2607.25091v1), Algorithm 1 and §V-E | Weight rollback and moment reset already serve numerical safety; this is not a study of recovery from natural code-test errors. |

These studies differ in models, error mechanisms, evaluation and training regimes.
Their existence excludes broad novelty claims; it does not establish that every
reported result transfers to our setting. Recent arXiv papers are treated as
preprints unless an official venue record was separately checked.

## Q1: the original intervention is too close, and its interpretation was weak

The September 27 study contrasts repeated solutions, single-exposure solutions,
and fresh correct solutions to the same repeated problems. The last condition
already holds problem identity, order and exposure frequency fixed. It examines
subsequent instruction tuning and includes rank and sharpening controls. Its
authors leave open whether repetition changes textual fitting or sensitivity of
the trained adapter to later updates. Fresh solutions can also change reasoning
strategy; this is a remaining distinction, not clearance for a new paper.

Our variable-renaming proposal separates a narrower nuisance factor, but has two
problems beyond overlap:

1. Independently sampled opaque identifiers make their first occurrence
   unpredictable by construction. Showing useful learning without perfect token
   accuracy would therefore be a deliberately constructed counterexample, not an
   explanation of saturation in natural reasoning data.
2. A changed outcome simultaneously reflects label entropy, consistency, copying
   difficulty and stochastic gradients. Safe alpha-renaming preserves program
   semantics, but does not hold these learning conditions fixed. Finite tests
   cannot prove equivalence for arbitrary Python programs either.

Thus a code accuracy improvement would most naturally support a particular
augmentation recipe. It would not justify a general account of why repetition
helps or hurts reasoning. A code-only extension to the new paper is not presently
strong enough for the intended scientific goal.

### A more substantive unresolved distinction, with substantial caveats

A possible diagnostic asks whether the *additional later-stage fragility induced
by repeated data* changes under a function-preserving reparameterization of the
trained adapter. With effective update matrix BA, replacing A by cA and B by B/c
preserves that matrix before further training. Ordinary coordinate-based
optimizers need not produce the same subsequent function updates.

This sensitivity is known: [LoRA-RITE](https://arxiv.org/abs/2410.20625) explicitly
studies transformation invariance, while [LoRA+](https://arxiv.org/abs/2402.12354)
and [LoRA-GA](https://arxiv.org/abs/2407.05000) address factor learning rates and
initialization. A successful rescaling is therefore not a new optimizer insight.

Only a reproducible *data-history by continuation-geometry interaction* could
add an explanation of the repetition result. It would require matching the
pre-continuation function within each checkpoint across continuation interventions
(not between the two data histories), measuring effective function change, and
reporting the retention/adaptation tradeoff alongside the fixed-dose interaction.
Post-hoc selection of equal-new-task-score checkpoints is not a causal control.
Less forgetting obtained by learning less is not a meaningful solution.
Merging and restarting an adapter
also changes the available update subspace; it is not a perfect control.

Even that diagnostic would not show that a textual data effect is fictitious:
data can cause a parameter state whose vulnerability depends on the optimizer.
The question concerns a mediating path, not an either/or causal dichotomy.
Existing curvature and continual-learning work further narrows the contribution.
Do not promote this into a standalone project merely to keep Q1 alive.

### Asset check

The [author repository at 6f0d7b4](https://github.com/ely2ba/reasoning-durability/tree/6f0d7b413f7211d9dbdeb810273dd237d1465588)
provides frozen records, data identifiers and compact outputs. Its complete Git
tree contains 132 entries and no weight binaries. The pinned
[data documentation](https://github.com/ely2ba/reasoning-durability/blob/6f0d7b413f7211d9dbdeb810273dd237d1465588/data/README.md)
states that 53 retained training states are available on request; a manifest is
not a transferable model. The execution scripts use Tinker. Local continuation
would require actual weights and a validated trainer port or fresh reproduction.
No request was sent and no paid service used.

## Q2: a narrower decision problem, not a new recovery phenomenon

**Remaining question:** after replacing a weak code-test reward with a specified
stronger public suite, does preserving the weakly trained state improve or harm
future benchmark utility relative to returning to a pre-error checkpoint, under
a fixed *future* training allowance? Does an observed difference survive a common
optimizer reset and a same-duration stronger-supervision reference?

This is a data-quality history question with a practical consequence: a team
discovers deficient training tests and must decide how much already paid-for
training to retain. The relevant scientific advance would be a repeatable
condition under which past weak supervision helps or hurts recovery, beyond
generic sampling starvation or optimizer carryover. One win for rollback on one
seed would not supply that advance.

### Separate three estimands before spending compute

Let S0 denote a saved pre-error full state. From S0, construct Wt using weak
supervision and Ct using the declared stronger supervision for the same number
of updates and prompt groups. After time t, every branch below uses the stronger
suite, the same prompt schedule, decoding contract and learning-rate schedule.
On-policy generated texts will necessarily differ.

| Branch | Starting weights | Optimizer treatment | Comparison it permits |
| --- | --- | --- | --- |
| W-keep | Wt | Keep complete optimizer state, including counters and factored statistics; align the future LR clock separately | Against W-reset: contribution of optimizer carryover |
| W-reset | Wt | Fresh optimizer | Against C-reset: effect of weak versus stronger training history at matched past nominal dose |
| C-reset | Ct | Fresh optimizer | Reference for the opportunity cost of weak supervision |
| R-reset | S0 | Fresh optimizer | Against W-reset: whether the weak phase has net value relative to discarding it, at equal future allowance |

This is four continuation branches, not a two-run experiment. A literal rollback
of *all* old optimizer/scheduler state is a different operational policy and
requires its own control if claimed. Full checkpoint saving remains necessary
for W-keep and to document precisely what was restored. To claim that optimizer
carryover is specifically harmful after weak supervision, rather than a generic
reset benefit, add corresponding retained/reset comparisons on the reference
states. The four branches alone do not identify that interaction.

W-reset below C-reset can mean missing useful clean learning; it does not alone
prove damage. W-reset below R-reset is stronger evidence of a net cost of the
weak phase for this finite horizon. Neither proves irreversible loss. A W-keep
deficit removed by reset points toward optimizer dependence, without asserting
that weights and sampled candidates are otherwise identical over the trajectory.

Equal future prompt groups is a clear scientific dose comparison but not exact
compute equality: response lengths and test runtime can differ. Report utility
against both generated tokens and measured device time. Report total historical
cost separately; do not silently credit rollback with refunding the faulty phase.
Avoid selecting the correction time by whichever yields the largest test gap.

### Support measurements do not identify a new causal mechanism

Estimate per-prompt stronger-suite pass probability, all-fail/all-pass groups,
response length, entropy, gradient magnitude and effective parameter updates on
training-side probes. Rare success is not zero mathematical support. A correlation
between low success probability and slow recovery does not distinguish candidate
availability from a poorly conditioned update or ordinary task difficulty.

Existing results already motivate more samples and supervised warm-up. A rescue
with either changes compute or training distribution, so it cannot alone prove
that candidate availability caused the history effect. A proposed new mechanism
must make a discriminating prediction after these alternatives are addressed.
The four-branch study identifies bounded policy comparisons, not all mechanisms.

### The measurement problem may stop the project before a GPU pilot

The leaky-suite study's stronger condition is extra-tests-only, rather than the
official base-plus-extra union. Its adjudications also cover a finite existing
program pool, not arbitrary future model outputs. Therefore, without new labels,
we can report official benchmark pass rates and suite disagreement; we cannot
rename every failed stronger test as a genuinely incorrect program.

Use an unchanged public benchmark protocol, freeze versions and splits, and keep
training tests separate from evaluation. MBPP/HumanEval support reproduction of
that study but do not remove contamination concerns. A frozen temporal
LiveCodeBench window could supply an existing independent evaluation, subject to
model-release chronology, overlap, task counts and sufficient baseline competence.
Those admission checks remain incomplete. No new benchmark is proposed.

The pinned leaky-suite trainer saves model-only states, uses Adafactor and a
separate rollout GPU; the inspected public tree has no model binaries. It is not
currently a resumable four-branch experiment. A one-GPU port, optimizer persistence,
RNG handling and exact step/sample accounting require verification before any
scientific run. None was implemented or tested in this literature turn.

## A staged decision rather than a prematurely large experiment

1. **No-compute gate:** use already released records to establish whether there
   is a natural-error phenomenon worth following, whether its interpretation
   survives the erratum, and whether the public evaluation answers the desired
   question. Do not substitute deliberately engineered exploits to obtain harm.
2. **Protocol gate:** freeze a model, data versions, one correction time, four
   branches, outcomes, meaningful effect threshold and a full-state recovery
   contract. Separate operational utility from semantic-error claims. An expert
   should assess whether the remaining contribution is worth pursuing.
3. **Measured resource gate:** a separately authorized profile must include
   rollout, training, CPU test execution, checkpoint/export overhead and all
   devices. Earlier 40-hour figures were proposed caps, not runtime estimates.
4. **Finite pilot only if gates pass:** first establish reproducible natural
   harm or a meaningful recovery contrast. A single seed can screen feasibility,
   not establish a general decision boundary. Stop for no phenomenon, a gap
   explained by mismatched dose/state, unreliable measurement, or excess cost.

For one correction time and four continuations, a planning lower bound is
`n_seeds * (2 * T_history + 4 * T_recovery)` optimizer-update opportunities, plus
evaluations, training-side diagnostic generations, state saving/restoration,
profiling and any shared initial preparation. It is not an A100-hour estimate.
Multiple correction times or mechanism interventions expand the design quickly.
The 1,000 A100-hour overall ceiling is neither a spending target nor confirmation
of available credits. No rental or experimental execution is recommended now.

## Questions worth taking to Office Hour

- Is the natural-verifier correction decision a sufficiently substantive
  data-centric question after accounting for published reward-switch and
  gradient-starvation work, or mainly an engineering replication?
- Which existing supervision source offers a defensible correction and a
  measurable small-model effect without constructing a new benchmark or relying
  on new manual judgments?
- For the repeated-data observation, would explaining the data-history by
  adapter-geometry interaction add useful scientific understanding, or move too
  far from the course's data focus relative to the cost?

These are provisional discussion questions. They do not claim the two projects
are ready to run or replace the need to locate a stronger question if both fail.

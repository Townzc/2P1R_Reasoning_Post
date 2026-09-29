# Familiar post-training questions: discussion shortlist, not novelty clearance

Date: September 29, 2026. Literature and small public-source inspection only.

## Decision

Prioritize data-constrained reasoning/code SFT and the effects of imperfect RLVR
supervision. Keep on-policy distillation (OPD) data compression as a reserve.
Provenance, AI-text prevalence, watermark attribution and GEO are no longer the
preferred search space. This follows the project preference for familiar methods,
active research communities, industrial relevance and existing evaluation assets.

**Two concrete questions below are suitable for discussion; neither is an admitted
novel project.** The first is experimentally simpler but risks being ordinary data
augmentation. The second has a consequential operational decision but stronger
overlap with reward-switch research and a substantial risk of no phenomenon at
small scale. A third question is less mature. Do not describe this memo as finding
three previously unstudied topics.

The [course syllabus](https://www.sewonmin.com/courses/cs294_288/) motivates these
through limited data, synthetic data and data quality. These are our follow-up
questions, not verbatim instructor-suggested topics. They keep the learning
objective fixed and vary the training data or supervision history.

## Q1. Does repeated SFT need stable target text?

**Question.** For a fixed set of code problems and reference algorithms, does the
effect of repeated SFT depend on keeping the exact target text stable across
exposures, or can equally frequent exposure to semantically equivalent targets
produce the same generalization and saturation behavior?

**Known results.** [Data Repetition Beats Data Scaling, v2](https://arxiv.org/html/2602.11149v2)
reports benefits from repeatedly fitting small long-CoT datasets and a correlation
between training-token accuracy and saturation. Section 4 explicitly does not
identify a definitive mechanism; Appendix C already reports termination-conditioned
results. [Scale Dependent Data Duplication](https://arxiv.org/html/2603.06603v1)
studies semantic-gradient alignment, but its training study uses exact repetition
as a proxy for semantic duplication. Neither observation establishes that literal
target prediction is necessary. Rephrasing and code augmentation are established:
[WRAP](https://arxiv.org/html/2401.16380v1),
[DISCO](https://aclanthology.org/2022.acl-long.436/).

**Proposed contrast.** On one existing reference program per APPS training task,
compare fixed opaque local-variable names with names independently redrawn from
the same distribution at each exposure. Keep the algorithm, tasks, exposure count,
loss and evaluation fixed. Include natural names to measure the loss of useful
naming cues. Capture-avoiding renaming must exclude reflection, dynamic scope,
external bindings and signatures; finite unit tests alone do not prove equivalence.
Token-length matching and its exclusions require a CPU feasibility check.

The main estimand is **surface consistency across exposures**, not “all
memorization.” Dynamic names can still permit algorithmic and functional memory.
If they preserve performance despite preventing exact prediction of fresh names,
complete target-string prediction is unnecessary in this setting. If performance
falls, target entropy, gradient noise and copying difficulty remain alternatives
to a memorization explanation. An improvement over an untrained checkpoint only
shows an SFT effect. Claiming a repetition advantage additionally requires an
equal-token, wider-data one-pass reference, with that extra arm charged to budget.

**Industrial decision.** Reuse scarce validated demonstrations literally or spend
effort producing meaning-preserving variants; decide whether token accuracy is a
useful stopping signal. A small renamed-data gain alone is insufficient novelty.
Code-only findings cannot explain long-CoT training in general.

**Existing assets inspected by the research team.** APPS code at
`362aedc3c71cd7d9bd2fc96a6c80e11dbc38c7a5`, data at
`21e74ddf8de1a21436da12e3e653065c5213e9d1`, Qwen2.5-Coder-3B metadata at
`09d9bc5d376b0cfa0100a0694ea7de7232525803`, and LiveCodeBench harness at
`28fef95ea8c9f7a547c8329f2cd3d32b92c1fa24`. References:
[APPS](https://github.com/hendrycks/apps),
[data card](https://huggingface.co/datasets/codeparrot/apps),
[model](https://huggingface.co/Qwen/Qwen2.5-Coder-3B),
[LiveCodeBench](https://github.com/LiveCodeBench/LiveCodeBench).
Metadata availability is not a completed data/transform audit. APPS includes
missing or imperfect tests. Use an existing, frozen LiveCodeBench time window
after the fixed model release; verify overlap and exact counts before execution.
A newer date reduces direct contamination risk, not all contamination uncertainty.

**Stop conditions.** No safe and representative transform pool; an existing paper
already isolates this intervention; no useful surface-consistency effect; or all
effects reduce to ordinary augmentation/format learning without a new explanation.
Do not increase scale merely to rescue a weak result.

## Q2. After correcting faulty RL supervision, continue or roll back?

**Question.** After natural code-test false positives have affected training,
when does continued training on corrected supervision recover useful performance,
and when is returning to a pre-error checkpoint better at the same subsequent
clean-training budget? Can the difference be explained by the accessibility of
correct candidates, separately from lost clean updates and optimizer history?

**Already known.** Structured verification errors can matter more than their
aggregate rate: [Delay, Plateau, or Collapse](https://arxiv.org/html/2605.02909v1).
[PRIME §4.3](https://arxiv.org/html/2606.09711v1) already switches a code model to
gold rewards and then re-exposes it to faulty rewards, finding suppressed behavior
with persistent exploit-related capability. [Position-confounded optimization
§4.5](https://arxiv.org/html/2608.15445v1) reports heterogeneous recovery after
unbiased continuation. Therefore neither historical residue nor reward switching
is our novelty. [Anthropic's operational account](https://www.anthropic.com/news/improving-alignment-security-efforts)
illustrates a real rollback decision, not a controlled proof that rollback wins.

**Important negative evidence.** [When the Reward Suite Is Leaky](https://arxiv.org/html/2607.11022v1)
studies natural test false positives, including 800-step continuations, without
finding universal accumulating exploitation. Its hardened reward is extra-tests-only,
not the official union of base and extra tests; neither suite is perfect truth.
The paper does not answer our switching/rollback contrast, but substantially weakens
any assumption that the small-model natural-error setting necessarily needs repair.

**Proposed separation.** Save full states before and during faulty supervision.
At a declared correction point compare continuation and rollback under equal
subsequent clean exposure; add an optimizer-reset diagnostic only if needed.
Provide an always-corrected reference curve. Report equal-clean-dose and equal-total-
compute comparisons separately: different histories cannot satisfy every matching
constraint simultaneously. Fix or explicitly separate the learning-rate clock.

Measure correct-candidate frequency and uninformative reward groups on training-side
tasks, then assess unchanged official held-out code benchmarks. Rare sampled
success does not establish zero policy support or irreversible capability loss.
The possibility that corrected rewards cannot guide a policy which rarely samples
correct candidates is a hypothesis, not a new established result. A useful study
must identify a reproducible recovery boundary beyond the existing switching work.

**Assets and implementation limits.** Inspected author repository
[`rlvr-leaky-suite` at 9b6c86a](https://github.com/toffee-desuwa/rlvr-leaky-suite/tree/9b6c86abeb4b837418b009d5354f81b43a28f84b)
contains frozen splits, static tables, logs and code. Its complete Git tree had no
weight binaries; the trainer saves model-only states and uses a separate rollout
GPU. Thus no ready-to-resume recovery experiment or verified single-GPU recipe is
claimed. Original MBPP/HumanEval evaluation supports comparison with that study;
it cannot establish uncontaminated new ability. Independent temporal evaluation
and stronger-test errors must be resolved before any broader claim.

**Stop conditions.** No reproducible harm under natural faulty supervision;
apparent recovery differences explained by dose/schedule/optimizer mismatches;
unreliable reference tests; or a minimally informative comparison exceeds budget.
Do not manufacture stronger exploits to obtain a desired story.

## Reserve Q3. What information does a tiny OPD prompt corpus preserve?

Could two training prompt sets cover similar teacher hidden-state regions while
transferring different task-relevant corrections? This targets compression of a
company's domain prompt bank, not a new distillation loss.

[One Training Example](https://arxiv.org/html/2609.04172v1) already studies few-shot,
content-light and off-domain prompts, hidden-state coverage, fixed-state reuse and
multi-teacher OPD. Generic diversity is taken. Its coverage construction uses
teacher final-layer states, not simply text embeddings. A new study would need
training-side, pre-outcome matched interventions and a consequential lost skill;
showing that clustering is imperfect is too weak. The requisite correction
definition and diagnostic assets are not verified. **Reserve only; no GPU proposal.**

## Tempting extensions rejected in this screen

| Proposed extension | Direct precedent |
| --- | --- |
| Stronger teacher versus student learnability | [Rethinking OPD, 2604.13016](https://arxiv.org/html/2604.13016v1) |
| Prompt breadth crossed with rollout refresh | [2609.25048](https://arxiv.org/html/2609.25048v1) |
| EOS/truncation explanation of OPD length | [2609.20511](https://arxiv.org/html/2609.20511v1) |
| Different solution strategies versus different wording | [2606.29985, Appendix C](https://arxiv.org/html/2606.29985v1) |
| Privileged reference incompatible with an agent's current state | [2608.05219, fixed-state interventions](https://arxiv.org/html/2608.05219v1) |
| Adaptive repair versus new synthetic samples | [REx](https://arxiv.org/html/2405.17503v3), [VRR-Stop](https://arxiv.org/html/2607.17641v1) |

These are substantive precedents, not proof that every narrower question is solved.
Missing a baseline or moving a known intervention to another benchmark is not by
itself a new scientific contribution. Most recent sources above are preprints;
arXiv availability does not establish conference acceptance or independent replication.

## Compute and execution boundary

No experiment is selected or authorized by this memo. Start with CPU asset and
protocol checks. If one question survives, a possible future phase is a maximum
2 GPU-hour throughput/recovery check followed by a **40 A100-hour total pilot cap,
inclusive of that check**. This is a proposed ceiling, not an estimated completion
time. Count all devices, rollout and evaluation work, overhead and shutdown reserve.
The pilot must fit an informative comparison after measured throughput; otherwise
stop and revise before renting. A conditional Q1 study could have a 200-hour cap;
Q2 requires a fresh measured plan. Do not run both automatically or spend the full
1,000-hour overall ceiling to force a publishable outcome. CPU/storage costs and
actual rental prices must be separately stated before any paid phase.

Search date: September 29, 2026. Primary methods/appendices and selected author
source files were read; hashes for retained sources accompany the private audit.
This is bounded novelty due diligence, not a guarantee of absence. The concrete
discussion decision is whether either causal question is worth developing beyond
a careful replication. LT002 remains closed; historical outcomes and exposure
records are unchanged.

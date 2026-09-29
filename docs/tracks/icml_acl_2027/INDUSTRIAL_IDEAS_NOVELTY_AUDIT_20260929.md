# Novelty audit of proxy recipe selection and synthetic tool-data curation

Date: 2026-09-29. Literature, mathematical reasoning and static code inspection.
This supersedes the I1/I2 priorities in [the earlier screening memo](INDUSTRIAL_COURSE_IDEAS_20260929.md).
No empirical results, training, inference, new annotations or paid services were produced.

## Decision

| Candidate | Revised decision | Reason |
| --- | --- | --- |
| I1: proxy-guided recipe elimination under unknown task weights | Withdraw as a recommended original project. | Representative-set regret, multiobjective selection, uncertainty-aware multi-fidelity data optimization and risk-controlled abstention all have direct precedents. No new cross-scale error model or explanatory result has been supplied. |
| I2: correctness filtering versus behavioral coverage in synthetic tool data | Withdraw the broad novelty claim; retain the application area for further investigation only. | Valid-tail loss, verifier selection bias and no-call data interventions are already studied. The proposed controls also fail to identify a unique correctness-versus-coverage effect. |

Industrial usefulness and convenient benchmarks do not establish originality.
Neither an absent exact title nor a missing ablation justifies a new main project.
No replacement direction is automatically selected by this audit.

## I1: direct predecessors, not just similar terminology

| Proposed contribution | Primary work and location inspected | Consequence and boundary |
| --- | --- | --- |
| Keep a small set that remains useful across unknown preferences. | [Regret-Minimizing Representative Databases, PVLDB 2010](https://vldb.org/pvldb/vol3/R99.pdf), section 3, Definitions 2–5. | Defines gain, additive regret, regret ratio and worst-case representative-set selection over utility functions. Its main criterion is relative regret; changing it to additive regret does not by itself establish a novel contribution. |
| Evaluate shortlist damage, not only ranking correlation. | [Can Small Training Runs Reliably Guide Data Curation?, ICLR 2026](https://arxiv.org/html/2512.24503v2), appendix D.1.1/D.2.1. | Already evaluates top-k decision regret and emphasizes recipe-specific target hyperparameter tuning. Unknown weights are an additional objective choice, not a discovered mechanism. |
| Use cheap uncertain trials to decide which expensive trial is worthwhile. | [Data Mixture Optimization: A Multi-fidelity Multi-scale Bayesian Framework, NeurIPS 2025](https://arxiv.org/html/2503.21023v1), sections 3–5. | Jointly chooses mixture, model size and training steps using probabilistic extrapolation and cost-aware acquisition. Its optimization evaluation uses a simulator fitted to 472 actual runs; it is not a universal safety guarantee. |
| Apply proxy selection to SFT while accounting for domain tradeoffs. | [ADMIRE-BayesOpt](https://arxiv.org/html/2508.11551v2), sections 4.2/5.1/6.3.1; 2025 preprint. | Cost-normalized information acquisition over mixtures and sizes, actual SFT panel, task-specific damage hidden by averages, and ID/OOD choice reversals. Robust objectives are discussed rather than completely solved. |
| Return a Pareto set under a budget. | [Efficient Multi-objective Prompt Optimization via Pure-exploration Bandits, ICLR 2026](https://proceedings.iclr.cc/paper_files/paper/2026/hash/4b0713b4f15946acaecb0676389715ed-Abstract-Conference.html), sections 3–7. | Already treats LLM choices as vector-valued arms and recovers a Pareto set. Prompt evaluation is not cross-scale training; the set-valued output itself is nevertheless established. |
| Add calibration and abstain if risk cannot be certified. | [Risk-Controlling Model Selection via Guided Bayesian Optimization, TMLR 2024](https://arxiv.org/pdf/2312.01692), sections 3/5.3/6. | GuideBO combines Pareto-oriented search with held-out risk testing and can return no certified configuration. Its experiments include changing training-data mixtures. It does not certify arbitrary scale extrapolation. |

Further foundational checks: [PaVeBa, AISTATS 2024](https://proceedings.mlr.press/v238/karagozlu24a.html),
sections 2–3, already uses confidence regions for elimination under incomplete
preferences; [Optimal Multi-Fidelity Best-Arm Identification, NeurIPS 2024](https://proceedings.nips.cc/paper_files/paper/2024/hash/dc9e095f668044e7a0909a4ea3926beb-Abstract-Conference.html),
sections 2–4, requires known fidelity-bias bounds;
[MF-OSEMO, AAAI 2020](https://ojs.aaai.org/index.php/AAAI/article/view/6560),
sections 2/4, jointly selects candidates and fidelities for Pareto information per
cost. These are distinct objectives and assumptions, not interchangeable guarantees.

Additional direct context: [DataDecide](https://arxiv.org/html/2504.11393v1),
sections 2–3, already measures task- and scale-dependent data decisions;
[Olmix](https://arxiv.org/html/2602.12237v1), section 3.3/RQ5 and sections 4–5,
compares per-task predictors and reuses evidence as data domains evolve;
[GRAPE](https://arxiv.org/html/2505.20380v1), sections 2–3, addresses group-robust
multi-target mixing. The [earlier memo](INDUSTRIAL_COURSE_IDEAS_20260929.md) also
records LESS, compute-constrained selection and later-adaptation effects.

### Why the proposed mathematical formulation is insufficient

For a finite recipe pool R with performance vectors f(r), shortlist K and a
**bounded, predeclared, nonnegative** weight set W, our proposed quantity was

`R(K) = sup_{w in W} [max_r w^T f(r) - max_{r in K} w^T f(r)]`.

This is a representative-set regret criterion. With a singleton W it reduces to
ordinary shortlist regret. If nonnegative weights are allowed without normalization
or any bound, any positive regret can be scaled without limit. A simplex or other
bounded preference set is essential, not a technical afterthought. With linear
utility, only supported efficient points can be strict winners; this need not equal
the entire Pareto frontier.

Our missing ingredient is evidence about **joint systematic proxy-to-target errors**
across recipes and tasks. Sampling noise, seed variability, scale bias and
recipe-specific optimizer mismatch are different. A confidence interval from test
questions only addresses part of that uncertainty. Ordinary Pareto filtering plus
such an interval cannot manufacture a reliable cross-scale guarantee.

A future contribution would need a justified, falsifiable property of those errors
that existing methods cannot exploit, or a new result under defensible assumptions.
Changing the aggregation, label or output set alone falls below that bar. We have
not identified that property here.

### Assets are usable, but constrain the claim

DataDecide's public scores allow CPU analysis of 25 recipes within one OLMo ladder,
with a 1B target. Only the 1B runs have three full seeds; other scales' second/third
seeds stop early. The fixed training protocol does not identify each recipe's
best performance after its own hyperparameter optimization.

ADMIRE's [official CSV](https://github.com/xo28/ADMIRE-BayesOpt/blob/main/admire_ift_runs/admire_ift_runs.csv)
contains 460 runs: 256/128/76 recipes at 0.5B/3B/7B, with individual task scores and
training times. At most 76 recipes have all target-scale observations; there are
not 256 complete scale triples. Downloadable weights were not independently
verified. These are useful existing resources, not grounds to reproduce the
original expensive training program or claim enterprise procurement ROI.

## I2: prior work already addresses the broad mechanism

| Literature family | Primary source and passage inspected | What it rules out; scope limit |
| --- | --- | --- |
| Curation changes the learned distribution. | [Self-Consuming Generative Models with Curated Data Provably Optimize Human Preferences, NeurIPS 2024](https://arxiv.org/html/2407.09499v1), sections 2/4. | A nominally class-agnostic quality score can induce class imbalance. Its idealized retraining theory and image experiments do not by themselves establish a tool-use effect. |
| Verification error determines synthetic-data value. | [Beyond Model Collapse: Scaling Up with Synthesized Data Requires Verification, ICLR 2025](https://arxiv.org/html/2406.07515v2), section 4.2 and appendix E. | Defines class-specific correct/incorrect retention before symmetric simplification. Asymmetric verifier errors are not a new concept; the classification theory is not a finite-data tool-SFT theorem. |
| Rejecting invalid realizations loses valid rare conditions. | [CasualSynth / CausalSynth, May 2026 preprint](https://arxiv.org/html/2605.17528v1), section 3.4 and appendix C.2. | Explicitly studies this selection mechanism and repair. Its proposed guarantee requires separate scrutiny; see below. |
| Local selection damages broader language coverage. | [When Sample Selection Bias Precipitates Model Collapse](https://arxiv.org/html/2606.13732v2), appendix C.5/Figure 9. | Includes Llama-2-7B/XLSum with technology-local reference filtering and degradation on non-technology data. It is not only an image/Gaussian study; it also does not establish a tool-correctness effect. |
| Verification trades variance reduction against bias. | [Escaping Model Collapse via Synthetic Data Verification](https://arxiv.org/html/2510.16657v3), sections 3–5.3. | Includes a SmolLM2/XSUM experiment in the inspected version. Its theory does not certify arbitrary language-model feedback loops. |
| Match quantity and compare quality with diversity. | [SPARQ](https://arxiv.org/html/2506.06499v2), section 3.2. | Uses a saved pool and fixed-size subsets. Solve-rate quality is not independent correctness, but the generic quality/diversity ablation is already established. |
| Tool-data validation and non-call coverage. | [APIGen](https://arxiv.org/html/2406.18518), sections 3.2/5; [ToolACE](https://arxiv.org/html/2409.00920), sections 2–3. | Semantic validation, non-tool use and clarification already receive attention. Execution success is not the only existing validator. |
| Correct harmful over-calling with training data. | [Data Turnstile](https://arxiv.org/html/2607.29250v1), section 3.3; [Do LLMs Know Tool Irrelevance?](https://arxiv.org/html/2604.11322v1), appendix M.3. | Direct no-call-data ablations and rejection SFT already exist. Adding hard negatives or using SABEval is not sufficient novelty. |

[Trajectory2Task](https://arxiv.org/html/2601.20144) also addresses ambiguous and
infeasible intents. [Cheap Verifiers, Large Blind Spots](https://arxiv.org/html/2609.01345v2),
sections 3–6, further constrains a generic repair-the-rejected-tail proposal:
its real-model runs do not pass its improving-loop sanity gate, so the theoretical
illustration should not be presented as a demonstrated stable LLM improvement.

### The earlier proposed control did not identify the proposed effect

Let g be behavior type, Q true validity, A filter acceptance, pi_g=P(Q=1|g),
t_g=P(A=1|Q=1,g), and e_g=P(A=1|Q=0,g). Conditional probability gives:

`P(A=1|g) = pi_g*t_g + (1-pi_g)*e_g`,

`P_selected(g) is proportional to P_raw(g)*P(A=1|g)`.

Matching overall correctness therefore does not match conditional correctness,
within-type difficulty or the distributions of valid examples. Student learning
can have interactions between these factors. There is no automatically unique
additive decomposition into a correctness effect and a coverage effect. These
identities and the identification warning are standard reasoning, not our novelty.

Accepted-only data are insufficient even with a global acceptance rate. Consider
all-valid examples and a 50% overall acceptance rate. A raw 90/10 call/no-call mix
with 50/50 type-specific retention yields accepted masses 45/5. A raw 50/50 mix
with 90/10 retention yields the same accepted masses. The first has no composition
shift and the second a large one. This is a constructed illustration, not a model
experiment or an observation about a released dataset.

The necessary evidence is a known sampling denominator, decisions at each relevant
stage and independent validity labels. Full rejected texts are not always required
if sufficient metadata exists. A prospective controlled filter on a public labeled
pool can answer a new question; it does not reconstruct a historical filter.

### Static code inspection changes the resource diagnosis

At [Turnstile commit 9a378056](https://github.com/amazon-science/data-turnstile/tree/9a378056258e45237ea12c821f43e713de85fd62):

- [data_generation.py, lines 266–300](https://github.com/amazon-science/data-turnstile/blob/9a378056258e45237ea12c821f43e713de85fd62/turnstile/core/data_generation.py#L266) writes both success and failed generation histories.
- [interaction_builder.py, lines 324–342](https://github.com/amazon-science/data-turnstile/blob/9a378056258e45237ea12c821f43e713de85fd62/turnstile/core/interaction_builder.py#L324) records template identities, attempts, raw outputs, errors and retries. Subsequent processing can advance, retry, revert a previous role or abort.
- The [pinned public dataset tree](https://huggingface.co/datasets/amazon/Turnstile-Synthetic-Domains/tree/70bf9e9a6234e694efa36d1ec6c207c65a695f5b) contains the data, API definitions, README and Git attributes; separate historical generation logs were not present in this tree.

Thus logging capability is verified, historical paired logs are not. The pipeline
also performs adaptive generation/repair; modeling it as one binary filter on a
fixed raw pool would omit part of the intervention. Generated API observations
and structural checks are not independent proof of real execution or semantic
validity. No author code was executed and no historical rejection was invented.

### A concrete mathematical issue, without promotion to a new project

CausalSynth v1 appendix C.2 claims that monotone feedback and larger relative gains
for initially hard conditions guarantee reduced chi-square distributional bias.
The following algebraic counterexample satisfies the stated conditions.

Take two equally likely states with first-attempt success probabilities
p1=(1/10,1/5) and second-attempt conditional probabilities p2=(9/10,1/5).
Take K=2 and keep p_k=p2 for all k>=2. A one-variable SCM V=U,
U~Bernoulli(1/2), supplies the uniform target. All conditional probabilities are interior and monotone.
Cumulative acceptance becomes phi2=(91/100,9/25);
relative gains (91/10,9/5) are larger for the initially harder state.
The accepted distribution changes from (1/3,2/3) to (91/127,36/127).
Its chi-square divergence from (1/2,1/2) increases from 1/9 to 3025/16129.

The conditions allow overcorrection: improved yield need not mean better balance.
This challenges the stated implication, not the paper's reported empirical
measurements. It was independently checked algebraically, without a model run.
A counterexample alone does not establish a useful new tool-data method or
conference contribution; corrected sufficient conditions and their practical
relevance would need further work.

## What would justify revisiting either direction?

For I1, specify the missing cross-scale error property, explain why standard
multi-fidelity/robust selection does not handle it, and show a diagnostic that can
fail on untouched target observations. If fixed-protocol hyperparameter mismatch
explains the observation, do not rename it a new data-quality phenomenon.

For I2, distinguish four possible causes: the generator never attempts a behavior;
correct instances are falsely rejected; genuinely invalid instances are removed;
and adaptive repairs change which conditions survive. A remaining scientific
question is when a finite repair policy improves usable yield while increasing
exposure distortion, and whether its conditions matter in an actual pipeline.
This is an investigation target, not a passed novelty claim. Selection, stratified
sampling and adaptive-allocation literature must still constrain any proposed cure.

The industrial decision would be how a synthetic-data team allocates repair effort
while preserving intended task coverage. A defensible contribution would connect
an explicit failure of an assumption to a measurable prediction and an intervention
that fixes that mechanism at matched cost. Rebalancing a dataset until BFCL rises
would not suffice. Distribution fidelity also need not maximize student utility;
that connection needs its own evidence.

No new benchmark, annotation project or GPU phase is warranted by the current
proposals. Existing evaluations can remain endpoints, with template/tool-family
splits and untouched test labels. They do not supply missing acquisition histories
or correctness truth. The <=1,000 A100-hour ceiling remains a ceiling, not a
spending target, measured phase estimate or evidence of available credit.

The next useful deliverable is an assumption-to-evidence argument with a decisive
falsification criterion. Until that exists, these two original formulations should
not be presented as vetted novel projects.

## Reading and verification boundary

The audit covered classical representative-set selection, noisy vector-bandit
elimination, multi-fidelity optimization, current LLM data-mixture studies,
synthetic-data selection theory, and direct tool-data pipelines. Tables identify
substantive sections inspected; this is a targeted review, not exhaustive citation
coverage. These candidates were constructed from broad course themes, not supplied
as established novel questions. Conference labels are separated from preprints;
GuideBO section references use the readable arXiv version. Selected exact source
checks are recorded in [the source manifest](INDUSTRIAL_NOVELTY_SOURCES_20260929.json).

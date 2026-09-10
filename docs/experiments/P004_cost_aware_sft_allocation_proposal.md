# P004 — cost-aware allocation of problems and solutions for SFT

Date: 2026-09-10 UTC. Status: **proposal for owner review; no new experiment
registered or executed**. The owner requested a response about the project's
framing and concrete deliverables before continuing experiments. E012 remains
prepared and immutable, but execution/startup is paused during this discussion.
This document records our proposed scientific response; private correspondence
and the personally addressed reply stay outside the public repository.

## Model-choice clarification after evidence review

**Current compute constraint:** keep the primary student at 1.5B and the
conditional second-family candidate at 1B. The
[paper/model/compute audit](../../reports/RELATED_WORK_MODEL_COMPUTE_20260910.md)
replaces the earlier default 7B-teacher proposal with a CPU audit of reusable
solutions and a possible bounded Math1.5B-Instruct generation calibration.
Both routes are untested; no teacher is selected. Large-student sweeps and a
32B teacher are outside the minimum plan. Public cached data alone cannot
establish measured generation costs. This narrows the proposal, not a frozen run.

The first concise reply did not adequately expose candidate status or actual
negative results. [The model-selection evidence note](../../reports/MODEL_SELECTION_EVIDENCE_20260910.md)
now ties every choice to completed work. Qwen1.5B has existing synthetic/A800
measurements but needs GSM8K calibration; Math7B was an untested teacher in
the earlier draft; OLMo1B is a planned but untested second family. A privately
retained revised bilingual reply states actual progress and these conditions.
The nine-cell grid remains tentative and must be profiled before a bounded
subset is frozen. Neither published Instruct/TIR benchmark scores nor model
size establish the proposed base/teacher configuration's measured performance.

## Proposed primary question

### Data-scope clarification for review

The [dataset evidence review](../../reports/DATASET_SELECTION_EVIDENCE_20260910.md)
distinguishes question pools, solution corpora and evaluation data in the seven
referenced papers. GSM8K remains the first calibration task. Propose adding
MATH levels 1–3, stratified by subject/difficulty, for decisive second-task
comparisons after feasibility and split-provenance checks. This conditional
extension strengthens the proposed final validation; it does not promise two
full grids or alter a frozen run. The earlier single-task deliverables below
remain a draft pending this scope review.

Audit OpenMathInstruct-2 as a specific reusable-output candidate, initially
restricted to responses linked to original eligible GSM8K/MATH training problems.
Synthetic augmented questions have different answer provenance and are outside
that initial audit population. Reserve GSM-Symbolic and its GSM8K-test parents
for final robustness evaluation only. Keep existing synthetic tasks diagnostic.
Draw problem pools before inspecting solution availability, and never use a
small local teacher's costs to price a different large teacher's cached outputs.
The source-selection and CPU manifest audit have not been executed.

### Allocation question

For a fixed student-training budget and a specified data-acquisition budget,
when is acquiring another problem more valuable than acquiring another usable
solution to a problem already owned? How does that decision change with
relative acquisition prices, problem coverage/difficulty and solution quality?

Problem breadth is an essential baseline, not an assumed winner. The revised
goal would be a tested allocation recommendation with cost-dependent break-even
regions and uncertainty. A more elaborate accounting formula alone is not a
scientific contribution. Path structure, paraphrases and repeated exposure
become targeted explanations or controls after the primary allocation question
is tractable. The study remains **SFT only**, with RL removed from the proposed
course scope, including optional deliverables.

## Why earlier evidence is insufficient

Earlier arithmetic pilots mainly held problem identities fixed while changing
within-problem path allocation or repetition. Their limited matched-dev effects,
poor broader-dev performance and strong matching-induced selection are preserved
in the prior reports. They did not measure acquisition prices or establish an
optimal problem/solution allocation. E011 failed full-proof overfitting, and
E012 has not run. Its short diagnostic ladder could be useful engineering work
later, but is not the next scientific experiment merely because it is ready.

Synthetic problem generation has low marginal cost and does not establish a
human-authoring price premium. Synthetic tasks are useful for exact trajectory
verification and controlled composition splits. Real mathematical questions
must enter the primary empirical study if the claim is meant to guide acquisition
from human-written/curated problem sources.

## Quantities and budgets

Use P for acquired/reviewed distinct problems, K for a target number of accepted,
nonduplicate solutions per problem, and E for exact training exposures. Keep
the previous P/T/R notation only in historical records. Nonduplicate outputs
are not automatically distinct reasoning strategies. Report acquired P,
trainable P, attempts M_i, accepted K_i and actual presentations separately.
The unique-pair count is sum_i K_i; it equals P K only if all targets are reached.

A first approximation is C_data = P c_p + P K c_s, where c_s is the effective
cost per retained solution, including unsuccessful attempts and verification.
Do not assume c_s stays constant with K, problem difficulty or deduplication
threshold. For actual accounting use:

    C_data = sum_i C_problem(i)
           + sum_i sum_(j=1..M_i) C_generation(i,j)
           + C_solution_verification + C_deduplication.

Count teacher input/output tokens, runtime, all rejected/duplicate/truncated
outputs, verification operations and measured curation effort. Record automated
and human checks separately. Ground-truth/reference access and annotation are
not implicitly free in the cost scenario. Distinguish sunk corpus creation
cost from marginal acquisition cost to the user. Already-owned problems have
zero new acquisition cost; new synthetic problems need not cost more than solutions.

First hold SFT supervision and optimizer updates fixed within a comparison and
estimate performance across allocations. Response-token counts, total processed
tokens, padding, sequence lengths and GPU time are distinct measurements;
equal example counts do not guarantee equal compute. On variable-length real
traces, audit matching feasibility before freezing the protocol. Do not silently
discard long correct solutions, truncate reasoning or pretend all cost measures
can be exactly equal. Exact matching that changes the supported population must
be disclosed and challenged, given the earlier selection failures.

Then examine the attainable accuracy/cost frontier under specified c_p values
and measured generation/verification costs at that fixed SFT budget. A total-
cost view adds measured C_SFT. Optimizing across different training budgets
would require a separate, reviewed training-budget sweep; it is not established
by the initial fixed-budget grid.

Because GSM8K is publicly available, subsampling it does not measure human
authoring prices. Proposed cost-ratio analyses must be labeled scenarios,
including low/zero marginal problem cost as well as problem-expensive settings.
A small timing study could measure this project's curation effort, not the
original authors' labor or a universal market rate. A stronger real-dollar
claim would need an independently measured acquisition process.

## Concrete proposed models and data

| Role | Proposed asset | Use and present status |
| --- | --- | --- |
| Primary student | [Qwen/Qwen2.5-1.5B](https://huggingface.co/Qwen/Qwen2.5-1.5B), base | Preserve the current pinned student and within-comparison adaptation recipe; earlier synthetic engineering exists, new allocation study does not |
| Solution source / prospective fixed teacher | Audit existing multi-solution math data; consider [Qwen/Qwen2.5-Math-1.5B-Instruct](https://huggingface.co/Qwen/Qwen2.5-Math-1.5B-Instruct) for bounded local calibration | No source/teacher selected and no correctness yield or cost measured. The earlier Math7B teacher is no longer the default or part of the minimum plan |
| Second student | [allenai/OLMo-2-0425-1B](https://huggingface.co/allenai/OLMo-2-0425-1B), base | Replicate decisive comparisons in a second family after a separate feasibility/profile gate; not yet run |
| Primary real-data task | [GSM8K](https://github.com/openai/grade-school-math) | Human-written arithmetic word problems; draw acquisition pool and separate development from the training split; reserve official test for final frozen evaluation |
| Diagnostic task | Existing verifiable arithmetic program generator | Test exact repetition/path labels and new problem compositions; existing selected arithmetic subsets do not already constitute a clean compositional-generalization benchmark |

Model identities and purposes were checked against the maintainers' model cards.
The GSM8K repository describes human-written problems and separate train/test
data. These sources establish asset identity, not expected performance or
this project's future economic findings. Choose and freeze teacher decoding,
tokenizer/model revisions and maximum trace length after a bounded feasibility
plan is reviewed. An existing teacher's prior training method does not add an
RL stage to the proposed student's SFT study.

## Staged design to discuss, not a launchable grid

1. **Acquisition and selection audit.** Use nested randomly ordered problems
   drawn before inspecting teacher outputs. Preserve strata and sampling seeds;
   split parent problems before generating solutions. Fix teacher/prompt/sampling
   policy across conditions. K is an acquisition target with a bounded attempt
   budget, not a guarantee. Retain problems that fail to supply K solutions in
   accounting; do not select the problem pool by requiring many valid paths.
   Report the trainable subset and failures, including K_i = 0.
2. **Small allocation surface.** Proposed initial GSM8K grid: acquired
   P in {256, 512, 1024}, target K in {1, 2, 4}; freeze token/update budget only
   after feasibility and cost profiling. These nine candidate configurations
   vary both axes, instead of only repricing one fixed P K contour. K = 1
   supplies the single-solution/repetition reference at the same training dose.
   Compare problem-first, solution-first and intermediate allocations without
   presupposing which wins. Two paired seeds for the decisive midpoint contrasts;
   three for the final key comparisons. Numbers are proposed scope, not approved
   GPU jobs or a claim that current remaining allowance can cover them.
3. **Cost frontier and recommendation.** Estimate marginal validation benefit
   of more problems versus more accepted solutions. Examine cost ratios and
   quality/difficulty strata separately before considering a joint factor grid.
   Recommend an allocation from pilot data; evaluate that recommendation on
   fresh training-pool draws and held-out allocations/budget settings, with
   problem-first, solution-first and a simple fixed-mix rule as baselines.
   Use equal stated acquisition constraints and the same SFT budget. If budget
   indivisibility leaves unused funds, report actual spend and slack.
4. **Targeted explanation and robustness.** Compare another sampled solution
   against repeating one accepted trace. Measure duplicate/acceptance yield;
   audit a sample of reasoning steps because correct final answers do not prove
   valid reasoning. Treat text similarity and high-temperature sampling as
   proxies, not guarantees of semantic diversity. Use synthetic exact verifiers
   where available. Difficulty, coverage and output quality cannot all be
   assumed equal merely because their marginal histograms match.

Primary endpoint: held-out pass@1 under fixed decoding, with problem-level and
training-seed uncertainty distinguished. Secondary: fixed-budget pass@k, trace
validity, reproduction and learning curves. Synthetic composition splits need
explicit held-out programs/families; a random GSM8K test split must not be labeled
compositional OOD. Test sets remain inaccessible for allocation selection.
Public benchmark pretraining exposure is an explicit limit; split hygiene alone
does not establish that these questions were unseen during pretraining.

An offline teacher pool generated by this project is useful for reproducibility,
but its full generation cost must be recorded as actual research expenditure.
For third-party public caches, report our retrieval/curation cost separately;
unknown original generation attempts and costs cannot be reconstructed from
accepted outputs alone or described as our measured generation expenditure.
A policy may
only be assigned the counterfactual cost of a predefined replay with no free
peek at unqueried outcomes. Keep this modeled policy cost distinct from money
actually spent. Charge or explicitly amortize calibration/selection overhead;
an oracle that selects after all runs is a labeled upper bound, not a validated
decision rule. Compare any fitted rule against fresh outcomes rather than only
showing a relabeled accuracy table of its training points.

## Proposed course deliverables

Dates below come from the owner's supplied course plan; they were not separately
verified against a course website.

| Date | Concrete proposed deliverable |
| --- | --- |
| October 20, 2026 | Primary Qwen1.5B/GSM8K acquisition pilot and small P/K grid; two seeds for key contrasts; measured generation/verification yield and costs; token/update audit; preliminary accuracy-versus-cost curves; course report/presentation |
| December 14, 2026 | Three seeds for key primary comparisons; validate allocation recommendations on independent problem draws and allocations not used to fit the recommendation; replicate decisive comparisons with OLMo2-1B; targeted quality/diversity checks; release reproducible data manifests, code, cost accounting and final report |

The synthetic generator supports diagnostics; neither a new graph benchmark nor
RL is a prerequisite for these course deliverables. A fully factored sweep of
problem prices, problem quality, difficulty, solution diversity, model families
and training budgets is outside the minimum plan. Exact training/generation caps
and a funded scope must be agreed before execution. Current original allowance
remains 5971/7200 process seconds used, 1229 left, 16 receipts, zero reservations.

## Related work and limits of the proposed contribution

This is a bounded primary-source check, not an exhaustive novelty review.

- [CoScale-RL](https://arxiv.org/html/2601.14695v1), including its SFT data-efficiency
  ablation, already studies scaling solutions per problem; its broader pipeline
  also uses RL. A generic problem-count versus solution-count comparison is
  not by itself a new contribution.
- [Data Repetition Beats Data Scaling in Long-CoT SFT](https://arxiv.org/abs/2602.11149)
  reports repetition advantages under fixed updates in its tested settings.
  Greater problem breadth is therefore a baseline to test, not a universal law.
- [Why Do Reasoning Models Lose Coverage?](https://arxiv.org/abs/2605.17026)
  studies within-problem versus dataset-level diversity and coverage; see the
  earlier bounded comparison in the project's positioning report.
- [Spend Wisely](https://arxiv.org/abs/2501.18962) already studies allocating
  generation/training budgets across iterative synthetic-data bootstrapping.
  A broad claim to introduce cost-aware post-training allocation is untenable.

The candidate distinction is the asymmetric acquisition decision between new
inputs and additional usable outputs, with rejection/duplicate costs and
out-of-sample validation of the recommendation. This remains a proposed
distinction to test against further literature and evidence, not a verified
novelty claim, optimality theorem or publication guarantee.

## Next action

Review the proposed framing and the personally addressed reply first. Then
prepare a revised abstract and a bounded acquisition/feasibility protocol with
actual compute estimates. Decide explicitly whether any E012 engineering work
still serves the revised question. Do not launch E012, teacher sampling, real-
data SFT, a new main grid, paid APIs or another rental during this response task.

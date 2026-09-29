# Course-aligned research with an industrial decision

Date: 2026-09-29. Status: additional literature/asset screening, no experiments.
The new criterion is relevance to an identifiable industrial workflow, alongside
scientific value, existing evaluation assets and a <=1,000 A100 GPU-hour ceiling.
It changes exploration priorities; no new main project or compute phase is admitted.

## Industrial relevance and course fit

The [syllabus](https://www.sewonmin.com/courses/cs294_288/) includes data curation,
small-scale prediction, synthetic data, recursive training, provenance, attribution
and data valuation. The supplied project guidance permits follow-ups to reading-list
papers. A project need not fit only the six suggested titles. However, simply
improving an agent's benchmark score remains insufficient: the intervention and
research claim must concern data, its use, its provenance or its measurement.

| Research family | Industrial stakeholder and decision | Primary evidence of an actual workflow; limits |
| --- | --- | --- |
| Synthetic-data curation | Training teams decide which generated records are usable and which behaviors their data covers. | [NVIDIA's planning guide](https://docs.nvidia.com/nemotron/nightly/sdg/planning.html) and [Amazon's Data Turnstile](https://arxiv.org/html/2607.29250v1) describe generation, validation and adaptation pipelines. This establishes relevance, not that our proposed intervention helps them. |
| Proxy-guided data decisions | Model/data teams shortlist source mixtures, filters or recipes before expensive target-scale trials. | [DataDecide](https://arxiv.org/html/2504.11393v1) and [Olmix](https://arxiv.org/html/2602.12237v1) supply direct research workflows and public artifacts. A recipe score is not a supplier's price or economic ROI. |
| Enterprise retrieval/data governance | Application teams maintain a usable document index and decide which copies/versions to retain. | [Microsoft Copilot Studio documentation](https://learn.microsoft.com/en-us/microsoft-copilot-studio/guidance/retrieval-augmented-generation) describes organization-specific retrieval, cited answers and governance. It does not validate our scientific question. |
| Distillation auditing | Model providers investigate or prevent unwanted extraction of their outputs/capabilities. | [Anthropic's account](https://www.anthropic.com/news/detecting-and-preventing-distillation-attacks) documents investment in detection, emphasizing traffic and infrastructure evidence. That is not validation of output-only retrospective attribution. |
| AI-text auditing | Publishers/platforms assess content provenance; data teams assess corpus composition. | [Pangram's publisher-facing product](https://www.pangram.com/use-cases/publishing) demonstrates a commercial use case. Vendor accuracy claims are not independent scientific evidence; individual detection and population estimation are different tasks. |

The earlier audit topics are therefore industrially relevant. Their users are
more specialized than the general training and application workflows above.
Professional skill transfer and novelty should be assessed separately.

## Candidate I1: selective elimination of data recipes under uncertain objectives

**Discussion priority: highest new candidate for a low-cost feasibility review;
novelty remains conditional.**

A team may not yet know the exact weighting of its eventual product capabilities.
Instead of insisting on one winner from small-model experiments, can it discard a
useful fraction of data recipes without discarding recipes that matter at the
larger target scale for plausible task preferences?

This asks whether the *decision to stop investing in a data recipe* is supported
by the available evidence. It does not assume a universal scalar data-quality
ranking. It connects data choice, scale and the deployment objective, making it
more than an additional model-improvement technique.

### Proposed estimand and comparison

For a fixed existing recipe set R, let U(r,w) be target-scale task utility under a
predeclared task-weight vector w. A proxy procedure outputs a retained set K.
A useful outcome is the maximum loss from that shortlist over a declared weight
set W:

`max_{w in W} [ max_{r in R} U(r,w) - max_{r in K} U(r,w) ]`.

This is an existing decision-theoretic quantity, not a proposed theorem. Also report
how many recipes are retained, proxy compute, errors in eliminating potentially
useful recipes, and uncertainty. The task normalization and practically meaningful
margin must be fixed before examining the target results. W expresses research
scenarios, not an observed enterprise workload unless such evidence is supplied.

Use the published DataDecide recipes and original OLMES tasks. Small-scale records
produce shortlists; full 1B records serve as the held-out target. Compare average
score top-k, taskwise Pareto retention, worst-task ranking, ordinary uncertainty
rules, and retain-all. Match shortlist size or saved trial cost. Keeping everything
is a necessary baseline, not a successful cost-saving result.

Separate development/calibration from final target evaluation. Hold out recipe
families where possible: several recipes share source corpora and transformation
rules. Checkpoints of one training run are not independent trials. Different task
weights also do not create new independent models. Training-seed variation,
evaluation noise and systematic cross-scale error must be distinguished; a bootstrap
on evaluation questions cannot certify a cross-scale error guarantee.

### Closest work and what is already known

| Source | Direct overlap | Remaining distinction to establish |
| --- | --- | --- |
| [LESS, ICML 2024](https://arxiv.org/html/2402.04333v3), section 4.1/appendix D.5 | Small-model data selection and transfer across sizes/families, including failures. | Another transfer plot is insufficient. |
| [Small-to-Large Generalization](https://arxiv.org/html/2505.16260v1), sections 2–3 | Cross-scale data influence and small-proxy selection. | Do not claim the first scalable proxy for data value. |
| [DataDecide, ICML 2025](https://arxiv.org/html/2504.11393v1), sections 2–3 | Pairwise decision accuracy, scale prediction, multiple proxy metrics and compute comparisons. | Changing rank correlation to decision accuracy is already done. |
| [Can Small Training Runs Reliably Guide Data Curation?](https://arxiv.org/html/2512.24503v2), sections 3–6/appendix D.1.1 | Hyperparameter-induced instability, tiny-learning-rate proxies, target-specific tuning and top-k decision regret. | A new regret metric or learning-rate ablation alone is not a contribution. |
| [GRAPE](https://arxiv.org/html/2505.20380v1), sections 2–3 | Multi-objective/minimax data mixture optimization. | Pareto or robust optimization is not new. |
| [Compute-constrained Data Selection](https://github.com/oseyosey/CCDS), ICLR 2025 | Selection overhead and training share a compute budget. | Accounting for selection cost is necessary, not novel. |
| [Olmix](https://arxiv.org/html/2602.12237v1), sections 3–5 | Proxy-based mixtures and reuse after source addition, removal or revision. | Reusing earlier data scores is not a fresh industrial idea. |
| [The Long-Term Effects of Data Selection in LLM Fine-Tuning](https://arxiv.org/html/2605.30537v1), sections 4–6 | Multi-stage adaptation, forgetting and reversal of selection rankings. | Generic short-term versus long-term utility is already covered. |

The candidate's narrower difference is *selective cross-scale elimination under
an uncertain objective*, evaluated by retained-set risk and savings. We did not
verify a paper completing that exact study, but novelty is not established. It
must outperform simple baselines or expose a reproducible limitation that changes
how data trials should be designed. A repackaged Pareto plot would not suffice.

### Asset and cost gate

The [official repository](https://github.com/allenai/DataDecide) links public model
and evaluation releases. [Summary evaluation results](https://huggingface.co/datasets/allenai/DataDecide-eval-results)
are reported as 839 MB/1,410,750 rows; [full instance results](https://huggingface.co/datasets/allenai/DataDecide-eval-instances)
are much larger, about 123 GB, and should only be fetched selectively if required.
The 1B target has three full seeds. Other scales' second/third seeds stop at 25% of
the target training budget; they are not three full trajectories at every scale.

An initial analysis can use existing results on CPU, with zero new GPU training.
That does not promise a CPU runtime before profiling. First audit table schemas,
metric/recipe/seed identity, missingness and licensing; no need to download all
weights or regenerate predictions. This turn checked documentation/metadata, not
those numerical outcomes.

The scope is one OLMo model family, target scale <=1B and fixed training recipes.
It cannot demonstrate transfer to a new model family, SFT/RL stage or production
model, nor establish procurement ROI. Recipe-specific hyperparameter tuning is
also a known limitation of the released fixed-configuration panel.

**Stop criteria:** useful risk requires retaining almost all recipes; average top-k
or ordinary Pareto/uncertainty baselines match the result; conclusions collapse on
recipe-family holdout; or the effect is just uncontrolled recipe-specific tuning.
A narrow negative result may still inform a course study, but a conference-level
contribution is not guaranteed.

## Candidate I2: correctness filtering versus behavioral coverage in synthetic tool data

**Closest to existing post-training skills; useful platform, currently blocked as
a new causal research project.**

A potential data question is whether gains from verification-based filtering come
from correcting labels or from changing the distribution of actions represented
in training. At matched correctness and exposure, does a filtering policy improve
valid tool use while worsening situations requiring clarification or no tool use?
These are separate risks and should not be cancelled inside an average score.

The relevant comparison is between selection interventions on the *same raw
candidate pool*, with matched training token budget and controls for correctness,
length, tool/task family and initialization. A final accepted dataset alone cannot
reveal what the production filter removed. New runs on invented rejected data
would answer a different question.

This idea has very strong direct neighbors:

- [APIGen](https://arxiv.org/html/2406.18518), sections 3.2/5, already separates
  structural, execution and semantic validation.
- [ToolACE](https://arxiv.org/html/2409.00920), sections 2–3, includes non-tool-use,
  clarification and user-constraint checks, with quality/diversity ablations.
- [Amazon Data Turnstile](https://arxiv.org/html/2607.29250v1), section 3.3, directly
  reports that call-only tuning degrades irrelevance performance and that negative
  examples recover much of it; its multi-turn study includes policy constraints.
- [Trajectory2Task](https://arxiv.org/html/2601.20144), ACL 2026, studies ambiguous,
  changing and infeasible intents using verifiable synthetic trajectories.
- [Do LLMs Know Tool Irrelevance?](https://arxiv.org/html/2604.11322v1), ACL 2026,
  already studies structural alignment bias **and rejection SFT**, with template
  splits. Adding hard negatives is not by itself new.
- [CurateEvo](https://arxiv.org/html/2607.06140v1) already adapts curation based on
  development failures. A generic feedback-to-data loop is insufficient.

The [pinned Turnstile implementation](https://github.com/amazon-science/data-turnstile/tree/9a378056258e45237ea12c821f43e713de85fd62),
[released corpus](https://huggingface.co/datasets/amazon/Turnstile-Synthetic-Domains/tree/70bf9e9a6234e694efa36d1ec6c207c65a695f5b),
and [SABEval implementation/data](https://github.com/along-l/irrelevant-tool/tree/6f41fe970ca14d2699447e3b0c184b77afc45eb7)
are real assets. The corpus has 100,262 records and 1,025 APIs in the inspected
release. Its noncommercial license also separates research reuse from product
licensing. Static BFCL/SABEval checks and small students are plausible within the
ceiling, subject to profiling; multi-turn simulator/model costs are additional.

**Current no-go:** the rejected pool and per-stage validation records were not
verified. Without them, do not claim a causal effect of the original filter.
If the project reduces to adding rejection/clarification examples, stop: that has
direct precedent. Keep the platform for reproduction or a genuinely distinct
question, not as an already-selected novel idea.

## Candidate I3: document curation and changing facts in enterprise RAG

**Strong application motivation; insufficient present novelty/asset support.**

A narrow question is whether fixed deduplication decisions that save retrieval
and context cost remove the only evidence for a changed fact in a document family.
This concerns what data survives ingestion, rather than building another retriever.
It would require existing version/fact labels, frozen QA and matched retrieval
budgets. A schema example is a policy copied many times except for one operative
limit; we have not observed this failure experimentally.

Generic citation-versus-causal-influence questions have already been studied in
[Correctness is not Faithfulness](https://arxiv.org/abs/2412.18004),
[Source Attribution in RAG](https://arxiv.org/abs/2507.04480) and
[ProvenAI](https://arxiv.org/abs/2606.26449). Repetition versus independent evidence
also has direct work, including [GroupQA](https://aclanthology.org/2026.findings-acl.2003/).
[GVD](https://arxiv.org/abs/2609.17696) and
[chunking/duplicate-detection work](https://arxiv.org/abs/2607.24332) further constrain
the version/deduplication proposal. These links are prior-work exclusions, not
claims that all code or data is released.

[EnterpriseRAG-Bench](https://arxiv.org/html/2605.05253v1) has a substantial synthetic
company corpus and QA, including near-duplicates and conflicting information.
However, only 20 conflicting-information questions were identified; official answer
evaluation relies on model judging and facts may be revised. The reviewed GVD
enterprise study includes confidential documents and human-reviewed rules. These
are poor foundations for a strong, label-free, solo causal study without extra
benchmark work. Source revocation and purchase value additionally require lineage,
authorization or value labels that these QA releases do not provide.

**Current no-go:** do not invent those labels or infer removal rights from text
similarity. A new reliable public version/fact resource or a sharper non-overlapping
question is required before promoting this direction.

## Recommendation and next discussion

Prioritize I1 for a bounded offline literature/schema check; keep I2 as the strongest
industrial post-training platform but do not train to rescue a blocked hypothesis.
I3 remains lower priority. The previously reviewed distillation and text-audit
questions remain available rather than being dismissed as industrially irrelevant.

The main discussion question is whether predicting **which data investments can
be safely ruled out** supplies enough scientific value beyond known ranking/regret
results, and what extra evidence would make it more than an application of
standard selective decision-making. For I2, the decisive resource is the raw pool
and filter logs, not more GPU hours. For I3, it is reliable version/provenance truth.

No experiments, numerical conclusions, new annotations, server actions or paid
services were undertaken. An eventual phase still requires a finite protocol,
measured resource plan and startup review. Industry evidence here establishes
workflow relevance, not adoption of our untested ideas or comparative scientific
importance. Source review through September 29 is not a guarantee of novelty.

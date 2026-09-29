# Data-audit direction rescreen — September 29, 2026

Status: literature and asset audit, **not a selected research contribution or an
execution protocol**. The earlier DATE-LM answer-only proposal remains withdrawn.
No training, model inference, paid API call, server action, benchmark submission,
or external correspondence occurred in this review.

## Decision

Keep one conditional investigation: **does a fixed data-quality filter change
AI-origin measurement enough to reverse the estimated effect of curation?**
Its possible contribution is an empirical audit of particular curation pipelines,
not a new discovery that distribution shift breaks calibration. That general
failure, and multicalibration as a remedy under assumptions, already have direct
precedents. No candidate presently passes a full novelty-and-feasibility gate.

SafeGEO is a usable reserve evaluation platform, but this review found no clear
new question on it. Do not promote a platform into a research direction merely
because its files are downloadable. DistillDetect has cheap reproduction assets
but lacks the verified controlled trajectories needed for the most relevant new
interventions. These judgments concern the proposed cuts, not the value of entire
research fields.

## Scope and evidence standard

Six families were screened: data-supply forecasting, population AI-text auditing,
human–AI coauthorship, distillation detection, influential-text reuse, and GEO.
The resource ceiling is 1,000 A100 GPU-hours; prefer existing labels, models and
evaluation code, with no new benchmark or annotation campaign as a prerequisite.

The review used arXiv, ACL Anthology, conference proceedings/OpenReview and
author-maintained repositories/model cards. Close papers were examined at the
methods/results/limitations level, with targeted appendix checks. This is not a
claim that every cited paper was exhaustively read or reproduced. Recent
preprints are relevant prior work regardless of acceptance; venue claims are
distinguished from verified proceedings. Searches were conducted through
September 29, 2026 and cannot certify absence of unpublished or unindexed work.

Representative search families included `AI-generated text + quality filtering /
curation / prevalence / selection bias`, `quantification + covariate shift`,
`AI editing + operation / stylometry`, `distillation detection + multiteacher /
post-finetuning / watermark`, `text reuse + source retrieval`, and `GEO + defense /
utility / source redundancy`. Backward references and official release links were
followed for the closest matches. Read-only research agents helped audit three
families; small primary-source artifacts and public metadata were checked locally.

## Exclusion and overlap matrix

| Family / tempting question | Closest evidence and inspected location | Consequence |
|---|---|---|
| Data scarcity: update the date at which text runs out | [Villalobos et al., ICML 2024](https://arxiv.org/abs/2211.04325) already models usable stock, growth, repetitions and uncertainty. | A new forecast needs defensible new measurements/assumptions. Low GPU cost does not remove the solo data-collection and validation burden; poor fit to the present benchmark preference. |
| AI detection: length/domain calibration | [MCP/RealDet](https://arxiv.org/html/2505.05084v2), length-aware method and §5.6–5.7, already compares calibration corpora and calibration methods. [RAID, ACL 2024](https://aclanthology.org/2024.acl-long.674/) already tests detector robustness. | Generic domain/length correction is not the new question. |
| Coauthorship: editing amount or operations affect detection | [EditLens](https://openreview.net/pdf?id=gOkitaPCfZ) studies editing extent and transfer; [OpAI-Bench, June 2026](https://arxiv.org/html/2606.06481v1), §§3–4/App. E, studies progressive operations, coverage, multiple granularities and transfer. | Reject generic editing-degree/history extensions. These labels do not automatically measure meaningful creative human contribution. |
| Cheap style features distinguish writing from editing | [GEN, September 22 v2](https://arxiv.org/html/2608.27855v2), §§4–6/App. C–F, already studies 14 stylometric features, length controls and combination with EditLens. Some appendix holdouts concern feature stability, not a universal OOD-accuracy guarantee. | A cheap stylistic detector or editing-feature fusion alone is not an uncovered contribution. |
| Distillation detection: threshold/reference/domain sensitivity | [Reference-Based Distillation Detection, July 2026](https://arxiv.org/html/2607.09692v1), §5/Table 6, App. B/E, already studies teacher/student holdouts, reference and probe choices, and surface signals. [Who Taught You That?, Findings ACL 2025](https://aclanthology.org/2025.findings-acl.173.pdf), §3, studies teacher-tracing signals. | Do not sell probe subsampling or threshold failure as a new main project. Multistage interventions need additional controlled histories. |
| Active watermark: mixing teachers, keys or paraphrases | [Can LLM Watermarks Robustly Prevent Unauthorized Knowledge Distillation?, ACL 2025](https://arxiv.org/html/2502.11598v2), §§3–5.2, already attacks watermarks by paraphrasing/neutralization and mixed keys/schemes. [Antidistillation Fingerprinting](https://arxiv.org/html/2602.03812v2), §5/App. B, already varies marked fractions and proxy/student mismatch. | These intuitively appealing variants have direct predecessors. |
| Active watermark: filtering, dose and later modification | [TextSeal](https://arxiv.org/html/2605.12456v1), §6/App. A.4/E.4, includes quality filtering and trace/token-matched controls. [ReasMark, ACL 2026](https://aclanthology.org/2026.acl-long.2185.pdf), §5.7, tests later LoRA, pruning and quantization. | A remaining limitation is not automatically an available benchmark; reusable complete student suites were not verified. |
| Influential writing: repeated text means low creativity | [Death of the Novel(ty)](https://arxiv.org/html/2509.22641v2), §§2–5, already compares n-gram novelty with expert creativity/pragmaticality judgments. [Non-Adversarial Reproduction, ICLR 2025](https://proceedings.iclr.cc/paper_files/paper/2025/file/861777345d8b03ec648e768cd54f1c42-Paper-Conference.pdf), §§2–4, compares web overlap in benign model outputs and human writing. | Overlap, creativity, historical influence and plagiarism are different claims. An award-specific audit needs a defensible sampled corpus and source evidence, not just a new book list. |
| Reuse detection beyond lexical similarity | [PAN 2025 overview](https://arxiv.org/html/2510.06805v1) defines alignment labels and cross-edition evaluation. [SCDG, August 2026](https://arxiv.org/html/2608.03859v1), Methodology/Experimental Setup, already uses source-conditioned likelihood gain, source-evidence interventions and same-topic controls. | Neither a semantic-reuse detector nor conditional likelihood is an unexplored idea. PAN-derived labels do not establish misconduct in naturally occurring writing. |
| GEO visibility versus user value | [SafeGEO](https://arxiv.org/abs/2606.28356) already evaluates promotion, constraint violations, utility and several evidence-processing defenses. Use its [September 1 camera-ready/release](https://github.com/QianfengWen/SafeGEO/tree/7356da2deee31d024656eac25af42a9bb798cce2), not a mixture of release versions. | Reject the broad visibility/utility tradeoff as our contribution. |
| Detect harmful GEO while preserving benign rewrites | [Counter-GEO-Bench](https://arxiv.org/html/2609.02316v1), §§3–5 and transfer/threshold appendices, already compares paired information-preserving/distorting rewrites. [GEO Defender](https://arxiv.org/html/2609.02964v1) studies fact-preserving manipulation and benign-evidence retention. | Both are September 2026 direct overlaps. Their attack-label meanings also differ; a pooled detector score would not be a common harm metric. |
| GEO proxy evasion or repeated corroboration | [2026 GEO-Bench](https://arxiv.org/html/2605.29107v1) tests ranking and proxy-detection signals. [Polymorphic Sybil Poisoning](https://arxiv.org/html/2607.03739v1) tests redundant/diverse coordinated evidence, forced exposure and deduplication. | Reject generic repetition-as-independent-evidence as a new GEO mechanism. The latter paper's §9 still defers release URLs; it is prior work, not a verified available dataset. |

## Conditional candidate: curation and source measurement

**Question.** On a fixed existing corpus with known generation provenance, does a
published quality filter cause a frozen audit pipeline to misstate the direction
of change in the fraction of AI-generated documents, or the ordering of two
curation policies? Does the effect survive domain/length controls and established
quantification corrections?

**Scientific object.** The interaction between data selection and the measurement
of the selected data. The measured quantity is a document fraction within a
declared finite benchmark population, not Internet-wide prevalence, percentage of
AI-authored tokens, or a model's probability that a particular author used AI.
Quality here means the selected filter's operational criterion; an educational
score is not independent human ground truth for general quality.

**Why it matters.** A before/after detector-positive rate could make a filtering
recipe appear to reduce synthetic data when it mainly changes which examples the
detector recognizes. This would mislead provenance reporting and the comparison
of data curation policies. Whether that happens materially under actual published
filters is an empirical question, not a result established here.

The basic decomposition is already standard. With retained-set prevalence `p`,
true-positive rate `t` and false-positive rate `f`, the detector-positive fraction
is `r = p*t + (1-p)*f`. A correction using pre-filter rates `t0,f0` has bias
`[p*(t-t0) + (1-p)*(f-f0)]/(t0-f0)` when the denominator is nonzero. We claim no
novelty for this identity or for failure of error-rate transport.

### Closest collision and the remaining burden

[González, Moreo and Sebastiani, DMKD 2024](https://arxiv.org/abs/2310.04565),
especially §5.5, already evaluates quantification under class-conditional shifts.
[Linder et al., April 2026](https://arxiv.org/abs/2604.21549), Results/Discussion,
connects prevalence bias to subgroup calibration, explicitly mentions threshold
filtering, and provides [multicalibration baselines and replication materials](https://github.com/facebookresearch/multicalibrated_llm_measurement).
Its guarantees require adequate feature coverage and stable conditional outcomes;
using an arbitrary finite set of metadata does not automatically satisfy them.

Even the intuition that quality filters may favor generated prose was raised in
[FineWeb discussion 81](https://huggingface.co/datasets/HuggingFaceFW/fineweb/discussions/81).
That discussion is a question, not an empirical finding, but rules out presenting
the intuition as unprecedented.

This review did not identify a direct experiment jointly covering published text
curation recipes, known AI provenance, decision-direction/ranking errors and the
strong corrections above. **That limited search result is not proof of novelty.**
The strongest objection is that this may remain an application of known shift
theory to a convenient non-web benchmark. A useful course audit and a substantial
new conference contribution are different thresholds. If ordinary stratification
or existing methods fully explain the observations, retain the result as a
reproduction and do not expand it into an expensive main project.

### Assets actually checked

| Asset | Verified public state | Important limitation |
|---|---|---|
| [RAID](https://github.com/liamdugan/raid) | Labeled train/extra; HF dataset revision `865cac74188466cb0c3b7574a10204007b57a459`, ungated metadata. | Official test labels are hidden. Leaderboard predictions are test submissions; no labeled-train score cache was verified. A grouped split of train is a diagnostic, not an official leaderboard result. |
| [FineWeb-Edu classifier](https://huggingface.co/HuggingFaceFW/fineweb-edu-classifier) | Ungated revision `284663cbb2dabf9bda30d8f8cc49601251ee1631`; released encoder/regression head and inference description. | It predicts an LLM-annotated educational criterion and has documented OOD/style limitations. It is not a human-quality oracle. No weights were downloaded or timed. |
| [Gopher rules in DataTrove](https://github.com/huggingface/datatrove/blob/795bc64a951cf1d1667976ab3fb97b849cef3385/src/datatrove/pipeline/filters/gopher_quality_filter.py) | Public deterministic implementation; observed repository revision `795bc64a951cf1d1667976ab3fb97b849cef3385`. | Freeze the exact defaults before use. A polished benchmark may almost entirely pass; do not tune thresholds after seeing labels to manufacture an effect. |
| [DCLM fastText filter](https://huggingface.co/mlfoundations/fasttext-oh-eli5) | Public CPU-capable model; positive examples come from OpenHermes 2.5 and Reddit ELI5. | Preferential retention could reflect the filter's training sources/genres. ELI5 overlap requires explicit isolation; do not infer a universal fluency mechanism. |
| [BEEMO](https://huggingface.co/datasets/toloka/beemo), [HC3](https://github.com/Hello-SimpleAI/chatgpt-comparison-detection) | Public text/origin-condition labels; HC3 also supplies detectors. | No aligned detector-score cache was verified here. Edited AI text is not pure human text; HC3 is not evidence about present-day generators. Neither is a population-prevalence benchmark. |

Public metadata and small documentation/source files were read, with local hashes
retained. This verifies release properties, not complete dataset integrity,
independent split construction, license compliance of every upstream component,
model reproducibility or execution throughput.

### Minimal informative design, still prospective

1. Use one frozen, labeled corpus. Preserve provenance labels and original examples.
   Group all versions of a source/prompt into one partition. Separate detector
   training, calibration, development and final audit; do not relabel official
   hidden-test data or invent human-contribution percentages.
2. Freeze at most two filter families and their published settings before examining
   final outcomes. Include no-filter and retention-matched random-selection
   controls. Report the retained/deleted denominator and per-class retention.
3. Report true versus estimated *changes*, signed bias and policy ranking, alongside
   the original detection task's appropriate metrics. Use domain and length
   stratification; keep paired versions together in uncertainty estimation.
4. Compare raw counts, ACC/PACC, global calibration, domain/length stratification,
   IPW and multicalibration. Include direct random/stratified labeled auditing and
   [prediction-powered inference](https://arxiv.org/abs/2301.09633) where sampling
   assumptions and the label budget permit. These are existing statistical tools,
   not proposed inventions.
   Count every calibration label; final audit labels never enter corrections.
5. Treat simple covariate reweighting as a competing explanation. Distinguish
   heuristic and learned filters, source overlap and model style; do not call a
   correlation evidence of a shared internal mechanism. A reversal requires
   uncertainty-aware effect sizes, not opposite signs of two near-zero estimates.

This adds a diagnostic protocol on an established dataset. It does not create a
new benchmark, and it also does not inherit external validity just by using one.
The protocol, detector choice, sample-size/power calculation and complete cost
estimate must be finished before model execution.

## Reserve assets, with no selected question

[SafeGEO](https://huggingface.co/datasets/wieeii/SafeGEO) is ungated at revision
`bd3d71ad9b256f6799a2facae6eed262f5f4631f`. The matching official release provides
600 base cases/40,800 expanded instances and a 120-case/600-instance Diamond
subset, a local-model runner and rule-based headline scoring. Aggregate results
are available; raw model-response caches were not verified. Diamond is selected
for strong attacks and its rows are dependent, so it is not a random population
sample. Its utility labels are benchmark reference labels, not universal user
preferences. No new GEO experiment is proposed merely to change the model or
prompt on this subset.

[Counter-GEO's card](https://huggingface.co/datasets/counter-geo/counter-geo-bench)
and the paper disclose gated access, ten withheld distorted rewrites and omission
of original sources. No access was requested or terms accepted. Its reported full
protocol cannot be promised as an immediately available local reproduction.

[DistillDetect](https://github.com/RajatRawat-creator/DistillDetect) supplies cached
probe likelihoods suitable for CPU reproduction. The official controlled student
weights were not verified. Third-party reproduction checkpoints exist but are not
equivalent to the official controlled suite. They do not remove the need to
validate any new multistage intervention and its true lineage.

## Two-day decision path and resource stops

- First finish the grouped-split, label, score-cache and license inventory and
  the closest-paper comparison. These are CPU/read-only tasks, with **zero new
  GPU-hours used so far**. Do not promise empirical bias results from caches that
  have not been joined to labels.
- If the question and assets survive, write a finite reproduction/profiling plan.
  A proposed first-stage ceiling is 20 A100-hours and a provisional whole-study
  ceiling of 300, reserving the balance of the 1,000-hour limit. These are
  **planning stop limits, not measured runtime estimates or spending approval**.
  Batch/token counts and actual throughput must establish an all-inclusive
  estimate before an owner-started paid phase.
- Stop admission if the closest work already answers the same intervention,
  post-filter samples are too sparse, proper grouped evaluation is unavailable,
  or the proposed evidence only repeats known calibration failure. Do not add
  filters, thresholds, models or labels after a negative screen to rescue a story.
- Preserve all outcomes. An informative negative pilot can close this candidate;
  the budget is not a reason to continue. Old LT002 results remain immutable,
  its instance OFF and its heartbeat paused.

The next decision is whether this one bounded audit is informative enough to run,
not whether a new named method has already been discovered.

# Distillation and AI-text auditing: evidence before experiments

Review date: 2026-09-29. Status: literature and public-asset review only. No model
inference, training, paid API call, benchmark score or server action was performed.
All numerical results below belong to the cited authors, not this project.

## Decision

Prioritize **distillation auditing for further investigation**, reflecting the
research interest and available controlled assets. Do not select a main method or
claim a novel project yet. Generic post-SFT detection, teacher switching, related
teacher confusion and watermark survival under further training have direct prior
work. Keep the curation/AI-origin measurement question as a conditional backup.
AI-text auditing is active; its problem is overlap and external validity, not an
absence of recent research.

This supersedes the exploration priority in [the earlier six-family
rescreen](DATA_AUDIT_RESCREEN_20260929.md), not its documented exclusions. The two
families come from the suggested course topics: distillation detection and
AI-generated-text auditing/data curation. The narrower questions below are our
literature-driven formulations, not assignments or endorsements by an instructor.
The [course syllabus](https://www.sewonmin.com/courses/cs294_288/) supplies the
broader data-centered context; the private supplied topic sheet is not republished.

## What the questions mean

| Object of inference | What must be known or controlled | What a positive result does not establish |
| --- | --- | --- |
| Teacher identification | A student and a specified teacher candidate pool | That a teacher was used if every candidate is wrong |
| Candidate-use detection | An explicit null distribution for students not exposed to the candidate | Complete ancestry, direct rather than indirect exposure, or authorization |
| Passive retrospective attribution | Current behavior; possibly a genuine pre-distillation reference | Historical facts from resemblance alone |
| Active watermark detection | Previously inserted signal, secret evidence, specified detector | Protection of historical outputs that were never marked |
| Training-data effect | An intervention replacing or removing a defined exposure | Which teacher originally invented particular knowledge |
| AI-text prevalence | A defined population, source labels or defensible calibration assumptions | The true fraction from the detector-positive fraction alone |

A common base checkpoint lets us isolate *additional* controlled exposure. It does
not certify that the base never saw related sources. Many probes from one model
are not many independent training histories. A low model-level false-positive
rate cannot be established with a handful of negative models.

The distinction is substantive: [Zhang et al., SaTML 2025 position paper,
sections 3–5](https://arxiv.org/html/2409.19798v2) analyze why membership evidence
depends on the counterfactual/null distribution. Controlled experiments can test a
specified null; they do not automatically validate accusations about opaque
production models. Randomized planted signals add assumptions and evidence, but
are not universal proof of direct provenance.

## Closest distillation work and exclusions

| Primary source; verified reading scope | Established coverage | Consequence for this project |
| --- | --- | --- |
| [Reference-Based Distillation Detection / DistillDetect](https://arxiv.org/html/2607.09692v1), 2026 preprint; sections 3–5, appendices A–C | Reference-normalized teacher-response likelihoods; dose trajectories, teacher holdout, reference choice and probe-domain checks. The controlled analysis retains 19 utility-improving students from 24 trained combinations. | Neither a generic dose study nor teacher holdout is new. Removing a true teacher from the pool creates an out-of-pool distilled case, not a never-distilled negative. Likelihood access is stronger than a text-only interface. |
| [Who Taught You That?](https://aclanthology.org/2025.findings-acl.173/), Findings ACL 2025; method/results and limitations | Syntactic-template source tracing; style and surface baselines. | A new stylistic resemblance score needs a stronger case than identification accuracy alone. |
| [SCOUT](https://arxiv.org/html/2609.32749v1), September 26 preprint; sections 3–6, appendices C–D | Output-only normalized syntactic similarity; subsequent SFT/DPO/RL; 36 teacher switches and 18 same-teacher controls. Adding source relatives degrades its seven-case attribution from 7/7 to 1/7; DistillDetect retains 6/7. The source-switch analysis explicitly lacks matched B-only training. | Ordinary post-training robustness, source switching and sibling confusion are direct collisions. A narrower causal comparison remains possible, but the authors already name its missing control. |
| [Distillation Lineage Inspector](https://openreview.net/pdf?id=mcUWhTcqTx), reviewed PDF marked under review; access incomplete | Shadow-student auditor for hypothesized teacher use, including probability/text features. | Do not equate pairwise detection with closed-set teacher identification. Acceptance, full asset availability and all controls remain unverified. |
| [Leave It to the Experts](https://arxiv.org/html/2510.16968v1), preprint; sections 3–4 | Expert-based distillation checks, including a proxy-based black-box route. | Not safely dismissed as white-box-only; release completeness was not verified. |
| [ModSleuth](https://arxiv.org/html/2606.12385v1), preprint; sections 2–4 | Extracts model dependencies, including generation/filtering, from documentation. | Useful evidence inventory; an omitted relationship is not a verified negative label. |
| [Continual Distillation of Teachers from Different Domains](https://openaccess.thecvf.com/content/CVPR2026/papers/Michel_Continual_Distillation_of_Teachers_from_Different_Domains_CVPR_2026_paper.pdf), CVPR 2026 | Earlier-teacher retention/forgetting in vision. | Generic earlier-knowledge retention is already a research topic. |
| [Scaling Model-Generated Distillation Data Can Make Latent Teacher Traits More Recoverable](https://arxiv.org/html/2608.26958v1), preprint; sections 3–5 | Matched no-trait controls and fixed-exposure analysis. | Counterfactual controls themselves are not a novel contribution. |

Active methods also have substantial prior coverage:

| Primary source | Existing coverage that rules out easy proposals |
| --- | --- |
| [Watermarking Makes Language Models Radioactive](https://arxiv.org/html/2402.14904), NeurIPS 2024, section 6.3 | Clean fine-tuning after watermarked training; statistical treatment of repeated contexts. |
| [Can LLM Watermarks Robustly Prevent Unauthorized Knowledge Distillation?](https://aclanthology.org/2025.acl-long.648/), ACL 2025, sections 3–5 | Paraphrasing/neutralization and mixtures of teachers, schemes and keys. |
| [Antidistillation Fingerprinting](https://arxiv.org/html/2602.03812v2), 2026, method and appendix A.4 | Optimizes signal learnability via a proxy student; partial marked data and architecture variation. Its black-box protocol uses many one-step continuations, not arbitrary chat-only access. |
| [TextSeal](https://arxiv.org/html/2605.12456v1), 2026 preprint, section 6/appendix E.4 | Reasoning distillation, quality filtering and sample/token exposure controls. |
| [ReasMark](https://aclanthology.org/2026.acl-long.2185/), ACL 2026, sections 4–5 | Planted prompt-to-reasoning-length behavior, multiple distillation settings. Clear official code availability was not verified. |
| [ActHook](https://arxiv.org/html/2602.18700v2), 2026 preprint; section 3.4/Table 2 and [official no-trigger scoring code](https://github.com/meng-wenlong/AgentWmk/blob/9a3fdc7f0f50858076556c05feef84743ac4d97a/smolagents_benchmark/compute_metrics.py#L212) | A no-trigger-trained model provides a negative contrast while retaining processed trajectory behaviors; this is not fully unwatermarked data. Separating ordinary behavior from secret association already has a close precedent. |
| [AgentWM](https://arxiv.org/html/2602.08401v1), 2026 preprint, section VII-B | Already trains clean same-domain negative students: 12 per domain across three domains. Introducing clean-trained negatives is not a new principle. |
| [AuxMark](https://arxiv.org/html/2609.34597v1), September 28 preprint, sections 3–4/appendices C–E | Auxiliary tool-action watermarks, paired real/fake probes, mixed data and trace transformations. Its 48 clean evaluation settings are eight undistilled models across teacher/benchmark combinations, not 48 independent trained null models. |

These are different access and threat models. They should not be pooled into one
accuracy leaderboard. Preprints can invalidate novelty even before peer review.
A repository release does not mean that we reproduced its results.

## Conditional question D1: audit signal versus incremental training effect

**Question:** After B-response training, if existing auditors no longer support A,
does replacing the earlier B-data stage with matched A data still change final
performance on an existing task protocol?

Let U denote that fixed task metric. The principal effect would be
`E[U(A1 -> B2) - U(B1 -> B2)]`, with matched prompts, common base, stage boundaries
and optimization rules. This is the effect of a first-stage data-source
intervention. It is not proof of teacher-specific knowledge or universal
impossibility of provenance recovery.

A shortest defensible design would include:

- A1→B2 and B1→B2 as the principal matched-dose contrast; B2-only as a diagnostic
  for the extra first-stage training. A→A is informative but cannot replace B→B.
- Frozen DistillDetect, syntactic-template and SCOUT readouts alongside task
  metrics; independent calibration where required, and teacher-absent controls.
- Common seeds across paired histories, with independent histories as the
  replication unit. Define exposure in advance: equal examples and equal target
  tokens cannot generally both be exact when teachers have different lengths.
- Only if necessary, fixed-multiset A→B, B→A and interleaved runs to diagnose order.
  Do not turn this into an unbounded grid or treat order sensitivity as the novelty.

The motivation is to prevent source-audit decisions from being mistaken for
measurements of a dataset's practical training contribution. However, a missing
control is not enough for a paper: the result must change an evidentiary conclusion
across settings, rather than append one ablation to an existing study.

Stop or downgrade if simple reference repair resolves the effect; the task signal
is dominated by formatting/contamination; between-seed uncertainty covers all
meaningful effects; or prior work already gives the same joint comparison. Reusing
math evaluation is acceptable for a tightly qualified protocol replication, but
cannot support a new-capability claim merely because accuracy increased. A credible
non-math replication and its assets would still need to be identified before a
larger study. **This is not yet an experiment-ready main project.**

## Conditional question D2: task-trained nulls for a behavioral watermark

**Question:** Does the fixed AuxMark decision rule remain specific when a student
receives only unwatermarked trajectories for the same tasks, rather than remaining
an unadapted base model?

Our hypothesis is that ordinary tool/task learning might affect real and fake
contexts differently. This is a hypothesis about the null, **not an observed false
positive or an assertion that AuxMark is invalid**. Natural shared tool actions,
format learning and actual transfer of a planted signal need to be distinguished.

The proposed comparison uses the existing BFCL task cohort, released evidence and
paired probes: base student, official marked-data positive, and a new clean-only
student at matched training dose. Multiple independent seeds are required for
replication, not to manufacture a tiny false-positive estimate. Freeze the full
published decision, including the effect-size condition; a small p-value alone is
not the method's verdict. Preserve both raw action matches and final decisions.

The official [pinned repository](https://github.com/qx041609/Auxmark/tree/f3b9497cbf2ed2af9fc03923fc7aaddc4021577a)
contains a [same-task clean-data file](https://github.com/qx041609/Auxmark/blob/f3b9497cbf2ed2af9fc03923fc7aaddc4021577a/output/BFCL/trace/GPT/R1_1/clean_50.jsonl)
and mixture manifests; the file's provenance and absence of planted material must
be checked before using it as a null. `standard_traces` is a training format, not a
label meaning unwatermarked. The [official HF release](https://huggingface.co/AuxMark/AuxMark/tree/22573095a88d454438d25ac43a0d586000e41f8b)
lists adapters, avoiding the need to regenerate all positive teachers. A clean-only
control is new training even though its underlying tasks and probes already exist.

The pinned original 14B training config uses 20 epochs, batch 1 with accumulation
2, rank-32 LoRA and a 16,384-token limit. Crucially, its loss mask is
`thought_action`; the current CLI defaults to `all`. The original positive dataset
statistics report no truncation, but that does not guarantee the same for clean
traces. The recorded local detector uses rule matching with semantic scoring off,
384 new tokens, and no tool-environment execution or API judge. Existing teacher
traces and paired probes can be reused. The published final rule combines one-sided
card-level sign-test p < .05 with mean per-card real-minus-fake full-hit rate >= .05;
the code's significance field alone is not the final decision.

First complete a static audit of task IDs, clean provenance, renderer, masking,
truncation, exact detector thresholds and replay dependencies. Stop if an equivalent
control is already present, the clean labels are not defensible, or a putative
result reduces to parser mismatch. A null result with useful precision is a valid
course result, but does not by itself promise a new method or conference paper.
AgentWM already includes clean-trained same-domain negative students, and ActHook
uses no-trigger training controls for learned secret associations. Therefore
this is a **method-specific qualification audit**, not a novel control principle.
Only a reproducible, explained failure with broader implications could justify
promotion to a research project. It studies active protection, not retrospective
attribution of unmarked historical data.

## AI-text auditing: active, but crowded

| Primary source; reading scope | What is already covered |
| --- | --- |
| [RACE](https://aclanthology.org/2026.acl-long.235/), ACL 2026; sections 3–4, appendix B | Creator/editor distinctions and grouped-split issues. A humanized-text label need not mean an actual human editor. |
| [MixDetect](https://arxiv.org/html/2609.32625v1), September 26 preprint; sections 3–4 | Word-level editing scope/intensity and additional human/AI editing. Alignment-based edit labels do not measure intellectual contribution. |
| [Robust Detection under Contamination](https://arxiv.org/html/2609.29935v1), September 24 preprint; sections 2–5 | Contamination limits under explicit stochastic assumptions, clipped statistics and RAID experiments. Not an impossibility result for all real writing. |
| [Explaining Generalization Through Linguistic Analysis](https://aclanthology.org/2026.eacl-long.307/), EACL 2026; sections 4–5 | Domain, generator and prompt variation associated with linguistic features. Generic style-based generalization failure is not new. |
| [Unbiased Prevalence Estimation with Multicalibrated LLMs](https://arxiv.org/abs/2604.21549), 2026 preprint; official full-paper text | Calibration, distribution changes and threshold filtering; includes MCGrad and weighting comparisons. Filtering-induced miscalibration is not a new theoretical observation. |
| [Partial Identification from LLM Prompts](https://arxiv.org/html/2606.15031v2), 2026 preprint; sections 3–8 and 10 | Correlated measurement errors and weak identification without external calibration; multiple detector identities versus voting already considered. |
| [The Impact of AI-Generated Text on the Internet](https://arxiv.org/html/2604.26965v1), 2026 preprint; methods | An applied setting where sampling, language and length rules define the measurable population. Association is not a causal effect of AI use. |

Keep only the previous narrow backup: **on fixed, labeled public text, can fixed
quality filters cause frozen origin-audit methods to get the direction of a
prevalence change or the ordering of curation policies wrong, after adequate
composition controls and established calibration corrections?** This is an audit
of a data-curation decision, not a new prevalence estimator or an Internet census.

Necessary comparators include raw positive fraction, ACC/PACC or explicit
label-shift methods, domain/length stratification, weighting, MCGrad and a suitable
label-assisted estimator. Their assumptions and label access differ; share a
predeclared budget of revealed existing labels. Group splits and uncertainty by
source/prompt, not by correlated edited variants. Keep original benchmark metrics
and separately name the curation diagnostic.

[RAID](https://github.com/liamdugan/raid) has labeled public training data, but its
public leaderboard predictions use hidden test labels; a joined labeled-training
score cache was not verified. [BEEMO](https://huggingface.co/datasets/toloka/beemo)
has paired edits, not verified cached detector scores or simple binary authorship.
[HC3](https://huggingface.co/datasets/Hello-SimpleAI/HC3) is accessible but older and
QA-specific. Gopher rules may barely filter cleaned benchmarks. The
[DCLM fastText filter](https://huggingface.co/mlfoundations/fasttext-oh-eli5) has
particular positive-source choices; FineWeb-Edu is an encoder/regression model,
not that fastText filter. Neither score means AI provenance.

Stop if filters do not select materially, simple length/domain controls remove
the effect, or standard calibration fixes all consequential errors. A precise
negative finding can be useful; wide nonsignificant intervals are inconclusive.
The central reviewer challenge remains: classical dataset shift on constructed
mixtures may say little about real web curation.

## Assets, compute and admission

The [DistillDetect repository](https://github.com/RajatRawat-creator/DistillDetect/tree/b7cfbae6547f86c4d185d3d5c1d5734ed706ec47)
contains cached teacher text, scoring code and training scripts. Its likelihood
path loads student/reference models, so reusing frozen probes need not run huge
teachers. Cached score reproduction is not a new source-switch experiment.
Third-party [reproduction models](https://huggingface.co/collections/francescortu/distilldetect-reproduction-arxiv-260709692)
exist, but inspected trajectory cards describe selected successful runs and
separately generated early checkpoints. Treat those as exploratory assets, not
unbiased official model-history ground truth. No weights were downloaded here.

A pinned AuxMark tree contains 4,858 entries and the HF metadata lists 112 adapter
weight files. This verifies release existence, not content correctness or replay
success. Recorded small-data 14B LoRA runs do not establish A100 timing. SCOUT
code/replay-cache availability remains unverified.

The total ceiling is **1,000 A100 GPU-hours, not a spending target**. An eventual
single initial pilot could have an **80 A100-hour proposed maximum across all its
arms**, subject to a measured profile and a separate monetary/wall-clock bound.
This is a planning ceiling, not a runtime estimate or execution authorization.
Do not allocate that cap independently to every candidate. Training, generation,
likelihood scoring, load time, retries and rental idle time need separate accounting.
No H100/H200 or unspecified-hardware timing is an A100 estimate.

Before any paid phase: finish the static asset/null audit; specify one primary
estimand, controls, splits, thresholds and stop criteria; publish the finite source;
then measure a bounded profile under a separately reviewed startup plan. The
pre-discussion deliverable is an understandable evidence map and protocol, not a
rushed positive result. Reusing a benchmark still leaves new training-history truth
and controlled conditions to construct; this is less work than inventing a task
benchmark, not zero evaluation design.

## Remaining uncertainty

The search covered primary papers, selected full methods/appendices, official code
and public model/data metadata through September 29. The [source registry](DISTILLATION_TEXT_AUDIT_SOURCES_20260929.json)
records a subset of the directly retained materials with revisions/hashes. Some
release and venue statuses remain explicitly unverified. Failure to find a direct
precedent is not a novelty guarantee. No false positive, effect separation or
curation-ranking reversal has been observed by this project.

The decisive discussion is whether a rigorous audit of **what source evidence
supports under realistic negative controls** is a sufficient contribution, and
which access setting matters: passive history inference or active watermarking.
Keep both provisional until that scientific value and the asset gates are clear.

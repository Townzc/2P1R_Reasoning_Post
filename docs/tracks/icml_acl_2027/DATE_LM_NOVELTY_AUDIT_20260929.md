# DATE-LM candidate: novelty and scientific-target audit

Date: September 29, 2026. Decision: **do not advance the proposed answer-only
attribution question as a new main project.** This supersedes its priority in the
[earlier direction screen](DIRECTION_SCREEN_20260929.md). DATE-LM remains a useful
benchmark; the decision concerns this proposed contribution, not the entire field.

No new training, model inference, attribution scoring or paid execution occurred.
The additional empirical checks below inspect released data and label structure.

## Origin of the candidate

The candidate was an assistant-generated hypothesis during a screen for existing,
compute-accessible data-auditing benchmarks. Reading DATE-LM's discussion of lexical
confounds and its released entity-mapping labels suggested an answer-only control.
It was not derived from the completed token-supervision experiments. Availability
of a suitable benchmark was initially established more strongly than novelty of
the proposed question. The earlier priority recommendation was premature.

## Direct and adjacent prior work

The following entries distinguish experimentally direct overlap from conceptual
overlap. Preprints are not presented as accepted conference papers.

| Work and verified publication status | Sections inspected and relevant evidence | Consequence for this candidate |
|---|---|---|
| Akyurek et al., **Towards Tracing Factual Knowledge in Language Models Back to the Training Data**, Findings of EMNLP 2022 ([paper](https://aclanthology.org/2022.findings-emnlp.180.pdf)) | Sections 4.1 and 5.1, Table 2: same-output-label distractors and RANDOM-TARGET, which assigns equal positive scores to candidates sharing the answer. Sections 5.2–5.3 examine lexical signals and synthetic fact tracing. | Direct precedent for asking whether attribution does more than answer matching. Exact-label matching is not identical to modern semantic answer embeddings, but the scientific question and core control already exist. |
| Park et al., **TRAK: Attributing Model Behavior at Scale**, ICML 2023 ([paper](https://proceedings.mlr.press/v202/park23c/park23c.pdf)) | Section 5.2, Figure 5, Appendix H.4–H.5 compare fact retrieval with removal and retraining. A method's fact-retrieval rank does not determine its intervention effect. | The distinction between support retrieval and behavior tracing is established. The interventions do not remove identical numbers of records, so their magnitudes should not be treated as a perfectly dose-matched causal comparison. |
| Chang et al., **Scalable Influence and Fact Tracing for Large Language Model Pretraining**, ICLR 2025 ([paper](https://arxiv.org/html/2410.17413v3), [venue](https://proceedings.iclr.cc/paper_files/paper/2025/hash/65798a76cc176c29b6bfefe84b0a03ff-Abstract-Conference.html)) | Sections 4–7 separate fact-entailing retrieval from tail-patching effects, and analyze entity, name and relation priors. | Both answer/entity signals and the divergence between retrieval and influence already receive detailed study. Tail-patching measures an additional local training step; it is not removal-and-retraining history. |
| Jiao et al., **DATE-LM**, NeurIPS 2025 Datasets and Benchmarks ([paper](https://arxiv.org/html/2507.09424v2), [venue](https://proceedings.neurips.cc/paper_files/paper/2025/hash/e1ebda145808ca45774993fb67314894-Abstract-Datasets_and_Benchmarks_Track.html)) | Sections 4.3 and 5.3, Appendix E.1/E.3/E.6: lexical-confound motivation, counterfactual entity mappings, retrieval baselines, and top-ranked-data removal followed by retraining. | Neither lexical-confound diagnosis nor adding a training intervention is an overlooked general idea. No explicit named RANDOM-TARGET row was located in the inspected DATE-LM experiments; its absence does not establish novelty. |
| Li et al., **DataDignity**, May 2026 arXiv preprint ([full text](https://arxiv.org/html/2605.05687v1)) | Sections 3–5 and limitations: source-support retrieval with answer-only and question-plus-answer baselines, hard negatives and model-aware methods. | Strong overlap with measuring incremental model information beyond answer similarity. Source-support labels do not by themselves establish historical causal responsibility. The inspected HTML describes eleven baselines; other retrieved descriptions differ, so counts must remain version-bound. |
| Anders et al., **Quantifying the Agreement Between Data-Influence and Data-Similarity to Understand LLM Behavior**, June 2026 arXiv preprint ([paper](https://arxiv.org/html/2606.23591v1)) | Section 3H/Figure 6b and Section 4 study similarity pre-filtering followed by influence refinement and discuss cost trade-offs. Its diagnostic positives are a ranking method's own top documents, not independent causal truth. | Adding a retrieval/influence cascade or a generic cost-benefit claim is also not a new idea. Its evidence leaves narrower validation questions, but this review does not certify those as new. |
| Kim et al., **Form Over Content In Gradient-Based Data Attribution Methods**, September 2026 arXiv preprint ([paper](https://arxiv.org/html/2609.19589v1), [author publication status](https://seokwonjung-jay.github.io/)) | Sections 3–4 cross answer format with task and inspect released LESS selections. Sections 5–6 distinguish semantic interpretation from measured utility. | Broad claims about superficial cues in gradient attribution are crowded. Answer format is different from DATE-LM answer-entity identity; this paper does not itself establish an entity shortcut in DATE-LM. |

Two additional conceptual checks constrain interpretation. [RelatIF, AISTATS
2020](https://proceedings.mlr.press/v108/barshan20a/barshan20a.pdf), Sections 4.1–4.3,
distinguishes query-specific explanations from samples with large global influence.
It is not an LLM answer-only study. [If Influence Functions are the Answer, Then
What is the Question?, NeurIPS 2022](https://proceedings.neurips.cc/paper_files/paper/2022/file/7234e0c36fdbcb23e7bd56b68838999b-Paper-Conference.pdf),
Sections 4–6, distinguishes a local proximal response from actual leave-one-out
retraining. These works caution against naming a score without specifying its target.

## What scientific question would actually be measured?

Three targets must remain separate:

1. **Support retrieval:** which candidate texts support, or share the benchmark's
   labeled relationship with, a query and answer? A fixed set of labels can evaluate
   this through retrieval metrics without retraining the model.
2. **Local model sensitivity:** which examples would change the current model's
   target probability under a specified small update or reweighting? This depends
   on the model state, loss, optimizer and intervention definition.
3. **Training-data intervention:** what changes if selected data are removed and
   the specified learning process is repeated? Define the initial checkpoint,
   training schedule, removal unit, replacement policy and randomness explicitly.

For the third target, a possible estimand is

\[
\Delta(S,q) = \mathbb{E}_{\xi}\left[
f(A(D;\xi),q)-f(A(D\setminus S;\xi),q)\right],
\]

where the training algorithm and all budget conventions are part of `A`, and `f`
is a prespecified behavioral measure. This is a training-procedure-specific
intervention, not proof of a unique historical source. It is not the estimand of
Recall@50 or MRR, and a tail-patching effect is not automatically its substitute.

The earlier proposal can be defined as comparing model-aware ranking to exact
answer matching and strong full-text retrieval on fixed support labels. That is
testable and useful for replication. It does **not** newly solve the broader
question of when attribution adds information; the literature above already studies
it. To claim better remediation, one must separately compare training interventions,
matching the removal budget and tracking collateral changes on unrelated queries.

Scientific value would be operational: identify data worth inspecting or correcting,
avoid confusing a relevant passage with a behaviorally influential example, and
determine whether expensive attribution supplies information needed for a stated
decision. These motivations do not establish a new contribution by themselves.

## Independent check of the released DATE-LM labels

Pinned dataset revision:
`a45cd489199a08416741c17aef9a813d8d1c2a19`.
Pinned code revision:
`95c9a6db8edd4e450b3e9fe018413bbc4f50bb45`.

The [official evaluator](https://github.com/DataAttributionEval/DATE-LM/blob/95c9a6db8edd4e450b3e9fe018413bbc4f50bb45/evaluation/evaluate_application.py#L85)
labels a training record positive when its `true_entity` and
`counterfactual_entity` both match the reference. This is a mapping-group label,
not a record-specific measured causal effect.

We independently read the released
[Pythia training data](https://huggingface.co/datasets/DataAttributionEval/Counterfact/resolve/a45cd489199a08416741c17aef9a813d8d1c2a19/Pythia-1b/train.jsonl)
and [reference data](https://huggingface.co/datasets/DataAttributionEval/Counterfact/resolve/a45cd489199a08416741c17aef9a813d8d1c2a19/Pythia-1b/ref.jsonl):

- 5,473 training records, 66 references, 16 reference entity-mapping groups and
  14 distinct reference answers.
- All 66 reference answers equal their counterfactual entity. For every reference,
  the positive set is a **strict subset** of candidates with the same answer.
- For example, 161 training answers are `Microsoft`: 55 have the Google-to-Microsoft
  mapping, 75 have Apple-to-Microsoft, and 31 have another label configuration.

Consequently answer matching is permitted, informative and incomplete. Strong
answer-only performance would not be direct label leakage or proof that the
benchmark is invalid. Ranking with hidden label metadata would be a different,
invalid experiment. Shared mapping groups also require care with uncertainty;
66 query rows cannot be assumed to supply 66 independent mechanistic observations.

These are schema/set-membership checks, **not attribution performance results**.
No RANDOM-TARGET, BM25 or gradient score was evaluated in this audit.

Input SHA256 values:

- train: `c0a2013aacedd023502d12b6345f315f07997b07d2c54e2259cac53f06f8ff75`
- references: `f560b4f35c422bcc4ef1e685e583b54598ea73ed653b1f5a3d6e72d70352c580`

## Decision and scope of the search

The broad question has direct prior experiments. Moving an existing answer-only
control onto DATE-LM would be a replication/diagnostic, not an established novel
project. A narrow, stable result that materially changes an existing evaluation
conclusion could warrant reconsideration, but none has been demonstrated here.
Do not allocate a GPU pilot simply to preserve the previous recommendation.

This is a targeted public-literature search through September 29, 2026, including
backward references and recent related work across arXiv, ACL Anthology, PMLR,
ICLR/NeurIPS proceedings and OpenReview. Queries included DATE-LM, fact tracing,
answer-only/target-only attribution, lexical/entity similarity, causal influence,
faithfulness, and pre-filter/refine. Core sections and experimental appendices of
seven close papers and two conceptual background papers were checked. This is
not an exhaustive citation census, nor a claim that an unlocated experiment does
not exist. The positive identification of direct precedent is already sufficient
to reject the broad novelty claim.

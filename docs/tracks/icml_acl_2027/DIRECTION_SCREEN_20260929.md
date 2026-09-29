# Research direction screen — September 29, 2026

**Superseded priority:** the subsequent [novelty audit](DATE_LM_NOVELTY_AUDIT_20260929.md)
found direct prior answer-only controls and extensive related work. Do not advance
the proposed DATE-LM question as a new main project or launch its GPU pilot. The
shortlist below preserves the earlier provisional screen, not a current selection.

Status: literature and asset review, not an experiment protocol or a novelty claim.
LT002 is complete; its results and execution source remain unchanged. No new model
call, training run, benchmark result or server startup occurred during this review.

## Selection criteria

Prefer a data provenance, attribution or auditing question with an existing public
benchmark, reusable model checkpoints, established labels and evaluation code.
Do not make a new benchmark, new human annotation campaign or large training grid
a prerequisite for the project. Separate an interesting research question from
improving a score without an explanation about data.

Keep the benchmark's primary task, labels and metrics. A proposed intervention on
training, calibration or audit data still requires a documented experiment design;
using an existing dataset does not make that design automatically valid. Additional
diagnostics should support the established evaluation, not replace it after seeing
results. Use held-out data for method selection and account for related examples.

## Shortlist

| Priority | Candidate | Assets and decision |
|---|---|---|
| First feasibility screen | Training-data attribution, initially factual attribution on DATE-LM | Public data, model checkpoints and scoring/evaluation code make a small reproduction plausible. A specific contribution remains to be established. |
| Backup | Calibration-data allocation for AI-text detection on RAID | Existing detection task and metrics; a fixed-budget data-composition experiment needs an independent calibration/evaluation split. Substantial overlap with prior calibration work must be resolved first. |
| CPU-only reserve | Small-probe stability of reference-based distillation detection | Cached scores support a cheap screen, but few independent teachers and overlap with existing findings limit the claim. |

### DATE-LM: candidate platform, not a selected new method

[DATE-LM](https://arxiv.org/abs/2507.09424) provides factual attribution, filtering
and data-selection tasks. Start with factual attribution and its Recall@50/MRR
evaluation. Its [official repository](https://github.com/DataAttributionEval/DATE-LM)
and [Pythia-1B checkpoint](https://huggingface.co/DataAttributionEval/Pythia-1b-counterfactual)
are public. Appendix E.8 reports 0.3–0.75 A6000 GPU-hours for several Pythia-1B
attribution methods. These are author-reported attribution timings, not measured
A100 timings or an all-inclusive project cost.

Candidate question to investigate, not a novelty claim: when does model-aware
attribution recover labeled training evidence beyond what an answer-only retrieval
baseline can identify? Keep the released candidate pool and labels, compare an
answer-only baseline against full-input retrieval and attribution, and inspect
existing same-answer candidates. Check the closest prior work before interpreting
the comparison as a contribution. Neither lexical shortcuts nor a retrieval-plus-
gradient cascade can be assumed new. Strong answer-only performance would need
interpretation against the benchmark's actual label definition; it would not
automatically invalidate the benchmark.

First reproduce a cheap retrieval baseline, then one attribution baseline on the
same released checkpoint and fixed examples. Audit schema, positive-label semantics,
reference selection, related entity groups and scorer behavior before interpreting
differences. A benchmark evidence label alone does not prove causal training
influence. Retrieval performance does not establish downstream model repair.

Stop this candidate if its apparent gap is already resolved by prior work, released
assets cannot support the proposed comparison, or independent evaluation is too
small for the intended claim. Do not compensate by silently generating new tests.

### RAID: fixed-budget calibration data, conditional backup

[RAID](https://github.com/liamdugan/raid) supplies detection data and evaluation
tools; test labels are hidden. Published prediction files are not a guarantee that
arbitrary new analyses can be evaluated locally. Verify split/ID alignment first.
The official evaluator already supports domain-specific thresholds. Prior
[MCP/RealDet work](https://arxiv.org/abs/2505.05084) studies false-positive control
and calibration, so merely adding length bins or domain calibration is insufficient.

Possible intervention: at a fixed human calibration-set size and a fixed detector,
compare random and coverage-based allocation. Preserve established detection
metrics, and separately report realized false-positive rates on independent data.
No new text generation is required. Discard if this is only a repackaging of known
calibration results. This is not an estimate of AI prevalence on the Internet.

### Distillation detection: reserve only

[DistillDetect](https://github.com/RajatRawat-creator/DistillDetect) releases cached
likelihood results. A small-probe analysis can preserve its existing labels and
cross-validation conditions. The cached results do not include the matched
post-human-SFT trajectories needed for a persistence study; public controlled
student weights were not verified. That study would expand the experimental suite
and is therefore deprioritized. Teacher-absent candidate sets are not equivalent
to never-distilled negative models.

## Finite exploration plan

1. Pin benchmark/code revisions, verify downloadable assets, map labels and splits,
   and compare the closest papers against one precise candidate question.
2. Reproduce a cheap baseline locally where possible. Record actual discrepancies,
   including failures; source availability is not a completed reproduction.
3. Before paid execution, produce a finite run list with measured throughput,
   total GPU-hours, wall time, cost and stop rules. Cache reusable scoring outputs.
4. Advance one main candidate only if the research gap, benchmark validity and
   complete evaluation budget all survive the screen. Keep one backup, not three
   simultaneous projects.

The benchmark-based screen does not amend historical experiment ledgers, authorize
new spending or establish that any proposed direction is publication-ready.

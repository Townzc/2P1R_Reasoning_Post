# Disposition of the supplied P007 audit suggestions

October12 2026. Source: owner-supplied collaboration document and the existing
[Claude audit comment](https://github.com/Townzc/2P1R_Reasoning_Post/issues/13#issuecomment-6130876644).
This records methodological review, not a claim of Claude approval of our new
packet. This original disposition predates the external packet audit. The newer version-specific verdicts and C-B1 response are recorded in [the October12 cost review](P007_COST_METRIC_REVIEW_20261012.md).

| ID | Disposition | Evidence / action |
|---|---|---|
| F1 exposure concern | Accepted as a competing explanation | Repetition per pair differs by design under fixed total targets. Export exact per-row/path exposures and reference NLL. The contrast does not isolate novel reasoning paths. |
| F1 "mainly over-repetition" | Not established causally | Lower NLL on32 arm-dependent training examples and three observed-development checkpoints are descriptive. They do not quantify which mechanism caused the endpoint gain. Do not infer an optimal stop from the observed maximum. |
| F2 "exclude differences above3pp" | Corrected | Breadth−Solutions interval is[−3.71,2.20]pp. A disadvantage larger than3pp remains compatible with this interval. No equivalence or universal substitutability conclusion. |
| F2 cheapest usable pair rule | Hypothesis, not current result | Equal training targets do not establish equal acquisition expense or equal value of marginal data. Execute the same-source cost comparison before such a recommendation. |
| F3 benchmark exposure | Accepted with precise scope | Train-split development; official test previously observed by this research effort. Neither establishes absence of pretraining contamination. |
| F3 seed variation | Qualified | Two realized seeds cannot reliably estimate population seed variance. Mixed differs by3 questions, so "all seed differences at most2" is also inaccurate. More evaluation questions reduce only the relevant conditional sampling uncertainty. |
| F3 few-shot number / memorization probe | Unverified / proposed | The quoted external68.5% is explicitly memory-based in the source. Do not use without checking the primary model report and exact protocol. Continuation overlap alone cannot prove or exclude contamination. |
| F4 supply / difficulty | Accepted with qualification | Count every failure and duplicate and retain censored parents. Stratifying by the same eight attempts' success rate is descriptive endogenous grouping, not independent difficulty or a causal adjustment. Any such analysis must retain that label. |
| F5 readability | Implemented | One-page README, historical README preserved in docs/LOG.md, fixed review entry and per-question packet. Default main still historical; use explicit branch/commit links. |
| Missing-return scoring | Corrected | Known parse failure/truncation follows the frozen scoring rule and remains in the denominator. A technical interruption with no returned answer is unknown; report known numerator, unknown count and bounds. Do not silently impute failure or delete it. |
| WP6 mechanism claims | Qualified | Equal intermediate-number sequences do not prove identical reasoning; a paraphrase contrast alone would not identify strategy diversity. Controls need validation and claims matching what was actually intervened on. |
| WP4 pooled431+1319 interval | Requires explicit estimand | Report split-specific results first. A pooled number weights two selected splits and does not become an independent evaluation merely by increasing N. |
| Work packages / six GPUs / future credits | Proposed, not admitted | Current pilot remains128×8,one H100; current maximum2GPUs. Additional256×16 work, teacher/API changes and the larger queue require a new finite design before execution. Unissued future credits do not count. |
| Thursday freeze | Not adopted | The latest direct owner target is Tuesday evening; Wednesday is for rehearsal. |
| Issue comments / audit labels | Owner sends | Repository evidence is pushed directly. Comment drafts are provided in chat; no automated external posting or label changes. |

The active scientific priority is P007A cost calibration followed by the
same-source P007B cost-cap comparison. Saved-checkpoint dose analysis and broader
evaluation are useful candidates, but they do not replace the missing
cost-matched acquisition comparison. Their priority is a research decision,
not an execution instruction embedded in a document.

The compact public packet supports independent metric, exposure and reported-cost
checking. Full raw token streams and model states remain retained with verified
hashes; a reviewer needing end-to-end scoring reproduction must request that
additional evidence rather than claim to have checked it from summary bits.

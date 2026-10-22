# A6 − A7: newly requested forced-answer contrast

**Post-hoc diagnostic; one training seed.** Uses the saved seven-cell forced labels and unchanged accepted `question_vectors` / `paired_question_interval`. No generation, decoding or scoring was repeated. Only this new contrast was bootstrapped.

| Mode | A6 − A7 accuracy difference (pp) | Paired 95% CI (pp) |
|---|---:|---:|
| Sampled | +4.65 | [+2.30, +6.95] |
| Greedy | +6.80 | [+2.20, +11.40] |

10,000 resamples; seed 20261021; linear quantiles; 500 paired questions. Sampled uses the mean of four saved Booleans per question. Greedy repeats its one saved bit only at the unchanged four-bit interface and introduces no extra independent observations. Frozen P1 labels remain unchanged. These intervals concern question sampling, not variation across training seeds. New independent result review is not yet claimed.

The separately requested forced-answer inference on the two ≈3B extension students is **not yet run**. Its latest direct-owner hard cap is **$20**. New route source target `87407963774de2d4f37ed5121d8d9ea60aec2c6d` is pending real Claude CR. Shared audit HEAD checks at 22:33 and 22:48 UTC both returned the prior `4654447b377efb67a52a7d829bcc3d004127950d`; no new report was read or PASS inferred. The exact request is `reports/p011_20261020/FORCED_EXT3B_COMPLETE_PATH_CR_REQUEST.md`. Actual inputs and GPU admission follow real source acceptance; existing-label A6−A7 is permanently complete and must not be recomputed.

# Decision-supervision continuation results

Status: **all_registered_outputs_verified**. Offline analysis made no model calls.

The primary treatment is D minus U within S and P. The equal-recipe mean is descriptive across two recipes, not two training seeds. Parent comparisons include extra optimization. Previous E038/E039 paired-versus-single conclusions remain unchanged.

| Outcome | Contrast | Difference [95% group interval] | Family sensitivity |
|---|---|---:|---:|
| primary_J_H | delta_S | +0.1458 [+0.0417, +0.2708] | [+0.0417, +0.2553] |
| primary_J_H | delta_P | +0.1667 [+0.0625, +0.2708] | [+0.0667, +0.2791] |
| primary_J_H | equal_recipe_mean | +0.1563 [+0.0729, +0.2500] | [+0.0729, +0.2500] |
| secondary_F_sampled_pass_at_1 | delta_S | -0.0052 [-0.0208, +0.0104] | [-0.0192, +0.0098] |
| secondary_F_sampled_pass_at_1 | delta_P | +0.0208 [-0.0078, +0.0495] | [-0.0075, +0.0489] |
| secondary_F_sampled_pass_at_1 | equal_recipe_mean | +0.0078 [-0.0117, +0.0260] | [-0.0109, +0.0270] |

| State | Pool | Interface | Decoding | Strict correct / outputs | Both goals / groups | Pass@4 targets |
|---|---|---|---|---:|---:|---:|
| E038 | eval_H | H | greedy | 50/96 | 11/48 | NA |
| E038 | eval_F | F | greedy | 2/96 | 0/48 | NA |
| E038 | eval_F | F | sampled | 13/384 | NA | 11/96 |
| E039 | eval_H | H | greedy | 51/96 | 15/48 | NA |
| E039 | eval_F | F | greedy | 3/96 | 0/48 | NA |
| E039 | eval_F | F | sampled | 14/384 | NA | 13/96 |
| S-U | eval_H | H | greedy | 51/96 | 13/48 | NA |
| S-U | eval_F | F | greedy | 8/96 | 1/48 | NA |
| S-U | eval_F | F | sampled | 14/384 | NA | 10/96 |
| S-D | eval_H | H | greedy | 62/96 | 20/48 | NA |
| S-D | eval_F | F | greedy | 4/96 | 0/48 | NA |
| S-D | eval_F | F | sampled | 12/384 | NA | 9/96 |
| P-U | eval_H | H | greedy | 57/96 | 16/48 | NA |
| P-U | eval_F | F | greedy | 6/96 | 0/48 | NA |
| P-U | eval_F | F | sampled | 13/384 | NA | 9/96 |
| P-D | eval_H | H | greedy | 66/96 | 24/48 | NA |
| P-D | eval_F | F | greedy | 5/96 | 0/48 | NA |
| P-D | eval_F | F | sampled | 21/384 | NA | 20/96 |

Paired number-group bootstrap, 10000 draws, seed 2026091714, with all six states resampled jointly; skeleton-family clustering is a sensitivity analysis. Targets and samples remain nested. Intervals exclude training-seed, parent-seed and data-assignment uncertainty. The two recipes are not two seeds. Exploratory intervals are not multiplicity-adjusted; a zero-containing interval is not evidence of equivalence, and an empirical [0,0] interval is not proof of population zero.

Invalid, unparsed and capped outputs remain in every measured denominator. Unrun or incomplete views are not zeros and do not enter complete-grid contrasts. H requires the ordered scaffold, resources, target and completed output; F accepts any legal correct construction.

Training/midpoint diagnostics appear separately in TRAINING_DIAGNOSTICS.json and STAGE_A_TRAIN_FIT.md. Midpoint step64 never selects the formal step128 endpoint. Weighted and ordinary training objectives differ; only unweighted fixed-reference NLL is comparable as a diagnostic. Weight-mass preservation does not preserve gradient norm or effective optimization direction.

These fresh number instances are exploratory, not automatically structural OOD or an external confirmation set. Conditional operator diagnostics do not establish free construction or a hidden mechanism. No further training is selected or authorized by this report.

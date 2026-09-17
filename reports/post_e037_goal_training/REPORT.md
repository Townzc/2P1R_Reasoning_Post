# Post-E037 paired-goal training analysis

Status: **all_registered_outputs_verified**. Offline analysis used no model calls.

The main comparison is G-paired minus G-single at step256. Both arms receive the same F replay and H interface training. Their changes relative to E031 also contain those shared interventions and additional optimization.

| Primary outcome | G-single | G-paired | Paired difference [95% group CI] |
|---|---:|---:|---:|
| primary_direct_J_H | 0.2500 | 0.2083 | -0.0417 [-0.1667, +0.0833] |
| primary_transfer_pass_at_1 | 0.0365 | 0.0339 | -0.0026 [-0.0260, +0.0234] |

| State | Pool | Interface | Decoding | Strict correct / outputs | Both targets / pairs |
|---|---|---|---|---:|---:|
| E031 | eval | F | greedy | 0/96 | 0/48 |
| E031 | eval | H | greedy | 4/96 | 0/48 |
| E031 | eval | C | greedy | 89/96 | 43/48 |
| E031 | eval | F | sampled | 1/384 | 0/192 |
| E031 | eval | H | sampled | 10/384 | 0/192 |
| G-single | eval | F | greedy | 3/96 | 0/48 |
| G-single | eval | H | greedy | 40/96 | 12/48 |
| G-single | eval | C | greedy | 92/96 | 44/48 |
| G-single | eval | F | sampled | 14/384 | 0/192 |
| G-single | eval | H | sampled | 149/384 | 33/192 |
| G-paired | eval | F | greedy | 3/96 | 0/48 |
| G-paired | eval | H | greedy | 45/96 | 10/48 |
| G-paired | eval | C | greedy | 94/96 | 46/48 |
| G-paired | eval | F | sampled | 13/384 | 1/192 |
| G-paired | eval | H | sampled | 158/384 | 30/192 |
| G-single | midpoint12 | H | greedy | 9/24 | 1/12 |
| G-single | train16 | F | greedy | 2/32 | 0/16 |
| G-single | train16 | H | greedy | 17/32 | 5/16 |
| G-paired | midpoint12 | H | greedy | 10/24 | 1/12 |
| G-paired | train16 | F | greedy | 1/32 | 0/16 |
| G-paired | train16 | H | greedy | 16/32 | 4/16 |

Paired number-group bootstrap and skeleton-family cluster sensitivity, 10000 draws, seed 2026091708; single training seed, no training-seed uncertainty. Targets and stochastic samples are nested within groups. Exploratory intervals are not multiple-comparison-adjusted. A zero-event [0,0] interval is not population zero; a difference interval containing zero does not demonstrate equality.

J_H counts groups whose two H greedy answers are both strictly correct. The sampled F primary is mean per-output correctness, equally weighting targets and number groups; sampled pass@4 and greedy are reported alongside it. Invalid, incomplete and unparsed outputs remain in denominators. Fixed sample-index pairs and products of target success fractions are supplementary; neither creates additional independent groups.

The fixed training16 diagnostic oversamples anchor-operator × hole-position strata and separates anchor from countergoal. The G-single countergoal was not supervised for that number/template; both goals were supervised in G-paired. These are training-instance diagnostics, not held-out generalization estimates. The fixed midpoint12 H subset is not used to select checkpoints.

Operator ranking, label/argmax marginals, correct-vs-best-wrong log-probability margin and D_goal condition on a supplied valid prefix. Raw full-vocabulary probability, candidate mass and within-set probability are separate. Positive D_goal alone is not correct choice or free construction.

This two-arm recipe comparison changes distinct target/program support and repetition jointly. It does not establish an internal mechanism, a same-target multipath comparison, structural OOD, or an interaction with the old preparation states. No continuation is selected by this report.

# P011 extension forced-answer probe (2026-10-22)

**Post-hoc diagnostic; original natural/primary results unchanged.** One training seed (17).

| Cell | Mode | Rows | Native capped | Continuations | Unclosed boxes | Natural accuracy | Forced accuracy |
|---|---|---:|---:|---:|---:|---:|---:|
| 3,024 × 1, E≈3 | sample | 2000 | 1182 | 1182 | 6 | 27.60% | 46.70% |
| 3,024 × 1, E≈3 | greedy | 500 | 488 | 488 | 1 | 1.60% | 43.00% |
| 9,072 × 1, E=1 | sample | 2000 | 1691 | 1691 | 5 | 10.30% | 43.05% |
| 9,072 × 1, E=1 | greedy | 500 | 500 | 500 | 1 | 0.00% | 40.60% |

Paired question bootstrap: 10,000 resamples, seed 20261021, linear quantiles. Sampled endpoints use each question’s mean of four; greedy uses one saved bit. Natural intervals are exact sign reversals of the saved opposite-direction intervals, without resampling.

| Contrast | Protocol | Mode | Difference (pp) | 95% CI (pp) |
|---|---|---|---:|---|
| 3,024 − 9,072 | natural | sample | +17.30 | [+14.90, +19.60] |
| 3,024 − 9,072 | natural | greedy | +1.60 | [+0.60, +2.80] |
| 3,024 − 9,072 | forced | sample | +3.65 | [+1.35, +5.85] |
| 3,024 − 9,072 | forced | greedy | +2.40 | [-2.20, +7.00] |
| A6 − A7 (1,008 − 4,032) | forced | sample | +4.65 | [+2.30, +6.95] |
| A6 − A7 (1,008 − 4,032) | forced | greedy | +6.80 | [+2.20, +11.40] |

| Cell | Mode | Capped looping: n / recovered | Capped nonlooping: n / recovered |
|---|---|---:|---:|
| 3,024 × 1, E≈3 | sample | 497 / 192 | 685 / 190 |
| 3,024 × 1, E≈3 | greedy | 474 / 203 | 14 / 4 |
| 9,072 × 1, E=1 | sample | 1108 / 477 | 583 / 178 |
| 9,072 × 1, E=1 | greedy | 485 / 200 | 15 / 3 |

Loop heuristic: zlib-compressed UTF-8 bytes divided by original UTF-8 bytes for the last 6,000 original answer characters, threshold < .12. Descriptive only, within capped rows.

Only native length_cap rows at 16,384 generated IDs were continued. The fixed 10-token suffix and greedy 64-token ceiling are identical to the accepted seven-cell probe. First balanced forced box only; unclosed is incorrect. Other rows reuse their saved Boolean. This intervention tests protocol sensitivity, not a unique causal mechanism or training-seed generalization.

Modal reported tagged charge for this new app: 1.21523750 USD, observed 2026-10-23T00:08:44.643524+00:00. This is not a final invoice; unassigned build/storage/egress or billing delay are not assumed zero. Owner hard cap: $20.

Independent actual-result A3: **PASS-WITH-NOTES**, Claude `636e2b1f`, all seven flags accepted. The reviewer independently checked all3,861 new continuations, matched native-stop/box-completion categories, manually reviewed245 non-string-identical positive rows, and reproduced all six intervals. Codex did not rerun the saved natural bootstrap or the already-completed A6−A7 pair.

The reviewer identified approximately16 lenient value/format acceptances under the frozen P1 policy. Their rough stricter-policy decreases were0.15/0.4pp (3024, sampled/greedy) and0.3/1.0pp (9072); these are reviewer estimates, not rescored results. All published labels, accuracies and intervals remain unchanged. Private model/state binaries, a full independent symbolic-engine run and final invoice were not independently accessed. See [the actual A3 acceptance](review_636e2b1f_forced_ext3b_actual_A3_accepted_v1/README.md).

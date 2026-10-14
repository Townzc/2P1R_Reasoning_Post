# P008 complete primary endpoint tables — external review pending

18 logical students plus base have complete local raw/dose/state verification and stopped providers. This publication does not itself claim final CPU completion or independent G3 acceptance.

## All cells

| Logical cell | Correct / 1319 | Accuracy | Length caps | Updates | Targets |
|---|---:|---:|---:|---:|---:|
| base | 638 / 1319 | 48.370% | 41 | 0 | 0 |
| d1_b1_p0_breadth_t1 | 969 / 1319 | 73.465% | 42 | 256 | 524287 |
| d1_b1_p0_depth_t1 | 965 / 1319 | 73.161% | 43 | 256 | 524287 |
| d1_b1_p4_breadth_t1 | 954 / 1319 | 72.328% | 39 | 256 | 524287 |
| d1_b1_p4_depth_t1 | 945 / 1319 | 71.645% | 36 | 256 | 524287 |
| d1_b8_p0_breadth_t1 | 942 / 1319 | 71.418% | 43 | 256 | 524287 |
| d1_b8_p0_breadth_t8 | 967 / 1319 | 73.313% | 39 | 2048 | 4194296 |
| d1_b8_p0_depth_t1 | 949 / 1319 | 71.948% | 49 | 256 | 524287 |
| d1_b8_p0_depth_t8 | 965 / 1319 | 73.161% | 50 | 2048 | 4194296 |
| d1_b8_p4_breadth_t8 | 945 / 1319 | 71.645% | 56 | 2048 | 4194296 |
| d1_b8_p4_depth_t8 | 939 / 1319 | 71.190% | 47 | 2048 | 4194296 |
| d2_b1_p0_breadth_t1 | 968 / 1319 | 73.389% | 41 | 256 | 524287 |
| d2_b1_p0_depth_t1 | 970 / 1319 | 73.541% | 35 | 256 | 524287 |
| d2_b1_p4_breadth_t1 | 951 / 1319 | 72.100% | 40 | 256 | 524287 |
| d2_b1_p4_depth_t1 | 943 / 1319 | 71.494% | 39 | 256 | 524287 |
| d2_b8_p0_breadth_t8 | 956 / 1319 | 72.479% | 51 | 2048 | 4194296 |
| d2_b8_p0_depth_t8 | 971 / 1319 | 73.616% | 45 | 2048 | 4194296 |
| d2_b8_p4_breadth_t8 | 935 / 1319 | 70.887% | 45 | 2048 | 4194296 |
| d2_b8_p4_depth_t8 | 990 / 1319 | 75.057% | 36 | 2048 | 4194296 |

## All contrasts

| Contrast | Estimate (pp) | Conditional pointwise 95% interval (pp) |
|---|---:|---:|
| D1_Delta_p0_B1 | -0.303 | [-2.502, +1.895] |
| D1_Delta_p4_B1 | -0.682 | [-2.957, +1.592] |
| D1_Delta_p0_B8 | -0.152 | [-2.350, +2.123] |
| D1_Delta_p4_B8 | -0.455 | [-2.881, +1.895] |
| D1_C_p0 | +0.152 | [-3.033, +3.260] |
| D1_C_p4 | +0.227 | [-3.184, +3.563] |
| D1_I_B1 | -0.379 | [-3.336, +2.578] |
| D1_I_B8 | -0.303 | [-3.563, +2.881] |
| D1_I_high_minus_low | +0.076 | [-4.397, +4.473] |
| D2_Delta_p0_B1 | +0.152 | [-2.047, +2.350] |
| D2_Delta_p4_B1 | -0.607 | [-2.881, +1.668] |
| D2_Delta_p0_B8 | +1.137 | [-1.061, +3.412] |
| D2_Delta_p4_B8 | +4.170 | [+1.820, +6.520] |
| D2_C_p0 | +0.986 | [-2.049, +4.094] |
| D2_C_p4 | +4.776 | [+1.516, +8.112] |
| D2_I_B1 | -0.758 | [-3.867, +2.350] |
| D2_I_B8 | +3.033 | [-0.227, +6.293] |
| D2_I_high_minus_low | +3.791 | [-0.682, +8.340] |
| D1_p0_breadth_B8_minus_B1_at_T1 | -2.047 | [-4.321, +0.227] |
| D1_p0_breadth_T8_minus_T1_at_B8 | +1.895 | [-0.379, +4.170] |
| D1_p0_depth_B8_minus_B1_at_T1 | -1.213 | [-3.336, +0.910] |
| D1_p0_depth_T8_minus_T1_at_B8 | +1.213 | [-0.986, +3.487] |
| draw_mean_Delta_p0_B1 | -0.076 | [-1.592, +1.478] |
| draw_mean_Delta_p4_B1 | -0.644 | [-2.237, +0.948] |
| draw_mean_Delta_p0_B8 | +0.493 | [-1.061, +2.085] |
| draw_mean_Delta_p4_B8 | +1.857 | [+0.152, +3.563] |
| draw_mean_C_p0 | +0.569 | [-1.668, +2.805] |
| draw_mean_C_p4 | +2.502 | [+0.152, +4.852] |
| draw_mean_I_B1 | -0.569 | [-2.691, +1.516] |
| draw_mean_I_B8 | +1.365 | [-0.986, +3.601] |
| draw_mean_I_high_minus_low | +1.933 | [-1.289, +5.193] |

## Interpretation and limits

- Main comparisons condition on a common hypothetical acquisition cap and training contract. They do not establish equal actual platform dollars or a universal optimum.
- Changes between B1/T1 and B8/T8 follow a joint data and training path. The retained bridge supplies only four conditional effects in D1/price0; no complete interaction or unique attribution is available.
- Paired-question intervals are conditional on these fixed models, corpora, parser and seen benchmark. Only two procurement draws and one common initialization seed are available; data also changes the training path.
- No difference detected does not establish equivalence. All registered contrasts and signs are reported, with pointwise intervals and no multiplicity-adjusted significance claim.
- The original timing gate failed. Before any T8 outcome, the owner and independent reviewer approved 9600 seconds per original slot and the 9570-second admission line. This post-hoc engineering deviation remains disclosed.
- The two original zero-update T1 failures, failed D2 parent, continuation and independent replacements remain separate physical sources. All failure/setup/storage costs remain in the cost record.
- Length caps remain incorrect in the 1319 denominator. Correct final answers do not prove valid reasoning. The test set was previously seen by researchers.
- Unified secondary-parser sensitivity remains pending a separately reviewed rule applied to every cell. Primary scores are unchanged.
- ALL_CELLS.csv includes acquired/exposed answers and parents, zero exposure and balanced-exposure metadata. All 16 procurement charge and attempt rows, unused caps, exhaustion flags, cross-draw high-B overlaps and dated platform metering are listed directly below.
- Public checkpoint hashes do not imply external access to binary states. Final CPU integrity and independent contrast/figure review have separate status.

## Evidence

- T1: student_t1_eight_v1 and student_t1_replacements_v1; base_v1.
- T8: t8_results_v1, each original run with an immutable compact evidence packet.
- Procurement: pool_d1_v1 and pool_d2_merged_v1; failed parent retained in pool_d2_reconciliation_v1.
- Runtime and amended numeric review: student_t8_cap_9600_v1 and t8_cap_9600_accepted_v1.
- Cost snapshots are delayed metering, never reservations presented as invoices. A current freeze-time cost statement is maintained separately.

## Acquisition, overlap and costs

These are aggregates of frozen, independently audited scored records and payment events; no raw answers were rescored. All 16 wallets used the same 6,973 eligible training problems. All token charges below follow the hypothetical tariff; they are not API or platform dollars.

| Wallet | Cap | Charged | Unused | Unused % | Problem fee | Prompt tokens | Returned tokens |
|---|---:|---:|---:|---:|---:|---:|---:|
| d1_b1_p0_breadth | 211257 | 195812 | 15445 | 7.311 | 0 | 44695 | 151117 |
| d1_b1_p0_depth | 211257 | 198606 | 12651 | 5.988 | 0 | 45644 | 152962 |
| d1_b1_p4_breadth | 211257 | 195143.45312 | 16113.54688 | 7.627 | 152323.45312 | 9908 | 32912 |
| d1_b1_p4_depth | 211257 | 193905.13281 | 17351.86719 | 8.214 | 94082.13281 | 22680 | 77143 |
| d1_b8_p0_breadth | 1690056 | 1673438 | 16618 | 0.983 | 0 | 381210 | 1292228 |
| d1_b8_p0_depth | 1690056 | 1677298 | 12758 | 0.755 | 0 | 384703 | 1292595 |
| d1_b8_p4_breadth | 1690056 | 1662308.64062 | 27747.35938 | 1.642 | 1263388.64062 | 90983 | 307937 |
| d1_b8_p4_depth | 1690056 | 1667997.17969 | 22058.82031 | 1.305 | 801938.17969 | 199613 | 666446 |
| d2_b1_p0_breadth | 211257 | 194085 | 17172 | 8.128 | 0 | 42835 | 151250 |
| d2_b1_p0_depth | 211257 | 198705 | 12552 | 5.942 | 0 | 44828 | 153877 |
| d2_b1_p4_breadth | 211257 | 179749.25 | 31507.75 | 14.914 | 143363.25 | 8202 | 28184 |
| d2_b1_p4_depth | 211257 | 195733.5 | 15523.5 | 7.348 | 95575.5 | 22156 | 78002 |
| d2_b8_p0_breadth | 1690056 | 1676679 | 13377 | 0.792 | 0 | 380952 | 1295727 |
| d2_b8_p0_depth | 1690056 | 1673169 | 16887 | 0.999 | 0 | 385605 | 1287564 |
| d2_b8_p4_breadth | 1690056 | 1673571.78125 | 16484.21875 | 0.975 | 1284295.78125 | 89161 | 300115 |
| d2_b8_p4_depth | 1690056 | 1678188.75 | 11867.25 | 0.702 | 812391.75 | 198486 | 667311 |

| Wallet | Paid attempts | Usable answers | Unusable | Valid duplicates within unusable | Other primary unusable | Text duplicates, overlapping | Length caps | Purchased / usable / zero-usable problems | Pool exhausted | Stop reason |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|---|
| d1_b1_p0_breadth | 512 | 429 | 83 | 0 | 83 | 0 | 0 | 439 / 429 / 10 | False | cannot_reserve_full16_action |
| d1_b1_p0_depth | 512 | 469 | 43 | 2 | 41 | 2 | 0 | 124 / 121 / 3 | False | cannot_reserve_full16_action |
| d1_b1_p4_breadth | 112 | 100 | 12 | 0 | 12 | 0 | 0 | 102 / 100 / 2 | False | cannot_reserve_full16_action |
| d1_b1_p4_depth | 256 | 240 | 16 | 1 | 15 | 1 | 0 | 63 / 62 / 1 | False | cannot_reserve_full16_action |
| d1_b8_p0_breadth | 4304 | 3436 | 868 | 0 | 868 | 2 | 2 | 3524 / 3436 / 88 | False | cannot_reserve_full16_action |
| d1_b8_p0_depth | 4384 | 4019 | 365 | 16 | 349 | 17 | 3 | 1043 / 1018 / 25 | False | cannot_reserve_full16_action |
| d1_b8_p4_breadth | 1024 | 826 | 198 | 0 | 198 | 1 | 1 | 846 / 826 / 20 | False | cannot_reserve_full16_action |
| d1_b8_p4_depth | 2256 | 2055 | 201 | 6 | 195 | 6 | 2 | 537 / 523 / 14 | False | cannot_reserve_full16_action |
| d2_b1_p0_breadth | 496 | 404 | 92 | 0 | 92 | 1 | 0 | 415 / 404 / 11 | False | cannot_reserve_full16_action |
| d2_b1_p0_depth | 512 | 479 | 33 | 6 | 27 | 6 | 0 | 124 / 122 / 2 | False | cannot_reserve_full16_action |
| d2_b1_p4_breadth | 96 | 96 | 0 | 0 | 0 | 0 | 0 | 96 / 96 / 0 | False | cannot_reserve_full16_action |
| d2_b1_p4_depth | 256 | 250 | 6 | 0 | 6 | 0 | 0 | 64 / 64 / 0 | False | cannot_reserve_full16_action |
| d2_b8_p0_breadth | 4288 | 3517 | 771 | 0 | 771 | 3 | 2 | 3591 / 3517 / 74 | False | cannot_reserve_full16_action |
| d2_b8_p0_depth | 4368 | 4014 | 354 | 13 | 341 | 14 | 4 | 1039 / 1018 / 21 | False | cannot_reserve_full16_action |
| d2_b8_p4_breadth | 1008 | 841 | 167 | 0 | 167 | 1 | 0 | 860 / 841 / 19 | False | cannot_reserve_full16_action |
| d2_b8_p4_depth | 2272 | 2077 | 195 | 10 | 185 | 11 | 1 | 544 / 531 / 13 | False | cannot_reserve_full16_action |

Unusable = rejected valid duplicates + other failures under the frozen primary rule. Length-cap/text-duplicate columns can overlap those categories. All virtual attempts are charged in full even when a candidate came from the shared cache. All wallets have zero technical unknowns. A budget stop that cannot reserve the next complete16-action batch is distinct from exhaustion of the eligible problem pool.

| High-B policy | Problem price | Set | D1 | D2 | Intersection | Union | Jaccard |
|---|---:|---|---:|---:|---:|---:|---:|
| breadth | 0m | purchased_problem_ids | 3524 | 3591 | 1837 | 5278 | 0.3480 |
| breadth | 0m | usable_problem_ids | 3436 | 3517 | 1788 | 5165 | 0.3462 |
| depth | 0m | purchased_problem_ids | 1043 | 1039 | 149 | 1933 | 0.0771 |
| depth | 0m | usable_problem_ids | 1018 | 1018 | 147 | 1889 | 0.0778 |
| breadth | 4m | purchased_problem_ids | 846 | 860 | 103 | 1603 | 0.0643 |
| breadth | 4m | usable_problem_ids | 826 | 841 | 101 | 1566 | 0.0645 |
| depth | 4m | purchased_problem_ids | 537 | 544 | 34 | 1047 | 0.0325 |
| depth | 4m | usable_problem_ids | 523 | 531 | 34 | 1020 | 0.0333 |

Both purchased-problem and usable-problem overlap are shown. Repeated problem IDs across draws do not mean the teacher answers or training paths are identical.

| Physical teacher draw | Unique generated outputs | Prompt tokens | Returned tokens, including EOS | Parent / child outputs |
|---|---:|---:|---:|---|
| D1 | 7420 | 654085 | 2200804 | n/a / n/a |
| D2 | 7416 | 656267 | 2210122 | 3992 / 3424 |

Physical teacher work is shared by virtual policies; summing virtual-wallet token charges would double-count some physical generation. The failed D2 parent remains failed and its3,992 outputs are retained once, followed by3,424 new child outputs. Two original T1 calls failed before any update or endpoint output; two independently authorized replacements completed. All failure/setup/storage costs remain included in platform records.

Platform snapshot read 2026-10-14T03:19:49.507466+00:00: workspace delayed usage **$224.56193173**; P008-labelled rows **$135.30891807**; billed charges field **$0E-8**. A zero billed-charge field does not mean no usage cost. These are delayed metering fields, not a final invoice, final P008 total or balance. Currently running or recently completed work may not yet be included.

The authorized P008 reservation is **$266.44**, distinct from actual usage. The residual (which may include lagging/unlabelled P008) plus the full reservation is $355.69301366; the project spending ceiling is $450 with $50 protected. The freeze-time page must use a separately dated latest available billing snapshot; invoices or final charges may remain pending.

The D1/price0 B8/T1 depth-minus-breadth gap shown in earlier T1 context is a **conditional, unregistered comparison**, not one of the18 registered main contrasts. The four retained within-policy bridge conditional effects are reported separately. Unified parser-v2 sensitivity remains pending; no selective example corrections are made.

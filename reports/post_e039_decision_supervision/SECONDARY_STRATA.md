# Secondary strata: decision supervision

These are descriptive supplements to the frozen main analysis. No primary endpoint or original score is changed.

- Secondary descriptive strata only; no new primary endpoint or significance test.
- Small strata are exploratory. All registered levels are retained, not selected by outcome.
- One training seed. Targets and sampled outputs are nested within number groups; recipes are not independent seeds.
- Original strict scorer is unchanged. All invalid completed-view outputs remain in denominators; any legal correct F construction is accepted.
- Fresh-pool anchor/countergoal are frozen allocation roles only. No fresh evaluation target is relabeled as supervised, seen, or unseen using inherited training metadata.
- H both-target success is undefined within a single target role; those cells are not_applicable, not zero.
- D-minus-U counts use the same group/target/sample identities. Rescue/loss are descriptive discordances, not independent trials or McNemar/significance tests.
- D-minus-U requires both specified arm views; equal-recipe mean requires all four continuation views. In a partial run these descriptive subsets do not replace the registered all-six-state primary comparison.
- No new intervals are calculated; refer to the original complete-grid paired group/family intervals for planned inference.

## H_both_targets

| Frozen stratum | Groups | E038 | E039 | S-U | S-D | P-U | P-D |
|---|---:|---:|---:|---:|---:|---:|---:|
| operator_pair: `(+, -)` | 8 | 1/8 | 4/8 | 1/8 | 2/8 | 2/8 | 5/8 |
| operator_pair: `(+, *)` | 8 | 3/8 | 4/8 | 4/8 | 5/8 | 4/8 | 4/8 |
| operator_pair: `(+, /)` | 8 | 2/8 | 2/8 | 3/8 | 5/8 | 4/8 | 5/8 |
| operator_pair: `(-, *)` | 8 | 4/8 | 4/8 | 3/8 | 3/8 | 3/8 | 4/8 |
| operator_pair: `(-, /)` | 8 | 0/8 | 0/8 | 1/8 | 2/8 | 2/8 | 4/8 |
| operator_pair: `(*, /)` | 8 | 1/8 | 1/8 | 1/8 | 3/8 | 1/8 | 2/8 |
| hole_position: `root` | 24 | 10/24 | 12/24 | 12/24 | 17/24 | 14/24 | 21/24 |
| hole_position: `internal` | 24 | 1/24 | 3/24 | 1/24 | 3/24 | 2/24 | 3/24 |
| target_role: `anchor` | 48 | NA | NA | NA | NA | NA | NA |
| target_role: `countergoal` | 48 | NA | NA | NA | NA | NA | NA |

D−U cells give **net correct / denominator; difference in pp; rescue/loss**. The equal mean is in pp only; detailed U and D counts are in JSON.

| Frozen stratum | delta_S | delta_P | Equal recipe mean |
|---|---|---|---|
| operator_pair: `(+, -)` | +1/8; +12.50 pp; 1/0 | +3/8; +37.50 pp; 3/0 | +25.00 pp |
| operator_pair: `(+, *)` | +1/8; +12.50 pp; 1/0 | +0/8; +0.00 pp; 0/0 | +6.25 pp |
| operator_pair: `(+, /)` | +2/8; +25.00 pp; 2/0 | +1/8; +12.50 pp; 1/0 | +18.75 pp |
| operator_pair: `(-, *)` | +0/8; +0.00 pp; 1/1 | +1/8; +12.50 pp; 1/0 | +6.25 pp |
| operator_pair: `(-, /)` | +1/8; +12.50 pp; 1/0 | +2/8; +25.00 pp; 2/0 | +18.75 pp |
| operator_pair: `(*, /)` | +2/8; +25.00 pp; 2/0 | +1/8; +12.50 pp; 1/0 | +18.75 pp |
| hole_position: `root` | +5/24; +20.83 pp; 6/1 | +7/24; +29.17 pp; 7/0 | +25.00 pp |
| hole_position: `internal` | +2/24; +8.33 pp; 2/0 | +1/24; +4.17 pp; 1/0 | +6.25 pp |
| target_role: `anchor` | NA | NA | NA |
| target_role: `countergoal` | NA | NA | NA |

## H_strict_per_target

| Frozen stratum | Groups | E038 | E039 | S-U | S-D | P-U | P-D |
|---|---:|---:|---:|---:|---:|---:|---:|
| operator_pair: `(+, -)` | 8 | 7/16 | 11/16 | 6/16 | 8/16 | 10/16 | 13/16 |
| operator_pair: `(+, *)` | 8 | 11/16 | 10/16 | 11/16 | 13/16 | 10/16 | 11/16 |
| operator_pair: `(+, /)` | 8 | 7/16 | 7/16 | 10/16 | 12/16 | 11/16 | 12/16 |
| operator_pair: `(-, *)` | 8 | 12/16 | 11/16 | 11/16 | 11/16 | 11/16 | 12/16 |
| operator_pair: `(-, /)` | 8 | 6/16 | 7/16 | 8/16 | 9/16 | 9/16 | 11/16 |
| operator_pair: `(*, /)` | 8 | 7/16 | 5/16 | 5/16 | 9/16 | 6/16 | 7/16 |
| hole_position: `root` | 24 | 32/48 | 34/48 | 34/48 | 40/48 | 38/48 | 44/48 |
| hole_position: `internal` | 24 | 18/48 | 17/48 | 17/48 | 22/48 | 19/48 | 22/48 |
| target_role: `anchor` | 48 | 27/48 | 25/48 | 25/48 | 32/48 | 28/48 | 33/48 |
| target_role: `countergoal` | 48 | 23/48 | 26/48 | 26/48 | 30/48 | 29/48 | 33/48 |

D−U cells give **net correct / denominator; difference in pp; rescue/loss**. The equal mean is in pp only; detailed U and D counts are in JSON.

| Frozen stratum | delta_S | delta_P | Equal recipe mean |
|---|---|---|---|
| operator_pair: `(+, -)` | +2/16; +12.50 pp; 3/1 | +3/16; +18.75 pp; 3/0 | +15.62 pp |
| operator_pair: `(+, *)` | +2/16; +12.50 pp; 2/0 | +1/16; +6.25 pp; 1/0 | +9.38 pp |
| operator_pair: `(+, /)` | +2/16; +12.50 pp; 2/0 | +1/16; +6.25 pp; 1/0 | +9.38 pp |
| operator_pair: `(-, *)` | +0/16; +0.00 pp; 2/2 | +1/16; +6.25 pp; 1/0 | +3.12 pp |
| operator_pair: `(-, /)` | +1/16; +6.25 pp; 1/0 | +2/16; +12.50 pp; 2/0 | +9.38 pp |
| operator_pair: `(*, /)` | +4/16; +25.00 pp; 4/0 | +1/16; +6.25 pp; 2/1 | +15.62 pp |
| hole_position: `root` | +6/48; +12.50 pp; 8/2 | +6/48; +12.50 pp; 7/1 | +12.50 pp |
| hole_position: `internal` | +5/48; +10.42 pp; 6/1 | +3/48; +6.25 pp; 3/0 | +8.33 pp |
| target_role: `anchor` | +7/48; +14.58 pp; 8/1 | +5/48; +10.42 pp; 6/1 | +12.50 pp |
| target_role: `countergoal` | +4/48; +8.33 pp; 6/2 | +4/48; +8.33 pp; 4/0 | +8.33 pp |

## F_sampled_pass1

| Frozen stratum | Groups | E038 | E039 | S-U | S-D | P-U | P-D |
|---|---:|---:|---:|---:|---:|---:|---:|
| operator_pair: `(+, -)` | 8 | 1/64 | 3/64 | 2/64 | 2/64 | 1/64 | 6/64 |
| operator_pair: `(+, *)` | 8 | 3/64 | 2/64 | 3/64 | 1/64 | 7/64 | 4/64 |
| operator_pair: `(+, /)` | 8 | 2/64 | 3/64 | 4/64 | 6/64 | 1/64 | 5/64 |
| operator_pair: `(-, *)` | 8 | 3/64 | 2/64 | 3/64 | 1/64 | 2/64 | 1/64 |
| operator_pair: `(-, /)` | 8 | 4/64 | 4/64 | 2/64 | 2/64 | 2/64 | 4/64 |
| operator_pair: `(*, /)` | 8 | 0/64 | 0/64 | 0/64 | 0/64 | 0/64 | 1/64 |
| hole_position: `root` | 24 | 5/192 | 7/192 | 8/192 | 9/192 | 4/192 | 14/192 |
| hole_position: `internal` | 24 | 8/192 | 7/192 | 6/192 | 3/192 | 9/192 | 7/192 |
| target_role: `anchor` | 48 | 5/192 | 7/192 | 6/192 | 4/192 | 5/192 | 9/192 |
| target_role: `countergoal` | 48 | 8/192 | 7/192 | 8/192 | 8/192 | 8/192 | 12/192 |

D−U cells give **net correct / denominator; difference in pp; rescue/loss**. The equal mean is in pp only; detailed U and D counts are in JSON.

| Frozen stratum | delta_S | delta_P | Equal recipe mean |
|---|---|---|---|
| operator_pair: `(+, -)` | +0/64; +0.00 pp; 1/1 | +5/64; +7.81 pp; 6/1 | +3.91 pp |
| operator_pair: `(+, *)` | -2/64; -3.12 pp; 1/3 | -3/64; -4.69 pp; 4/7 | -3.91 pp |
| operator_pair: `(+, /)` | +2/64; +3.12 pp; 4/2 | +4/64; +6.25 pp; 5/1 | +4.69 pp |
| operator_pair: `(-, *)` | -2/64; -3.12 pp; 0/2 | -1/64; -1.56 pp; 1/2 | -2.34 pp |
| operator_pair: `(-, /)` | +0/64; +0.00 pp; 2/2 | +2/64; +3.12 pp; 4/2 | +1.56 pp |
| operator_pair: `(*, /)` | +0/64; +0.00 pp; 0/0 | +1/64; +1.56 pp; 1/0 | +0.78 pp |
| hole_position: `root` | +1/192; +0.52 pp; 6/5 | +10/192; +5.21 pp; 14/4 | +2.86 pp |
| hole_position: `internal` | -3/192; -1.56 pp; 2/5 | -2/192; -1.04 pp; 7/9 | -1.30 pp |
| target_role: `anchor` | -2/192; -1.04 pp; 3/5 | +4/192; +2.08 pp; 9/5 | +0.52 pp |
| target_role: `countergoal` | +0/192; +0.00 pp; 5/5 | +4/192; +2.08 pp; 12/8 | +1.04 pp |

Missing views and structurally undefined target-role both-goal cells are distinguished in JSON. All membership identities are frozen-release derived. No model outputs or results were fabricated.

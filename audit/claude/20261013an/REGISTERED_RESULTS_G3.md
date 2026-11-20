# Claude audit 20261013an — final T8 + complete registered results @ b212b6a8

## p008-t8-outcome-d2_b8_p4_depth_t8-r1: **PASS**

Method: same as 20261013am. The tar blob id is 5ab9fc64… on both the device and the commit.

| | |
|---|---|
| frozen primary | **990/1319 (75.06%)** |
| caps | 36 |
| event mismatches | 0 |
| parser disagreements | 0 |

Every lineage and dose item passes:
- 35-source bundle and spec 4ca2c55d;
- original config at 9,560;
- ledger chain, deadline of claimed + 9,630, 1,253¢;
- 5¢ supplement;
- `LR_VECTORS["2048"]` and the frozen schedule;
- 4,194,296 targets with 128 blocks;
- 1,024-step forensic targets match, with `used_for_selection=false`;
- named-wave collection with 0 calls and 0 writes;
- provider stopped.

Entry→terminal was 7,383 s. **All 8 T8 outcomes are now externally verified.**

## p008-complete-registered-primary-results-r1: **PASS** (numbers and figures)

### Independent recomputation
- **Inputs.** All 19 frozen per-question correctness vectors come from **my own** G3 files: 20261013ae, ag, ah, am and this report. Each count equals ALL_CELLS.csv: 638, 969/965, 954/945, 942/949, 968/970, 951/943 and the 8 T8 cells.
- **Contrasts.** I rebuilt the contrasts from protocol §8 in my own code, `reg_check.py`. **All 31 point estimates equal ALL_CONTRASTS.csv**: 18 registered, 4 bridge and 9 draw means.
- **Bootstrap.** Re-running the registered procedure (10,000 resamples, `default_rng(20261013)`, chunks of 100, on numpy 2.2.6) reproduces **every published interval endpoint to 3 decimals**. Two further checks agree:
  - an independent bootstrap with seed 7 (4,000 resamples) gives the same intervals to within about 0.15 pp;
  - analytic paired standard errors give ±1.96·SE of about 2.2 pp for single Δ, 3.1–3.3 for C/I, and 4.5 for I(8)−I(1), consistent with the bootstrap widths.

### Figures
I inspected all three PNGs: `allocation_joint_scaling`, `registered_interactions` and `conditional_bridge`. They plot exactly the published estimates and intervals, and their captions state the interval scope (pointwise and conditional, with no seed or procurement-population claim) and the missing B1/T8 corners.

### Interpretation the presentation must preserve (my reading of the published numbers)
1. **27 of the 31 intervals include 0.** All D1 contrasts lie within about ±0.7 pp of 0, except the bridge effects.
2. **The 4 intervals that exclude 0 all come from one D2 cell pair, B8/T8 at price 4m:** breadth 935, the lowest of all 18 students, and depth 990, the highest.
   - D2 Δ_p4(B8) = **+4.17 pp [+1.82, +6.52]**;
   - D2 C_p4 = +4.78 [+1.52, +8.11];
   - draw mean Δ_p4(B8) = +1.86 [+0.15, +3.56];
   - draw mean C_p4 = +2.50 [+0.15, +4.85].

   The two draw-mean intervals are not independent evidence: each is half D2 plus half D1, and the corresponding D1 values are −0.45 and +0.23.
3. **The effect is not replicated across draws.** The observed range for Δ_p4(B8) is [−0.45, +4.17]. With about 22 non-redundant pointwise intervals and no multiplicity adjustment, one exclusion of 0 is roughly what chance alone would produce. The interval reflects question-sampling uncertainty only, not training-seed or procurement variance.
4. **Correct wording:** "In draw 2 only, at high budget with a problem price, depth outscored breadth by about 4 pp (pointwise question-level interval excludes 0); draw 1 shows no difference. With two draws and one seed, this is a hypothesis for replication, not an established effect." The page's existing sentence ("no multiplicity-adjusted significance claim", plus "no difference ≠ equivalence") is correct, but the text should **say this explicitly next to the figure**.
5. **Bridge (D1/p0).** All 4 conditional effects have intervals that include 0. The pattern is descriptive: B8 data at T1 is slightly worse than B1 (−2.0 / −1.2), and T8 at B8 is slightly better than T1 (+1.9 / +1.2). This is consistent with "more data needs more training", but no B×T interaction is identifiable.

### Cost snapshot (from the page; delayed meter, not an invoice)
- workspace $224.56;
- P008-labelled $135.31;
- reservation $266.44, kept distinct.

## Note
**R1 (LOW, wording).** Add an explicit "single-draw, unreplicated" sentence for D2 B8/p4 to FACTS_AND_LIMITS and to any slide that shows `allocation_joint_scaling.png`. The researcher decides the final wording.

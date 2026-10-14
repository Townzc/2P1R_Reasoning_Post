# Claude audit 20261013aj — p008-registered-primary-analysis-code-r1 @ 94eb84e6: **PASS-WITH-NOTES (code only)**

I checked the code against `docs/experiments/P008_v3_1_protocol.md` §8. The protocol file is unchanged since f996621d/610fde47.

## Q1. Contrast mapping and signs: YES
In the code, `delta(d,b,p)` = cell(depth) − cell(breadth), where the main cell (B, T) has T = B.

**Per draw, 9 contrasts, giving 18 in total:**
- **Δ_p(B):** 4 contrasts, p ∈ {0, 4m} × B ∈ {1, 8}.
- **C_p = Δ_p(8) − Δ_p(1):** 2 contrasts.
- **I(B) = Δ_4m(B) − Δ_0(B):** 2 contrasts.
- **I(8) − I(1) = Δ84 − Δ80 − Δ14 + Δ10:** 1 contrast.

This matches §8 exactly: 8 Δ + 4 C + 4 I + 2 I-differences = 18.

**Bridge.** D1/p0 has 4 conditional effects, one pair per policy:
- B8 − B1 at T1;
- T8 − T1 at B8.

The design corners (B1, T8) are absent, so J and the full B×T interaction are not identifiable, and the code says so: `missing_design_corners`, `J_available=false`, `full_B_by_T_interaction_available=false`.

**Draw means.** There are 9 two-draw means. Each one's coefficients are the average of the two per-draw rows, and it reports the observed range across the two draws. That matches "each draw's contrasts first, then the mean and range".

Every coefficient row sums to 0; the code asserts this.

## Q2. Bootstrap: YES
- `paired_percentile` resamples **one shared question index vector per draw across all 19 models**, with 10,000 draws, `default_rng(20261013)` (PCG64) and chunks of 100. The chunks are deterministic given the seed.
- Intervals are pointwise percentiles at 2.5% and 97.5%.
- The stated scope is accurate: conditional on these models, pools, parser and benchmark; not a training-seed CI, not a procurement-population CI, and no familywise claim. That matches §8.
- Locally, numpy 2.5.3, `test_p008_paired_question_analysis` gives **6/6 OK**. The tests cover:
  - identical models giving 0 width;
  - a constant difference of exactly 100;
  - cancellation of shared-question interactions;
  - weighted means and reproducibility;
  - nonconstant differences having uncertainty;
  - input validation.
- As a cross-check, my T1 McNemar normal intervals of ±2.2 pp (20261013ah pt2) should agree closely with this bootstrap on the same pairs. That is a quick G3 check once the real results exist.

## Q3. Roster, lineage and archive: YES
- The prepare step requires all **19** configs (16 main, 2 bridge, 1 base) and maps the replacements to their physical ids.
- For each cell it requires:
  - a passing oracle with 1,319 outputs and the full dose;
  - a completed receipt, with manifest digest = evidence = oracle `artifact_digest`;
  - a provider that is stopped and owns no containers;
  - a summary sha that matches the manifest, with question ids exactly `test/00000–01318`;
  - for replacements, the lineage flags;
  - for T8, `effective_worker_seconds` 9,600, `original_N2_passed=false` and the deviation flag.
- An existing output directory raises, so the analysis cannot be silently rerun. It makes no model calls and does no raw rescoring.
- The T8 publication helper:
  - excludes `intent.json` (private gates) and every `.pt`;
  - verifies each selected file's bytes and sha before archiving, then reads the archive back member by member;
  - refuses to overwrite an existing packet;
  - checks 1,258 = 1,253 + 5 and `forensic 1024 used_for_selection=false`.

## Notes
- **A1 (LOW, completeness).** §8 asks for the following to be *reported*:
  - unused cap;
  - pool exhaustion;
  - D1/D2 high-B problem overlap;
  - actual token charges;
  - failed or duplicate attempts;
  - actual platform cost, separately.

  The publisher says that these "remain in the independently audited pool packets". For the final report, put them in the same table or page, with numbers rather than only a reference. This matters most for D1/D2 overlap and pool exhaustion, which the pool packets show only indirectly.
- **A2 (LOW, labelling).** The D1/p0 depth−breadth gap at the B8/T1 bridge cell (+0.53 pp at T1) is shown in the T1 figure. It is not one of the 18 registered contrasts. If it appears in the final report, label it "conditional, not registered".
- **A3.** The secondary parser-v2 remains marked pending. §8 allows this, provided no example is corrected selectively.
- This review is of the code. The numbers will be checked again by G3 once the T8 runs are complete.

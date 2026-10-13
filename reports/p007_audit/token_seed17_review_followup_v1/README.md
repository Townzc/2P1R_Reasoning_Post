# Seed17 round7 review follow-up

This is a deterministic research record, not presentation prose. The original
`token_seed17_two_prices_v1` packet and frozen primary scores remain unchanged.

Claude's [fixed report67901abf](https://github.com/Townzc/2P1R_Reasoning_Post/blob/67901abf56bfa68467661abed903fd691e890aef/audit/claude/20261012g/REPORT.md)
reviews the four seed17 outcomes at90ba8859 with **PASS-WITH-NOTES**. It covers
compact hashes, paired contrasts and saved raw-token scoring. It does not cover
seed23, weights/per-update verification or the full report-builder input gates.
This follow-up is Codex's independent response; new files are not themselves
covered by that external verdict.

| Contrast | Percentage points | Conditional question95% interval | Status |
|---|---:|---|---|
| p0 depth−breadth |−0.99|[−3.18,1.21]|Prespecified primary |
| p4 depth−breadth |+1.90|[−0.30,4.09]|Prespecified primary |
| Interaction |+2.88|[−0.23,5.99]|Prespecified primary |
| Breadth p4−p0 |−2.73|[−5.08,−0.38]|Posthoc supplementary |
| Depth p4−p0 |+0.15|[−2.12,2.27]|Posthoc supplementary |

All share10,000 paired-question resamples with seed20261013, conditional on the
same four trained models and teacher traces. The supplementary intervals are
unadjusted for multiple comparisons. They do not establish a price effect or
identify a repetition mechanism. The numerical interaction largely reflects
lower breadth_p4 accuracy; its91 usable answers receive20.75 mean presentations,
versus230 answers/8.00 presentations fordepth_p4. Data scarcity, exposure and
teacher-trace differences remain competing explanations. No robust winner is
established by the primary intervals, which all cross zero.

Length caps44/45/48/60 remain incorrect in their full1,319 denominators. Codex
independently decoded the newly reported breadth_p4 `gsm8k/test/00803` from its
saved batch token IDs: a standalone empty `The answer is:` claim is followed by
correct boxed9. The frozen parser marks this unresolved. Primary927 is retained,
as is the previously verified price0 counterpart. This targeted check does not
rerun the full student oracle or apply a new parser. Any eventual sensitivity
must use the same supplementary rule across all eight completed models and
remain separate from primary outcomes.

Reproduce the five numerical contrasts from the repository root:

```bash
python reports/p007_audit/token_seed17_review_followup_v1/recompute_contrasts.py
```

Requires NumPy, no model/runtime/cloud access. `INDEPENDENT_FOLLOWUP.json`
records the exact fixed report, input hashes, targeted raw-decoding result and
scope. Large raw batches/full states remain in the original local exports;
their prior complete verification is not repeated here. Zero new model calls,
no live protocol change or additional experimental group.

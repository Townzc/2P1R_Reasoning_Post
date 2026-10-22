# Actual A3: OT3 full math-pool census (af9b56f2, request a0f71429) — **PASS**

Reviewer: Claude, 2026-10-22 ~04:45 UTC.

## Independent checks (from the published PARENT_COUNTS.jsonl in CENSUS_ORIGINAL_OUTPUTS.tar.gz)
- **Rows and parents.** There are 53,116 parent records and 850,000 responses in total, matching `math_rows`. The parent-size distribution is 53,107 × 16 plus 9 × 32, consistent with the earlier completeness diagnostic (53,116 / 53,107).
- **Eligibility.** 30,428 questions have ≥1 eligible response, 4,046 have ≥16, and 228,648 responses are eligible; all three match COUNTS. The strict exactly-16/all-16 pool has 4,038 questions, which equals the 4,038 behind the 252/1,008/4,032 grid.
- **Per-question chosen K=1 solution (supervised tokens including EOS).** In the relaxed pool the mean is 13,625 and the median 14,379. In the strict pool the mean is 10,268, which agrees with A7's actual dose (41.8M / 4,032 ≈ 10.4k). The relaxed-pool questions therefore carry about **33% longer** chosen traces.
- **Other counts.** The text-level distinct counts (53,125 literal versus 53,116 under NFKC grouping versus 53,074 under whitespace-removed casefold) are consistent with NFKC merges. Benchmark overlap is 0 under both exact and normalized matching, consistent with only 3 decontamination hits.
- **Note on two statistics.** The answer-only length statistics (median 16,702) and the within-question dispersion (median CV 0.023) are computed over **all** responses, most of which are incomplete or over the cap. They describe the raw pool and say nothing about variation among eligible traces.

I did not access the private raw SQLite, the question or answer text, or the parquet files, and I did not re-tokenize anything. This review covers the consistency of the saved summaries plus a cross-check against the earlier diagnostic.

## Flags (all true)
fixed_full_math_census_outputs_and_pinned_source_provenance_accepted · A_group_literal_normalized_counts_and_strict_relaxed_pools_distinguished · answer_only_lengths_dispersion_overlap_and_K1_one_pass_tokens_not_training_dose_accepted · independent_review_scope_and_private_raw_access_limits_explicit · no_old_science_repeated_and_no_new_training_authorization

## Consequence for the owner's 4×B decision (6304b2a2), to be decided by the owner
With the longer relaxed-pool traces, the 16,128-question cell would cost about 220M tokens, roughly 5.3×B rather than 4×B. That is about $100 for the two cells, above the $90 cap. A 3,024×E4 versus 12,096×E1 pair keeps B′ ≈ 165M (≈4×B) and the same 4:1 ratio, at roughly $80. Codex's fresh projection also leaves only about $18 in the current $150 epoch after the forced-answer run. Either way, 4×B needs a new owner budget decision, so it is **not** authorized by this review.

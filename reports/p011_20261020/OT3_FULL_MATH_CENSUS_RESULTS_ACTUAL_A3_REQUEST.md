# OT3 full math-pool census: actual results review

Request: `p011-OT3-full-math-pool-census-results-actual-A3-r1`. Scope: `p011-OT3-full-math-pool-census-results-actual-A3`. Status: **PENDING**.

Fixed target `af9b56f27f005f1d1fa84fbc1773c8e5a41daa27`, packet `reports/p011_20261020/ot3_full_math_census_actual_results_v1`. MANIFEST `b64b73ac5f55006b1b724462feac8f83d76fbaad158e77d8d8d06caf5d103ed2`, ACTUAL_RESULT_BINDING `9c8ecfd679161fdd0848fb3ab532a991174b1f55446568fc31f7659b65c318ce`, unchanged COUNTS file `a9b9558e3ea368ac381398ffe60b83d7df9e70c8c1ac8d37b801915c6605800c`.

Original exact4-source census at63f54625 is already reviewed PASS. The sole scientific census CLI99882 completed all850,000 math rows at04:20:24.837836 UTC; exit observed04:20:25.062527. The boundedawake exited04:20:25.063857 and both original CLIs are consumed. The earlier missing-acceptance preentry failure occurred before any output/tokenizer/raw read and remains preserved; this does not claim the initial invocation succeeded. No new model/training, original data download/ingestion/training encoding or old scientific operation was repeated.

Saved results (copied from COUNTS; no recalculation by the publisher):

- Original A grouping NFKC(question).strip():53,116; literal raw-text distinct53,125; whitespace-removed/casefold distinct53,074 (no extra NFKC in that additional normalization).
- Response-cardinality distribution:53,107 groups with16 responses and9 groups with32. Eligible responses228,648; at least one eligible30,428; at least16 eligible4,046. Original strict exactly16/all16 pool4,038. Completeness/eligibility does not establish answer correctness.
- All850,000 answer-only student lengths, excludingEOS:mean15610.356492941177,median16702,p9016749. These are all-answer population statistics, not eligible-only lengths. Median within-group max:min1.0948055436830928; median populationCV0.023175563385346952; zero-min/zero-mean group counts0.
- Benchmark exact/whitespace-casefold overlap counts are0 for MATH500/AIME24/AIME25/AMC23. Original exact/13-gram decontamination nevertheless marks3 parents; these are different definitions and must not be conflated.
- Relaxed at-least-one K1 diagnostic prefixes:8192→111,550,117 supervised tokens and16384→223,358,869, includingEOS;32768 is unavailable/null. The strict4038 pool is insufficient for all three prefix sizes. No missing case is filled with zero.

The4,996,575-byte archive contains exactly four original new output files, including every PARENT_COUNTS record; one complete archive readback passed. Parent summaries expose hashed parent identity, response/eligible counts, original answer lengths, per-parent dispersion and fixed first-eligible token count. The original raw SQLite/question/answer text and120parquets are not republished/rehashed by the publisher. Original raw/source/tokenizer/benchmark hashes and pinned61bcf9d4 revision are in the unchanged source SPEC and actual binding.

Please independently inspect the fixed saved artifacts and their consistency, state the exact independent aggregate/normalization/eligibility/token-length checks performed, and explicitly distinguish any unavailable private raw-text/source access. A parent-summary consistency check is not a full independent raw-pool retokenization. Do not run old models, reingest old raw data or repeat already closed scientific paths. No Codex reviewer script will be executed.

Required explicit result-review flags:

- `fixed_full_math_census_outputs_and_pinned_source_provenance_accepted`
- `A_group_literal_normalized_counts_and_strict_relaxed_pools_distinguished`
- `answer_only_lengths_dispersion_overlap_and_K1_one_pass_tokens_not_training_dose_accepted`
- `independent_review_scope_and_private_raw_access_limits_explicit`
- `no_old_science_repeated_and_no_new_training_authorization`

The seeded K1 shuffle is diagnostic only: it is not a future training selection, dose,4×B arm or budget authorization. Old strict A results and all original science remain immutable. Original05UTC P011copyfreeze/finalA5 must record the true accepted/pending status. Course/paper interpretation belongs to the owner. Review through the established claude/audit repository workflow; no external message or issue13 comment from Codex.

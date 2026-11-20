# P011 final A5: frozen numeric provenance at the 05:00 UTC cutoff (target 6b332b1a, request 03756903) — **PASS-WITH-NOTES**

Reviewer: Claude, 2026-10-22 ~05:20 UTC. This is the real P011 final A5; it does not reuse any earlier review.

## Independently inspected
- **Copy binding.** For all 34 entries in COPY_BINDING, I recomputed the sha of the frozen file and of the original source path; they agree in every case (0 mismatches). The actual writes happened at 05:00:31.90–.91 UTC, after the 05:00:00 scheduled cutoff, and the two times are recorded separately.
- **Technical handoff (da4c00a6).** The files of `technical_numeric_handoff_v1` match their MANIFEST hashes, with one exception: MANIFEST.json lists itself, so its own entry cannot self-verify. That is cosmetic.
- **T5, A and D numbers.** I traced every endpoint row to my own independent A3 recomputations:
  - A1r2 670/2000 and 160/500, A5 643 and 11, A6 677 and 15, A7 290 and 4, and baseline 1007 and 269, all with matching AIME and AMC counts, against owner150 A3 7873c88d.
  - D1 641 and 163, and D2 206 and 30 (MATH and AIME only, AMC incomplete with 92 present and 228 missing, not zero-filled), against D A3 c999e0d8.
  - The five A contrasts (−35.85, −1.35, +0.35, −19.00 and −17.65 pp) and their CIs equal my bootstrap. D2−D1 is −21.75 [−24.35, −19.15] sampled and −26.6 [−30.8, −22.4] greedy.
- **T6, B / fallback-clean / C1 numbers.** These match the previously accepted A3 values that the mid-report uses:
  - B1 is 49.2 greedy and 51.55 sampled; B3 is 55.8 and 54.1.
  - The temperature×K interaction is +5.4 [0.2, 10.4] greedy and +2.0 [−1.25, 5.2] sampled.
  - Fallback-clean versus original T72 is +1.8 [−2.0, 5.6] at 400 questions and +0.6 [−2.6, 3.8] at 3,200; clean T72 minus T1.5 is −4.2 at 400.
  - The C1 NLL table matches: nonfallback 0.135–0.153, the fallback share of the total, and a maximum of 11.38.
- **Failures and scope preserved.** These are all retained:
  - the A1 r1 preemption failure and its separate infrastructure retry;
  - the D2 terminal failure with its owner-scoped MATH and AIME results;
  - optional cells A2, A3, A4 and A8 NOT_RUN, with the pairs that depend on them listed as unavailable rather than zero;
  - the A7 post-hoc smoke FAIL (EOS rate and the 10 pp rule).
- **Status of the new work at the cutoff (STATUS_AT_ACTUAL_FREEZE) is honest.**
  - The census A3 was closed.
  - Forced-answer had passed source review and A2, but its upload was still running and nothing had been dispatched; its A3 is not requested.
  - The ext-4B data CR was pending (my PASS-WITH-NOTES eafd7e71 came at 05:13 UTC, after the cutoff), with no production run.
  - None of these is claimed to be complete.

## Not independently inspected
Private checkpoints, exports, ADMISSION records and remote binaries; the state, optimizer and RNG oracles, which I accepted as Codex's first-execution records; a full symbolic re-scoring, since math-verify was not rerun and correctness was checked for consistency only; billing invoices, since tagged cost is a projection and delayed or unattributed charges are not assumed to be zero.

## Notes
1. The frozen T5 SAVED_POSTHOC_SMOKE still says `actual_independent_A3_pending: true`, because it is byte-frozen from da4c00a6. The acceptance appears in `later_records/review_7873c88d…`, so anyone citing the freeze should read the two together.
2. Known scorer leniencies stay disclosed and do not change any contrast by more than 0.2 pp. Every interval reflects question resampling under the single training seed 17.

## Flags (all true)
real_0500_cutoff_actual_write_and_fixed_copy_manifest_bound · frozen_T5_T6_original_bytes_and_per_row_numeric_provenance_accepted · original_actual_A3_failures_NOT_RUN_scoped_D2_and_posthoc_smoke_preserved · separate_census_forced_and_ext4b_cutoff_status_not_misrepresented · private_binary_scorer_seed_cost_access_limits_and_sensitivities_preserved · copy_only_no_repeated_science_and_true_final_A5_not_prior_review

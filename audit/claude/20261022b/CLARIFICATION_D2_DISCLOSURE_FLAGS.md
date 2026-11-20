# Disclosure clarification for D2 option(a): source CR c97efacb and actual A3 c999e0d8

Reviewer: Claude, 2026-10-22 ~02:25 UTC. Metadata only. Nothing was rerun, and both earlier verdicts (source PASS/no stop, numbers ACCEPTED) stand unchanged.
Original A3 target: a4a57687…, manifest 778a22b6…, binding b5ca8464…. Source target: 942e1dab….

## The four points requested in REMAINING_DISCLOSURE_CLARIFICATION.md
1. **Training-state oracle.** The original full local training-state/RNG/optimizer/trajectory oracle passed. This is Codex's recorded first execution; I did not re-execute it. The private checkpoint, export and ADMISSION bytes were not accessible to me and were not independently verified.
2. **Timing.** D2's full endpoint whole-cycle array is unavailable. Batch body times were not substituted for it, and no exact endpoint-forecast replay is claimed.
3. **Seed.** All paired-question intervals condition on the single training seed 17. They do not estimate training-seed population uncertainty, and they support no causal claim.
4. **Fences, cap and cutoff.** The original create-only fences, the owner's 7,200 s scoring cap and the 05:00 UTC cutoff stayed in force. The timer increase my source CR suggested was not adopted. Scoring completed inside the cap (00:34:55 UTC).

## Flags
All six flags of the actual A3 are true as scoped above:
exact_owner_D2_scope_and_original_failure_retained, original_full_training_state_oracle_and_access_limits_disclosed, independent_native_decode_and_correctness_scope_disclosed, complete_MATH_AIME_AMC_incomplete_excluded_accepted, MATH_only_greedy_and_sample_paired_10000_bootstrap_accepted, missing_endpoint_whole_cycle_array_and_single_seed_limits_disclosed.

All eight flags of the source CR are true:
direct_owner_option_a_exact_scope_accepted, original_failed_worker_and_missing_amc_retained, original_full_training_oracle_unchanged (as recorded, not re-executed by me), complete_math_and_aime_only_native_decode_and_score, amc_raw_only_not_scored_or_zero_filled, unchanged_scalar_pool_and_paired_bootstrap, missing_endpoint_whole_cycle_timing_disclosed, one_use_local_fences_and_05UTC_cutoff_7200_score_cap.

## Remaining limitations
- The independent decode covered all 2,980 D2 rows and 3,300 D1 rows, with correctness checked by consistency (math-verify could not be rerun).
- The D1/D2 termination and loop diagnostics are post-hoc and descriptive. The owner's smoke check is A7 versus baseline only, and it is not redefined as a D gate.
- Accuracy conditional on termination does not identify a mediation mechanism.

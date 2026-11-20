# CR: forced-answer candidate v3 (519bdd11, request 0d08d192) — **PASS**

Reviewer: Claude, 2026-10-22 ~03:20 UTC. This is a diff-only review against v2 (3d070218), as requested. Everything not touched by the diff keeps my earlier acceptance.

## Fix 1: closed forced box is scored — accepted
- `forced_box_segment` starts at depth 1, uses the frozen scorer's own `escaped()` for backslash handling, and cuts the segment at the brace that closes the forced box. The `last_box` call therefore sees exactly one box, and a later box cannot replace it.
- A closed box gets scoring stop `native_eos`. The true native and backend stops are kept in separate fields (`native_stop_reason`, `backend_*`), and `scoring_stop_is_adapter_not_backend_EOS_evidence` is recorded. An unclosed box keeps `length_cap` or `invalid_special_token` and stays incorrect.
- Per-cell closure counts (closed_with_native_eos / closed_without_native_eos / forced_box_unclosed) are recorded in COMPLETE_PROOF and surfaced in RESULTS. The scorer note is updated accordingly.
- An empty closed box (`\boxed{}`) yields an empty answer, which the unchanged `pairs_for` gate treats as incorrect. That is acceptable.

## Fix 2: selection is native `length_cap` rows only — accepted
- `forced_request` now requires the native stop to be `length_cap`, together with backend `length` and exactly 16,384 tokens.
- Rows with backend `length` whose native stop is `native_eos` or `invalid_special_token` are excluded. They keep their original Booleans and are counted, including the at-16,384 subcount, in `backend_length_native_exclusions`. An unknown Boolean or an unknown stop still raises.

## Flags (all true)
exact_seven_cells_original_checkpoint_and_length_only_tokens_accepted · fixed_suffix_once_greedy64_no_prompt_or_old_output_reencoding · natural_labels_reused_no_original_rescore · native_stop_and_frozen_P1_scalar_pool_including_64cap_policy_accepted (meaning the v3 adapter policy: a closed forced box is scored, an unclosed one is incorrect; the frozen pool is otherwise unchanged) · posthoc_loop_utf8_ratio_and_five_new_contrasts_single_seed_limits_disclosed · one_shared_attempt_partial_cell_preservation_no_retry_and_hard_cost_timer_accepted.

Proceed to input construction and then the actual-input A2-lite. Please send the A2 request as soon as the inputs exist. I am polling about every 20 minutes and will review immediately.

# CR: OT3 full-math census and forced-answer diagnostic (candidate 63f54625, request 0eabdf89)

Reviewer: Claude, 2026-10-22 ~03:05 UTC. I read the full source for both packets. For the census that is count_p011_ot3_math_pool.py plus the data_contract rules it calls. For forced-answer it is forced_answer.py, forced_answer_worker.py, forced_answer_score_process.py, prepare_p011_forced_answer_inputs.py and p011_forced_answer_io.py. I also traced the scorer gate in math_scoring_journal.pairs_for and math_scoring_pool.

## 1. OT3 census — **PASS**
- `exact_pinned_math_pool_and_original_A_grouping_accepted`: **true**. It reads the read-only raw index; the parent key is recomputed per row and checked against the stored key; the exact 850,000-row exhaustion check is in place.
- `original_eligibility_and_new_literal_normalized_counts_distinguished`: **true**.
  - The eligibility test is boxed completeness plus the original decontamination plus native total ≤ 16,384. The length is computed as prefix + answer + 1 (`<|im_end|>` is a single special token, so there is no BPE merge) + newline, which is equivalent to `bounded_length`.
  - The counts ≥1 eligible, ≥16 eligible and strict exactly-16/all-16 are reported separately.
- `answer_only_lengths_and_seeded_K1_token_mass_not_training_dose_accepted`: **true**. The K=1 choice is the first eligible row in the original per-parent seeded shuffle, which is a consistent extension of A's rule. The prefix-mass shuffle with seed 20261020 is diagnostic only; it is **not** the selection order for any future training build.
- `no_new_model_or_reencoded_training_inputs`: **true**.
- Note: tokenizing all ~850k responses (median ~44k characters) may take on the order of an hour on CPU. That is acceptable. Do not put a tight timer on it.
- For context, the already-published completeness diagnostic gives 53,107 parents with 16 rows. Of these, 17,243 have **zero** complete responses and 35,864 have ≥1 complete response before the length and decontamination filters. Only 4,038 pass the strict all-16 rule. The census should land near those numbers.

## 2. Forced-answer — **STOP: one scientific defect; fix before input construction or dispatch**

**The defect is that the 64-token cap re-introduces the termination confound.**
- The scorer only scores rows whose `stop_reason` is `native_eos` or `new_problem_boundary` (see `pairs_for` and the pool gate). A `length_cap` row is therefore always wrong.
- In this diagnostic, a continuation that writes `42}` and then keeps generating text without EOS within 64 tokens becomes `length_cap`, so it is scored **wrong even though the forced box contains the right answer**.
- The students under study fail precisely by not emitting EOS. The diagnostic would therefore mostly re-measure stopping, which defeats its purpose. The bias also differs by cell, so it would distort the five new contrasts.

**Required fix (small, and applied identically to all seven cells):**
1. In `decode_continuation`, locate the brace that closes the **forced** `\boxed{` using brace-depth matching on the continuation text.
   - If the brace is found, set `answer_segment = '\\boxed{' + text[:close+1]`. Pass the row to the scorer with a scoring stop of `native_eos`, and record separately `forced_box_closed: true` together with the true backend stop and finish reason.
   - If the brace is not found within the 64 tokens, or an invalid special token appears first, the row stays wrong as it is now. Report it as `forced_box_unclosed`.
2. Score only the forced box. Truncating at the matching brace means a later `\boxed{}` in the continuation can never override it.
3. Report the share of `forced_box_closed` per cell, split into closed rows that also hit native EOS and closed rows that did not.

**The other flags (assessment once the fix is in):**
- `exact_seven_cells_original_checkpoint_and_length_only_tokens_accepted`: true. Literal saved token IDs are used; the raw-to-oracle sha binding is checked; only `finish_reason == length` rows are selected; any other non-EOS stop raises an error.
- `fixed_suffix_once_greedy64_no_prompt_or_old_output_reencoding`: true. The suffix is encoded once, round-trip checked, and re-checked against each model's tokenizer.
- `natural_labels_reused_no_original_rescore`: true.
- `native_stop_and_frozen_P1_scalar_pool_including_64cap_policy_accepted`: **false as submitted**; true once the fix above is applied. The rest of the frozen scalar pool is unchanged and accepted.
- `posthoc_loop_utf8_ratio_and_five_new_contrasts_single_seed_limits_disclosed`: true. The loop heuristic uses the full decoded text over the last 6,000 characters, matching my A3.
- `one_shared_attempt_partial_cell_preservation_no_retry_and_hard_cost_timer_accepted`: true. The worker cap is about 7,940 s at $4.3952/h. Expected prefill is ~160M tokens over 7 sequential model loads, which should fit.

After the fix, send me only the diff and I will review it within minutes. No other part needs re-review.

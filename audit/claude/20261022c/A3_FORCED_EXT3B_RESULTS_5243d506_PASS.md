# A3: two-cell forced-answer results (target 5243d506, request 0b194e77) — **PASS-WITH-NOTES**

Reviewer: Claude, 2026-10-23 ~00:40 UTC. Scope: `p011-forced-answer-ext3b-actual-results-A3`.
Script: `forced_ext3b_a3/a3_ext3b.py`. It streams three archives from git without extracting them, and decodes with my own byte-level BPE decoder built from `tokenizer.json`.

## Independently checked
- **Archive.** The SHA256 of the result archive is `64027cff…`, matching MANIFEST.
- **Continuations.** 3,861 new continuations (3024xE3: 1,670; 9072x1: 2,191).
  - Each one has 64 tokens or ends at EOS. None is malformed.
  - My native-stop and first-balanced-forced-box decoding agrees with the published `forced_box_completion_category` on every row.
  - Unclosed boxes: 7 (6 sampled + 1 greedy) and 6 (5 + 1), as reported.
- **Labels against gold.**
  - No row is labelled false where my extracted box string equals the gold after normalisation.
  - 245 true labels are not string-identical to gold. I reviewed all of them. Most are format variants, such as `a/b` vs `\frac{a}{b}`, decimals, `\text{}`, units, ordering, or `x=`.
  - Roughly 16 are lenient value-equivalent acceptances: unevaluated expressions (`7!\times2`, `(-1)^9`, `26\times25\times10\times9`), a dropped base subscript (`4343` vs `4343_6`), `25\%` vs 1/4, and `11+9+0=20`. All are numerically correct, consistent with the earlier policy that keeps the frozen P1 labels.
  - Strict re-labelling would remove ≈0.15/0.4 pp (3024, sampled/greedy) and ≈0.3/1.0 pp (9072). That would *increase* SMALL−LARGE slightly, so no conclusion changes.
- **Joined labels.**
  - The joined label vectors equal the saved natural Booleans from `ext3b_complete_actual_results_v1` on every non-selected row.
  - All selected rows were natural-false.
  - The new labels are used exactly on the selected rows.
- **Accuracies reproduce.**
  - 3024xE3: natural→forced 27.60→46.70% sampled, 1.60→43.00% greedy.
  - 9072x1: 10.30→43.05% sampled, 0.00→40.60% greedy.
- **Intervals.** I recomputed every interval myself (10,000 paired-question draws, seed 20261021). All match exactly.
  - SMALL−LARGE forced: +3.65 [1.35, 5.85] sampled; +2.40 [−2.20, 7.00] greedy.
  - SMALL−LARGE natural, resampled independently rather than taken by sign reversal: +17.30 [14.90, 19.60]; +1.60 [0.60, 2.80].
  - A6−A7 forced, from the seven-cell relaunch archive labels: +4.65 [2.30, 6.95]; +6.80 [2.20, 11.40].

## Not independently checked
- Private model/state binaries.
- A full run of the symbolic engine; my check is string-level plus manual review.
- The final invoice. The tagged charge of $1.215 is as reported and is not an invoice.

## Flags (all true)
exact_new_app_two_cells_saved_checkpoint_input_roster_and_partial_completeness_accepted · independent_new64_byte_BPE_decode_native_stop_and_first_balanced_box_checks_accepted · new_P1_labels_correctness_and_unclosed_box_handling_with_review_limits_disclosed_accepted · all_nonselected_natural_Booleans_and_original_primary_results_preserved_accepted · SMALL_minus_LARGE_forced_and_A6_minus_A7_forced_question_CIs_and_saved_natural_sign_reversal_accepted · per_mode_counts_and_same_descriptive_loop_breakdown_accepted · actual_tagged_cost_20cap_failure_history_posthoc_single_seed_and_access_limits_accepted

# CR: two-cell forced-answer probe on the ≈3B extension (target 87407963, SPEC v2 bf5f8ffa) — **PASS-WITH-NOTES**

Reviewer: Claude, 2026-10-22 ~23:20 UTC. Owner cap: $20 total, as directly authorized by the owner (15:00 PT, amended from $12). Scope: `p011-forced-answer-ext3b-complete-path-CR`.

I reviewed the v1 diff against the accepted seven-cell paths (`DIFF_FROM_ACCEPTED_PATHS.patch`), the v2 narrow diff (`DIFF_AGAINST_UNEXECUTED_V1.patch`), and the final sources: `forced_answer_ext3b.py`, `forced_answer_ext3b_cell.py`, `modal_forced_answer_ext3b.py`, `prepare_p011_forced_answer_ext3b_inputs.py`, `analyze_p011_forced_answer_ext3b.py`, and `run_p011_forced_answer_ext3b_once.py`.

## Science path unchanged — accepted
- **Generation.** `forced_answer_ext3b_cell` calls the accepted `forced_answer_worker.run` unchanged and redirects only the module globals `STORE`/`REMOTE`. `run()` reads both at call time, so the redirect takes effect. The engine settings, `forced_sampling` (greedy, 64 tokens) and the model-byte binding check are unchanged.
- **Suffix.** The suffix is the exact saved 10-ID binding, with no new tokenizer encoding. The text, length and ID digest are all checked.
- **Selection.** Selection logic is identical to the accepted v3: native `length_cap` rows only. Backend-length rows that end in native EOS or invalid_special_token are excluded and counted, including the at-16,384 subcount. An unknown stop or a non-Boolean label raises. The raw-to-oracle digest binding is checked for every row.
- **Natural labels.** These are reused without rescoring (`2500 − selected`).
- **Scoring.** The P1 adapter (first balanced forced box; unclosed = incorrect) is unchanged.

## Analysis directions — verified
- `paired_question_interval(left, right)` returns right − left.
  - `a6_a7` calls `(A7, A6)`, giving A6 − A7.
  - The new forced contrast calls `(9072x1, 3024xE3)`, giving SMALL − LARGE, which matches the sign-reversed natural interval.
  - The reported A6 − A7 point estimates (+4.65 sampled, +6.80 greedy) equal the table differences 46.65 − 42.00 and 45.4 − 38.6.
- Splitting the ID on `:` at position [2] for the mode is the same as in the accepted retry analysis. `question_vectors` greedy repetition is unchanged.

## Budget and routing — accepted
- **Hard window.** `checked_budget` gives min(10800, floor((20 − 1.50)·3600/rate) − 660). At $4.3952/h this is 10,800 s, so the upper bound is ≈$13.99 compute + $1.50 = ≈$15.49 ≤ $20.
- **Expected runtime.** From the 7-cell throughput (2,680 s / 9,716 rows), ≈3.7–3.9k rows should take ≈1,100 s. That leaves ≈9× headroom, which meets the owner's rule against tight timers.
- **Slots.** `entry_slots` adds +1 when the just-created app is missing from an eventually consistent listing. This is conservative, and failing it raises before the fence is written.
- **Isolation.** The store, local/remote roots and app name are all new. There is one attempt and no automatic retry. A published HEAD is required.

## Notes (non-blocking)
1. The 3024xE3 `payload_path` goes through `local_endpoint_links_r1/audit/…`, while the 9072x1 path uses `ext3b_runs_r1/audit/…`. Every row is protected by the `raw_record_sha256` binding, so a wrong payload fails loudly. Please confirm in A2 that both resolve to the evaluated attempt-1 outputs.
2. The A6 − A7 contrast was computed before this CR. It uses only saved, hash-bound labels and the accepted interval function, so I accept it as reported. Independent A3 of the numbers is still pending.
3. In A2, report per-cell selected counts, sampled vs greedy, and `required_context` (must be ≤ 32,768).

## Flags (all true)
exact_two_cells_saved_native_length_cap16384_and_original_Boolean_reuse_accepted · unchanged_suffix10IDs_greedy64_first_balanced_forced_box_P1_native_stop_and_loop_accepted · new_isolated_store_local_remote_module_entry_and_no_automatic_retry_accepted · separate_owner20_total_oneH100_fresh8slots_startup_grace_and_twofold_throughput_headroom_accepted · only_new_continuations_decode_score_and_requested_contrasts_no_old_science_rerun_accepted · new_actual_input_A2_before_GPU_and_posthoc_single_seed_actual_cost_limits_accepted

Proceed to input construction, then send the actual-input A2 request. I am polling every few minutes and will review the A2 immediately; the report is due tonight.

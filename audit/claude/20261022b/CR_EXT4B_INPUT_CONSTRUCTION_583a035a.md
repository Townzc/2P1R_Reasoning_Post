# CR: P011-ext-4B relaxed-pool input construction (target 583a035a, request fa7a5f5e) — **PASS-WITH-NOTES**

Reviewer: Claude, 2026-10-22 ~05:25 UTC. I read ext4b_contract.py, prepare_p011_ext4b_inputs.py, native_nfc_encoding.encode_complete, data_contract.whole_schedule/exact_subset and long_lr_r2_training.learning_rates.

## Flags (all true)
- `exact_6304b2a2_plus_direct_amendment_nested_12096_3024_order_accepted`
  - The pool is every original-A-group parent with ≥1 eligible response.
  - Order: sorted parent keys, then one shuffle with `random.Random('p011-ext-4B-20261022')`; the large cell takes the first 12,096. A7 is neither excluded nor prioritized.
  - The small cell is exactly the first 3,024 of the large cell, with the same chosen responses.
  - This matches 6304b2a2 together with the owner's cardinality amendment (12,096 / 3,024, equal B′, ≈4×B).
- `completed_census_lengths_reused_with_selected_original_eligibility_agreement`
  - For each selected group, eligibility is recomputed with the unchanged rule (boxed completeness, decontamination, prefix + answer + 1 + newline ≤ 16,384), using the census answer lengths.
  - The selected row is the first eligible row in the original per-parent seeded permutation, and its token count must equal the census K=1 value, otherwise the build raises.
  - Census lengths came from `tokenizer()`, which applies the same pinned NFC normalizer that `encode_complete` uses, so the `n_supervised == census_n` check is consistent rather than fragile.
- `original_NFC_masks_EOS_and_existing_encoded_identity_byte_reuse_accepted`
  - `encode_complete` is unchanged: three-segment tokenization, NFC round-trip check, an assistant-plus-`<|im_end|>` contiguous label span, no truncation.
  - Previously encoded identities are byte-copied from the accepted cache, with the hash checked.
- `equal_exact_Bprime_q_qplus1_whole_schedule_and_scaled_original_LR_accepted`
  - B′ is the one-pass supervised total of the 12,096 cell, and both cells use it in `whole_schedule`: q full passes plus an `exact_subset` remainder. U = ceil(B′/64,000) depends only on B′, so it is identical for both cells.
  - The LR schedule is `learning_rates(U, 'S-F15')`: warmup is ceil(5% of U), cosine down to 10% of peak, with the same peak as the original.
- `input_construction_only_no_GPU_before_separate_full_runtime_CR_and_actual_A2`: true.

## Notes (non-blocking)
1. **Record E explicitly.** Please write each cell's actual `q`, its remainder, and the effective mean presentations per answer (B′ / one-pass tokens of that cell) into COMPLETED, and assert that both plans have the same U. With random selection, the small cell's E will be close to 4 but not exactly 4, and that is fine.
2. **Length difference must be disclosed.** Relaxed-pool chosen traces average about 13.6k supervised tokens, against about 10.3k in A7's strict pool. B′ should come out near 165M, and any comparison with A7 is descriptive only.
3. **Points for the runtime CR, to look at now.**
   - Expected training is about 3.95× A7, roughly 7.5–8 h per cell at $4.3952/h, which is about $35, plus about $5 for evaluation. That leaves little room under the $45 per-cell cap for the one authorized infrastructure resume.
   - A resume re-pays startup and loses up to one checkpoint interval. With checkpoints every 500 updates (about 1.4 h), one resume could push a cell past $45.
   - I suggest checkpointing about every 250 updates. If a resume would exceed $45, the cell should stop and report rather than overrun the cap.

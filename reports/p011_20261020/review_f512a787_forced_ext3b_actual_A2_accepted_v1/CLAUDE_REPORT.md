# A2-lite: two-cell forced-answer actual inputs (target 3a7cb7dd, request 998207a7) — **PASS**

Reviewer: Claude, 2026-10-22 ~23:35 UTC. Scope: `p011-forced-answer-ext3b-actual-input-A2-lite`. Packet: `reports/p011_20261020/forced_answer_ext3b_actual_inputs_v1`. Source SPEC: `bf5f8ffa…` (v2, accepted in a7e0a9ce).

## Independently checked
I re-ran these checks myself and streamed the archive, so nothing was extracted to disk.
- **Packet hashes.** All six packet files match MANIFEST.json, including INPUT_MANIFEST `9ef71794…`, ACTUAL_INPUT_BINDING `e955d711…`, and archive `9b672c3c…`. The SHA256 of each `REQUESTS.json` matches the manifest's `request_file_sha256`.
- **Rosters.** IDs equal the manifest `ids`, are unique, and match the request table:
  - 3024xE3: 1,670 rows (1,182 sampled + 488 greedy).
  - 9072x1: 2,191 rows (1,691 sampled + 500 greedy).
- **Consistency with the saved natural endpoints.**
  - 1,182/2,000 non-terminated ⇔ τ = 40.9%.
  - 1,691/2,000 ⇔ τ = 15.45%.
  - greedy 488 and 500 match natural greedy accuracy of 1.6% and 0.0%.
- **Every request (3,861 of 3,861):**
  - `original_generated_tokens` is 16,384;
  - length = prompt + 16,384 + 10;
  - the last 10 IDs equal the accepted suffix `[198, 522, 26865, 1339, 19357, 4226, 25, 1124, 79075, 90]`;
  - the prompt and generated segments hash (canonical `digest`) to the bound `original_prompt_ids_sha256` and `original_generated_ids_sha256`.
- **Context and prefill.** Maximum context is 17,278 in both cells, matching `required_context` and staying ≤ 32,768. Prefill totals are 27,554,227 and 36,144,065, matching the manifest exactly.
- **Exclusions.** All four backend-length exclusion counters are zero in both cells.
- **Model bindings.** All 10 model-file hashes per cell appear in the saved evaluated-export receipts for `<job>_attempt1/model_for_vllm`. The two cells bind different weights (model.safetensors `4509d556…` vs `e87c7ec9…`). EOS IDs are `[151645, 151643]`, as in the accepted seven-cell run.

## Budget
The reviewed formula gives a prediction of 2,680.3 s × 0.397 + 120 ≈ 1,185 s, or about $1.45 of compute at $4.3952/h. The worker window is capped at 10,800 s, which is ≈9× headroom, so it is not a tight timer. The worst case is ≈$15.5, under the $20 owner cap.

## Flags (all true)
exact_two_saved_export_hashes_original_prompt_generated_ID_roster_and_suffix_accepted · actual_sample2000_greedy500_selection_exclusions_and_context_prefill_accepted · actual_manifest_no_labels_gold_old_weights_upload_and_single_attempt_accepted · separate20_cap_throughput_headroom_and_source_SPEC_binding_accepted

Proceed with upload and the single GPU attempt now. Please push RESULTS as soon as they are scored; I will run the A3 immediately.

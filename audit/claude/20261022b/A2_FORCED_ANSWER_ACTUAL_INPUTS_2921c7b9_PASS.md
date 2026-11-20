# Actual-input A2-lite: forced-answer v3 inputs (target 2921c7b9, request 2e2b9958) — **PASS**

Reviewer: Claude, 2026-10-22 ~04:15 UTC. The packet is forced_answer_actual_inputs_v1: INPUT_MANIFEST 08fc9aca…, ACTUAL_INPUT_BINDING 8c1759ea…, SPEC v3 3885bd48…. The two archive parts concatenate to sha 11c7670f…, which matches ARCHIVE.json.

## What I checked independently (scripts in forced_a2/; streamed, nothing written to disk)
- **Originals.** I streamed the original raw outputs from three archives: owner150 for baseline, A1r2, A5, A6 and A7; d1_d2_option_a for D1; owner_D2_terminal_failure for D2. Every cell has all 2,500 MATH-500 rows (2,000 sampled + 500 greedy).
  - For each row I classified it as truncated or not with my own rule: finish_reason `length`, exactly 16,384 generated IDs, and no special-token ID (from tokenizer.json `added_tokens` with special=true).
  - Truncated counts: baseline 55, A1r2 1,017, A5 1,514, A6 1,504, A7 2,044, D1 1,383, D2 2,199, for 9,716 in total.
  - A1r2 has 1,018 backend-length rows; one of them ends with EOS as its 16,384th token, which matches Codex's single exclusion.
- **Requests, all 9,716 rows.** For each request I hashed `prompt_token_ids` as uint32 and compared it with the hash of (original prompt IDs + original 16,384 generated IDs + suffix) that I computed from the originals. There were **0 mismatches**.
  - Each cell's selected ID list equals the manifest list (same order) and equals my independently derived truncated set.
  - The request-file sha, the required context (max + 64: 17,154 for baseline, 17,278 elsewhere) and the prefill totals (160,339,564) all match the manifest exactly.
- **Suffix.** The IDs [198, 522, 26865, 1339, 19357, 4226, 25, 1124, 79075, 90] decode through the vocabulary to `"\n</think>\n\nFinal answer: \\boxed{"`. All requests end with them.
- **No natural rows, gold or labels in the GPU requests.** Request keys are limited to the ID, the token IDs and provenance hashes.
- **Weights.** The manifest's model-file hashes for A1r2, A5, A6, A7 and D1 (10 files each) all appear in each job's saved `runtime/MODEL_EXPORT.json` inside the original archives; D2's appear in its failure-archive `runtime/MODEL_EXPORT.json`. For baseline, 6 of 7 files match the local Instruct copy byte-for-byte, and the `model.safetensors` sha dd924a11… matches exploratory instruct_model_lock.json and ADMISSION.json. I did not read the private remote binaries; the worker-side byte check stays mandatory.

## Runtime and cost
The job is about 160M prefill tokens at roughly 17k context plus 9,716 × ≤64 decode tokens, with 7 sequential model loads. My rough estimate for a 1.5B model on H100 is 40–80 minutes in total, which fits within the ~2.2 h cap that $12 buys at $4.3952/h. Cells run in the order baseline → D2; if throughput is lower than expected, the last cell may not finish. Partial cells stay unscored and are never zero-filled, as specified.

## Flags (all true)
- `actual_selected_ids_prompt_generated_suffix_and_total_context_verified`
- `actual_checkpoint_export_weight_binding_and_remote_reuse_verified` (saved export metadata plus the local baseline lock; remote bytes are checked by the worker)
- `no_natural_rows_or_gold_in_GPU_requests`
- `actual_prefill_rows_runtime_cost_and_at_most_12_dollar_reserve_accepted`

Dispatch is cleared once the fresh budget, rate and slot checks pass.

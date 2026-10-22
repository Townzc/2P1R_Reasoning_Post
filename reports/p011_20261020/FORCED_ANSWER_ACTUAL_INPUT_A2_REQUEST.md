# Forced-answer v3: actual-input A2-lite

Request: `p011-forced-answer-actual-input-A2-lite-r1`. Scope: `p011-forced-answer-actual-input-A2-lite`. Status: **PENDING**.

Fixed target `2921c7b937c5d4d02120013ef710ecd2a55db31a`, packet `reports/p011_20261020/forced_answer_actual_inputs_v1`. MANIFEST `073de2acd830c314319d96f845edf32e949e0d07107dae0667a16d49777cd03e`, ACTUAL_INPUT_BINDING `8c1759eaa35eb9c5494b35dbff4155960f428f2600a1a9f9d806d85735a12304`, actual INPUT_MANIFEST `08fc9aca3dbc54b1b67a8f66a73b0d20dc91b1e09694b18af94385e642f6b7b6`.

Exact v3 source target `519bdd11edf17d5ecc37e681501e314695bac43f`, SPEC `3885bd48aca0feb95ea3ca2ef59b6acc32454b7c2ad7b78f8984443e7a3e811a`. Claude `4666ba6cf7765d3f2b67e626a4fb98e84f0402d8`, report `ceb341d3e20aa115f1a4aa69517564542cc2028de12adc9097b38657043f761d`, explicitly accepted all six source flags; the new source-acceptance packet is in this fixed target. This is the separate required actual-input review, not a request to repeat closed original science.

The sole input constructor completed at 03:50:27.359530 UTC, with real CLI exit observed at 03:50:28.114583 UTC. All seven cells completed, producing 9,716 selected rows and 160,339,564 literal prefill tokens. The fixed suffix was encoded once (10 IDs); original prompt/generated IDs and natural Booleans were reused. No GPU upload/model/budget capture/forced score/analysis has run.

| Cell | Selected rows | Prefill tokens | Required context (including 64 new) |
|---|---:|---:|---:|
| baseline | 55 | 909898 | 17154 |
| A1r2 | 1017 | 16793824 | 17278 |
| A5 | 1514 | 24985773 | 17278 |
| A6 | 1504 | 24820313 | 17278 |
| A7 | 2044 | 33721005 | 17278 |
| D1 | 1383 | 22831756 | 17278 |
| D2 | 2199 | 36276995 | 17278 |

Selection is original saved native `length_cap`, plus original backend `length` and exactly16,384 original IDs. One A1r2 backend-length row has native EOS at16,384 and is excluded, retaining its original Boolean; all other native-EOS/invalid-special exclusion counters are explicit zeros. The complete selected-ID rosters, model-file hashes, source-raw hashes and context totals are in INPUT_MANIFEST. ARCHIVE lists two parts (69,085,685 bytes), containing all18 new input artifacts; one complete archive readback passed. Natural-label/gold payloads are excluded from the archive and GPU upload, with only their local hashes retained in the manifest.

Please verify literal prompt+original generated IDs+fixed suffix, exact checkpoint/export receipt bindings and selected rosters against already retained original evidence. Model hashes are saved evaluated-export metadata; this is not a claim that private model binaries were independently read. Future worker byte verification remains mandatory. No new training or old decoding/scoring/bootstrap is requested.

Required flags (each explicit):

- `actual_selected_ids_prompt_generated_suffix_and_total_context_verified`
- `actual_checkpoint_export_weight_binding_and_remote_reuse_verified`
- `no_natural_rows_or_gold_in_GPU_requests`
- `actual_prefill_rows_runtime_cost_and_at_most_12_dollar_reserve_accepted`

Budget/runtime review must use these actual rows and prefill totals, without assuming a throughput guarantee. One global attempt, seven cells sequentially, complete-cell durability, no automatic retry. Reserve is at most $12 including $1.50 new noncompute; startup600s and platformgrace60s are priced within it. Worker cap is min(10800, floor((12−1.50)×3600/fresh hourly rate)−660). Old4.39520/h is historical only (about2.2h effective cap), not fresh admission. The original $150 epoch also retains $20.02 prior unassigned/delayed allowance. Only after real A2 acceptance will the necessary dated fresh rates/tagged app cost/unknown-pending shared max8 check run; insufficient budget means no dispatch. Partial cells will not be scored or filled with zero.

Source-approved v3 scoring adapter matches only the forced outer box: a closed box is scored even without actual EOS, while actual native/backend stops remain separate; unclosed is incorrect. Frozen last_box/scalar/pool remain unchanged. This is a fixed-suffix posthoc diagnostic with a single training seed, no primary-label replacement or causal claim. Original05UTC formal numeric freeze will record the true new-analysis status even if pending.

Return a fixed report with this target/SPEC/INPUT_MANIFEST and all four flags. No source PASS substitutes for this actual A2. Preserve independent-access limitations. Use the existing claude/audit repository workflow; Codex sends no external message or issue13 comment.

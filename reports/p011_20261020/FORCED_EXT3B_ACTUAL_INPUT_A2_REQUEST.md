# Actual-input A2-lite: two-cell forced-answer probe — PENDING

Request: `p011-forced-answer-ext3b-actual-input-A2-lite-r1`
Scope: `p011-forced-answer-ext3b-actual-input-A2-lite`
Fixed actual-input target: `3a7cb7dd807c301494ce2a880c7efb0acd631d40`
Packet: `reports/p011_20261020/forced_answer_ext3b_actual_inputs_v1`
Accepted source target: `87407963774de2d4f37ed5121d8d9ea60aec2c6d` (v2, exact 47 files).
Source SPEC SHA256: `bf5f8ffa76efe6855c5e11c7c20c78d9582ef1943e43d0d51bffd5bd136b9f25`
INPUT_MANIFEST SHA256: `9ef71794b8ad5858286c37127dd8c40ad55f81407ad34e33673e0a5c931171af`
ACTUAL_INPUT_BINDING SHA256: `e955d711376c99b6d8aa7448dc10529a65aa0dea640d75044143df921beb5c43`
Packet MANIFEST SHA256: `3ecd28d230a2277123cb6fee5021e6542f80db5106c42946c8c07dbe1cf00331`

Claude `a7e0a9ce` explicitly accepted the exact source, all six flags, and directed input construction followed by this A2. Constructor and publisher each completed once; no budget, upload or model has run. Owner directly authorizes execution after actual approval, total cap **$20**, one H100, one attempt, no automatic retry. No confirmation from the owner is needed.

| Saved student | Natural sampled / greedy rows | Selected sampled | Selected greedy | Total | Prefill tokens | Required context incl.64 |
|---|---:|---:|---:|---:|---:|---:|
| 3024×1, E≈3 | 2000 / 500 | 1182 | 488 | 1670 | 27,554,227 | 17,278 |
| 9072×1, E=1 | 2000 / 500 | 1691 | 500 | 2191 | 36,144,065 | 17,278 |

There are 3,861 selected continuations, 63,698,292 prefill tokens; context is below32,768. Backend-length/native-EOS and backend-length/invalid-special exclusions, including at16,384, are all zero for both cells. Original natural labels stay unchanged. The exact saved10 suffix IDs are copied without encoding. Original16,384 generated IDs are neither decoded nor regenerated.

The payload locations resolve to the evaluated attempt-1 outputs:
- Small: `.local/p011_20261020/r1/ext3b_runs_r1/local_endpoint_links_r1/audit/long_R3024xE3_S-F15_s17_attempt1/payload`
- Large: `.local/p011_20261020/r1/ext3b_runs_r1/audit/long_R9072x1_S-F15_s17_attempt1/payload`

The constructor checked each original raw-record digest against its saved oracle and binds the five original raw-file hashes per cell in INPUT_MANIFEST. Saved model export bindings point to the same evaluated attempt1 `/evidence/p011-ext-3B-20261022/runs/<job>_attempt1/model_for_vllm`. The future worker checks those model bytes; no new independent local binary read is claimed. Natural labels/gold remain local: only their manifest hashes are published. The new archive contains seven new request/metadata members,708,952,603 bytes uncompressed,26,909,135 compressed; its one complete readback is DONE. No original weights or old raw archive is reuploaded.

Actual size will feed the already-reviewed throughput budget formula: prior2,680.325s×max(rows/9,716,prefill/160,339,564)+120s, with at least2× headroom. Fresh H100/CPU/RAM rates and all shared slots (unknown/pending included) are checked only after A2. The $20 envelope retains $1.50 noncompute,600s startup and60s platform grace, up to10,800s worker if affordable. No old budget transfer or invoice claim.

Required flags (each must be explicit):
- `exact_two_saved_export_hashes_original_prompt_generated_ID_roster_and_suffix_accepted`
- `actual_sample2000_greedy500_selection_exclusions_and_context_prefill_accepted`
- `actual_manifest_no_labels_gold_old_weights_upload_and_single_attempt_accepted`
- `separate20_cap_throughput_headroom_and_source_SPEC_binding_accepted`

A6−A7 forced contrasts are already complete, accepted as reported in source CR, and will only be copied into the final diagnostic. No repeat bootstrap. New two-cell results and existing-label contrast still need independent actual A3; all claims are post-hoc, single training seed, diagnostic, with original primary results preserved.

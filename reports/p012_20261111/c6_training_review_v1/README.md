# C6 and training launcher: final pre-C8 review packet

Prepared for the owner's designated Claude review. Owner requested a pause at the current milestone; this packet is ready for relay when the owner returns. C8 has not started.

- `frozen_data.zip`: both complete frozen task inventories, all five training cells, 500 held-out problems, 1,000 NLL targets, four reserved demonstrations, ordered parent IDs, source-row provenance and per-family token lengths. MATH has 6,623 eligible parents; GSM8K has 7,397.
- `MANIFEST.json`: data hashes, counts, nesting checks, difficulty distributions and token totals. P/K8/K4 each contain 4,096 rows; R/L each contain the same 512 rows. Sample presentations are 8,192 except L's 1,024; tokens are reported separately.
- `ACTUAL_FROZEN_ROWS_PREPROCESSING.json`: three real frozen training rows per task, across all four model initializations. All 24 checks pass: actual pinned LLaMA-Factory preprocessing, prompt masking, exported-template counting and evaluation prompt IDs agree. The training `problem` field includes the OMI instruction. Full inventory lengths are bounded by 2,300 tokens for Qwen and 2,167 for Llama.
- `SOURCE_MANIFEST.json`: exact shared execution and data-construction files. `../review_601_training_fixes_v1/` contains the earlier actual preflight and 59 relevant regression checks; `tests/test_p012_grid.py` adds two allocation checks.

Changes requested by 601aebd2: explicit cell/dose and complete non-path configuration validation; main-grid final-save-only; preflight length-report binding; final local checkpoint file hashes verified before loading; training run and weight hashes recorded in evaluation manifests. R1/R2 retain the released checkpoint schedule. D4 is 4,096 output / 8,192 context. D5 is recorded; no checkpoint was deleted.

Two implementation repairs are recorded separately: SDK-only local launcher import (`../r1_admission_v1/`) and physical-line JSONL parsing for literal Unicode separators (`../jsonl_unicode_fix_v1/`). Neither changes input text or an experimental protocol.

The public UWNSL short checkpoint model card says global batch 16. Owner amendment M3 freezes batch 8 from the released YAML. R1 executes batch 8; this source discrepancy is explicit in its request manifest. R1's state is tracked in `../EXECUTION_STATUS.json`; training completion is not a G0-T accuracy pass.

Requested review: C5/C6 sampling and serialization, the complete training-request checks, local-checkpoint verification and main retention policy. Updated G0 raw outputs and labels are in `../g0_judged_and_base_v1/` for independent numerical review. C7 capability NLL implementation is still outstanding; it is not represented as reviewed here.

Built with Llama.

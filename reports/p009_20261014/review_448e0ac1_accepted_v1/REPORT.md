# Audit 20261014by: Stage 1 scientific core, NC exact inputs/plans, P1 complete read-only publisher

## A. `p009-stage1-scientific-core-code-r1`

- **Scope:** `p009-stage1-scientific-training-and-endpoint-core-code`
- **Target:** `919ab478f4301333e79946d2e7427a457d165108`
- **Manifest:** `159f6ed74e740bbb054a71fa38780ac109da08ab89c995599f71e9ade5c11606`. All 27 entries match.
- **source_files:** the exact 22-entry map in `SOURCE_BINDING.json`. Both the packet copies and the repository files at the target hash to it.

### Decision: PASS-WITH-NOTES (code only)

**Unchanged P008 primitives.** None of these was modified after the P008 training runs (last-change commits shown):
- `runtime.py` (76c33db0, 10-12)
- `checkpoint.py` (60e1e6dc)
- `block_journal.py` (c206f0dc, 10-13 04:31)
- `schedule.py` (f996621d)
- `common.py` (59383b4c)
- `sft_data.py` (dd24ef59)

They carry the same settings: FP32 LoRA r16/α32, AdamW(1e-4, foreach=False), clip 1.0, bf16 autocast, and the whole-answer + EOS label convention.

**Recipe gate (`checked_recipe`), checked before any model load:**
- Seeds are restricted to {17: 100/400/1600/3200, 29: 400/3200}, and NC to seed 17 with n ∈ {400, 3200}. This matches PREREG §5.1.
- Dose is 1024 updates / 2,097,148 targets. The LR vector SHA is `14ac59d2…`, the 1024-entry vector in `LR_VECTORS.json`.
- `validate_plan` is called with EOS 151643. It is the same function reviewed in bv (`training_plan.py` `fff9a0a1…`).
- S2 is rejected.

**Training path (`train_and_merge`):**
- It requires a fresh 1024-update block journal, and the training rows must be identical to the frozen rows (path_ids and digest).
- Runtime retokenization must equal the frozen encoding exactly, with no filtering or truncation.
- It saves only at step 1024. The checkpoint manifest is read back and checked for step, targets and identity.
- Then it does a single FP32 `merge_and_unload(safe_merge=True)` and stores BF16. There is no optimizer step after the terminal save and no intermediate evaluation or selection.

**Endpoint (`stage1_endpoint_engine`):**
- Endpoint sizes are full: NC 1319 / max 512, S1 500 / max 1024. Prompts are original token IDs, with prompt length ≤ 2048 − cap.
- Sampling is greedy with inference seed 17 and stop ids [151643].
- The cursor accepts only the next original 256-row offset, so repeats and skips are refused.
- `returned_records` keeps returned shapes verbatim, there is no scoring on the GPU, and the merged-model manifest is verified before vLLM is built.

**Tests.** I ran the 8 new tests here (unittest) and all pass. They are mocked, so they show the call order only, not real numerics.

### Notes
- **N1 (runtime).** `training_environment()` calls `torch.use_deterministic_algorithms(True)` but neither sets nor checks `CUBLAS_WORKSPACE_CONFIG`. P008 set `:4096:8` in its Modal image. Without it, the first cuBLAS GEMM raises RuntimeError. That wastes worker time but cannot produce a wrong result. I suggest the future parent or image bind it, and that the core assert `os.environ.get('CUBLAS_WORKSPACE_CONFIG') in (':4096:8', ':16:8')`. P008's `environment()` also pinned `set_num_threads(4)` and checked the GPU type; the future runtime admission should bind those too.
- **N2 (science, comparability).**
  - The NC base reference 650 came from the P0 engine, which used `enforce_eager=True`. The Stage 1 endpoint uses `high_throughput_v1` (CUDA graphs FULL_AND_PIECEWISE).
  - This only enters the NC G0 gap, which is 34.6 pp against a 20 pp threshold, so no decision changes.
  - The G1 rule compares students with each other on one engine, so it is unaffected.
  - Any reported "NC student − base" number should state the engine difference.
  - The S1 base (qwen_math_zero) was measured on the same high-throughput engine as Stage 1.
- **N3 (binding).** The core does not hash the base-model path passed to `rt.new_model`, nor the separate endpoint `paths['tokenizer']`. Only the merged model is verified. The future parent must bind both.
- **N4 (NumPy 2.2.6 vs 2.3.2).** Training draws no NumPy randomness that affects numerics: the schedule is precomputed, dropout is 0, and LoRA init uses torch's RNG. All P009 students share one stack, so the difference is immaterial within P009. It is correctly disclosed as not bitwise-comparable with P008.

## B. `p009-stage1-NC-exact-input-and-plan-r1`

- **Scope:** `p009-stage1-NC-exact-input-and-plan`
- **Target:** `7abac8610879ec3d79c49177dd29c1a6e7d934e0`
- **Manifest:** `04770096ec8e99a651b75a69885d3a563ece042e6cdb7f747d0bc346049ae2fb`. All 23 entries match.
- **Archive:** all 21 members match `ARCHIVE_MANIFEST`.
- **BASIS file SHA:** `af7149bd26f0a46762f1a108e9ff6c9e6f1c3dadb9d9b4532aec6319f7b4be6a`
- **ARCHIVE file SHA:** `266fde7c700a5360594163162f24b662d04c51a306ec645445223c479c6ce92e`
- **source_files:** the exact map in `SOURCE_BINDING.json`, including `scripts/plan_real_math_scale.py` `b6aa2a38…` and `scripts/prepare_p009_nc_inputs.py` `09382c68…`.

### Decision: PASS-WITH-NOTES

All checks below are independent (`nc_inputs_verify.py`, using my own Qwen BPE encoder).

**Inventory**
- `ORIGINAL_D1_INPUT.jsonl` has 3,436 rows over 3,436 unique problems.
- Its SHA is `3e239334…`, the same D1 corpus SHA recorded in P008's T1 dispatch/readback admission records.

**Order**
- Sorting by SHA256(`p009-stage1-question-order-v1:17:<pid>`) reproduces `ROSTER.full_order` exactly.
- n400 and n3200 are the exact prefixes, and n400 equals n3200[:400] (nested).

**Tokenization**
- For all 3,436 rows, my encoding of `"Problem: {prompt}\nSolution:\n" + response` + EOS 151643 equals `ALL_ENCODED`, covering input_ids, labels, n_prompt, n_processed, n_supervised and response hash.
- There are 0 boundary-crossing tokens and 0 embedded EOS, and every row is ≤ 2048 tokens.
- The selected encoded rows equal the inventory rows.

**Whole-answer sums:** 114,758 (n400) and 934,547 (n3200). Both match.

**Plans**

| | n400 | n3200 |
|---|---|---|
| Updates | 1024, all non-empty | 1024, all non-empty |
| Targets | 2,097,148 | 2,097,148 |
| Exposures per answer | {18, 19}, q = 18 | {2, 3}, q = 2 |
| Unexposed answers | 0 | 0 |
| Presentations | 7,308 | 7,183 |

- `row_exposures` matches the schedule.
- `lrs` equals `LR_VECTORS['1024']` (SHA `14ac59d2…`).
- The config digests (encoded / plan / training rows) recompute with the repo's `common.digest`.

**Endpoint**
- 1,319 rows. `input_ids` equal the Stage 0 `qwen_gsm_zero_parity.json` prompts (the P0 vLLM-650 inputs) in the same order.
- They also equal my own encoding of the GSM8K test prefix.
- `source_row_sha256` recomputes, and the longest prompt is 192 tokens.

### Notes
- **N1 (labeling).** The plans carry `subset_selection_depends_on_lengths: true`. That is a constant from the unchanged P008 `schedule.py`. In P009 the n-subset is the pure hash-order prefix, which I verified does not depend on lengths. The field is historically named but could mislead a reader, so it should be described in the README.
- **N2 (science).** At n400 each answer is seen 18–19 times. That is somewhat more than PREREG §5.2's "约 15 遍" estimate, but in the same regime. At n3200 each is seen 2–3 times. The G1 contrast therefore compares heavy repetition with near-single-epoch training at equal compute, as preregistered.

## C. `p009-math-p1-complete-readonly-publication-r1`

- **Scope:** `p009-math-p1-complete-readonly-publication-code`
- **Target:** `0e79cff57233d594f42c10a15b0b28d4f2c21fbc`
- **Manifest:** `3257dde7fb4d309862a4ee6a0dcbf30409c47597adb615ad7c2f1df616731f02`
- **source_files:** `{"scripts/p009_p1_complete_evidence.py": "8863741fe13e6ff966aa61e20e04a45ab8e8d70a973c4183b9512221231942a8"}`

### Decision: PASS

**It never scores.**
- It imports no scorer, pool or extractor.
- Unattempted rows must have pair None, correct False and parsed False. Cap and invalid rows must keep their stop status.

**Field check against real records.** I checked the publisher's assumptions against the actual first100 journal and the driver_extended code:
- Its pair-id formula equals `pair_digest`, verified on all 73 real pair files.
- `BASIS.row_count` and `binding` exist and match.
- Chunk intent, completion and result fields exist, and attempt indices are contiguous (0..72).
- The journal reloads `pool.attempts` across sessions, so remainder numbering continues. `unique_pairs_in_session` and `rows_in_session` are cumulative, which matches the publisher's checks.
- The driver writes every file the publisher requires: `ALL_ROWS_SCORED.json` with all six False flags, `REMAINDER_COMPLETED.json`, and `FIXED_AUDIT_SAMPLES.json` with the exclusions.

**Accounting**
- It requires the exact 12-source scoring lineage and the timing-review fields. Remainder wall = approved − first command (exact).
- Partial or failed state is refused.
- It requires every generated row to be either scored or an explicit unsupported-gold record, and all 500 endpoint golds.
- The fixed samples are recomputed under the original domain and order, with null adjudications.
- The fallback >2% and unique-pair outer-timeout >0.5% flags are recomputed from saved verdicts.

**Archive**
- The archive is create-only (`x:gz`).
- Readback hashes every member, and the member set must equal the expected set.
- Only `timing_review.local_report_path` is projected out of chunk intents. The original SHAs are retained and the projection is explicitly labelled.

**Tests.** I ran the 9 new tests here and all pass.

**N1 (minor, not blocking).** The publisher does not check that a native or boundary row with pair None really had no extractable box. It deliberately trusts the scorer's saved status and does not re-extract. My bx replay already shows that `last_box` agrees with an independent extractor on all 10,489 rows, so this is covered externally.

## 科学信号检查 (science-signal check)

- No new outcomes. All three items are code or inputs.
- The NC corpora are exactly the preregistered nested hash-order subsets, using no P009 outcome.
- The NC repetition gap (18–19× vs 2–3×) is by design. If NC shows ≥ 5 pp, the prereg stops the study (§5.3).
- The main open risk is still S1 G0. Stage 1 can only run NC until P1 completes and is adjudicated.

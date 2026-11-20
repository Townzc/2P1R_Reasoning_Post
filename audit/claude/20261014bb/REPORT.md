# Audit 20261014bb — P009 P0 parity runtime and bootstrap-measurement exception

- Request: `p009-p0-parity-runtime-r1`
- Target: `6b8c5764b46c12c277f12dcf8323b375dfc119ec` (also checked at HEAD `e9ea1b72`: the 19 sources are byte-identical)
- Packet manifest: `reports/p009_20261014/p0_runtime_preflight_v1/MANIFEST.json`, SHA-256 `872e60e2fc074d247b8632e46289714a70af18d52c34edd0031a192612b74182`; all 33 entries match
- Spec (`ADMISSION.json`) digest: `cdb52f9b9b726fbc5276230ce674084d72baeb3a3943a567cf412b46ce22df77` (recomputed with `common.digest`; matches the request). Plan digest: `2205da68…96c3` (matches)

## Verdict

**PASS-WITH-NOTES.** The bootstrap-measurement exception is **ACCEPTED** as written:
- the first 4 complete batches of each role are paid inside P0;
- they are reused once and never regenerated;
- after them, every batch is gated by the slowest complete batch, a 1.2× margin, a 300 s uncalibrated allowance, ≤ 1,170 worker-seconds and ≤ 80% of the remaining Stage 0 money.

**A0 status for this release only.** For P0 and the Stage 0 P1/P2/P3 work, the A0 decision of 20261014ba is equivalent to **PASS-WITH-NOTES**. Its R1 and R2 do not touch P0, P1, P2 generation or P3. They must still be frozen in the protocol before any P2 teacher output is read for eligibility, and before Stage 1 or Stage 2 admission.

## What was checked

| Item | Result |
|---|---|
| Inputs | `HF_REFERENCE_OUTCOMES.json`, `gsm8k_test1319.jsonl` and `qwen_gsm_zero_parity.json` match the spec hashes. The parity prompts are the same file (`bfbb7b5b…`) that I reproduced in 20261014ba; they have 0 / 1,319 differences from the frozen P008 base-format prompts |
| HF reference provenance | base 638 / 1,319 and correct-969 969 / 1,319. The bound artifact digests `a900c72a…` and `9f6447f4…` equal those I verified in CPU G3 (20261014aq) for base and `d1_b1_p0_breadth_t1_replacement_r1`. No old raw is re-decoded and no old file is rewritten |
| Reference checkpoint | `state.pt` SHA `c3e6de44…`, identity digest, step 256 and 524,287 targets are all checked before merging. The adapter is copied exactly in FP32 with an equality check, merged in FP32 (`safe_merge=True`), then saved as bf16. This is the same path all P009 students will use, so P0 measures the pipeline that matters |
| Decode | vLLM 0.11.0, bf16, greedy, `max_model_len` 2,048, 512 new tokens, `stop_token_ids=[151643]`, `generation_config='vllm'`, prefix caching off, eager mode; prompts passed as token IDs. EOS set {151643} equals the P008 HF student/base endpoint, so no new stop token was introduced |
| Raw contract | Raw bytes are saved before interpretation. EOS must be the single terminal token; otherwise exactly 512 tokens with `length`. A missing EOS is never invented. A duplicate unit blocks generation. No retries |
| Finite execution | One H100 function with `retries=0` and `max_containers=1`, a hard 1,200 s timer that kills children and calls `os._exit`, platform 1,260 s and startup 600 s. A permanent claim, any prior campaign record or a non-empty container list blocks dispatch. Source drift is checked inside the worker |
| Money | 1,860 s × $0.00122044 = 228¢, plus 20¢ build/storage/transfer = **248¢ reserved of Stage 0's 1,000¢** (752¢ remain). The rate equals H100 + 4 CPU + 32 GiB at published rates (≈ $4.39/h). Project gate: prior upper + $100 ≤ $450 |
| Tests | 9 contract and 3 mocked flow tests, logs present. They do not exercise real CUDA, vLLM, merge timing or GPU cleanup; the packet says so |

## Notes

- **N1 — wall-clock risk.** Both roles plus one merge share a single 1,200 s worker. My rough estimate, in eager mode, is a 6–15 s tail per 32-prompt batch × 42 batches × 2 roles, plus about 3 × 60–120 s for startup and merge: **roughly 500–1,300 s**. The forecast gate will stop safely if it is too slow. But a stop consumes the one-shot campaign, and P0 would then need a new admission. If the 4-batch prefix shows more than ~10 s per batch, expect a forecast stop. In that case, re-admit with one worker per role rather than relaxing any cap.
- **N2 — EOS in vLLM `token_ids`.** `raw_checked` assumes vLLM includes the terminal EOS in `token_ids` when `finish_reason='stop'`. I believe vLLM v1 does. If 0.11.0 does not, every early stop fails the contract on the first batch: raw is preserved, the cost is under $0.5, and there is no retry. No code change is required for this approval. If it happens, the fix is to record `stop_reason` as backend metadata, without appending an EOS, and re-review.
- **N3 — Stage 0 budget.** After this slot, Stage 0 has 752¢ for P2 (≤ 8,993 teacher generations at ≤ 1,024 tokens) and P3 (7 evaluations). That is plausible with vLLM but not large. Forecast P2 from P0's measured throughput before admitting it.
- **N4 — release gate.** `validate_release` accepts only `PASS` / `PASS-WITH-NOTES` for the design review. Cite 20261014ba with the P0-scoped equivalence stated above.

## Science-signal check

No outcome exists yet. The parity decision (pass-comparable, internal-only, stop, or blocked) is computed only by the independent CPU oracle after STOPPED0. I will replay it from raw.

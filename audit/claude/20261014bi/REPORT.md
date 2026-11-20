# Audit 20261014bi — P009 Plan A: fresh full P0 in the high-throughput configuration

- Request: `p009-p0-high-throughput-full-r1`
- Scope: `p009-p0-high-throughput-full-runtime-and-bootstrap-numeric`
- Target: `fe8a6bcc60b1fee23336f9fb39ae10ed8053f370`. The 26 sources are also byte-identical at HEAD `77df6258`.
- Manifest: `reports/p009_20261014/p0_fast_preflight_v1/MANIFEST.json`, SHA-256 `4082a261eac3991e4e8352cf0488bec311ae398972d426c0ff4f28cb36e56f13`; all entries match
- Recomputed digests:

| Item | Digest |
|---|---|
| `spec_sha256` | `1238d0cb542d27cf27ea0f565d96bffbc1292c280cd0dd6c7c0f00f1b2e145bc` |
| `plan_sha256` | `ce6a7a52d6e9b832f712fd86ba1ec0a2fccb9d2cdef92e1ed5e7aa332f588506` |
| `owner_plan_A_sha256` | `aa1186e0b6ff91d2f30fcc86d9e467fb0fd1348c86de9de61495990c86fb8110` |

- `source_files`: exactly the 26 entries in ADMISSION.json. The original `p0_engine.py`, `p0_contract.py` and `p0_runtime.py` are byte-identical to `6b8c5764`.

## Decision

**PASS-WITH-NOTES.**

| Flag | Value |
|---|---|
| `fresh_full_P0_accepted` | **true** |
| `first_one_batch_bootstrap_accepted` | **true** — only the first base 256-row chunk; every later chunk, including the first correct-969 chunk, is forecast from all observed batches |
| Owner authority | Plan A was chosen by the owner directly in chat; the record is `OWNER.json` |
| Design dependency | 20261014bd scoped Stage 0 PASS-WITH-NOTES (original target `e6350f0b` + supplement) |

## Checked

| Item | Result |
|---|---|
| Configuration | V1 engine with `VLLM_USE_V1=1` enforced; bf16; TP 1; context 2,048; 256 sequences; 8,192 batched tokens; memory utilization 0.80; chunked prefill on; prefix caching off; `enforce_eager=False`; compilation level 3; `FULL_AND_PIECEWISE` with capture sizes up to 256. **The actual engine configuration is read back from `vllm_config` and compared before any generation; any silent eager or other fallback raises.** |
| Science unchanged | Same 2,638 prompts (`bfbb7b5b…`); greedy, 512 new tokens, `stop_token_ids=[151643]`; same raw contract (`raw_checked`); same FP32 copy and merge then bf16 save of checkpoint `c3e6de44…`; same HF reference maps (`06de676f…`); frozen CPU logical scoring; parity thresholds unchanged |
| Lineage | The failed eager parent stays failed. Its 128 rows are excluded and stay unscored. The suffix is retired and was never dispatched. A new permanent claim, plus the successor marker taken from the parent, blocks every competing variant. Retries 0, `max_containers` 1 |
| Chunks | 5 × 256 + 39 per role, 12 chunks in total. Chunk composition is frozen by the fixed order |
| Money | 252¢ new + 248¢ unrecycled = 500¢ of Stage 0's 1,000¢. The 500¢ unallocated reserve is untouched |
| Tests | 10 new CPU or mock checks. CUDA capture and real throughput are untested; the packet says so |

## My projection

| Phase | Estimate |
|---|---|
| Load + compile + graph capture, ×2 models | ~60–180 s each |
| Merge | ~60–120 s |
| Per 256-row chunk at ≤ 512 tokens with CUDA graphs | ~8–20 s |
| **Total** | **roughly 350–700 s** |

At the bootstrap point (elapsed ≈ 150–250 s, chunk ≤ 20 s), the gate forecast is about 150–250 + 1.2 × (20 × 11 + 300) ≈ 770–870 s ≤ 1,170 s, which passes. Correction to 20261014bg: the figure "150–250 s margin" there was the margin of the *forecast gate* (with the 1.2× factor and 300 s allowance) at the start of the correct-969 role, not raw time against 1,770 s. Codex's 520–620 s is the raw-time margin. Both are moot now.

## Notes

- **N1 — compile-API risk.** If vLLM 0.11.0 rejects or renames a `compilation_config` field (for example `level` versus `mode`), the read-back check fails closed at startup. That is the right behaviour, but it consumes the once-only campaign, at a cost under $1 of setup. Codex cites the pinned 0.11.0 sources, and I accept that.
- **N2 — Stage 0 reservation arithmetic (budget planning).** After this slot Stage 0 has 500¢ left. A 1,900 s-window worker reserves about 252¢, so **at most one more full-window worker fits.**
  - Plan P2 (8,993 samples at ≤ 1,024 tokens, roughly 36 × 256-row chunks) and P3 (7 endpoints) as at most two workers with windows sized to measured throughput from this P0, for example about 1,200 s windows at roughly 166¢ each.
  - Alternatively, ask the owner before any part of the $5 unallocated reserve is touched.
  - Do not size them the same way as this P0.
- **N3 — batch composition.** Greedy outputs under 256-way continuous batching depend on which rows are co-scheduled. The frozen chunking makes that deterministic in order, but not guaranteed bit-identical across hosts. That is acceptable, and P0 measures exactly this effect against HF.
- **N4 — downstream binding.** As the protocol amendment states, this P0 validates only these two Qwen/GSM8K endpoints in this configuration. P3, Stage 1 and Stage 2 must import the same `high_throughput_v1.ENGINE_KWARGS` byte-for-byte, and each needs its own source review.

## Science-signal check

No P009 scores exist. The 128 eager rows stay unscored permanently.

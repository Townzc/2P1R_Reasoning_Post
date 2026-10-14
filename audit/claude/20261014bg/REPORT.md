# Audit 20261014bg — P009 P0 unattempted suffix

- Request: `p009-p0-unattempted-suffix-r1`
- Target: `7c9f093cd9f0b866cce65329d0b88c42fe0066b8`
- Manifest: `reports/p009_20261014/p0_suffix_preflight_v1/MANIFEST.json`, SHA-256 `694c0a226a50a74b3d1ba4213bf0de6b57991da01101e48fe38aa2a8e0d18e6e`
- Spec digest: `dd6785e05ee36c5fa13b796b042f53051a7c4b2826039afb99481fe88da5e1e8` (recomputed; matches)
- Parent preservation: `7d0b862f…`

## Decision

**HOLD-PENDING-OWNER.**
- Code, lineage and numerics: technically sound (§1).
- Dispatch: not recommended until the owner chooses the evaluation-engine / Stage 0 budget path in §2.

This is deliberately not PASS. Under the engine configuration this suffix freezes, Stage 0 cannot be completed inside its $10 cap. The choice between the options below is a spending decision for the owner. When the owner decides, I will issue a scoped verdict for the chosen path.

## 1. Technical review (would be PASS-WITH-NOTES on its own)

**What happened.** The original stop is exactly what 20261014bb N1 warned about. The 4-batch maximum was 11.79 s, the forecast was 1,583 s against the 1,170 s line, and the worker stopped before batch 5. It was not retried. Preservation is complete: 4 intents and 4 dones, 128 raw rows, 0 unknowns, provider stopped with 0 containers. No partial accuracy was computed, and none should be.

**What the suffix does.**
- Generates only the never-attempted rows: base 128..1318 (38 batches) and correct-969 0..1318 (42 batches), 80 batches in total.
- Uses the same 32-row boundaries the original would have used, so batch composition is unchanged.
- Leaves the 19 engine/runtime sources byte-identical. Decode settings are unchanged (eager, `max_num_seqs` 32, bf16, greedy, EOS 151643).
- Verifies the parent before any model loads, checking raw/ack/ledger, `raw_checked` on all 128 rows and the failed forecast.
- Writes a permanent cross-campaign marker that blocks replay.
- Forecasts before every batch with no new exemption, using the maximum of all observed batches.

**Projection.** My estimate is about 45 s of setup + 38 × 11.8 s + roughly 150 s of merge and load + 42 × 11.8 s, giving **about 1,150–1,250 s**. The gate margin to 1,770 s is roughly 150–250 s. The main risk is merge/load time, which is unmeasured.

**Money.** 326¢ new plus 248¢ unrecycled = 574¢ of Stage 0's 1,000¢. The project gate holds.

**Mixing of hosts.** The 128 prefix rows and 2,510 suffix rows come from different containers running identical software. Greedy vLLM is not guaranteed bit-stable across hosts or batch timing, so a few rows could differ from a single-run endpoint. This is acceptable and must be disclosed in A2.

## 2. Science-schedule / budget signal (why HOLD)

The observed throughput is 32 prompts × ≤ 512 tokens in 11.8 s, roughly 600–700 tokens/s. That is very low for a 1.5B model on an H100, because the run uses eager mode and 32 sequences at a time, so each batch waits for its longest output.

Projected cost at this configuration (H100 at ≈ $4.39/h, my estimates):

| Work | This configuration | High-concurrency configuration (CUDA graphs, ≥ 256 sequences) |
|---|---|---|
| P0 remainder (2,510 rows) | ~$1.4 actual, 326¢ reserved | ~$0.3 |
| P2 teacher sampling (8,993 × ≤ 1,024 tokens, about 282 batches × ~24 s) | **~$8** | ~$0.5–1 |
| P3: 3 GSM8K evaluations at 512 tokens + 3 MATH-500 evaluations at 1,024 tokens | ~$3.6 | ~$0.5–1 |
| Stage 1: 14 student evaluations | ~$9 and about 2 hours of wall clock | ~$1–2 |

Stage 0 has only 426¢ of reservation headroom left after this suffix.

**Options for the owner:**

- **Option A — recommended.** Use one high-throughput vLLM configuration for every new endpoint.
  - Re-run P0 completely (2,638 outputs) in that configuration as a new campaign, keeping the failed 128-row parent as sunk evidence.
  - Then run P2, P3 and all Stage 1/2 evaluations in the same configuration.
  - P0 then validates the configuration actually used downstream.
  - Estimated Stage 0 total is about $5–6 reserved, including the sunk 248¢, and later evaluations are about 5–10× faster.
  - Cost: one more code/runtime review cycle, about 1–2 hours.
- **Option B.** Dispatch this suffix now, keeping the slow, P0-validated configuration for all evaluations, and use a fast configuration for P2 only. P2 is temperature-0.8 sampling, so engine parity is irrelevant there.
  - Stage 0 then needs about 574 + ~100–200 + ~360 ≈ **$10.4–11.4 reserved, which exceeds the $10 cap**.
  - The owner would have to release part of the $5 unallocated reserve.
  - Stage 1 evaluations stay slow, which affects tonight's timeline.

Under either option, P2's sampling configuration may differ from the evaluation configuration without any parity concern. Its seeds and sampling parameters stay frozen.

## Science-signal check

No scores exist. The 128 prefix rows must stay unscored until the complete A2.

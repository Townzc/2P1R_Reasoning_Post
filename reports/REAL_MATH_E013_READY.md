# E013 — GSM8K engineering prepared; GPU execution awaits server access

2026-09-10 UTC. The owner requested the next experiment after C017. Source
implementation was published as `c11bf824b31c683d823d0d7d3e5627ad368f3fbb`
before immutable preparation. Linux preflight and one bounded execution are
next. **No model has trained and no GPU throughput has been measured.** A
read-only SSH probe at 04:32:40 UTC returned connection refused. This does not
establish instance power state; availability or updated access is required.

| Item | Frozen value |
|---|---:|
| Student | Qwen2.5-1.5B base, original pinned revision |
| Training parents / responses | 32 / 32 |
| Development parents | 16, frozen development-rank prefix |
| Updates / responses per update | 256 / 4 |
| Microbatch / exposures per response | 1 / 32 |
| Supervised response tokens, including EOS | 167,232 |
| Processed nonpadding tokens | 229,056 |
| Padding / packing / truncation | 0 / none / none |
| Maximum training sequence | 424 tokens |
| Context / new-token generation caps | 1,024 / 768 |
| Baseline / final generated sequences | 16 / 48 |
| Process cap plus exit guard | 900 + 15 seconds |

Full FP32 parameters, BF16 autocast, AdamW, lr 5e-5 and the existing prompt
serialization are preserved. This is C017's already selected engineering
subset, not a scientific draw conditioned on four-solution support. Development
parents come only from the original training split. No official test, fresh
reserve, new source shard or teacher generation is used.

The gate requires all 256 updates, the complete 64-update profile after eight
warmup updates, at least 31/32 numeric-correct train completions ending in EOS,
zero truncations and finite train NLL < .1. Numeric agreement is not proof
verification. Development results are descriptive at n=16. Preserve failures
and partial records; do not add steps or retry automatically. See the
[registration](../docs/experiments/E013_gsm8k_engineering.md).

CPU verification passed:

- 38 focused tests pass; two GNU-timeout integration tests are skipped on
  macOS and remain mandatory on Linux before model execution.
- All 48 original question identities, 32 response locations/hashes and 32
  exact input/label sequences match the C017 source cache.
- Independent raw-tokenizer counts and a separate 32-epoch reconstruction
  agree on all 256 updates, exposures and exact token totals.
- Eight tampering cases fail: missing/reordered train rows, changed gold,
  prompt or candidate, duplicate groups, a test identity and reordered dev.

Evidence: [input manifest](real_math_e013_inputs_r1/manifest.json),
[independent verification](real_math_e013_inputs_r1/independent_verification.json),
[test log](real_math_e013_inputs_r1/focused_tests.log),
[release](../configs/real_math_e013/release.json), and
[availability receipt](real_math_e013_inputs_r1/availability.json).
Input-manifest SHA256 is
`37f868089001c62131e0c53f86634d94efd882bc8ef6383a6b10ae9ad8ee129b`.
Unmodified public response excerpts carry NVIDIA/OpenMathInstruct-2 attribution;
full source caches remain local.

The ledger remains **5971 / 7200 seconds used, 1229 remaining**, 16 receipts,
zero reservations. Preparation added zero GPU seconds. The fixed 915-second
maximum reservation fits, leaving 314 seconds unreserved; actual elapsed time
will be charged. Verify the ledger and original base snapshot again on the
existing owner-started A800. A clone does not reset the balance. The launcher
inspects by default; `--execute` is explicit.

No training-scale conclusion follows yet. E013 records separate model load,
baseline generation, training, final generation, NLL and checkpoint timings.
Its token-scaled projections for C017's four arms are training-only proxies,
not a complete-phase bound. Freeze and price evaluation and overhead before
a scientific comparison. E012 stays paused.

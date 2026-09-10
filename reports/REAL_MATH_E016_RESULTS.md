# E016 completed: capability loss and a failed base termination screen

2026-09-10 UTC. The fixed 128-generation diagnostic completed successfully, but
both registered operational screens failed. The provider confirms that the
instance is shut down. Compact outputs and the updated ledger are independently
retained and verified; no new checkpoint or training job was created.

The original base has **26/64 clean correct answers versus E015 0/64**. E015
produces parseable marked answers on 62/64 questions, all incorrect, so its
zero score cannot be explained solely by missing answer markers. The base has
measurable numeric capability, yet its **14/64 truncations exceed the frozen
8/64 limit**. Do not relabel the base screen as passed or enter the registered
base-pass training branch. [Frozen metrics](../runs/gsm8k_capability_e016_r1/metrics.json),
[prospective registration](../docs/experiments/E016_capability_preservation.md).

## Complete denominators

| Endpoint, all 64 parents | Original base | E015 |
|---|---:|---:|
| Marked numeric answer correct | 39 (60.94%) | 0 |
| Correct with actual EOS | 29 (45.31%) | 0 |
| Clean correct: correct, EOS, no truncation or new-problem continuation | 26 (40.63%) | 0 |
| Marked answer parsed | 49 | 62 |
| Missing marked answer | 14 | 2 |
| Unresolved marked answer | 1 | 0 |
| Actual EOS | 50 | 62 |
| Truncated at 768 new tokens | 14 | 2 |
| Generated new-problem continuation | 16 | 0 |
| Original strict scorer correct | 1 | 0 |

The paired clean-correct table loses all 26 base successes and gains none.
The base passes the correct-count and parsed-count components, but fails the
truncation component. E015 fails the clean-correct and retention requirements;
its retention screen also requires a passing base. Better formatting and fewer
truncations therefore do not establish preserved mathematical performance.
All raw strict scores remain intact. [Paired records and descriptive reconstruction](real_math_e016_execution_r1/summary.json).

These are development endpoint measurements, not a powered noninferiority test,
proof verification, causal estimate of terminal LR decay, or a scientific
allocation comparison. E015 intentionally memorized 32 training parents and
passed that engineering gate; that success did not transfer to this calibration.
The base/E015 weights differ, and prior E013/E015 numerical trajectories also
diverged before decay. No particular optimizer or backend mechanism is proven.

## Execution and verification

Execution source: `84e9ea35fc54a0d94e70d4efca74b5f15783091b`; implementation
`d27c17c7b644199ddbdac045ae357cf6b60d6061`; input release
`32240fd8be020a0da9b6871ea532765d0991b91a`. Release SHA256:
`c95f7c6d48c5aac11b330bab4989d4efe8a231ec1e4c18e3f8b8bbb21a9204ac`.

All 42 Linux checks passed, including both GNU-timeout integrations. Source
staging preserved 14 byte-identical untracked E015 compact files before checking
out their published copies. The existing 19-receipt ledger already matched and
was never reset. Both complete model inventories passed preflight hashes.

The original Qwen2.5-1.5B base revision
`8faed761d45a263340a0528343f099c05c9a4323` ran first, followed by the exact E015
checkpoint. Each decoded the same 64 C017 development parents, ranks 17–80,
with the original `Problem: ...\nSolution:\n` prompt, greedy batch 8, one beam,
768 new tokens, context 1024, FP32 weights/BF16 autocast, SDPA and TF32 off.
Effective generation configurations match. There were zero optimizer updates,
teacher calls, official-test evaluations, retries or new weight writes.

Base/E015 generated 19,391/10,086 tokens in 145.36/80.71 seconds. Model loads
took 1.97/1.20 seconds; the worker measured 229.47 seconds overall. Peak allocated
memory was 6,738.53/6,733.17 MiB and peak reserved memory 7,042/7,070 MiB.
The guarded process charged **235 seconds**. [Timings](../runs/gsm8k_capability_e016_r1/phase_timings.json),
[base profile](../runs/gsm8k_capability_e016_r1/base_profile.json),
[E015 profile](../runs/gsm8k_capability_e016_r1/e015_profile.json).

Server and local CPU auditors independently checked all 128 raw token streams,
original scores, marked sidecars, profiles, effective configurations and frozen
gates; their reports are byte-identical. This verifies saved-record consistency,
not recomputed model logits or every reasoning step. All 20 full public receipts
equal their private ledger entries: **6,921/7,200 seconds used, 279 left, zero
reservations**. [Local audit](real_math_e016_execution_r1/local_record_verification.json),
[Linux tests](real_math_e016_execution_r1/linux_tests.log),
[ledger reconciliation](real_math_e016_execution_r1/ledger_verification.json).

## What the saved text illustrates

These observations are post-hoc examples, not additional scored endpoints. On
the first registered question (`gsm8k/train/04514`), E015 emits arithmetic such
as `6 * $2.5 = $12` and finishes with 60 rather than the gold 44. The base reaches
44 in unmarked prose, which the frozen marked-answer rule intentionally does
not count. On the third question (`gsm8k/train/02597`), the base ends correctly
at 27, while E015 repeats the same incorrect explanation until truncation.
Thus raw errors include semantic/arithmetic failures and a repetition case;
the calibration is neither just an extractor failure nor evidence that every
wrong output has the same cause. [Original streams](../runs/gsm8k_capability_e016_r1/e015.jsonl).

## Rental closeout and next decision

The provider stop timer was set before launch. All 25 compact/auxiliary files,
including 13 run files and the current ledger, were exported and hash-verified
in 6.47 seconds. Normal shutdown was confirmed by 18:41:10 UTC, and the temporary
timer was cancelled afterward. The notification-to-confirmation span was 721
seconds, about **12 minutes / CNY1.60** at CNY8/hour, within the 15-minute target
and 20-minute ceiling. This is an observed-span estimate, not the provider
invoice; actual power-on may predate the notification and rounding/storage fees
are unverified. [Export evidence](real_math_e016_execution_r1/compact_export_verification.json),
[provider closeout](real_math_e016_execution_r1/shutdown_closeout.json).

Keep the server off. E015's complete 12-file/6.19GB weights passed preflight
hashes and remain on its retained volume. Their independent backup is still
incomplete; no full-weight transfer was attempted in this GPU window. Do not
release/delete the instance. The separately priced no-card recovery remains
open in [the recovery plan](../docs/E015_RECOVERY_PLAN.md).

Do not scale training or add a 512-step retry. The next offline decision must
address two separate issues: a prospective prompt/termination contract for
the base, and a capability-preserving SFT calibration before an allocation
comparison. Lower integrated update strength with broader training coverage
and partial parameter freezing remain alternatives motivated by the earlier
[ICLR/ACL review](REAL_MATH_C019_CAPABILITY_AUDIT.md), not established fixes.
Any changed prompt, score, adaptation recipe or new GPU phase needs its own
concrete registration, finite total rental budget and review. The 80 observed
development parents can support diagnosis but are no longer fresh confirmation;
the other 432 remain reserved. Historical data, scores and gates stay unchanged.

The post-run tables and ledger proof can be reconstructed without a model:

```sh
python -m analyses.e016_result_summary --ledger PRIVATE_CURRENT_LEDGER --out-dir NEW_OUTPUT_DIRECTORY
```

Raw-token verification additionally uses the frozen `analyses.e016 audit` command
and the original pinned tokenizer. Always select a new output path.

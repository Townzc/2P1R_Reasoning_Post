# Actual A3 — owner-epoch A results (baseline, A1r2, A5, A6, A7) and original contrasts

Target fe82972a (request 91b65ec1). Packet reports/p011_20261020/owner150_complete_actual_results_v1.
MANIFEST 6ddb9969…, ACTUAL_RESULT_BINDING b9311fbe…. Reviewer: Claude, 2026-10-22 ~01:45 UTC.

**Verdict: numbers ACCEPTED (A3 PASS). The post-hoc smoke gate FAILS (A7 EOS 22.6% < 70%; A7 is 35.85 pp below baseline, more than the 10 pp allowed). Plan §2 rule 2 governs interpretation.**

## Integrity and access scope
- The 12 parts stream-reassemble to sha 634abf05…, which equals ARCHIVE_READBACK.
- Because of disk limits, only `runtime/raw/*`, `score/COMPLETED.json` and `score/owned_score/payload/ROWS.json` were extracted per job and deleted after use.
- Not read: private checkpoints/exports/ADMISSION, state/optimizer/RNG oracles, collect records. Those oracles are not independently re-executed. The cost projection ($100.02 exact-new-app, not an invoice) was not reconciled against billing, which I cannot access.

## Independent decode (own BPE, tokenizer sha c0382117…), 16,500/16,500 rows
- For every job, the decoded text and the region after the last `</think>` reproduce `raw_text_sha256` and `region_sha256` on every row.
- Stop reasons agree on every row. 0 unmapped tokens, 0 other stops.
- Stop counts equal ENDPOINT_STOP_COUNTS.json.

## Correctness consistency (math-verify not rerunnable; PyPI blocked)
- 0 truncated rows labelled True. 0 rows with last-box string equal to gold that are labelled False.
- 356 rows are labelled True without string equality (65 unique pairs), all reviewed manually. All are equivalences except the frozen scorer's known leniency:
  - baseline math500/179 sample1 and greedy: the plane equation is scaled (`10x-14y+22z+8=0`) or sign-flipped, so it violates the problem's normalization (A>0, gcd=1). Strictly this should be wrong. Effect: baseline sampled −0.05 pp, greedy −0.2 pp.
  - Base subscript dropped (`52` vs `52_8` in A1 ×4; `4210` vs `4210_5` in A5 and A6) and an unsimplified `8/18` (A6, 1 row): accepted as lenient-equivalent.
- None of these changes any contrast by more than 0.2 pp. They are disclosed; no change is requested.

## Contrasts (own recomputation; paired-question bootstrap 10,000, seed 20261021)
| contrast (plan §8) | sampled Δ (pp) [95% CI] | greedy Δ (pp) [95% CI] (secondary, my computation) |
|---|---|---|
| A7−baseline (smoke) | −35.85 [−39.00, −32.65] | −53.0 [−57.4, −48.6] |
| Δ_P 4096: A7−A1 | −19.00 [−21.80, −16.20] | −31.2 [−35.2, −27.2] |
| Δ_P 1024: A6−A1 | +0.35 [−2.15, 2.75] | −29.0 [−33.2, −25.0] |
| Δ_K 16: A5−A1 | −1.35 [−4.00, 1.20] | −29.8 [−34.0, −25.8] |
| Δ_diag: A7−A5 | −17.65 [−20.15, −15.15] | −1.4 [−2.6, −0.4] |

The saved primary values are reproduced exactly.

## Termination diagnostics (MATH-500)
| cell | sampled acc | sampled EOS | greedy acc | greedy EOS | truncated rows ending in repetition loops (sample / greedy) |
|---|---:|---:|---:|---:|---|
| baseline (Instruct) | 50.35% | 98.5% | 53.8% | 95.2% | 27/31, 22/24 |
| A1 (256,1) | 33.5% | 59.5% | 32.0% | 58.8% | **61/811**, 24/207 |
| A5 (256,16) | 32.15% | 48.8% | 2.2% | 2.2% | 407/1025, 474/489 |
| A6 (1024,1) | 33.85% | 49.0% | 3.0% | 3.2% | 390/1020, 462/484 |
| A7 (4096,1) | 14.5% | 22.6% | 0.8% | 0.8% | 1144/1548, 476/496 |

Loop = zlib compression ratio of the final 6,000 characters < 0.12 (a heuristic).
Two descriptive observations:
1. Every fine-tuned cell is far below the untuned Instruct baseline: this dose sits in the long-CoT "valley" (Luo et al. 2025).
2. The cell that repeats the fewest traces most often (A1) has the highest termination and almost no loops among its truncations. The cells with more distinct traces loop more, under greedy decoding especially.

These observations are not causal; there is a single training seed.

## Flags
All six required flags are true as scoped above, with the access limits stated. `cost_projection_reconciliation_scope_disclosed`: projection only, not reconciled.
This is not final A5.

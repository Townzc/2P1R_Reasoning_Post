# Actual A3: forced-answer diagnostic, seven cells (0cb5551b, request f09ba246)

Reviewer: Claude, 2026-10-22 ~08:45 UTC.

**Verdict: ACCEPTED (A3 PASS) with disclosed scorer leniency.**

## Independent scope
- I streamed the two-part archive (sha ac0d1958…) without extracting it to disk; the script is forced_a3/a3.py.
- **Decode.** I decoded all 9,716 new continuations (at most 64 tokens each) with my own byte-level BPE decoder built from tokenizer.json, independent of HF.
  - Native stop: the first EOS (151645/151643) or added special token, otherwise `length_cap` at 64 tokens.
  - My own forced-box brace matcher starts at depth 1 and treats a brace as escaped when it is preceded by an odd run of backslashes.
- **Agreement with saved data.** For all 9,716 rows, my segment equals the saved `answer_segment` and my stop/adapter classification matches the saved `stop_reason`.
- **Closure counts by cell.**

| cell | closed + EOS | closed, no EOS | unclosed |
|---|---:|---:|---:|
| baseline | 55 | 0 | 0 |
| A1r2 | 628 | 387 | 2 |
| A5 | 68 | 1,440 | 6 |
| A6 | 324 | 1,176 | 4 |
| A7 | 42 | 1,992 | 10 |
| D1 | 191 | 1,165 | 27 |
| D2 | 717 | 1,467 | 15 |

- **Correctness consistency.** No row is labelled True with an unclosed box. No row is labelled False whose box content string-equals the gold. 387 rows are True without string equality, and I reviewed every distinct pair by hand. Nearly all are equivalent forms: a/b versus \frac, decimals, dropped units or degree signs, `x=` prefixes, and reordered tuples or polynomials.
- **New leniency specific to forced answers: 16 rows across the cells, at most 4 per cell.** Unevaluated expressions are accepted, for example `26\times25\times10\times9` and `650\times90` for 58,500, `35\times(1/5)^4\times(4/5)^3` for 448/15625, and `11+9+0=20`. So are mixed numbers such as `15\frac{39}{40}` for 639/40, plus the known plane-scaling and base-subscript cases. The effect is at most 0.2 pp on any sampled rate and at most 0.6 pp on greedy (A6). No contrast changes materially. The rows are disclosed and no labels are changed.
- **Natural-label reuse.** In every cell, the joined labels on non-selected rows sum exactly to the original saved counts: baseline 1007/269, A1r2 670/160, A5 643/11, A6 677/15, A7 290/4, D1 641/163, D2 206/30. Every truncated row was originally False, and every selected row's joined label equals its new score.
- **Contrasts.** All ten contrasts (five pairs × sampled/greedy), recomputed with my own paired-question bootstrap (10,000 draws, seed 20261021), reproduce the saved values and intervals exactly.
- **Not accessed:** private checkpoints, binaries and billing; a full math-verify re-execution (correctness was checked for consistency only).

## Results (MATH-500; forced = natural labels plus forced box on truncated rows)
| cell | sampled orig → forced | greedy orig → forced | forced acc. on truncated, looping / non-looping (sampled) |
|---|---|---|---|
| baseline | 50.35 → 50.5 | 53.8 → 54.0 | 11% / 0% (n = 27 / 4) |
| A1r2 252×1 | 33.5 → 38.1 | 32.0 → 37.0 | 23% / 10% |
| A5 252×16 | 32.15 → 44.1 | 2.2 → 40.8 | 32% / 18% |
| A6 1,008×1 | 33.85 → 46.65 | 3.0 → 45.4 | 29% / 23% |
| A7 4,032×1 | 14.5 → 42.0 | 0.8 → 38.6 | 38% / 29% |
| D1 AM-Thinking | 32.05 → 39.65 | 32.6 → 41.8 | 14% / 11% |
| D2 Qwen3-235B | 10.3 → 36.35 | 6.0 → 34.4 | 30% / 29% |

Forced contrasts, in pp [95% CI], sampled then greedy:
- A7−A1r2: +3.9 [1.6, 6.25]; +1.6 [−3.2, 6.2]
- A6−A1r2: **+8.55 [6.15, 10.95]**; +8.4 [4.0, 12.8]
- A5−A1r2: +6.0 [3.45, 8.5]; +3.8 [−0.6, 8.2]
- A7−A5: −2.1 [−4.35, 0.15]; −2.2 [−6.6, 2.0]
- D2−D1: −3.3 [−5.5, −1.0]; −7.4 [−11.4, −3.4]

**Descriptive reading (single seed, post hoc, fixed suffix; not causal).**
- Most of each fine-tuned cell's deficit is a failure to stop, not a failure to reach the answer.
- Truncated outputs that **loop** are *more* often correct when forced than non-looping ones. That fits loops that start *after* the answer has been reached.
- Under forced answers, the sign of the P-effect flips. More distinct questions help: A6 and A5 beat A1, and A7 ≈ A5.
- The D2−D1 teacher gap shrinks from −21.75 to −3.3 pp.
- Every fine-tuned cell is still below the untuned baseline (50.5% sampled), although A6 comes within 4 pp.

## Flags (all true)
All seven flags are true, with the scope above. The cost flag covers the cumulative upper bound of $11.9995, which includes the failed first attempt; it is not an invoice.

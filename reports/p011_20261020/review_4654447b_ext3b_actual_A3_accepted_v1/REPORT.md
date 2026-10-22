# Actual A3: ext-3B matched-dose results (13dfdd59, request 49cebb37)

Reviewer: Claude, 2026-10-22 ~17:35 UTC.

**Verdict: ACCEPTED (A3 PASS).** Fine-tuning at about 3× dose does **not** improve on the 1× cells. Under the owner's standing rule, this is reported as "more budget did not improve the metric".

## Independent scope
- I stream-decoded the archive (sha df0660e6…, which matches ARCHIVE_READBACK) without extracting it. I covered all 5,000 MATH outputs (2,500 per cell) using my own BPE decoder (`ext3b_a3/a3.py`).
- For every row, my decoded text and answer region (the text after the last `</think>`, or the whole text if there is none) reproduce `raw_text_sha256` and `region_sha256` (5,000 of 5,000), and my stop classification equals the saved `stop_reason` (5,000 of 5,000).
- **Correctness consistency.**
  - No truncated row is labelled True.
  - No row that terminated natively and whose last box string-equals the gold is labelled False.
  - 67 rows are labelled True without string equality (15 in LARGE, 52 in SMALL). I checked each by hand. They are equivalent forms: `x=5`/5, degree signs, `\text{}`, a/b versus `\frac`, reordered tuples, base subscripts, `\dfrac{34}{100}` = 17/50, and a scalar times a vector equal to the gold vector.
- My paired-question bootstrap (10,000 draws, seed 20261021) reproduces both saved contrasts exactly.
- **Not accessed:** private checkpoints, exports and binaries; the full-state oracle, which I accepted as Codex's first-execution record; a full math-verify run (correctness was checked for consistency only); the invoice. The tagged cost of $26.71 + $30.44 = $57.15 is a projection.

## Results (MATH-500, B′ = 123,808,531 ≈ 2.96× A7's B, U = 1,935)
| cell | sampled acc | sampled EOS | greedy acc | greedy EOS | truncated rows that loop (sampled / greedy) | mean generated tokens |
|---|---:|---:|---:|---:|---|---:|
| 9,072×1 (E = 1) | 10.3% | 15.5% | 0.0% | 0.0% | 1,108/1,691, 485/500 | 15,620 |
| 3,024×E≈3 | 27.6% | 40.9% | 1.6% | 2.4% | 497/1,182, 474/488 | 14,088 |

LARGE − SMALL: **−17.3 pp [−19.6, −14.9]** sampled; −1.6 pp [−2.8, −0.6] greedy.

**Descriptive context (different pool and dose; not a registered contrast):**
- A1 252×1 (E≈16): 33.5% sampled, 59.5% EOS.
- A6 1,008×1 (E≈4): 33.85% sampled, 49% EOS.
- A7 4,032×1 (E=1): 14.5% sampled, 22.6% EOS.
- After forced answers, the same three cells reach 38.1%, 46.65% and 42.0%.

At 3× dose, "repeat about 3×" beats "new questions once" by about the same margin as at 1×, where A7 − A5 was −17.65 and A7 − A1 was −19.0. Neither 3× cell beats its 1× counterpart. Both remain far below the untuned baseline (50.4%).

Termination is still the dominant failure, and greedy decoding collapses completely. The relaxed pool's traces are about 33% longer, which is a confound against the 1× cells.

A forced-answer pass on these two checkpoints was **not** run. Whether the 3× cells reason better and only fail to stop more often is therefore unknown.

## Flags (all true)
All seven required flags are true, with the scope and limits above.

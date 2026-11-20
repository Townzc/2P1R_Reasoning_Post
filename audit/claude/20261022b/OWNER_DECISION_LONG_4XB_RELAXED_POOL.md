# Owner decision: the two 4×B cells are both drawn from the relaxed pool (replaces the data section of 5a00ef11 and lifts the hold in fa47f456)

- Recorded by Claude on 2026-10-22, about 03:15 UTC.
- The owner answered the multiple-choice question in the claude.ai conversation directly, choosing "都从宽松池重新抽 (推荐)" (draw both cells fresh from the relaxed pool, recommended).
- Purpose: compare buying new questions against repeating existing data at 4×B, with the same question-difficulty distribution in both cells. A7 is used only for descriptive comparison, because it comes from a different pool.

## Data (fixed now, no selection after seeing results)
- **Pool:** OT3 math parents (same grouping key as the A group) that have **≥1 eligible response** under the unchanged A eligibility rule: boxed completeness, original exact plus 13-gram decontamination, native total ≤ 16,384. The set comes from the CR-passed census, or from the same rule recomputed inside the build code. The two must agree.
- **Question order:** sort the parent keys of the pool, then shuffle once with `random.Random('p011-ext-4B-20261022')`. A7's questions are neither excluded nor prioritized.
- **Solution per question:** the first eligible response in the original per-parent seeded shuffle `random.Random(identity(key+'p011')[:16])`, the same rule as the census K1 diagnostic.
- **Cells:**
  - `long_R16128x1_S-F15_s17`: the first 16,128 questions in that order, one solution each.
  - `long_R4032xE4_S-F15_s17`: the **first 4,032** of those same questions with the same solutions (a strict subset of the cell above).
- **Dose:** B′ = the supervised token total of the 16,128 cell, one pass with EOS. Both cells use B′ under the original rules: U = ceil(B′/64,000) updates, and the R4032 cell trains each answer q or q+1 times through the existing `exact_subset`, giving E ≈ 4.
- If fewer than 16,128 questions are eligible, stop and report. Do not shrink the cells.

## Unchanged from 5a00ef11
Full fine-tuning, Qwen2.5-1.5B-Instruct, seed 17, peak lr 1e-5, warmup fraction and cosine schedule scaled to U, same sequence and mask rules. Evaluation identical to A7, with final checkpoints kept for a later forced-answer run. The two cells run in parallel on one H100 each. Training state is checkpointed about every 500 updates, and each cell may resume once automatically after an infrastructure failure. Worker timer 14 h. Reserve at most $45 per cell and at most $90 in total. New code paths need a Claude CR, then A2-lite, before launch.

## Later option (not authorized now)
`long_R4032xE1` at the original B (about $15) would connect these cells to the 1×B results within the same pool. It will be decided once funds are available.

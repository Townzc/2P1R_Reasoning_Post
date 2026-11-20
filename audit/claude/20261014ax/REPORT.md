# Claude audit 20261014ax — exploratory-completed-three-endpoints-g3-r1 @ 0debdeba: **PASS** (full 1,319 × 3, exploratory)

## Verification
- **Packet.** MANIFEST covers 46 files, all sha exact. The three `saved_suffix_evidence.tar.gz` archives have 338 / 379 / 399 members, all safe regular files and **all equal** to their ARCHIVE_MANIFEST (0 missing, 0 extra, 0 mismatched).
- **Independent decode and score of all 3 × 1,319 rows** (`fin_g3.py`: own BPE decoder, frozen `first_stop` with one vocabulary read, `completion_score`, `marked_answer_v1`):
  - The parent prefix (272 / 144 / 80 rows, from the preserved archive at bdf2ffd3) and the child suffix (starting exactly at 272 / 144 / 80) together cover all 1,319 IDs in official order, with no duplicates.
  - Every batch's `problem_ids` equals the frozen order. Every batch's `input_ids` equals the frozen prompt file.
  - **0 event mismatches and 0 score mismatches.** My per-question vector equals each child's `question_correct`.
- **Ledger and lineage.**
  - Each child has exactly one claim/attempt and a terminal of `completed`, with `claim_sha256 = digest(claim)`, receipt = terminal, and `digest(artifact_manifest)` = `evidence_sha256`.
  - Each failed parent is still `failed`, and each parent has its one-time suffix marker.
  - The providers show 0 owned containers.
- **Student.** `CHECKPOINT_RESTORED.json` records the original manifest (sha `45d38712…`, step 256, 524,287 targets), adapter and optimizer exact, `new_training_updates: 0`, and no new checkpoint written. This is a public proof; I did not read the binary.
- **Timing (actual).** Mean batch time was 11.6 / 16.9 / 28.2 s, with the in-worker audit taking about 0.3–0.4 s per batch. Wall times were 917 / 1,398 / 2,389 s, far below the 4,800 s cap. My aw estimate was conservative.

## Results (all 1,319; paired bootstrap over questions, 10k resamples, seed 20261014; pointwise, exploratory)

| model | correct | acc. | caps | vs base 0-shot (638) | vs 969 breadth student | vs 965 depth student |
|---|---:|---:|---:|---:|---:|---:|
| base 4-shot | 823 | **62.40%** | 9 | +14.03 [+10.99, +17.06] | −11.07 [−13.95, −8.34] | −10.77 [−13.50, −8.04] |
| Instruct 0-shot | 904 | **68.54%** | 54 | +20.17 [+17.06, +23.20] | −4.93 [−7.43, −2.35] | −4.62 [−6.97, −2.20] |
| wrong-pool student | 934 | **70.81%** | 43 | +22.44 [+19.33, +25.47] | **−2.65 [−5.08, −0.23]** | **−2.35 [−4.62, −0.08]** |

- All three are below **every one** of the 18 P008 students. The wrong-pool student sits 0.08–4.25 pp below them.
- Discordant pairs, wrong-pool student vs 969: 114 questions only it gets right; 149 only the 969 student gets right.
- The 4-shot prompt closes **58%** of the base 0-shot → mean-student gap (48.4 → 72.6%).

## Science-signal check (wording within GPT Pro 43–46 boundaries)
1. **Prompting explains a majority but not all of the zero-shot gap.** Four dev exemplars recover ~58% of it. SFT adds ~11 pp beyond 4-shot.
   - A 4-shot prompt carries content and organization as well as format, so this does not identify a "format-only" mechanism.
2. **The general Instruct model (local protocol) is below all our 100–4,000-answer students**, at 68.5% with 54 caps.
   - It is a reference, not a ceiling. It uses a Math-style system prompt on the general model, a 512-token cap, and a strict parser.
3. **The natural wrong-answer bundle trains a student that keeps ~92% of the base → student gain (+22.4 of +24.2 pp), yet is reliably a little worse (−2.4 to −2.7 pp).**
   - This is in line with Li et al. 2025: 66.3 vs 63.1 for wrong final answers, on a much larger student.
   - It is **not** a causal estimate of correctness. The bundle covers 101 parents, ≈10% of its rows sit on label-error items and ≈30% on ambiguous ones (AI-judged), and lengths differ.
   - **Correction to my earlier prefix-only reading (au, n = 80: "about the same"): over the full test it is lower.** The prefix was too small.
4. **Combined, for the midpoint.** In this setting most of the SFT gain is obtainable from a small amount of teacher-style demonstration data, even with wrong final answers. Answer correctness and quantity move accuracy by only a few points. That is consistent with the allocation insensitivity seen in P008. **The next study should move to a setting where the student is clearly data- and content-limited.**

Disclosures (carried from aw):
- I viewed the prefix results before the suffix completed. The design was fixed beforehand.
- The test set has been seen before.
- Exploratory, not preregistered.

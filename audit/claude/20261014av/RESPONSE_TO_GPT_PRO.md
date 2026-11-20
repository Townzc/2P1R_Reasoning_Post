# Claude 20261014av — response to GPT Pro review (audit/gpt_pro/20261014 @ 9327210e, notes 43–46 @ Obsidian e097b0cb)

I read the README and all four notes in full. I agree with nearly all of the corrections. Below: what I accept, what I fixed, and the one place where new evidence (20261014au) now answers a question the notes left open.

## Accepted corrections (my earlier wording was too strong)
1. **"SFT mostly teaches format"** is not identified. A 4-shot prompt also supplies content, organization and context. My own partial-prefix result (au: 4-shot 61.8% vs 0-shot 51.1% vs students 75–76% on the same 272) already contradicts the strong form, and I retracted it there. The defensible statement is: *a reasonable prompt explains part of the zero-shot gap; the remaining SFT gain is learned from ~100 examples and does not grow with more data in this setting.* Mechanism (elicitation vs. new skill vs. termination/extraction) is not identified.
2. **Union coverage 94.9% is an oracle over 18 different models**, not single-model pass@18 or "latent capability". The 8-model vote of 81.6% shows complementarity across models only. I withdraw "the ceiling is reliability, not capability".
3. **"Bad test problems ≈ 1%"** was an invalid extrapolation from a selected all-wrong subset. GSM8K-Platinum (full test) removed 110 and relabeled 10 of 1,319 (≈ 9.1% flagged, mostly problem issues), and its consensus items were not all human-checked. I withdraw the 1% figure.
4. **16.2% is an attempt share.** I recomputed the token share from the D1 pool rows: the per-attempt prompt + completion tokens sum to **1,673,438**, exactly the wallet's charged units. The 87 never-solved problems account for **289,502 units = 17.3%** of the charged tariff (696/4,304 = 16.2% of attempts).
5. **Adjudication records were incomplete.** The test CSV listed only 13 IDs plus a summary row. Both files are now per-item, with gold, modal model answer, label and a one-line reason, and every row is marked *AI-judged, not human-verified*:
   - `train_consistent_wrong_70_adjudicated.csv`. Following note 45 §2.2, the 10 items I had counted as teacher_error **without reading the full problem text** are now `unresolved`. New counts: label_error 17, ambiguous_or_flawed 33, teacher_error 8, representation_only 2, unresolved 10.
   - `test_all18_wrong_67_adjudicated.csv`, all 67 IDs: student_error 54, ambiguous_or_flawed 8, label_error 3 (00403, 00454, 01042), representation_only 1, unresolved 1 (00823, likely a label error but the text was truncated in my view).
   - "25 vs 1/4" is labeled representation_only: equal only under a percent unit, never a global parser fix.
6. **Wrong-demonstration experiment.** Agreed that the natural wrong pool cannot identify a causal effect of correctness: it covers 101 parents, ≈10% of its rows sit on label-error items and ≈30% on ambiguous ones, and lengths differ. Li et al. used Qwen2.5-32B-Instruct and still saw a 3.2-pp gap (66.3 vs 63.1) for wrong final answers. A same-parent correct/wrong pairing, or a final-answer-only intervention, is the right follow-up. Owner decides.
7. **B and T change together** on the main path, so "neither more data nor more training helps" cannot be separated. The bridge (B8/T1) shows many purchased answers were never exposed.

## What the new partial results add (20261014au; exploratory, prefix-conditional)
These are reviewer-side rescoring of preserved prefixes, not admitted results.

| | n | accuracy | same-prefix reference |
|---|---:|---:|---|
| base 0-shot | 272 | 51.1% | — |
| base 4-shot | 272 | 61.8% | Δ = +10.7 pp [+4.0, +17.6] over 0-shot |
| Instruct 0-shot | 144 | 67.4% | students 74–75% |
| wrong-pool student | 80 | 73.8% | 969/965 students: 75.0% / 73.8% |

Under note 46's pre-stated reading: the wrong-pool result is consistent with "this mixed-quality, 101-parent bundle can yield similar scores". It does **not** identify the effect of correctness. n = 80 is very small.

## Position for the midpoint (updated)
- **Report:** a local plateau under the tested teacher/student/LoRA/dose/decoding; no replicable allocation ranking; heterogeneous failure cost concentrated on a small tail (17.3% of tariff); exploratory baselines locating part of the gap at prompting.
- **Do not report:** a format mechanism; a single-model capability ceiling; a population bad-label rate; a causal correctness effect.
- **Next:** I agree with note 45's ordering.
  - P0: audits on existing outputs (evaluation contract, adjudication, tail tokens, exposure).
  - Then **one-axis** calibration for a learnable regime.
  - Then an evidence-conditioned stop/redirect rule compared with the fixed cap at equal tariff, judged by student outcomes rather than pass rates.

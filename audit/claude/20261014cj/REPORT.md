# Audit 20261014cj: `p009-stage1-S1-first-pair-actual-A4-r1` (S1 first-pair A4 + futility)

- **Scope:** `p009-stage1-S1-first-pair-complete-and-futility-A4`
- **Target:** `30b906daa81a3c1c5ce1603d701310be0c6e72f2`
- **Packets:**
  - First-pair packet manifest: `0882644c22da786f603b90d83dfbb46ed9b14faf583bfaa3355fa8ea72baa670`
  - Endpoint packet manifests: n400 `9f9b0929…`, n3200 `64c85f6a…`
  - Registered decision file: `88d2b615…`

## Decision: PASS
- The registered futility stop is **confirmed**: `stop_registered_futility`.
- The 4 remaining S1 slots and Stage 2 do not run.
- G1 was not assessed and must not be reported as passed or failed.

## Independent checks (`s1_first_pair_rescore.py`)
**For each run, from the original-byte archives**
- **Prompts.** 2 raw batches give 500 IDs in frozen order, and every prompt equals the frozen S1 `input_ids`.
- **Decoding.** My own BPE decoder ran the frozen `first_stop` with EOS 151643 and cap 1024. Every row's stop event equals `DECODED_ROWS`, and every `answer_segment` equals `SCORING_ROWS`.
- **Gold.** Every gold answer equals `math500.jsonl` `answer`.
- **Scoring.** I ran the frozen `math_scoring.last_box` and `decide()` on my own segments, using the journal's symbolic result for each (gold, answer) pair. There were 0 missing pairs.

| | n400 | n3200 |
|---|---|---|
| Correct (out of 500) | **273** | **276** |
| Native EOS | 464 | 446 |
| Length cap (counted wrong) | 36 | 54 |
| Technical unknown | 0 | 0 |
| Agreement with the oracle `question_correct` | exact | exact |

- **Dose.** For both runs, every one of the 1024 updates recomputes exactly from the cb-accepted plan and encodings. Totals are **2,097,148 targets**, 1091 units, merge fp32 → bf16 with 0 post-save updates, and exit 0 joined before the endpoint.

**Disagreements where the symbolic and string checks differ: 25 (n400) and 22 (n3200)**
- All are symbolic = equivalent, string = different, so they are counted correct. There were no fallback, timeout or tool-error rows.
- I adjudicated all 47 by hand (`disagreements.json`). **All are correct equivalences**, for example:
  - `\frac43` = `\frac{4}{3}`
  - `30^\circ` = `30`
  - `\text{(C)}` = `\text{C}`
  - `58,500` = `58500`
  - `\frac{11}{2}` = `5.5`
  - `\frac{639}{40}` = `15.975`
  - `x\in[-2,7]` = `[-2,7]`
  - `15\mbox{ cm}^2` = `15`
- One borderline case is `2516_8` vs `2516` (math500/71, n400): the base subscript is dropped. I accept it.
- **Limitation.** PyPI is blocked here (proxy 403), so `math-verify` could not be installed and I did not re-run symbolic comparisons. Symbolic true positives are covered by the manual adjudication above. Possible symbolic false negatives were screened: I ran a normalization screen over all 91 discordant questions, comparing the wrong side's boxed answer with both the gold and the other run's answer. It found **0 suspects**.

**Pair (registered `first_pair_decision`, recomputed)**
- Δ = 276 − 273 = **+3 (+0.6 pp)**.
- 91 discordant questions: 47 where only the n3200 student is right, 44 where only the n400 student is right.
- Futility rule: stop if 100·Δ < 2·500, i.e. if Δ < 10. **Δ = 3, so it stops.** Reversing the decision would take 7 net corrections in n3200's favor, and none were found.

**NC part of the decision.** It is unchanged: 954 → 967, `NC_gate_passed`.

## 科学信号检查 (science-signal check)
- **MATH (S1) is also flat at fixed training compute.** With 400 versus 3,200 distinct first-try-correct teacher answers, using 1,024 updates and 2,097,148 targets each, Qwen2.5-1.5B scores 54.6% and 55.2% on MATH-500.
- This is far above the student's 27.2% zero-shot baseline. So SFT helps a lot, but on this evidence 8× more distinct answers adds about 0.6 pp.
- Together with NC (+0.99 pp on GSM8K), **the preregistered search found no qualifying learning regime in either setting**. Allocation questions cannot be measured in these settings.
- **Caveats** (registered wording):
  - one seed only;
  - no bootstrap or G1 was run;
  - the pool is conditional on first-try-solvable problems (cb N1);
  - more answers come with fewer repeats per answer: 11–12× versus 1–2×;
  - n3200 has more length caps (54 vs 36).
- This is **not** evidence of equivalence, a capability ceiling, or a mechanism.
- **What the registered plan says next:** "停止花费，讨论转向" (stop spending and discuss a pivot), for example a larger student–teacher gap or an evidence-based stopping/cost write-up.

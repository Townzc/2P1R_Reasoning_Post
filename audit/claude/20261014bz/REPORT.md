# Audit 20261014bz: complete P1 scoring, independent adjudication, eligibility use and S1 G0

- **Request:** `p009-math-p1-complete-scoring-A2-r1`
- **Scope:** `p009-math-p1-complete-scoring-and-independent-adjudication-A2`
- **Target:** `ae8b8c3c2f1ad75bac25678d49f85f6a7c1b6694`. The packet is unchanged at `65841f8e`.

**File hashes, all recomputed:**

| File | SHA |
|---|---|
| `MANIFEST.json` | `6200fd888fe74686d1df350531b1055bff8b6819140c3c61398fdc40379eece6` (126 entries, all match) |
| `SUMMARY.json` | `984c91a03e12278c5a30620a7482f15dce7c8b3deab087cac6be2e58a3cea060` |
| `COLLECTION.json` | `8af88b2e83e27c53b4b57ba5826d962363f319c8cac06db267e7dde9cb7ed50b` |
| `evidence.tar.gz` | `637c97252e77426c10c10b7dc7023ea53db1dc16704223cd563f131651dcac64` |

- **source12:** identical to the map accepted in bx: driver `1c8447ce…`, journal `c7d86daf…`, pool `c3ac26aa…`, scoring `d310d7e6…`, and the rest unchanged. The publisher is `8863741f…`, accepted in by.

## Decisions

| Item | Decision |
|---|---|
| Raw / evidence integrity | **PASS** |
| Independent adjudication (117 fixed samples) | **PASS-WITH-NOTES.** 0 value-level false positives. 4 endpoint rows (1 Qwen 0-shot, 3 Qwen 4-shot) are value-equal but violate an explicit answer-form instruction. Labels are unchanged, per the frozen rule. |
| Procurement labels for teacher-answer eligibility | **ACCEPT-WITH-NOTES.** The scorer's errors in the audited strata are conservative: false negatives only. |
| **S1 G0** | **PASS**, under every adjudication sensitivity |

## 1. Evidence integrity (independent; see `p1_complete_verify.py`)

**Files and projections**
- All original files except the 104 projected chunk intents match COLLECTION's original SHAs.
- All 104 projections hash correctly. Each `COMPLETED.intent_sha256` equals the original intent SHA recorded in COLLECTION.

**Roster:** `ROWS.json` is byte-for-byte the roster I verified in bx against my own raw decode and gold extraction.

**Chunks**
- 105 chunks are contiguous over 0..10489, and the row ids follow the frozen order.
- Every `COMPLETED.result_sha256` matches, with technical_unknown 0.
- The concatenation equals `ALL_SCORED_ROWS.json`.

**Pairs:** 4,048 distinct pairs.

| Status | Count |
|---|---|
| compared | 4,031 |
| parse_failure | 16 |
| tool_error | 1 |
| outer_timeout | 0 |

**Every row**
- Using my own brace-matching box extractor, cap/invalid rows and rows with no box have no pair and are False.
- Every boxed native/boundary row references the pair (gold, my extracted answer).
- The frozen `decide` applied to the cached verdict reproduces the saved `correct` (0 mismatches).
- I could not re-run `math-verify` itself because PyPI is unreachable from this sandbox. The symbolic verdicts are therefore checked through the adjudication below, not by re-execution.

**Recomputed counts:** identical to SUMMARY.

| Pool | n | Correct | Caps | No box |
|---|---|---|---|---|
| procurement | 8,989 | 6,905 | 740 | — |
| teacher_math_zero | 500 | 359 | 36 | — |
| qwen_math_zero | 500 | 136 | 68 | 76 |
| qwen_math_four | 500 | 147 | 39 | 17; 386 new-problem boundaries (descriptive only) |

## 2. Independent adjudication of the 117 fixed disagreement samples

All 117 are the same kind of disagreement: symbolic equivalent = True while the normalized strings differ. So the only possible error is a **false positive**. I judged each against the full original question and reference solution from `math_train7500.jsonl` (`73d37f56…`) and `math500.jsonl` (`132582ca…`). The pairs are in `disagreement_samples.json`.

**Value-equivalent, formatting only: 112 rows.** Every one is benign:
- units or `^\circ` dropped (gallons, cm, \$, %, miles, inches², pounds);
- `\frac43` vs `\frac{4}{3}`, and `\tfrac` / `\dfrac`;
- leading zero (`.185` vs `0.185`) and thousands separators (`40,\!320`);
- `x=12` vs `12`, and `x\in[-2,7]` vs `[-2,7]`;
- reordered factors, terms or roots (`(x+2)(x+1)`, `2\cos a\sin b`, `1, -2`);
- an equivalent radical (`-1/\sqrt2 = -\sqrt2/2`);
- decimal vs fraction where no form was requested (`45.5`, `0.1`, `5.5`);
- choice letters (`(C)` vs `C`, `\text{D}`);
- pmatrix with `16/49` vs `\frac{16}{49}`;
- base subscripts where the question asks for that base (`2516` vs `2516_8`, `2003_6` vs `2003`, where 1+…+45₆ = 435 = 2003₆);
- `3992004/3988009 = 1998²/1997²` (no form requested);
- `-80\le g(x)\le 82` vs `[-80,82]`.

**Value-equal, form debatable: 1 procurement row.**
- `intermediate_algebra/train/792` asks for an interval. The answer is written as `[0,1/5] ∪ (1/5,2)`, which equals `[0,2)` as a set.
- I count it as mathematically correct and acceptable as training data.

**Value-equal but violating an explicit answer-form instruction: 4 endpoint rows.**

| Pool | Problem | Instruction | Answer given |
|---|---|---|---|
| qwen_math_zero | math500/179 | integer coefficients with gcd = 1 | `10x − 14y + 22z + 8 = 0` (same plane) |
| qwen_math_four | math500/181 | rational denominator | `1/√3` |
| qwen_math_four | math500/472 | mixed number | `550/4` |
| qwen_math_four | math500/162 | common fraction | unreduced `34/100` |

- Under the frozen value-equivalence scorer these stay correct. Labels are **not** repaired.
- Strict-form sensitivity: Qwen 0-shot 136 → **135**, Qwen 4-shot 147 → 144. The teacher has none.

**No row is a value-level false positive.** For the 539 procurement disagreements this gives 0/50 errors. The rule-of-three 95% upper bound is about 6%, i.e. at most about 32 rows, or ≤ 0.5% of the 6,905 correct procurement rows.

## 3. Fallback, tool_error, timeout and exclusions

**Fallback rows and thresholds.** 17 procurement rows and 1 per endpoint fell back to string comparison. No pool exceeds 2% fallback, and there are 0 outer timeouts, so the 0.5% flag is false everywhere.

**Procurement parse_failure rows (16).** In 12 rows the answer is value-correct but scored False. In most, the gold extraction kept trailing punctuation or markup, which defeats the string fallback:
- trailing punctuation or markup: `-\frac{5}{3}.`, `30^\circ.`, `7\text{ hours}.`, `43_5.`, `\text{(E)},`, `\dfrac{2469}{20,\!000}`, and `\dfrac{1}{29,\!322,\!216}` in all 4 attempts of counting/163;
- pmatrix with a trailing `.`, or containing `\phantom -1`.

2 parse_failure rows are True (`a+b+c`, `\sin^2 t`), and 2 are genuinely wrong (int_alg/10, int_alg/26). These errors are **conservative false negatives**: they remove some problems from eligibility and never add a wrong label.

**tool_error (1).** In `prealgebra/train/599` the answer is `17:00` and the gold is `05:00`. The question says "AB:CD without am or pm, such as 08:00", so 12-hour form is intended. Scoring it False is defensible; I record it as ambiguous.

**Endpoint fallback rows (3).**
- `teacher math500/398` boxed `\boxed{�in}`. The teacher's own generated text contains an invalid UTF-8 sequence where "Navin" should be; my independent decoder confirms the same segment. False is correct under frozen rules. Lenient strict-intent sensitivity: teacher +1.
- `qwen0 math500/298` and `qwen4 math500/15` are genuinely wrong.

**Unsupported gold (4).** `algebra/train/888` and `1011` have no box; `number_theory/train/661` and `663` have an empty box. I re-confirmed these against the original solutions in bx and again here. They are excluded with their full records and not scored as zero. The procurement count 8,993 = 8,989 + 4. All 1,500 endpoint golds are supported.

## 4. Eligibility-use decision

**ACCEPT-WITH-NOTES.** The frozen P1 `teacher_label_eligible` labels can be used for S1 roster preparation.
- Audited false-positive rate: 0/50.
- Known false negatives are conservative: 12 parse_failure rows, plus the ambiguous tool_error row.
- 6,905 is a row count that includes repeated attempts, not a count of eligible questions. Whether 3,200 eligible questions exist is for the separate frozen roster to decide.

## 5. S1 G0 (frozen integer rule)

| | Teacher | Qwen 0-shot | Gap | Caps (≤ 75 = 15%) | technical_unknown | Result |
|---|---|---|---|---|---|---|
| Frozen labels | 359 (71.8%) | 136 (27.2%) | 223 = **44.6 pp** | 36 / 68 | 0 | **PASS** |
| Strict-form | 359 | 135 | 44.8 pp | 36 / 68 | 0 | PASS |
| Extreme bound (teacher's 34 disagreements all wrong, student's 16 all right) | 325 | 152 | 34.6 pp | — | — | PASS |

**S1 G0 PASS is robust to any adjudication outcome.** Qwen 4-shot (147, 29.4%; 386/500 new-problem boundaries) is reported descriptively and is not a gate.

## 科学信号检查 (science-signal check)

- **This is the first real signal from P009.** On MATH, the same Qwen base student is 44.6 pp below the teacher, against 34.6 pp for NC/GSM8K. The headroom is large.
- **Caveat for interpreting G1.** 144 of 500 (28.8%) of the 0-shot student's outputs are format failures: 68 caps and 76 with no box. Any SFT will fix format quickly. Because G1 compares n400 against n3200 at equal compute, and both learn format, format alone should not create the G1 slope. Still, the n100 point and the A4 futility check should be read with this in mind.
- **Teacher 4-shot vs 0-shot.** The Qwen 4-shot prompt helps only +2.2 pp and mostly ends at new-problem boundaries. This matches the earlier observation that few-shot prompting is not a substitute for SFT here.
- **Now the candidates.** S2 is out (cap rule). S1 and NC both have G0 PASS. Stage 1 can proceed once the separate input/runtime/numeric gates pass.

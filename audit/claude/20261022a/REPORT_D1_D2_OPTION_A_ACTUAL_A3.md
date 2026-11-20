# Actual A3 — original D1 and owner-scoped D2 option (a)

Target a4a57687 (request ac841b67). Packet reports/p011_20261020/d1_d2_option_a_actual_results_v1.
MANIFEST sha 778a22b6…, ACTUAL_RESULT_BINDING sha b5ca8464…. Reviewer: Claude, 2026-10-22 ~01:05 UTC.

**Verdict: numbers ACCEPTED (A3 PASS), with a mandatory post-hoc smoke-gate FAIL disclosure (termination). This is not a code bug and nothing needs to be stopped or rerun.**

## Integrity
- New archive: the two parts reassembled to sha 0248fa36…, which equals ARCHIVE_READBACK. The D2 failure archive (0b44606a) reassembled to a4bceebe…, which equals its readback.
- SAVED_RESULTS.D1.endpoints is byte-identical to the archived D1 score COMPLETED.json.

## Independent decode (own byte-level BPE from tokenizer.json, sha c0382117…)
Scope: all 3,300 D1 rows (raw eval_0000–0006) and all 2,980 D2 scoped rows (raw eval_0000–0005 from the failure archive). Every scored row was decoded from original token ids.
- Stop rule: native_eos = the final token is 151645 or 151643, with no earlier EOS. length_cap = 16,384 tokens, finish=length, no EOS. 0 other, 0 unmapped tokens.
- Text: the decoded text before EOS reproduces `raw_text_sha256` (digest = sha256 of compact JSON) for **3,300/3,300 and 2,980/2,980** rows.
- Region: the region after the last `</think>` (whole text if absent) reproduces `region_sha256` for every row.
- Stop reasons agree on every row.

## Correctness consistency (math-verify not rerunnable here; PyPI blocked)
- 0 truncated rows labelled True, so length_cap is always wrong, as the protocol requires.
- 0 rows whose last-`\boxed{}` string equals gold (after light normalization) but are labelled False.
- Rows labelled True without string equality: D1 73, D2 19. All 92 were reviewed manually and every one is a correct equivalence (`\frac43` vs `\frac{4}{3}`, `5` vs `x=5`, `10080` vs `10,\!080`, `C` vs `\text{(C)}`, `1.5` vs `\frac32`, `-2,1` vs `1, -2`, units/`\$` dropped, `10\%` vs `10`, `45^\circ` vs `45`). No false positives were found.

## Contrast recomputation (own implementation, same paired-question bootstrap, seed 20261021)
| D2 − D1 (MATH-500) | Δ (pp) | 95% CI | saved |
|---|---:|---|---|
| sampled mean pass@1 | −21.75 | [−24.35, −19.15] | identical |
| greedy | −26.60 | [−30.8, −22.4] | identical |

A sensitivity check with seed 7 gives [−24.40, −19.10] and [−30.8, −22.4].

## Post-hoc smoke gate (owner directive) — FAILS on termination for both D cells
| | MATH-500 sampled EOS | accuracy | accuracy given EOS | mean generated tokens |
|---|---:|---:|---:|---:|
| D1 (AM-Thinking-v1) | **45.4%** (907/2000) | 32.0% | 70.7% | 9,557 |
| D2 (Qwen3-235B) | **13.3%** (267/2000) | 10.3% | 77.2% | 14,459 |
| D1 greedy / D2 greedy | 42.0% / 6.8% | 32.6% / 6.0% | 77.6% / 88.2% | 9,995 / 15,379 |

AIME24/25: EOS is 1–4% for both D1 and D2 and accuracy is 0/240 for both (descriptive only).

**Interpretation constraint (must be in the report):** both cells fail gate condition 1 (EOS ≥ 70%).
Conditional on terminating, D2 is not less accurate than D1. The whole D2−D1 gap is carried by D2's student failing to stop within 16,384 tokens; truncation is scored wrong by protocol.
Δ_T^D therefore measures the teacher's effect on **termination/length behaviour under a 16k cap**, not on reasoning accuracy. It must not be reported as "Qwen3-235B data teaches worse reasoning".
This also explains why D2's evaluation ran long and hit the 9,000 s timer.

## Request (priority)
The A cells (A1r2, A5, A6, A7) and baseline use the same F15 arm. Please publish **per-endpoint stop-reason counts** for them first, before or together with the scores. If A7 also has EOS < 70%, plan §2 rule 2 governs the interpretation of the A grid.
Scripts and outputs: `d1_d2_a3/`.

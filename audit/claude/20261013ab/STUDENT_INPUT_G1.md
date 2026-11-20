# Claude audit 20261013ab — p008-student-exact-input-g1-r1 @ 0be9e6e0: **PASS-WITH-NOTES (exact all-draw student inputs/specs)**

Audited 2026-10-13 ~19:55 UTC.
- **Packet identity:** the device copy of `student_admission_v1` is hash-identical to git: 68 files, combined digest `5f6099c1…29b5`.
- **Method:** my device scripts `~/aud/g1_students.py` and `g1s_extra.py`. They decode every raw teacher output again (D1 + D2 parent + D2 child, **14,836 candidates**). They take wallet accepted sets from the outputs I already verified (20261013u/aa), and they recompute every plan with my own re-typed `exact_remainder` + `schedule`.

## Q1 — rows, plans and common T: YES
**Rows: 16 cells, 0 failures.** For each cell:
- the path-ID set equals the wallet's accepted set exactly, with no duplicates;
- the problem/attempt/candidate identity is consistent;
- **every `response` equals my own decode of the original raw tokens** (truncated at the first EOS), and `response_sha256` matches;
- every `prompt` equals the GSM8K train question, and every `answer` equals the gold answer;
- `n_processed = n_prompt + n_supervised ≤ 2048`.

Row order is a fixed rule that never looks at scores: **frozen parent order, then attempt**. Consumption order differs from it in 15 of the 16 cells, so this sort is deliberate. The worker additionally re-tokenizes each row with the real HF tokenizer and refuses on any mismatch in n_prompt, n_supervised or n_processed (`runtime.encode`).

**Plans: 18/18 pass every check.**
- T is 524,287 for T1 and 4,194,296 for T8, both **nominal**. No downward search step was needed, which is consistent with `COMMON_PLAN_GATE.common_targets`.
- U is 256 or 2,048, and no update is empty.
- Exposures match the update multiset, and all lie in {q, q+1}.
- **The dose Σ n_supervised equals T exactly.**
- **My own schedule reimplementation, using seed 17 and the published lengths, reproduces every plan's `q` and the full `updates` list exactly.** The plans therefore come from the frozen deterministic rule.
- LR vectors are equal to the frozen `LR_VECTORS.json` (256 and 2,048). My re-typed formula differs from them by at most 1.4e-20 on a few entries, which is floating-point rounding.
- The D1 B8/T1 bridges have q=0, with 1,637 (breadth) and 2,216 (depth) zero-exposure answers. This is the pre-registered q/q+1-including-0 rule, and those answers stay in the denominators.
- Per-update supervised tokens range from 1,470 to 2,581, against a nominal 2,048.

**Evaluation set:** `gsm8k_test1319.jsonl` has 1,319 rows, and each row's question, gold answer and ID equal the GSM8K test source, in order.

## Q2 — preparation adapter: YES (by output)
The prepared rows reproduce the original 6,973-parent records, the teacher text and frozen-parser acceptance exactly, as checked above. I did not re-run the preparation itself. The prior local failures are recorded as producing no outputs.

## Q3 — plan and scope: YES
- `EXECUTION_PLAN` is the successor campaign: 20 slots identical to the original, 19,460¢, and a 6-day technical envelope. Its digest equals `TRANSFER_EXPECTED.successor_plan_sha256` (0c0262ee…).
- Worker caps are unchanged: base 5,492 s, T1 6,001 s, T8 9,560 s.
- The spec also carries `maximum_concurrent_gpus` 8, the 21:00 PDT freeze, and the block-journal policy, as reviewed at 20261013aa.

## Q4 — lineage and gates: YES
- D1 is bound to its completed original pool.
- D2 is bound to the failed parent plus the completed child, using the merged oracle that I passed at 20261013aa.
- **N2 is still open.** No T8 job may start until the actual T1 timings pass the reviewed T1-first rule (20261013u, C1/C2).

## Notes
- **SI-N1.** The schedule's seeded subset-sum (`subset_selection_depends_on_lengths=True`) chooses which answers receive the extra exposure, or any exposure at all in the bridges, by **length**. It never looks at scores. This remains a stated limitation.
- **SI-N2.** All gates are now in place for **T1 + base** dispatch under the completion campaign, once Codex records them: merged G1-D2, completion queue, this input G1, and quota. **T8 waits for N2.**

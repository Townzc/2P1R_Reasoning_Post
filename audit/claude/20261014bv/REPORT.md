# Audit 20261014bv: P1 36-hour local window, Stage 1 roster selection code, and early Qwen Stage 0 signal

## A. `p009-math-p1-local-window-36h-r1`

- **Scope:** `p009-math-p1-extended-local-window-and-first100`
- **Target:** `bb2629ba4ceb21db97cb500afa0d9b47387b9290`
- **Manifest:** `f9c6cd3d0c5d24998196d9093ed95e5fb370544e0dadd360bb443770d25931b5`. All entries match.

### Decision: PASS

Return values:

| Field | Value |
|---|---|
| `source_files` | 12 entries in `SOURCE_BINDING.json`, all recomputed. The original 10 (bu) are unchanged. The two new files are `p1_input_binding_extended.py` and `scripts/p009_p1_driver_extended.py`. |
| `generation_target_commit` | `974efcbf3c6eae6034828ef11c78831cb97dea46` |
| `generation_spec_sha256` | `e3775978166cf1e5209c864ef3e3e84c03c2751c3c58cbe2c14a58273efa6b24` |
| `conditional_first100_authorized` | `true` (same input conditions as bu) |
| `first100_wall_seconds` | `1200` |
| `maximum_total_wall_seconds` | `129600` |
| `local_window_amendment_sha256` | `de0ca58c2cb44877f210f4060f99cadcc9b447e53367ab6130c0ad2f4016b7b0`. This is the canonical digest of `OWNER_AMENDMENT.json`, which I recomputed. The file's own SHA is `cad4f96e…`. |

### Checks

**Owner decision**
- The owner chose option B with a direct reply ("就选b") before any first-100 measurement.
- 36 hours is Codex's concrete reading of that choice, and the record says so.
- No cloud budget, labels, scorer, timeout or forecast rule changed.

**Code change**
- The diff against the original driver touches only the scope, the 129,600 s cap, and the extra review bindings.
- Those bindings require `maximum_total_wall_seconds` and the amendment SHA on both the code review and the timing review. The proposal and input binding also carry the amendment.
- I ran the 5 new fixtures here and all pass.

**bu N1 is closed.** The 8 s outer timeout bounds every pair, and at most 10,493 pairs remain. So even the worst case, every pair at about 8 s, gives a serial scenario of about 1.2 × (8 × 10,493 + 300) ≈ 101,000 s. That is still below 129,600 s. The registered conservative scenario can therefore always be approved when the first 100 completes cleanly. Scenarios near that worst case would mean about 28 hours of local scoring: a schedule cost, not a block.

**Read-only first-100 publisher** (`b622aa17…`)
- It copies original bytes only and reads them back, and it gzips the full roster losslessly.
- It refuses if a remainder or failure already exists, or if any chunk other than `00000` is present.
- Cosmetic nit: its generated `REVIEW_REQUEST.md` text says "exact10-source", but the binding actually has 12 sources.

## B. `p009-stage1-roster-selection-code-r1`

- **Scope:** `p009-stage1-roster-selection-code`
- **Target:** `fd03e883c9377258c81ce080cef79dedee856b82`
- **Manifest:** `57d08a2bd1997bff15f4f0d870573888d62d3bbdbf4e7bebb17090c9303fa280`. All entries match.
- **`source_files`:** 7 entries, all recomputed. `training_plan.py`, `src/sft_data.py` and `schedule.py` have an empty diff against `c23ed875` (be), and the LR vector is `cb9c2e04…`.

### Decision: PASS-WITH-NOTES

This is code only. It admits no student.

### Checks

**Duplicate questions**
- The earliest source row per normalized question is chosen *before* correctness is read. This matches the protocol's R1 clarification, where algebra/train/925 wins over 959.
- If the earliest row was never generated (one of the 7 context exclusions), the question is excluded. No duplicate row can rescue it.

**S1 eligibility**
- Only attempt01 can be selected.
- It must have `native_eos`, and P1 must mark it `correct`, `parsed` and `teacher_label_eligible` with real Booleans. These field names match the output of `math_scoring.decide`.
- A `new_problem_boundary` stop is excluded, as are unsupported gold labels; neither is ever counted as a zero.
- The original answer text and the generation/P1 row digests are kept.

**Permutation**
- The sort key is `SHA256("p009-stage1-question-order-v1:SEED:PROBLEM_ID")`. Ties break on the ID.
- The key does not depend on correctness or input order. Every n is a prefix of one full order.
- Seed 17 uses n = 100/400/1600/3200, seed 29 uses 400/3200, and NC uses 400/3200 at seed 17 only.
- This makes the protocol's "single frozen permutation" concrete, and it is fixed before any student outcome.

**Dose**
- Fewer than 3,200 eligible questions blocks the run. So does a selected whole-answer target sum above 2,097,148. There is no smaller-n fallback and no q = 0 substitution, which matches be N1.
- `checked_rows` is unchanged.

**Tests:** I ran the 8 synthetic fixtures here and all pass.

### Notes

- **N1 (the Stage 2 order must reuse this key).** The protocol's Stage 2 P_nat and D lists follow "the raw seed17 question order over the supported unique-question domain before correctness". The future Stage 2 code should use **this same seed-17 key over all supported unique questions**, not a second permutation. That keeps Stage 1 and Stage 2 orders consistent, and keeps R2's "D starts at the first question of the same raw order" well defined.
- **N2 (feasibility).** S1 needs at least 3,200 eligible attempt01 answers out of about 7,492 supported unique questions, plus the exact dose sum. Both are checked on real P1 labels. If either fails, report it and stop. Do not change n or the dose.

## C. Science-signal check (first real Stage 0 outputs: Qwen, published at `b7ebf425`)

Qwen's MATH outputs are decoded but not yet scored. These numbers are descriptive, from the published `RESULTS.json`.

| Endpoint | Logical stops | Caps / 500 |
|---|---|---|
| `qwen_math_zero` | native EOS 420, new_problem_boundary 12, length cap 68 | **68 (13.6%)** |
| `qwen_math_four` | native EOS 75, new_problem_boundary 386, length cap 39 | 39 (7.8%) |

- **Throughput.** Batches took 14.0, 16.9, 19.3 and 19.3 s at the 1,024-token cap, and the worker ran 143.5 s in total. This is far inside the break-even. If the teacher's seeded sampling batches behave similarly, they are well below the 127 s break-even.
- **G0 cap rule.** G0 requires "every relevant complete endpoint has logical caps ≤ 15%". **The S1 student 0-shot endpoint sits at 13.6%, close to that line.** It passes the cap rule as observed, since 68 ≤ 75. But the teacher's MATH 0-shot cap rate, once collected, needs the same check.
- **Pending:** an independent full raw A3 of these Qwen outputs, and the teacher and OLMo collections.

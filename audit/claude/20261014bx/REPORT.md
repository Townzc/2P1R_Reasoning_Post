# Audit 20261014bx: P1 first100 actual throughput (numeric review)

- **Request:** `p009-math-p1-first100-throughput-r1`
- **Scope:** `p009-math-p1-first100-throughput`
- **Target:** `85f1321a4dd02ceaed769025eb5695ef826f4ecd`
- **Packet:** `reports/p009_20261014/p1_first100_actual_v1`
- **Manifest:** `e984d81f7e2dc17f35e7f35331b91e400d38e5119e37879292a34cd981dd828e`. All 93 entries were recomputed and every one matches.

## Decision: PASS

| Field | Value |
|---|---|
| `proposal_sha256` | `f925c84774aedaf68c6d915cab35ae116b59226b37b3b05f182225f1eda455b2` (file SHA of `original/FIRST100_PROPOSAL.json`, recomputed) |
| `basis_sha256` | `eb2c3989f867ff3b8ba82513b613bb2da43b300db5b5a5afd44d5aa28ddc832b` (canonical digest of `BASIS.json`, recomputed; the file's own SHA is `a91174c4…`) |
| `first100_result_sha256` | `2b8b226ba244a3258f3a5f947708d067cde0a4092b3619f04b27561b8acec027` (file SHA of `chunks/00000/RESULT.json`, recomputed) |
| `driver_source_files` | The exact 12-source map. It equals the map accepted in 20261014bv (`p009-math-p1-local-window-36h-r1`), and every byte in `source/` hashes to it. |
| `local_window_amendment_sha256` | `de0ca58c2cb44877f210f4060f99cadcc9b447e53367ab6130c0ad2f4016b7b0` |
| `approved_total_wall_seconds` | `129600` |

## Independent checks

### Roster
- `ROWS.json.gz` holds 10,489 rows: procurement 8,989, teacher_math_zero 500, qwen_math_zero 500, qwen_math_four 500.
- Its canonical digest equals `BASIS.ordered_rows_sha256`.

### Rows against my Stage 0 replay
I decoded every one of the 10,493 original MATH raw records myself (my BPE decoder plus the frozen `first_stop`; see `p1_segment_crosscheck.py`).
- All 10,489 rows match exactly on `stop_reason` and `answer_segment`.
- The 4 rows with no match are exactly the 4 unsupported-gold rows.

### Gold
I re-extracted gold from `math_train7500.jsonl` (last `\boxed{}`, brace-matched) and from the `answer` field of `math500.jsonl`.
- 0 mismatches across all 10,489 rows.
- The 4 exclusions are confirmed structurally unsupported:
  - train/888 and train/1011 have no box;
  - number_theory/661 and 663 have an empty box.
- These 4 are kept with their full records and are **not** scored as wrong. All 1,500 endpoint golds are present.

### Pair denominator
- `pairs_for` over the complete roster gives **4,048** distinct pairs.
- My own brace-matching box extractor agrees with `last_box` on all 10,489 rows (0 disagreements).
- 976 rows produce no pair:
  - 883 `length_cap`, which is 740 + 36 + 68 + 39, matching the A2 cap counts;
  - 65 `native_eos` and 28 `new_problem_boundary` rows with no boxed answer.
- These 976 rows stay in the roster and are not dropped.

### First100 observations
- The ordered ids equal `rows[:100]`.
- The pairs from the first 100 rows are exactly the 73 observed pairs.
- The 73 `pairs/*.json` files equal the observations in `RESULT.json`. Each file name equals `pair_digest(pair)`.
- All 73 have status `compared`, with 0 timeouts.
- Maximum time is **0.07497 s** and the sum is 0.380 s. Startup took 0.216 s and 0.128 s across the 2 workers.

### Scenario
- Remaining distinct pairs = 4,048 − 73 = **3,975**.
- Scenario = 0.549639 (chunk through proof) + 1.2 × (0.074970 × 3,975 + 300) = **718.157926718588 s**.
- `first100_forecast` re-run on the packet reproduces every proposal field.

### Approved total
- 718.16 ≤ 129,600 ≤ 129,600.
- The driver subtracts the original `total_command_seconds` of 1.0487 s. That leaves a remainder window of about 129,599 s, enforced by `hard_timer` and by a between-chunk check (`wall − 10`).

## Notes
- **N1.** The scenario's elapsed term uses the chunk-through-proof time (0.55 s), not the full first command (1.05 s), so the scenario is about 0.5 s low. This is immaterial at this approval. The driver's budget subtraction does use the full command time.
- **N2.** Even the pessimistic case of every remaining pair hitting the 8 s outer timeout gives 1.2 × (8 × 3,975 + 300) ≈ 38,520 s (about 10.7 h), which is well inside 129,600. The likely duration is minutes, not hours, but that is an observation, not a guarantee.
- **N3.** This approves only the single remaining local invocation. Complete P1 still needs the fixed disagreement/fallback samples, the unique-timeout flags, independent adjudication and A2 before any eligibility or S1 G0 decision. That matches the request.

## 科学信号检查 (science-signal check)

No scientific signal yet. The first 100 rows are a procurement prefix and are deliberately not a result. Two structural facts to watch:

1. **Rows without a pair are scored wrong.** 976 of 10,489 rows (9.3%) have no scorable pair: they hit the cap or have no box. For the teacher MATH endpoint, its 36 caps plus any unboxed native/boundary rows will count against the teacher in S1 G0.
2. **Many rows repeat an existing pair.** Only 4,048 distinct pairs exist across 10,489 rows, so the remaining run should be cheap.

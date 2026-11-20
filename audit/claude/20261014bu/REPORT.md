# Audit 20261014bu: P009 P1 driver and first-100 input contract; Stage 0 result publisher

## A. `p009-math-p1-driver-first100-r1`

| Field | Value |
|---|---|
| Scope | `p009-math-p1-driver-and-first100-input-contract` |
| Target | `7dc7168cb6aaf9ba03af613fee354b45285ae601` |
| Manifest | `ce6e4178a575bedaef819838b83b7d274f3d91154e2f743ec907aa1615aaeafd`; all entries match |
| `candidate_sha256` | `0d2adc7933e0b31abc540543b1df4ef355a690faa886aa2774dc4809bc47692a` (recomputed) |

### Decision: PASS-WITH-NOTES

Return fields:

| Field | Value |
|---|---|
| `source_files` | The 10 entries of `CANDIDATE.json`, all recomputed. `math_scoring.py`, `math_scoring_pool.py`, `math_scoring_journal.py` and `requirements_math.txt` have an empty diff against `542b453f` (bp). `stage0_generation_contract_v2.py` (`3f36030d…`) is byte-identical to the funded generation target. |
| `generation_spec_sha256` | `e3775978166cf1e5209c864ef3e3e84c03c2751c3c58cbe2c14a58273efa6b24` |
| `generation_target_commit` | `974efcbf3c6eae6034828ef11c78831cb97dea46` |
| `conditional_first100_authorized` | `true` |
| `first100_wall_seconds` | `1200` |

The first-100 authorization is **conditional**. It applies only after:
- `freeze` succeeds on the real complete teacher and Qwen outputs;
- the funded generation review accompanies those outputs;
- both raw oracles have passed;
- the receipts are completed, the ledger terminals match and the provider is STOPPED with 0 owned containers.

This decision is not a throughput PASS, not eligibility and not G0. All 12 new synthetic fixtures pass when I run them here.

### What I checked

**Input binding (`p1_input_binding.py`)**
- Rows follow the fixed order: 8,993 procurement rows, then 500 teacher MATH 0-shot, 500 Qwen 0-shot and 500 Qwen 4-shot, for 10,493 rows in total.
- Each row must match its original request on `candidate_id`, `problem_id`, `attempt`, `seed` and `source_row_sha256`. Partial denominators are refused.
- Gold answers:
  - Training gold is the final braced box of the original solution (bc N4).
  - MATH-500 gold is the original `answer` string.
- If gold is unsupported, the whole row is excluded, kept in full and counted. It is never scored as a zero. Any excluded test row sets `unsupported_test_gold_blocks_G0`.
- Decoded stops and answer segments are taken from the oracle and are not decoded again.

**Driver (`scripts/p009_p1_driver.py`)**
- The exact code review must be present and cover the actual driver file.
- `freeze` is create-only and refuses to run again.
- The first command must start at position 0 and score exactly the first 100 rows, under a hard wall of 1,200 s that also kills child processes.
- The remaining command requires a real first-100 numerical review bound to the proposal SHA, the driver sources and the approved total wall time.
- Permanent STARTED, COMPLETED and FAILURE markers are written, and there is no retry.
- Per-pool audit samples are taken: 50 disagreements, 25 fallback rows if fallback exceeds 2%, and an outer-timeout flag above 0.5%. Unsupported-gold exclusions are attached. All adjudications are left empty.

### Notes

**N1 (schedule risk; decide BEFORE the first 100 run).** The remaining command can only be admitted if

`serial_time_scenario_seconds ≤ approved_total_wall ≤ 21,600`

where the scenario is `elapsed + 1.2 × (max_pair_seconds × R + 300)` and R is the number of remaining distinct pairs. With roughly 10,493 rows, R is plausibly about 6,000 to 9,000. The break-even for the slowest pair is therefore only about **2.0 to 2.9 s**:

| Slowest pair in the first 100 | Scenario |
|---|---|
| One 8 s outer timeout | about 16 to 24 h |
| 3 s | already above 6 h |

Math-verify on MATH answers often has a few slow parses. Because the code hard-codes `serial ≤ approved`, **no reviewer could approve the remainder under such an outcome without a code change.** Any change made after seeing the first-100 data would be a post-result amendment.

I recommend fixing the scenario rule **now, before any first-100 exposure**. Two options:
- **(a) Split the scenario:** count outer timeouts at 8 s times the observed timeout fraction times R, and add the maximum of the non-timeout pairs times R.
- **(b) Raise the local wall:** local CPU time costs no money, so a larger value than 21,600 s is cheap.

Either choice needs Codex or the owner to decide it. I am not imposing one.

**N2 (S1 length check).** The driver correctly keeps the exact Stage 1 rule, *sum of selected 3,200 targets ≤ 2,097,148*, and does not replace it with an average-length proxy. My 655-token figure (be N1) was only an early warning signal and is not a gate.

**N3 (procurement order and caching).** The cache reuses only identical (gold, answer) pairs. Repeated attempts on the same problem with the same boxed answer are scored once and reused for each row, which is correct. The first-100 forecast correctly counts only new pairs.

## B. `p009-stage0-generation-result-publication-r1`

| Field | Value |
|---|---|
| Scope | `p009-stage0-generation-result-publication-code` |
| Target | `b679dd7dc5e889d9e95d718f7f2fd5b2a664c279` |
| Manifest | `da52a35f8db6ac0f2b019b4880c1eb3cd48c03f7ad587c25a28c75d48ff43717`; matches |
| `source_sha256` | `708d426fc1097e00e5f8a56b5daa6441c87c25c7eb62b3cf1477fb8d6f94ab26` (`PUBLICATION_SOURCE.py`, recomputed) |

### Decision: PASS

What I checked:
- Publication works per slot only, and its destination is create-only.
- Before publishing, it requires:
  - a matching exact code review;
  - `validate_release` on the original intent;
  - a passing oracle for this exact run and spec, with full rosters and 0 technical unknowns for each dataset;
  - receipt status `completed` and matching dataset counts;
  - matching artifact digest, ledger and closeout SHAs;
  - providers equal to the four P0 apps plus this slot's app, all STOPPED with 0 owned containers;
  - unchanged sources.
- Archive members are written with fixed metadata and read back against the original manifest.
- The oracle is stored gzip-compressed and verified byte for byte after decompression.
- Projections are explicit. Private intent and packaging files are omitted, but their SHAs are bound.
- `RESULTS.json` marks P1 as not performed, G0 as not admitted and the actual-result review as pending.
- No model, tokenizer, scorer or cloud call is made.

## Science-signal check

No outcome yet. Generation upload was still in progress as of 17:35 PDT. **P1 N1 is the most important open item**: if not resolved before the first 100 rows are scored, it could stall MATH scoring and therefore S1's G0.

# Audit 20261014bp: P009 P1 durable MATH scoring journal (code only)

- **Request:** `p009-math-p1-durable-journal-r1`
- **Target:** `542b453f5004f8c0e8ec16107bb65cf26e9e6558`
- **Manifest:** `reports/p009_20261014/math_journal_preflight_v1/MANIFEST.json`, SHA-256 `819ae59d67753c06592a2fc3944b5db3641c4533f089b1226f319dedf6593e09`. This matches the request.
- **Source files:** all five hashes match `SOURCE_BINDING.json`:

  | File | SHA-256 prefix |
  |---|---|
  | `math_scoring.py` | `d310d7e6…` |
  | `math_scoring_journal.py` | `c7d86daf…` |
  | `math_scoring_pool.py` | `c3ac26aa…` |
  | `requirements_math.txt` | `594eec6e…` |
  | `tests/test_p009_math_scoring_journal.py` | `8c524268…` |

- **Unchanged files:** `math_scoring.py`, `math_scoring_pool.py` and `requirements_math.txt` have an **empty diff** against the pool target `0b714161` that I accepted in 20261014bf. The scalar rules, the two workers, the 8 s outer timeout and the valid-False semantics are therefore unchanged.

## Verdict

**PASS-WITH-NOTES** (code only).

This verdict admits no real corpus, no P1 run and no student selection. The 11 new tests pass when I run them here (`PYTHONPATH=.:tests`); they use a fake pool. I did not execute math-verify; that limitation is unchanged from 20261014bc and 20261014bf.

## Checked

### Basis and locking

- The ordered rows and the caller's binding are frozen once in `BASIS.json`.
- On reopen, a changed basis is refused.
- If the folder holds anything besides `LOCK` and no basis exists, the journal is refused.
- The lock is `flock(LOCK_EX|LOCK_NB)` and is released on close.

### Create-only writes

- Every record is written with `open('xb')` followed by fsync of the file and its directory.
- A torn file, or a chunk without `COMPLETED.json` and `TIMING.json`, blocks all continuation.
- Restore only accepts chunks that are complete and contiguous, with the intent, result and row-ID binding intact.
- The pair cache must equal *exactly* the pairs of the committed rows.
- Attempt indices must run contiguously from 0 to n−1.
- Every row's `symbolic_attempt` must be a committed observation.

### No rescoring

- Cached pairs are never sent again.
- `pool._finish` raises if a pair would receive a second attempt.

### Failure path

- On a caught error, the confirmed pairs are saved.
- `FAILED.json` lists the unconfirmed pair intents and sets `retry_authorized=false`.
- The session closes.
- Any later reopen is blocked, because the chunk is incomplete.

### First-100 boundary

- Chunk 0 must be exactly `min(100, n)` rows.
- Every later chunk requires a real timing review in scope `p009-math-p1-first100-throughput`. That review must bind:
  - `basis_sha256`;
  - the first chunk's `RESULT.json` file SHA;
  - a 40-character report commit;
  - the report file SHA.

### Audit samples

- Up to 50 symbolic/string disagreements are drawn by fixed hash.
- Up to 25 fallback rows are drawn when fallback exceeds 2% of boxed rows (this addresses 20261014bc N2).
- Outer timeouts above 0.5% of unique pairs are flagged.
- Unbraced boxes are counted (this addresses 20261014bc N3).
- Adjudications stay `null`, and no labels change.

## Notes

- **N1: the first-100 forecast is dominated by its slowest pair (schedule risk).** The scenario is `elapsed + 1.2 × (max pair seconds × remaining distinct pairs + 300)`. I probed it with about 5,900 remaining pairs:
  - one 8 s outer timeout in the first 100 gives **about 15.8 h**;
  - a slowest pair of 0.5 s gives **about 1.1 h**.

  One pathological pair could therefore block P1 tonight on paper. This is conservative rather than a bug, and the scenario does not itself admit or refuse anything. For the first-100 throughput review I suggest also reporting a split scenario, so the decision is not driven by a single outlier: the outer-timeout share × 8 s, plus the maximum of the non-timeout pairs.
- **N2: unsupported gold is not counted here.** `validate_rows` rejects empty gold, so `structurally_unsupported_gold_rows=0` is true by construction. The excluded count (20261014bc N4) must come from the P2/P1 driver that builds the rows, and be reported with P2.
- **N3: a caught failure ends the journal.** There is no reconciliation or retry path, by design. Any recovery needs a new reviewed tool.
- **N4: timing semantics.** A pair's `elapsed_seconds` runs from send to receive on its worker. Worker startup is recorded separately in `startup_observations`, and the chunk interval excludes the final timing write, as disclosed.

## Science-signal check

No outcome yet: no actual teacher rows have been scored. The only signal is schedule risk (N1). Once real first-100 timings exist, the forecast should be checked before tonight's G0 plan relies on P1.

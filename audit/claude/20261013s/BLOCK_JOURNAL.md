# Claude audit 20261013s — p008-student-block-journal-r3 @ c206f0dc: **PASS-WITH-NOTES (code only)**

Audited 2026-10-13 ~11:45 UTC. This verdict does not admit any numbers: N2 stays OPEN and needs the T1-first numeric gate below.

## Correction to 20261013r
My earlier text said that "4/8" P007B-scaled T8 estimates exceeded 9,560 s. **The correct count is 3/8** (12,764 / 11,684 / 16,078); depth p4 s23 is 9,235 s, which is under the cap. The table I published was right; the count in the prose was my error. The HIGH conclusion still holds.

## Answers
1. **Provenance.** YES.
   - `Journal.begin(block)` runs a full fresh check and then the atomic unit put of all 16 exact step intents. This happens before any per-step local intent or compute.
   - Per-step intent and completion rows are dumped locally, and `end()` requires each completion to match its own intent field by field.
   - The block acknowledgement binds the ordered intent and completion SHAs. Any failure poisons the journal, and there is no resume branch.
   - Probe (`bj_probe.py`): a fence raised mid-block → the remaining in-block updates run without a remote check (by design) → the acknowledgement check fails → the remote ledger shows `unit/0017_0032` with no `done`, so the block is unknown and not counted. Later updates are refused.
2. **Fencing latency of ≤16 updates.** ACCEPTED.
   - Every work unit already runs inside a fixed per-slot reservation, with no retry and no claim reset. A fence that is observed late therefore costs at most ~16 × (2–6) s of GPU time inside the same reservation and changes no science.
   - The local deadline is checked before and after every update and after the boundary, and the hard timer is unchanged.
   - Test: 256 updates use exactly 32 remote checks and ≥512 deadline checks, so T8 needs 256 checks instead of 2,131.
3. **Science unchanged.** YES.
   - Independent AST check: the 28 leaf statements of `run()` in block_student_runtime.py, with the two hook lines removed, are identical to student_runtime.py.
   - The forensic steps (1024, 2048) are block-end steps, so checkpoints run after the acknowledgement.
   - `verify_training_blocks` rejected each of these in my probe: a tampered local loss (completions SHA), a missing step intent, and an extra remote `done` key.
   - The base role keeps the per-batch evaluation journal.
   - Shipped tests: 31/31 OK locally (block journal, parallel guard, student binding).
4. **Numeric gate.** Codex's scenarios under the block journal give point estimates of 6,489–9,539 s (all under the cap). **With the 20% margin, 3/8 still exceed it** (9,729 / 10,835 / 11,447), and the per-step fsync cost has not been measured. The block journal turns "likely fails" into "marginal". It does not close N2.

## Proposed T8 numeric criterion (Q4) — timing only; no endpoint scores read; no extra model job
Dispatch all T1 students and the base first under the 27-file source. From each completed T1 run i, take:
- `F_i` = worker wall − (first→last update mtime span): setup, eval and evidence.
- `c_i` = Σ optimizer `seconds` / Σ processed_tokens, giving compute per processed token.
- `m_i` = (span − Σ optimizer seconds) / 255: non-compute seconds per update, including local writes and amortized block boundaries. Report it next to `block_boundary_seconds` and `local_step_write_seconds`.

For each T8 slot j, use its exact joint plan: `P_j` = Σ processed tokens over the 2048 updates, plus `K` = 2 × the measured T1 checkpoint-save seconds for the forensic saves. Then:

`T8_hat_j = max_i F_i + P_j · max_i c_i + 2047 · max_i m_i + K`

**Admit T8 only if 1.2 × max_j T8_hat_j ≤ 9,560 − 30.** Use the max over hosts, not the mean, because P007B showed 0.5–4.5 s per gap depending on the host.

If the criterion fails, there is no automatic remedy. The owner chooses between raising the caps with new budget and recording T8 as pending or out of scope. The rule is about timing only and is fixed before any output exists, so it is outcome-blind.

Order change: T1 and base first, then T8. This changes dispatch priority only; science is unchanged. Timeline: if the pools close at 12:23 UTC, G1 runs to ~13:30, T1 to ~15:00, and T8 (≈2.7 h) to ~18:00 UTC (11:00 PDT). That fits inside the 21:00 PDT freeze and the 02:00 UTC cutoff, but only if the D2 pool completes or the repair succeeds.

## Notes
- N-s1. `m_i` folds in the per-step fsync dumps, which stay at 2 per update. If T1 shows `local_step_write_seconds/256` is large on the volume, buffering to local disk with a single manifest at block end is the next lever. That would need another review; do not change it now.
- N-s2. D2 repair: I accept Codex's choice to keep the strict zero-ambiguous-regeneration rule. Raw→scored recovery stays allowed under explicit reconciliation.

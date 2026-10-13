# Claude audit 20261013q — two scoped amendments + pool-timeout risk

Audited at origin/codex/icml-acl-2027 = 73d99e7f (2026-10-13 ~10:50 UTC).
This covers two pending requests. Neither verdict covers numeric G1, joint plans, or student admission.

## 1. p008-final-cpu-margin-amendment-r2 @ 391dedbf — **PASS** (code only)

Diff reviewed: e3d9b196..391dedbf in audit_binding.py, audit_bundle.py, modal_audit.py and tests.
- `check_soft_deadline(now, stop)` raises when `now >= stop-120`. The hard `os._exit` timer is unchanged. The comment correctly says that a blocking I/O or torch call can still hit the hard timer, which records an interruption rather than a soft failure.
- New `check()` calls run after each `copy_checked`, after unpack+verify, and before and after each `ck.load`. These are read-only and only make the audit stricter.
- Timing fields were added to the return dict. They are diagnostic only: there is no change to pass/fail logic and no new remote writes.
- Range 391dedbf..41c26651 touches no audit files, so this verdict also holds at 41c26651.
- `tests.test_p008_audit_binding` passes locally (unittest, CPU).

## 2. p008-student-activecheck-amendment-r2 @ 41c26651 — **PASS-WITH-NOTES** (code only; supersedes the f944723e student-code target only)

Reviewed: parallel_guard.py (new), the modal_students.py diff, the 25-file SOURCES roster (+parallel_guard.py), and guard.py `_owned/_registered/check_active`.

Answers to the three questions:
1. **Freshness, fencing and equivalence.** YES.
   - The key set is campaign + claim + attempt + terminal + reconciliation for every slot. That is exactly what the original `check_active` reads via `_registered → _owned → check_active`.
   - `_ReadSet.get` raises on any unfetched key, so a future validator change that reads a new key fails closed instead of silently passing.
   - The validator is a shallow `copy(g)` with only `.store` swapped. `plan_hash` stays the original, and `identity_hash(g.plan)` is checked first.
   - There is no caching across checks: every call builds a new `records` dict.
   - A missing remote key returns `None`, the same as the original `store.get(key)`.
2. **Timeout, clock and readers.** YES.
   - There are at most 8 readers. Each read set is limited to 15 s, enforced per future and again after validation.
   - `now_epoch` is taken AFTER the reads, which is stricter than the original call-time clock.
   - A post-read soft deadline was added in modal_students.
   - Any exception sets `failed=True`, and reuse is then refused.
   - `close()` uses `shutdown(wait=False, cancel_futures=True)`, so a stalled SDK thread is bounded only by the original hard timer. That is acceptable.
3. **Admission.** No live pool source was changed. The original caps and deadline are kept, and there is still no incomplete-pool student admission (validate_binding unchanged).

Independent probe (`pg_probe.py`, run on the 41c26651 tree), comparing the original and parallel checkers under the same mutation:

| mutation | original | parallel |
|---|---|---|
| none | ok | ok |
| terminal inserted | GuardError | GuardError |
| claim deleted | GuardError | GuardError |
| campaign record changed | GuardError | GuardError |
| in-memory plan mutated | GuardError | GuardError |

Further probe results:
- **Fencing:** reconciliation with this run as parent → fenced.
- **Failure handling:** a transport exception → fail-closed with `failed=True`. A slow store (0.3 s per read, 1 reader, 0.5 s budget) → TimeoutError, and reuse is then refused.
- **Clock:** an after-read clock past the claim deadline → GuardError.
- **Tests:** the shipped tests `tests.test_p008_parallel_guard` + `tests.test_p008_audit_binding` give 18/18 OK locally.

Notes. These do not block the code PASS, but **N2 must be closed at the joint-plan gate**.
- **N1 (thread safety).** Concurrent `modal.Dict.get` from 8 threads is supported only by the empirical diagnostic (identical records, 0.50/1.42 s). No API contract was cited. Fail-closed behaviour makes a failure safe, but it would cost a slot.
- **N2 (student wall time).** For P008 students, `check()` runs once per optimizer update (`Journal.begin` in `rt.train`) and once per eval batch (83). It does not run per row: P008 never calls `nll`.
  - A T8 student therefore makes ≈2,131 checks, which at the measured 0.50–1.42 s is +1,070–3,030 s.
  - The 9,560 s T8 cap was derived from P007B's 423.8 s per 256 updates and 3,976 s residual, ×1.2. P007B already paid its own (fewer-key, sequential) per-update reads, so whether this is additive is **not known**.
  - Before dispatching any T8 student, please show from P007B journal timestamps (or one short calibration) the old per-update read cost versus the new parallel cost.
  - Worst case 1.66×2048×1.2 + 3,030 + 1.2×3,976 ≈ 11,850 s > 9,560 s. If the margin does not hold, a **pre-declared check cadence** (full read set every k updates plus a local deadline check on every update) is a semantic change. It would need its own review, and it must not be patched in after a student starts.
- **N3.** `guard_read_metrics.json` is written on both the success and failure paths, which is good. Please include it in the G3 evidence so that N2 can be checked after the fact.

## 3. HIGH — pool timeout would block all students

This uses only Codex's committed observations (POOL_PROGRESS_OBSERVATION, TIMING_RISK). It involves no outcomes.

- The pools started ≈09:30 UTC with a 10,800 s cap, so the soft stop is ≈12:30 UTC (05:30 PDT).
- At ≈10:26 UTC: D1 b8_p0 was at 32.9% / 32.0% after ~88 rounds; D2 b8_p0 was at 15.5% / 15.4%.
- **Overhead model (hypothesis).** In `pool_runtime.run`, every round does 1 + (#active wallets) + (#physical batches) `journal.begin` calls. Each one is a 26-read guard check plus a put, followed by several `volume.commit`s.
  - With 8 wallets: D2 ≈ 8×7.1 s + 10 s gen ≈ 67 s against the observed 72–75 s. D1 ≈ 8×3.4 + 10 ≈ 37 s against the observed ≈38 s.
  - If this model holds, rounds speed up as wallets retire (b1 at ~92–94% of cap, D1 b8_p4 breadth at 98%).
  - My rough estimate is that D1 likely finishes and **D2 is roughly a coin flip** by 12:30 UTC. Please compute this from volume mtimes per active-wallet count, rather than trusting my estimate.
- validate_binding requires both pool terminals = completed, so a D2 timeout blocks ALL 18 students, including D1's.

**Recommendation.** Decide this BEFORE the timer fires and pre-register it now, blind to any student outcome. It needs owner authorization, a separate reconciliation admission, and my review.

- **R-a (no new teacher calls).** Reconcile the timed-out pool's saved cache. Each wallet's decisions depend only on its history, and the cap matters only at the stop rule, so a lower-B wallet is exactly the prefix of the B8 history up to its own cap.
  - Admit only wallets whose full lower-B prefix lies inside the saved, verified cache: B1 is complete in both draws, and possibly B2/B4.
  - The precise rule is: replay the lower-B wallet from the cache; it is admissible only if the replay reaches its stop rule without a missing key.
  - Students for the uncovered cells are dropped. This is reported as scope loss, not as a null result.
- **R-b (bounded new spend).** Run a resume-only continuation pool for D2 with the cache pre-loaded. It would use the same seeds (CRN keyed by draw/problem/attempt), so outputs are reproducible and duplicates are checkable. A fixed-cap continuation might cost ≈$13–15 of H100 time.
  - It needs its own code review (cache import, no regeneration of existing keys) and must fit the $250 stage cap: $237.68 reserved, with actual spend likely lower.
  - Using parallel reads for pool checks would cut round time ~3–5×, but that is a new pool source and needs review.
- In either case, P007B remains the frozen midpoint result. P008 is presented as an exploratory update only if it passes the gates by Wed 18:00 PDT.

I have not changed or approved any recovery. This is a decision for the owner.

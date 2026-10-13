# Claude audit 20261013x — p008-d2-continuation-runtime-g0-r1 @ a385fb38: **PASS-WITH-NOTES (exact child spec; one dispatch)**

Audited 2026-10-13 17:20 UTC, under time pressure. The latest full-window dispatch is 17:48:20 UTC.

**Owner authority.** `OWNER_D2_CONTINUATION_13PDT.json` records a direct owner reply in Codex's chat. That reply reached Codex, not me. It retains 2 draws, remaining-only work, a child deadline of 20:00 UTC, 7,200 s, +$12 (total $249.68), with review required. I treat this as the owner's decision as Codex recorded it, and I did not see it myself.

## Q1. Binding — YES
- `validate_continuation_binding` fixes the following:
  - campaign, run, deadline 1791921600 (= 20:00 UTC), and the 1,200¢ single slot;
  - draw 2, B8, 16,384 attempts and 7,200 s;
  - plan, config, spec and source digests;
  - accounting of 24,968 / 23,768 / 25,000 / 45,000 / 5,000;
  - the exact probe policy;
  - the owner fields;
  - upload/readback gates and provider release;
  - the reconciliation counts (3,992 / 146 / 1,190,193, with 0 unknown and 0 pending).
- It also checks the exact six parent/D1 dependency keys against claim, plan and intent digests, and that D1's terminal is `completed`.
- Cost check: ceil(7,900 s × $4.3936/h) = 965¢, within the 1,200¢ reservation.
- The worker re-hashes all 30 sources and re-reads the parent records before `admit`.

## Q2. Fences, timers and probe — YES, with one material note
- `ContinuationActiveCheck` reads a fresh 11-key set: 5 child keys (campaign, claim, attempt, terminal, reconciliation) and the 6 parent/D1 keys.
  - It rejects overlapping key sets and requires every parent record to be byte-equal on every check.
  - It then runs the original `RunGuard.check_active`, with a fail-closed reuse lock. This is the reviewed `ParallelActiveCheck` pattern.
- **W1 is satisfied.** The `Journal` used by `pool_continuation_runtime.run` receives this `check`.
- Timers: the hard timer is set at worker entry, at min(start+7,200, 20:00 UTC). It is refused if start+7,200 is past the deadline. The function timeout is 7,300 s, and the soft stop is −30 s.
- Dispatch: `main()` runs only if the committed source equals the remote branch head. It also requires:
  - the spec to be published;
  - no prior child-campaign keys and no remote run directory;
  - both original apps stopped, with zero containers;
  - a fresh 7,900 s window;
  - a single `spawn` with retries=0 and max_containers=1.
- **N1 (material).** `probe_forecast` compares 1.2×(136×per_round + 300) against the *remaining* soft window, which is measured after setup. Setup time is therefore counted twice: once inside the 300 s allowance, which the ×1.2 turns into 360 s, and once by being subtracted from the remaining window.
  - On a best-case host (read time ≤ 1.415 s) the prediction is 7,069.86 s. The gate passes **only if pre-probe elapsed time is ≤ 100.1 s**, which I checked numerically: it passes at 100 s and fails at 120 s.
  - Pre-probe elapsed covers source hashing, claim reads, admit, `volume.reload`, input, prefix and **teacher-asset hash verification**, torch import, and the three checks.
  - If the parent's own evidence shows that this phase normally takes more than 100 s, the dispatch will abort before model load almost certainly. It would then fail safe, at a cost of roughly $0.2–0.5, and leave D2 pending.
  - **Before dispatch, Codex should read the parent D2's start→`environment.json` interval from the Volume and decide.** The options are (a) dispatch as is, or (b) do not dispatch. I do **not** approve changing the formula in the remaining minutes. The conservative rule stands, and failing safe is acceptable.

## Q3. Merged G1 — scope accepted
`audit_p008_continuation.py` is parse-only. I will run my own merged oracle over the parent's raw outputs plus the child's raw outputs (child batches from 146 onward, with each origin decoded exactly once). That oracle uses `g1_pool.py`, extended to two directories. The parent stays `failed`, and the child is only `completed`.

## Q4. Disclosure — accurate
7,069.86 s is a proxy, not a bound. There are zero retries. Students, common T, N2 and the final CPU stay separate gates.

Tests: 15/15 `test_p008_continuation_worker` pass locally (run with `PYTHONPATH=.:tests`).

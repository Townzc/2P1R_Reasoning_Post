# Claude audit 20261013z (part 2) — p008-student-eight-gpu-code-r1 @ da4a404f: **PASS-WITH-NOTES (code only)**

This is a code review only: no student is admitted, and nothing here confirms the GPU quota.

- **Q1. Capacity guard: YES.**
  - **What it counts:** `occupied_capacity` counts every pending dispatch that has no terminal, even before a claim exists.
  - **How it counts:** each pending run counts as max(1, its live containers). Every container whose app is not one of the pending runs counts as one more.
  - **Ambiguity handling:** duplicate or empty run, app or container IDs, and containers with no app ID, are all rejected.
  - **Limit:** `require_capacity` refuses when the count is 8 or more, so at most 8 run at once.
  - **Probes:** 7 pending runs with 7 containers → 7, so dispatch is allowed. 7 pending runs plus 1 foreign container → 8, so it is refused. 7 pending runs not yet started → 7.
  - **Locking:** a non-blocking `flock` serializes the capacity read, the intent write and the spawn. A second local dispatcher fails immediately instead of queueing.
  - **Window:** a fresh check `now + max_seconds + 700 ≤ deadline` runs just before `mkdir`.
- **Q2. Owner, quota and science bindings: YES.**
  - `eight_gpu_student_binding` runs the full lineage binding that I passed at 20261013x, then `validate_quota`.
  - `validate_quota` requires an exact direct-owner record by digest, and a confirmed H100 quota that is at least 8, from the same workspace and backed by an evidence hash.
  - Compared with `modal_students_lineage.py`, only these change: the binding import, the app name, `max_containers` going from 4 to 8, and the locked dispatch block. Dose, seed, block journal, caps, reservations, the T1-first roster and N2 are all unchanged.
  - 10/10 tests pass locally.
- **Q3: YES.** `QUOTA_STATUS.json` correctly records the quota as **not confirmed**. The reason given is that the CLI does not expose the workspace H100 quota and the browser is signed into a different workspace. No quota is inferred.

## Notes
- **E8-1 (owner action, blocking for 8-way dispatch).** Someone has to confirm the H100 concurrency limit of the **experiment** Modal workspace, from that workspace's own settings or billing page. Until that happens, dispatch must stay at the reviewed 4-way entry or fail closed.
- **E8-2.** Every check uses `plan['deadline_epoch']`, which is the main campaign's 02:00 UTC deadline. The owner relaxed the student stop at 10:43 PDT (#13 comment 6151713942), so a new student campaign/plan deadline is still needed. That needs its own review, and it is a separate change from this code.
- **E8-3.** A pending run that crashes without writing a terminal keeps holding its slot until it is reconciled. This is conservative, and it is correct.

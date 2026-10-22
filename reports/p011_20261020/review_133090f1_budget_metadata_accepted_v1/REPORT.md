# Async CR: paid-budget schema continuation (09f3eaaa, request 0697cf2e) — **PASS, no stop**

Reviewer: Claude, 2026-10-22 ~07:40 UTC.

1. **Failure and snapshots preserved.** The original KeyError `'State'` failure is retained, and the four saved provider reads are reused without re-querying.
2. **Fail-closed alias handling.** `shared_slots` accepts `state`/`State` and `tasks`/`Tasks`. It raises if both spellings are present with different values, or if a field is missing. Any app that is not stopped counts as max(1, tasks) slots, and the total is never below the container count. The two training entries and the forced relaunch are added conservatively, with a check that the sum stays at 8 or below.
3. **Arithmetic is unchanged.**
   - Each cell: worker time 28,684 s at $4.9072/h. Compute upper bound is $39.999, plus $5 noncompute, for $44.999 against the $45 cap. The pair upper bound is $89.999 against $90.
   - Forced-answer: the failed first attempt's upper bound is $0.729, taken as the maximum of the reported cost and the wrapper time plus 60 s at the higher rate. The second attempt's upper bound is $8.270, plus $3.00 noncompute, for $11.9995 against $12. The worker window is 6,114 s (about 1.7 h), and the epoch upper bound is $132.04 against $150.
   - The snapshot must be less than 3,600 s old. **The observed epoch is about 07:07 UTC, so dispatch has to start by about 08:07 UTC.** Otherwise a fresh read is required, which is correct fail-closed behaviour.
4. **Boundaries unchanged.** The runtime (86 files) and forced (38 files) sources, the A2 approvals, the single-attempt rule, the fences and the caps are all unchanged.

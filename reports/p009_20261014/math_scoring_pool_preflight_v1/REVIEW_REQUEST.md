# Exact persistent scorer code review

Request `p009-math-scorer-persistent-pool-r1`.
Scope `p009-math-scorer-persistent-pool-code`.

Please bind the exact four source files and packet manifest, and review:

1. Unchanged scalar semantics and dependency versions; process main-thread
   alarms and parent timeout/kill; readiness cannot suspend an active deadline.
2. Exact-pair reuse including cached failures, no retry of original pairs,
   complete row identity/order/stop provenance, no correctness-based selection.
3. Technical startup/protocol/environment aborts, bounded cleanup, process cap.
4. Eight new synthetic fixtures; actual first-100 timing, durable driver,
   full fallback reporting and required adjudications remain unperformed.

This review blocks only use of the new local pool in future P1. It does not
block the original running P0, admit a teacher/student model, or replace P1's
actual-output audit. No external message is sent; request is in INDEX only.

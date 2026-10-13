# Claude audit 20261013r — N2 timing (1832a6e6) and conditional D2 repair blueprint (bd633a9b)

Audited at origin/codex/icml-acl-2027 = e187cda6, 2026-10-13 ~11:20 UTC. Both requests are reviews only, and neither verdict admits anything.

## A. p008-journal-timing-N2-r1 @ 1832a6e6 — Q1 YES, Q2 YES, plus a **HIGH** finding: the T8 cap is likely infeasible as frozen

Q1. Agreed. The compute-subtracted gaps include journal puts, file dumps and checkpoint writes, so they cannot all be credited as guard reads.

Q2. Agreed: N2 stays OPEN. Codex's scenarios are **not conservative**, though, because they keep the old per-update metadata at the 256-update scale. The direct empirical check is to scale P007B's own update stream. I computed this independently from `old_journal_timing/SUMMARY.json`:

`T8_est = worker_wall − stream_256 + (stream_256 / 255) × 2048`

That is, every per-update cost (compute, the 13 sequential reads, unit/done puts, dumps, and the checkpoints at P007B's cadence) is scaled 8×. Eval, setup and evidence are kept fixed.

| P007B run | wall (s) | update stream (s) | s/update | median gap | T8 estimate (s) |
|---|---|---|---|---|---|
| breadth p0 s17 | 3956 | 615 | 2.41 | 2 | 8,281 |
| breadth p0 s23 | 3488 | 716 | 2.81 | 3 | 8,523 |
| breadth p4 s17 | 5247 | 1069 | 4.19 | 4 | **12,764** |
| breadth p4 s23 | 5320 | 905 | 3.55 | 3 | **11,684** |
| depth p0 s17 | 4257 | 599 | 2.35 | 2 | 8,469 |
| depth p0 s23 | 3658 | 524 | 2.05 | 2 | 7,343 |
| depth p4 s17 | 5235 | 1542 | 6.05 | 6 | **16,078** |
| depth p4 s23 | 4039 | 739 | 2.90 | 3 | 9,235 |

- **The fixed cap is 9,560 s. Four of the eight estimates exceed it, before any ×1.2 margin.** The mean is 10,297 s.
- The gaps are steady (median 2–6 s per update; only a few checkpoint spikes of 16–21 s), so this is per-update metadata latency that varies by host, not checkpoint cost.
- P008 T8 uses the same per-update size (256×B updates for 524,287×B targets), so per-update compute is unchanged.
- **Caveats.**
  - P008 reads 26 keys with 8 parallel readers (0.5–1.4 s), against P007B's 13 sequential reads, so the read part may shrink.
  - The unit/done puts and dumps per update are unchanged.
  - Mtime resolution is one second.
  - The table above is an estimate, not a forecast with an error bound. Even so, it is direct evidence that dispatching T8 students under the frozen 9,560 s cap is likely to waste ≈$12.5 per failed slot, across 8 T8 slots.

Q3: evidence I need before the numerical gate. Choose ONE, pre-declared and blind to all outcomes:
- **(i) A pre-declared block journal (my recommendation, cheapest).** T8/T1 students would journal and guard-check per **16-update block**: begin(block) runs the full fresh 26-key check and puts the unit; done(block) is put at block end. Per-update records are still dumped to the evidence dir and bound in the manifest. Checkpoints, schedule, LRs and the dose stay identical.
  - Because students already have **no automatic retry or claim reset**, the per-update exactly-once ledger serves forensics only. Block granularity loses none of the scientific guarantees: a fenced or reconciled run can overrun by at most 15 updates of GPU time inside its own reservation.
  - It needs a code change and a new review, then a short GPU-free CPU test. It must not be applied to a running student.
- **(ii) Raise the T8 caps.** Each extra 1,000 s costs ≈$1.22 per slot; 16,000 s caps for 8 slots ≈ +$63. That breaks the $250 stage cap, so it needs a new owner budget decision.
- **(iii) Drop the T8 cells.** That is a scope change.

The T1 caps (6,001 s) are consistent with P007B's walls (3,488–5,320 s), but the margin on the slow host is thin: 5,320 s is 89% of the cap.

## B. p008-conditional-pool-repair-blueprint-r1 @ bd633a9b — PASS-WITH-NOTES (blueprint only; no run admitted)

Q1 YES. The blueprint keeps the same candidate IDs, seeds, order, prompt and checker, the cumulative cap of 16,384 parent+child attempts, unchanged wallet caps, full charging of paid work, and distinct claims. That preserves the original B1/B8 scope.

Q2 YES on the arithmetic:
- $237.68 + $12 = $249.68, within the $250 stage cap.
- A 7,200 s worker plus 700 s startup at $4.3936/h ≈ $9.64, which is under $12.
- The child stops at 15:00 UTC, well before the 02:00 UTC global cutoff.

Notes and additional requirements (Q3):

1. **Feasibility test before any dispatch.** Reconcile the remaining D2 rounds per active-wallet count, then multiply by the observed parent round time on that host.
   - If the forecast exceeds 7,200 s, **do not launch**, so we don't pay for a second incomplete pool.
   - At the measured 72–75 s rounds, the child is very likely too slow unless it uses the already-reviewed ParallelActiveCheck for its pool checks. If it does, that must be declared in the child source review.
2. **Soft vs hard stop.** The parent's soft TimeoutError is raised only at `journal.begin`/`check` boundaries. If a volume commit or a generate call straddles the last 30 s, `os._exit(124)` can leave a physical intent with no raw file.
   - Under the blueprint's zero-unknown rule, that bars repair. I think that is stricter than science requires. A request that never returned output was never observed by anyone, so regenerating it with the **same seed**, charging both attempts, involves no selection on outcomes.
   - A raw file without a scored file must be rebuilt from raw, not regenerated.
   - I recommend predeclaring this distinction now. If Codex prefers to keep the strict rule, I accept that too. Either way, the decision must be made **before** the parent stops.
3. **Pending wallet intents.** If the stop lands mid-round, the wallet intents for that round are already published. The child must resume exactly those pending actions, not re-propose them, and the reconciliation must show that every pending action equals the deterministic `propose()` replay from history.
4. **D1 also incomplete.** The blueprint does not cover this case, and $12.32 cannot fund two children. If D1 times out too, the choice goes to the owner: approve extra budget, or follow scope-change proposals that are reported as such.
5. **Timeline check.** The child ends ≤15:00 UTC (08:00 PDT). After that, G1 for D2, the joint plan, and students (T8 up to ~3 h or more, see A) must finish before 02:00 UTC and the 21:00 PDT freeze. This is feasible only if section A is resolved by then.

Current state from STATUS_0410: both pools are alive. At 10:51 UTC, D1 had 4,266 physical / 9,664 virtual attempts and D2 had 2,138 / 6,112. Soft stops are 12:23:11 (D1) and 12:24:22 (D2) UTC. Codex correctly flagged my "coin flip" as an unaudited heuristic, which I accept.

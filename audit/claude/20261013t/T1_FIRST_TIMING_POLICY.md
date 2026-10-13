# Claude audit 20261013t — p008-t1-first-timing-policy-r1 @ 485e7410: **PASS-WITH-NOTES (policy + code; two corrections required before use)**

Audited 2026-10-13 ~12:15 UTC at 4d21d41a. `timing_gate.py` is byte-identical to the TIMING_GATE_SOURCE.py in the packet. 8/8 CPU tests pass locally.

## Answers
- **Q1. T1 and base first, with no extra calls and no score gate.** YES, but see **C1**: as written, the roster rule can deadlock.
- **Q2. Alignment and components.** YES.
  - span(first→last completion) covers 255 intervals, so subtracting optimizer seconds for steps 2..256 is correct.
  - F includes packing and commit to terminal.
  - Using max(F, base wall) is a good choice: the untrained base probably produces the longest eval outputs, so it is a natural upper proxy for endpoint generation time.
  - K = 2 × the end gap counts the two T8 forensic saves. The end gap also absorbs the last block's acknowledgement. Counting it in both F and K is acknowledged and conservative.
  - Using 2,048 rather than 2,047 is also conservative.
  - See **C2** for the compute term.
- **Q3. Fail-closed.** YES. The fields are whitelisted and contain no outcome fields; the roster is exact; non-finite or inconsistent inputs raise; `N2_closed=False` and `runtime_admission=False` always hold; and the extractor writes PROPOSAL only.
- **Accounting correction accepted.** The right comparison is 2,131 → **339** remote checks for T8 (256 training + 83 eval), not 2,131 → 256.

## Required corrections
- **C1 (roster deadlock).** `expected_t1` = "all 10 T1 students" makes D1's T8 permanently uncomputable if D2 never passes G1, because D2's 4 T1 students can then never run.
  - At 11:52 D2 b8_p0 was at 42.8/42.0%, with its soft stop at 12:24, so this is the likely case.
  - Fix: predeclare **T1 roster = every T1 slot whose draw pool has passed G1, frozen in the joint-plan gate before any T1 starts**. Also predeclare that any T1 admitted later, for example D2 after a repair, must join the maximum before any of *its draw's* T8 runs are dispatched.
  - This stays outcome-blind and adds no selection.
- **C2 (compute term).** P·c_max scales only with tokens. Part of the per-update compute is fixed per step (optimizer.step, clip, sync), so it does not shrink when a T8 plan has fewer processed tokens per update than the T1 calibration runs.
  - Use `compute_j = max(P_j·c_max, 2048·max_i(Σseconds_i/256))`.
  - This is conservative in both directions: when T8 rows are longer, the token term dominates; when they are shorter, the per-update term does.

## Notes
- N-t1. In the worst case the 10 T1 + base jobs need 3 waves on 4 GPUs (≈3 × 1–1.5 h), and the 8 T8 jobs need 2 more waves (≈2 × 2.6 h). If D2 is incomplete, D1 has 7 T1/base jobs (2 waves), then 4 T8 (1 wave). With G1-D1 done by ≈13:30 UTC, T8 would finish ≈19:30 UTC (12:30 PDT). That fits the 21:00 PDT freeze but leaves little slack, so please publish the dispatch schedule with the joint-plan gate.
- N-t2. Pool progress at 11:52: D1 b8_p0 was at 82.9/81.7%, moving ~50 points per 86 min (136 rounds × ~38 s). Wallets stop when they cannot afford another full action, which for the B1 wallets happened at ~92–94%. D1 should therefore finish near **12:13–12:21 UTC, just ahead of its 12:23 soft stop. This is very tight**: no extension, and no change if it fails.
- N-t3. If a T1 fails by timeout, that is itself evidence against T8 under fixed caps. The rule correctly refuses to compute and keeps T8 pending. No replacement host may be sampled.

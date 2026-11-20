# Audit 20261014bc — P009 candidate MATH scorer (code only)

- Request: `p009-math-scorer-code-r1`
- Target: `4c652b03f6e319c82abb095d03577af631fa2ddc`
- Packet manifest: `reports/p009_20261014/math_scorer_candidate_v1/MANIFEST.json`, SHA-256 `fe6d0849c876a2fbbd1bf015587cb4df30f4a599bbfabba1fe8ec0b6be0c2e57`
- Scope: code and contract only. This is not P1 acceptance. The 50-item real-output disagreement audit remains mandatory before any student selection.

## Verdict

**PASS-WITH-NOTES.** The contract is right: last box only, never backfilled; caps and invalid stops count as incorrect; a valid symbolic False is final; string fallback only on parse failure, tool error or timeout; a dependency mismatch is a technical error, not a wrong answer; an unparsed unequal box can never enter the natural-wrong (C) condition. The isolation and timeout design (signal alarms in a fresh process's main thread, plus an 8 s outer timer and kill) answers the threading pitfall named in the protocol.

Limitation: I read the code and the 11 retained test logs, but I could not execute `math-verify` here (no package index access). Two of the 11 tests exercise a real symbolic subprocess.

## Notes (address before P1 freezes, not before P0)

- **N1 — throughput / schedule (science-schedule risk).** `score()` spawns a new interpreter per pair. Each spawn re-imports sympy and math-verify, which I estimate at about 1–2 s.
  - Load: 8,993 teacher outputs plus about 7 × 500 MATH evaluation outputs, roughly 12,500 spawns, which is about 3.5–7 CPU-hours single-threaded.
  - The cost is CPU only, but it can push G0 past tonight.
  - Suggested fix:
    - Run a bounded pool of long-lived worker processes, each evaluating one task at a time in its own main thread, with alarms re-armed per task and a kill-and-replace on outer timeout.
    - Deduplicate identical (gold, answer) pairs.
  - This keeps the timeout semantics unchanged. Measure per-item time on the first 100 items and forecast before the full pass, applying the same rule as GPU cost forecasting.
- **N2 — audit parse failures, not only disagreements.** The P1 sample covers `compared` cases where the symbolic and string verdicts disagree. Fallback cases (`parse_failure`, `tool_error`, `symbolic_timeout`, `outer_timeout`) are scored by strict string equality, so a correct but unparsable answer becomes a false negative.
  - These affect G0 accuracies and attempt-01 eligibility.
  - Required: report fallback counts per endpoint and per teacher pool.
  - If they exceed 2% of boxed answers anywhere, also adjudicate a fixed-hash sample of up to 25 fallback items before freezing P1.
- **N3 — box variants.** `\boxed 5` (no braces) is treated as `no_box`, and so counted incorrect. This is rare in Qwen-Math output, but include its count in the P1 report. `\fbox{}` is handled.
- **N4 — gold extraction.** Training gold uses the solution's final balanced box, and an absent gold is reported as unsupported. That is good. Report the unsupported count with P2.

## Science-signal check

No outcome yet.

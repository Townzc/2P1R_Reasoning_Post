# Audit 20261014bf — P009 persistent MATH scoring pool (code only)

- Request: `p009-math-scorer-persistent-pool-r1`
- Target: `0b714161dcc23a93cc44b52f4948eae271eaeb27`
- Packet manifest: `reports/p009_20261014/math_scoring_pool_preflight_v1/MANIFEST.json`, SHA-256 `3f3acf3e236bf949bde87ab8939123d79f3b41b36a43a11626b61945f8521390` (matches the request)
- `math_scoring.py` is byte-identical to the version reviewed in 20261014bc (empty diff between `4c652b03` and `0b714161`)

## Verdict

**PASS-WITH-NOTES.** This answers N1 of 20261014bc.

- **Worker model.** At most 2 long-lived spawned workers. Each imports the pinned libraries once and runs `symbolic()` in its own main thread, so math-verify's signal alarms remain valid.
- **Timeouts and failures.**
  - The parent enforces the 8 s outer timer, then kills and joins the worker.
  - A timed-out, EOF or send-failure pair is recorded once and **never retried**. A replacement worker handles only later distinct pairs.
  - Startup and environment mismatches abort as technical errors, not scored zeros.
- **Caching and row handling.**
  - The cache key is the exact `(gold, extracted_answer)` string pair, with no new normalization.
  - Every row keeps its own ID, stop rule and attempt provenance, in input order.
  - Duplicate row IDs, unsupported gold and unknown stops fail before any work.
  - Caps, invalid stops and unboxed outputs need no symbolic task and stay incorrect.
- **Scalar rules unchanged.** Every result passes through the unchanged `decide()`: a valid False stays final, and unparsed unequal answers stay C-ineligible.

I read the code and the 8 retained fixture logs but could not execute math-verify here.

## Notes

- **N1 — timeouts under contention.** A cached outer timeout is final for that pair and is scored by strict string fallback. If P1 scoring shares the CPU with other heavy jobs, transient timeouts could inflate the fallback rate. Report outer timeouts per pool. If they exceed 0.5% of unique pairs, flag them in the P1 freeze report before any eligibility use.
- **N2 — first-100 forecast.** Agree with the packet that the first 100 real rows must be timed, with startup, attempts and unique pairs separated, and that the full pass must be forecast from them. Cache hits must not count as symbolic speed. The P1 requirements from 20261014bc N2–N4 still stand.

## Science-signal check

No outcome yet.

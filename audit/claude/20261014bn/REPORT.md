# Audit 20261014bn — P009 closed-failure metered budget settlement

- Request: `p009-closed-failure-metered-settlement-r1`
- Target: `90d6e260e8643b61bd9586114bfe24068a8b9f38`
- Manifest: `reports/p009_20261014/closed_failure_budget_settlement_v1/MANIFEST.json`, SHA-256 `2708784b3bb0bf9bea7538d6968f8c34c04770493ea295d6a6fddfd382a3bcb3` (matches the request)
- Source files:
  - `experiments/learning_regime_p009/closed_budget_settlement.py` `2742feba9f6187079e9c3307a4af181214c86a10371ac32e3c3603949667d118` (matches)
  - `tests/test_p009_closed_budget_settlement.py` `d28c29694c91c7f8c880b2fc9dc48318ca22a2f3827004564c8ab66af08f9876` (matches)
- `SETTLEMENT_PROPOSAL.json` SHA-256 `5c22d61e840475ea86edd758fe44be87c7397fc4932e0211290d8944f7aa4f37` (matches)
- Scope: budget accounting overlay only. This review does not cover scientific A2, P1/P2/P3, Stage 1, or any runtime admission.

## Verdict

**PASS-WITH-NOTES.** Once this review is accepted, the 374¢ release may be used by future Stage 0 budget gates, subject to N1. The remainder runtime at `5c522257` keeps its own conservative 500¢ check, unchanged.

## Independent recomputation

I extracted the target with `git archive` and ran `build_settlement` on the packet's own `METER_SNAPSHOTS_PROJECTED.json`, `CLOSED_RUNS.json` and `PROVIDER_PROJECTED.json`, with `now` set to the proposal's prepared time. **Every field equals `SETTLEMENT_PROPOSAL.json`, with zero differences.** I also recomputed the numbers by hand:

| App | Gross meter | ⌈cents⌉ | Allowance max(50, ⌈20%⌉) | Accounted | Original | Released |
|---|---|---|---|---|---|---|
| ap-laRv7V5oQp7J6kKZdPolnd (eager) | $0.12296933 | 13 | 50 | 63 | 248 | 185 |
| ap-FkcENORfl85RlCVEvBibVl (fast) | $0.12490961 | 13 | 50 | 63 | 252 | 189 |
| **Total** | | | | **126** | **500** | **374** |

Stage 0 now stands at 126 + 252 (full remainder reservation) = **378¢ committed and 622¢ remaining** of 1,000¢. ✓

- The `claim_sha256` in both terminals equals `digest(claim)`, and the terminal digests equal the proposal (`0407a407…` and `4f771652…`).
- All 8 new tests pass when I run them here.

## Rule checks

| Rule | Result |
|---|---|
| Rounding | Decimal input from strings, `ROUND_CEILING` to cents; binary floats, NaN, Inf and negatives are refused ✓ |
| Allowance | `max(50, ceil(20% × rounded cents))`, applied to each app once ✓ |
| Freshness | The newest snapshot must be ≤ 3,600 s old and none may be from the future. Both the terminal and the provider `stopped_at` must be ≥ 900 s before the snapshot. Here the stop ages are 5,961 s and 2,186 s ✓ |
| Identity | A unique app roster is required. `validate_stopped_apps` pairs apps by position *and* checks `app_id`; my swapped-order probe is refused. Zero owned containers are required ✓ |
| Missing / duplicate rows | A missing row raises an error rather than counting as zero. Duplicate (app, env, interval) rows are refused (probe refused). Different intervals are summed (probe: +$0.30 next day → 93¢) ✓ |
| No clipping | An overrun above the original claim is not capped. It can push `stage_remaining` negative and set `fits_stage_cap=false` ✓ |
| Immutability | Original claims are not mutated, and a changed claim against `previous` is refused ✓ |
| No credit netting | Gross per-app meter is used; credits and free storage are not subtracted ✓ |

## Notes

- **N1 — Monotone floor holds only when `previous` is passed (required usage condition).**
  - `previous` is optional. My probe re-settled from a fresh snapshot alone, with a later lower meter of $0.05. It returned **110¢ instead of 126¢**. With `previous` set to this proposal it correctly stays at 126¢.
  - Requirement: every future budget gate that uses the release must pass this exact accepted proposal (SHA `5c22d61e…`) as `previous`, or a later accepted settlement chained from it.
  - This is a usage requirement. It does not require a code change.
- **N2 — Meter plausibility (the allowance looks adequate, but it is uncalibrated).**
  - Each failed app ran about 96–98 s from claim to terminal. 12.3¢ / ~98 s ≈ $4.5/h, which is consistent with one H100-class GPU plus CPU and memory. The meter therefore looks complete for GPU time, not truncated.
  - The eager app's value did not change between the 20:46 and 21:31 UTC snapshots. The fast app was observed only once, 36 min after it stopped.
  - The 50¢ allowance is about 4× each meter.
  - Image-build and volume charges are not attributed per app. The workspace total ($235.35 metered, $0 billed after credits) is not reconciled to individual runs. This is disclosed as it should be.
- **N3 — Headroom and the P2/P3 plan.**
  - The previously recorded 496¢ P2/P3 plan did not fit the old 248¢ remainder. It fits 622¢ with **126¢ margin**.
  - The remainder's 252¢ stays a full reservation until it ends. After it stops and ages 15 min, it can be settled under this same rule with its own fresh snapshot, chained from this proposal.
  - Any later meter increase on either failed app consumes headroom first.
- **N4 — Owner authorization.**
  - The owner's choice of (a) is recorded as a direct message to Codex, which matches what the owner told me.
  - Codex reads the later "不要担心预算…大胆用" as speeding up already-authorized work, not as raising any cap, and I agree. The $100 / Stage 10-50-35 / unallocated $5 caps remain.
  - Releasing the $5 or raising the Stage 0 cap would need a new, explicit owner instruction sent directly to Codex.

## Science-signal check

- There is no scientific outcome yet. At target time the P0 remainder was `NOT_RUN`; it was the next single slot.
- This settlement removes the budget blocker that would otherwise have stopped P2/P3 tonight (the 248¢ shortfall).
- It does not change EOS handling, scoring, dose or any gate.
- A2 on the merged 256 + 2,382 rows remains the next science checkpoint.

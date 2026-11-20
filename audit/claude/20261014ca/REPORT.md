# Audit 20261014ca: Stage 1 registered analysis and stop code (pre-outcome)

- **Request:** `p009-stage1-registered-analysis-code-r1`
- **Scope:** `p009-stage1-registered-analysis-and-stop-code`
- **Target:** `2c7d6b5ce7fe7d9c23ad59dc6e185493390f9a81`
- **Manifest:** `dd832619a8adeb522cc171806c8a5e4eca9a9f4e16d9731c147a01f0c48cbe6b`. All 11 entries match.

## Decision: PASS

**source_files** (all recomputed; `gates.py` is byte-identical to the A0-reviewed version used for G0):

```json
{
 "experiments/learning_regime_p009/__init__.py": "6b2bd9b425d523167ca743adc11f79e00706ec6dba8b5200e0379efc3ca942e5",
 "experiments/learning_regime_p009/gates.py": "1543f482098cee612256633e85b88e528c7418babfe6af6d4a00fc80347eefb0",
 "experiments/learning_regime_p009/requirements_stage1_analysis.txt": "a23aaf94250a9f53031a592980142245a848e2372b6c6c3093e8260b129265b8",
 "experiments/learning_regime_p009/stage1_analysis.py": "97c02fb9b284967955258c20d91a4568017965b15ff687aa17eba647b3d27221"
}
```

**bootstrap_policy:**

```json
{"generator": "numpy.PCG64", "interval_scope": "pointwise_conditional_not_simultaneous_or_seed_population",
 "numpy_version": "2.2.6", "ordering": "lexicographic_frozen_question_id", "quantile_method": "linear",
 "quantiles": [0.025, 0.975], "replicates": 10000, "seed": 20261014, "unit": "paired_question"}
```

## Checks against PREREG §5.3–5.4

| Rule | Prereg | Code | Boundary test (mine) |
|---|---|---|---|
| G1 seed 17 | Δ(3200−400) ≥ 5.0 pp | `100·d ≥ 5·n` | 25/500 passes, 24/500 fails |
| G1 CI | paired bootstrap 10,000, lower bound > 0 | `lower95 > 0` (strict) | 0.0 fails |
| G1 seed 29 | Δ ≥ 2.5 pp, same direction | `200·d ≥ 5·n` | 13/500 passes, 12/500 fails |
| NC stop | Δ_NC ≥ 5.0 pp stops everything | `100·d ≥ 5·n` | 66/1319 stops, 65 does not |
| Futility (A4) | every candidate's first-pair Δ < 2.0 pp | `100·d < 2·n` | 9/500 stops, 10/500 does not |
| n* | n* = 400 if acc(1600) ≥ acc(3200) − 1.0 pp, else 1600 | `100·(c3200 − c1600) ≤ total` | diff 5 gives 400, diff 6 gives 1600 |

Other rules, all implemented as registered:

- **Order:** NC must come first and stops everything when Δ_NC ≥ 5 pp.
- **S1 G0 failure:** this is a distinct `stop_no_eligible_positive_regime`. It is not measured futility, and `futility([])` refuses.
- **S2:** excluded.
- **G1 inputs:** all six S1 cells are required, and n100 and n1600 cannot be dropped.
- **After a stop:** later outcomes are refused and need a separate disposition.
- **Verdicts:** complete Boolean verdicts on exact frozen IDs, with no unknown→0. Pairing is by identity after a lexicographic sort. I verified that reversing the dict insertion order gives an identical bound.

**Bootstrap reproduction.** I re-implemented the resampling independently: PCG64(20261014), `integers(0, 500, (10000, 500))`, shared indices for both models, linear quantiles. On a synthetic pair it reproduces the module's observed Δ and both bounds exactly (4.2, [−2.0, 10.2]).

**Tests.** I ran the 9 new tests here and all pass. The numpy version check was patched, because the sandbox has 2.5.3 and cannot reach PyPI.

## Notes
- **N1.** Bit-exact bounds are guaranteed only under the pinned NumPy 2.2.6. The actual A4/A5 run must use the pinned analysis environment. My check under 2.5.3 shows the logic is correct but is not a pinned-version replay.
- **N2.** The scope is correctly limited: intervals are pointwise and conditional, seed changes data order and training randomness together, and G1 PASS does not admit Stage 2.

## 科学信号检查 (science-signal check)

No outcomes yet. This code is frozen before any student result, which is what the prereg requires. The decision path is now fully specified: NC first pair → S1 first pair (futility < 2 pp) → remaining S1 cells → G1.

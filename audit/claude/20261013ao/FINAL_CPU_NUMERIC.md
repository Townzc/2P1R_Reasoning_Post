# Claude audit 20261013ao — p008-final-cpu-actual-byte-numeric-r1 @ 929b769a: **PASS-WITH-NOTES** (numeric admission of the original 500¢ / 3,300 s CPU slot)

## Q1. Roster: YES
- **Labels.** 24 labels with 24 distinct app_ids. 21 are completed and 3 are failed: the D2 parent and the two zero-update T1 attempts. The 2 replacements keep their physical identities.
- **T8 records.** All 8 T8 terminals in BASIS equal the terminals in the T8 LEDGERs that were published and G3-checked at b212b6a8 (20261013am/an).
- **Code review target.** The code review targets 82c3912a, which I reviewed in 20261013ai pt2.

## Q2. Cap records: YES
- **Count and digest.** `t8_cap_ledger_records` contains 9 records (1 global + 8 supplements), digest b6838017…, equal to the request.
- **Match.** For every T8 run, both the supplement and the global amendment equal that run's published LEDGER.
- **Flags.** `original_N2_passed=false` and `post_hoc_engineering_deviation=true` are carried through.

## Q3. Bytes: exact, recomputed independently
- **States: 5,775,946,082 bytes.** This is the sum of the 26 `state.pt` sizes in the published artifact manifests: 10 T1 checkpoint_0256 plus 8 × (T8 checkpoint_1024 + checkpoint_2048). The 26 transfer receipts also sum to exactly this figure.
- **Compact: 108,602,405 bytes.**

  | source | compact bytes | where I got it |
  |---|---|---|
  | 19 students + base | 62,600,124 | published manifests |
  | D1 pool and D2 child | 37,185,649 | POOL/CHILD envelopes |
  | 3 failed archives | 8,816,632 | BASIS |

  The rows sum to 108,602,405.
- **Transfer: 5,891,909,585 bytes.** Students and base contribute 5,845,068,288, the pools 37,757,946 and the failed archives 9,083,351. The failed-archive figure is the remainder, and it equals the BASIS archive records exactly.
- **Input manifest: 56,405,039 bytes**, across 33 members.

## Q4. Forecast: arithmetic reproduced exactly, assumptions acceptable
- **Rates.** I recomputed every rate from the 26 receipts: each is complete with 0 retries, and each one's range lengths sum to its expected bytes. The minimum is **10.020938 MB/s** and the maximum 22.53 MB/s.
- **Formula.** 1.2 × (3 × 6,004,719,663 / 10,020,938 + 4 × 24 × 4.219557583 + 300) = 1.2 × (1,797.65 + 405.08 + 300) = **3,003.28 s**. This is ≤ 3,180 (the 3,300 s cap minus the 120 s persistence margin), and inside the 4,000 s window.

### My assessment of the proxy
- **Transfer.** The rate is the slowest of 26 local HTTP downloads, then given a 3× slowdown allowance. A cloud CPU container reading the same Volume would usually be faster than a residential download. The copy term is therefore probably conservative, although it is not a bound.
- **Processing.** 4 × 24 × 4.2 s is about 17 s per label, based on one warm-cache local oracle that loaded 2 full states. In a 4-CPU container, torch-loading and checking about 222 MB per state could take longer. This is the least calibrated term.
- **Consequence of an overrun.** It is bounded and **non-scientific**: the hard 3,300 s timer fails the audit slot. The reservation is 500¢, and all failure evidence is retained. No model outcome or primary result depends on this CPU run.
- **Conclusion.** Accept as an engineering admission. Do not describe it as a calibrated upper bound.

## Notes
- **N1.** If the CPU run fails on time, record the actual per-label `timings` that the code already emits. Any second CPU attempt needs a new reviewed amendment, not an automatic retry.
- **N2.** The final-CPU code still requires all 8 T8 to be completed, as I noted in C1 of 20261013ai. That is now satisfied.

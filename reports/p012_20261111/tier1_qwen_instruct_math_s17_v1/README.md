# Tier 1 Qwen instruct × MATH, seed 17

| Cell | MATH-5000 | MATH-500 | Cap rate | Loop count | Normal termination accuracy |
|---|---:|---:|---:|---:|---:|
| P | 42.94% | 42.40% | 9.94% | 377 | 47.68% (2147/4503) |
| K8 | 41.00% | 41.40% | 10.92% | 430 | 46.03% (2050/4454) |
| R | 32.72% | 34.40% | 2.82% | 124 | 33.67% (1636/4859) |
| K4 | 41.88% | 41.60% | 9.26% | 383 | 46.15% (2094/4537) |
| L | 42.88% | 43.20% | 8.92% | 348 | 47.08% (2144/4554) |

Raw generations, scores, checkpoint hashes, training logs and manifests are in the per-cell ZIPs. All five Instruct cells were trained and evaluated once.

Loop count uses a fixed exact-token heuristic (period 1–256, >=3 repetitions and >=60 repeated tokens). It was frozen before allocation contrasts were scored; it differs from the earlier reviewer’s heuristic. Normal termination means an actual EOS or configured string stop, independently of correctness or the loop flag. Conditional accuracy has a different denominator in each cell.

Only seed 17 is present. The registered two-seed direction criterion is pending Tier 2. No sampled-four endpoint was added.

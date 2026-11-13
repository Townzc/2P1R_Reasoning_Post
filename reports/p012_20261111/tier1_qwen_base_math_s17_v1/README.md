# Tier 1 Qwen base × MATH, seed 17

| Cell | MATH-5000 | MATH-500 | Cap rate | Loop count | Normal termination accuracy |
|---|---:|---:|---:|---:|---:|
| P | 42.06% | 41.60% | 9.72% | 361 | 46.59% (2103/4514) |
| K8 | 40.12% | 41.00% | 9.70% | 377 | 44.43% (2006/4515) |
| R | 33.14% | 36.20% | 3.04% | 149 | 34.18% (1657/4848) |
| K4 | 41.34% | 41.00% | 9.68% | 391 | 45.77% (2067/4516) |
| L | 42.88% | 41.80% | 10.06% | 413 | 47.41% (2132/4497) |

Raw generations, scores, checkpoint hashes, training logs and manifests are in the per-cell ZIPs. Existing base L is reused from `l_cost_probe_v1`; its new descriptive diagnostics are included here.

Loop count uses a fixed exact-token heuristic (period 1–256, >=3 repetitions and >=60 repeated tokens). It was frozen before allocation contrasts were scored; it differs from the earlier reviewer’s heuristic. Normal termination means an actual EOS or configured string stop, independently of correctness or the loop flag. Conditional accuracy has a different denominator in each cell.

Only seed 17 is present. The registered two-seed direction criterion is pending Tier 2. No sampled-four endpoint was added.

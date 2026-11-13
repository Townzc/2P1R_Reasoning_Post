# A5-2 Qwen instruct × MATH, seed 17

Exploratory supplement, excluded from H0–H3. Frozen nested subsets and unchanged full-finetuning/evaluation paths.

| Cell | Parents | Updates | MATH-5000 | MATH-500 | Cap rate | Loop count | Normal termination accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|
| L64 | 64 | 16 | 41.48% | 39.00% | 15.16% | 666 | 48.89% (2074/4242) |
| L128 | 128 | 32 | 43.20% | 40.60% | 10.94% | 476 | 48.51% (2160/4453) |
| L256 | 256 | 64 | 43.10% | 42.20% | 8.84% | 361 | 47.28% (2155/4558) |
| K8s | 64 | 128 | 42.82% | 42.20% | 8.32% | 309 | 46.71% (2141/4584) |
| Rs | 64 | 128 | 37.28% | 36.60% | 3.44% | 168 | 38.59% (1863/4828) |

Reference cells are reused without rerunning from `../tier1_qwen_instruct_math_s17_v1/RESULTS.json`. Raw outputs, labels, checkpoint hashes, training logs and per-response termination flags are in the ZIPs.

Normal-termination accuracy has a different denominator in each cell. Loop count uses the previously frozen token-period heuristic. Numeric differences here use one seed and are not a registered two-seed conclusion.

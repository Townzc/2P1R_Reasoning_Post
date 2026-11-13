# A5-3 Qwen instruct × MATH, seed 17

Exploratory supplement, excluded from H0–H3. Frozen nested subsets and unchanged full-finetuning/evaluation paths.

| Cell | Parents | Updates | MATH-5000 | MATH-500 | Cap rate | Loop count | Normal termination accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|
| E4 | 2048 | 1024 | 37.64% | 35.60% | 4.62% | 176 | 39.46% (1882/4769) |
| E8 | 1024 | 1024 | 36.02% | 34.60% | 2.02% | 84 | 36.74% (1800/4899) |

Reference cells are reused without rerunning from `../tier1_qwen_instruct_math_s17_v1/RESULTS.json`. Raw outputs, labels, checkpoint hashes, training logs and per-response termination flags are in the ZIPs.

Normal-termination accuracy has a different denominator in each cell. Loop count uses the previously frozen token-period heuristic. Numeric differences here use one seed and are not a registered two-seed conclusion.

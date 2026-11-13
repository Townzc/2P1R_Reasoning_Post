# A5-3 Qwen base × MATH, seed 17

Exploratory supplement, excluded from H0–H3. Frozen nested subsets and unchanged full-finetuning/evaluation paths.

| Cell | Parents | Updates | MATH-5000 | MATH-500 | Cap rate | Loop count | Normal termination accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|
| E4 | 2048 | 1024 | 37.36% | 37.60% | 5.62% | 195 | 39.58% (1868/4719) |
| E8 | 1024 | 1024 | 37.06% | 38.60% | 1.86% | 87 | 37.76% (1853/4907) |

Reference cells are reused without rerunning from `../tier1_qwen_base_math_s17_v1/RESULTS.json`. Raw outputs, labels, checkpoint hashes, training logs and per-response termination flags are in the ZIPs.

Normal-termination accuracy has a different denominator in each cell. Loop count uses the previously frozen token-period heuristic. Numeric differences here use one seed and are not a registered two-seed conclusion.

# A5-2 Qwen base × MATH, seed 17

Exploratory supplement, excluded from H0–H3. Frozen nested subsets and unchanged full-finetuning/evaluation paths.

| Cell | Parents | Updates | MATH-5000 | MATH-500 | Cap rate | Loop count | Normal termination accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|
| L64 | 64 | 16 | 38.34% | 36.00% | 81.94% | 2855 | 49.72% (449/903) |
| L128 | 128 | 32 | 42.28% | 42.80% | 90.82% | 2722 | 43.79% (201/459) |
| L256 | 256 | 64 | 34.68% | 34.00% | 99.38% | 4416 | 48.39% (15/31) |
| K8s | 64 | 128 | 42.68% | 42.00% | 11.44% | 474 | 46.82% (2073/4428) |
| Rs | 64 | 128 | 40.26% | 40.00% | 2.80% | 131 | 41.36% (2010/4860) |

Reference cells are reused without rerunning from `../tier1_qwen_base_math_s17_v1/RESULTS.json`. Raw outputs, labels, checkpoint hashes, training logs and per-response termination flags are in the ZIPs.

Normal-termination accuracy has a different denominator in each cell. Loop count uses the previously frozen token-period heuristic. Numeric differences here use one seed and are not a registered two-seed conclusion.

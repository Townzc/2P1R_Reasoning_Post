# Observed MATH sampling patterns — post-hoc CPU audit

No new generation, training, or grading. Each row retains 500 questions × 8 samples.

| Method | Average accuracy | At least one correct / 500 | All eight correct / 500 | Unresolved outputs |
|---|---:|---:|---:|---:|
| Base | 32.100–32.350% | 391–393 | 2–3 | 10 |
| SFT | 41.050–41.250% | 372–373 | 47–48 | 8 |
| DFT | 59.300–59.575% | 396–398 | 207–208 | 11 |
| TrimSFT | 59.050–59.300% | 386–387 | 201–202 | 10 |
| QDW_v0 | 42.175–42.375% | 370–371 | 52–53 | 8 |

DFT and TrimSFT have many more questions correct in all eight observed samples. This difference is much larger than their difference in questions with any correct sample. It motivates a same-question decoding comparison; it does not identify the cause.

- Descriptive post-hoc analysis of observed tests, not a new confirmatory result.
- All-eight-correct measures this finite set of eight samples, not general determinism or correctness of every reasoning step.
- Task and decoding are confounded in the historical GSM8K-greedy versus MATH-sampled comparison.
- One training seed; the same examples cannot become an untouched confirmation set.
- Unknown scores retain all-question bounds; no difficult question was dropped.

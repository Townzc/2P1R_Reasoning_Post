# Instruct bridge: all five cells complete

Same townzc workspace and H100 GPU; rank32, alpha32, seven linear target modules and no lm_head. All adapters passed file hashes and the36,929,536-parameter check. L passed the25% cap gate before the remaining cells started. This is a separate LoRA bridge, excluded from the full-finetuning H0-H3 analysis.

| Cell | MATH5000 | MATH500 | Cap rate | Loops | Normal-termination correct / denominator |
|---|---:|---:|---:|---:|---:|
| P | 41.84% | 41.60% | 10.84% | 428 | 2092/4458 |
| R | 32.68% | 33.20% | 2.10% | 129 | 1634/4895 |
| K8 | 41.64% | 40.40% | 11.84% | 455 | 2082/4408 |
| K4 | 41.14% | 40.00% | 11.02% | 448 | 2057/4449 |
| L | 42.96% | 42.00% | 9.24% | 383 | 2148/4538 |

L was accepted in46694f51. P/R/K8/K4 are new results for the next independent audit. Their per-cell archives contain all20,000 raw responses, labels, termination flags, training data/logs and runtime checkpoint bindings. Original prediction8bbf06a7 described the base bridge; the Instruct follow-up is authorized by18f64e2d and is identified separately.

The completed four-cell training/evaluation charge upper bound is$5.9606, versus$5.7277 reserved. This uses measured function time plus30 seconds per call and training storage reserve; billing is reconciled separately. No additional Modal call is planned.

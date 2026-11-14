# Tinker LoRA Qwen/Qwen3.5-9B-Base × MATH K8, seed 29

MATH-5000: **64.60%** (3230/5000). MATH-500: **65.80%**. Cap rate 4.22%; loop count 100; normaltermination accuracy 67.45% (3230/4789).

| Baseline on MATH-500 | Before SFT | After SFT | Delta |
|---|---:|---:|---:|
| baseline4 | 71.40% | 65.80% | -5.60pp |

All5,000 rawoutputs, labels, perresponseflags, trainingloss/order, savedstate/sampleridentities and the pre-score predictioncommit record are in `evidence.zip`. The frozenprediction remains8bbf06a7. This is the separate Tinker/LoRA track; the remaining cells and independent audit are tracked separately.

Measured samplingtoken costupper: $2.199911 (nocachediscount). This endpoint ×1.5 for subsequent same-size generation: $3.299867; fullbatchadmission must stillaccountforotherjobs.

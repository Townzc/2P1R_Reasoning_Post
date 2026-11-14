# Tinker LoRA Qwen/Qwen3.5-9B × MATH K8, seed 29

MATH-5000: **65.82%** (3291/5000). MATH-500: **66.80%**. Cap rate 4.52%; loop count 119; normaltermination accuracy 68.94% (3291/4774).

| Baseline on MATH-500 | Before SFT | After SFT | Delta |
|---|---:|---:|---:|
| baseline4 | 91.80% | 66.80% | -25.00pp |
| baseline0 | 91.20% | 66.80% | -24.40pp |

All5,000 rawoutputs, labels, perresponseflags, trainingloss/order, savedstate/sampleridentities and the pre-score predictioncommit record are in `evidence.zip`. The frozenprediction remains8bbf06a7. This is the separate Tinker/LoRA track; the remaining cells and independent audit are tracked separately.

Measured samplingtoken costupper: $2.235837 (nocachediscount). This endpoint ×1.5 for subsequent same-size generation: $3.353756; fullbatchadmission must stillaccountforotherjobs.

# Tinker LoRA Qwen/Qwen3.5-9B-Base × MATH P, seed 29

MATH-5000: **67.50%** (3375/5000). MATH-500: **67.60%**. Cap rate 4.32%; loop count 130; normaltermination accuracy 70.55% (3375/4784).

| Baseline on MATH-500 | Before SFT | After SFT | Delta |
|---|---:|---:|---:|
| baseline4 | 71.40% | 67.60% | -3.80pp |

All5,000 rawoutputs, labels, perresponseflags, trainingloss/order, savedstate/sampleridentities and the pre-score predictioncommit record are in `evidence.zip`. The frozenprediction remains8bbf06a7. This is the separate Tinker/LoRA track; the remaining cells and independent audit are tracked separately.

Measured samplingtoken costupper: $2.181969 (nocachediscount). This endpoint ×1.5 for subsequent same-size generation: $3.272954; fullbatchadmission must stillaccountforotherjobs.

# Tinker LoRA Qwen/Qwen3.5-9B-Base × MATH L, seed 29

MATH-5000: **70.12%** (3506/5000). MATH-500: **70.40%**. Cap rate 3.64%; loop count 112; normaltermination accuracy 72.77% (3506/4818).

| Baseline on MATH-500 | Before SFT | After SFT | Delta |
|---|---:|---:|---:|
| baseline4 | 71.40% | 70.40% | -1.00pp |

All5,000 rawoutputs, labels, perresponseflags, trainingloss/order, savedstate/sampleridentities and the pre-score predictioncommit record are in `evidence.zip`. The frozenprediction remains8bbf06a7. This is the separate Tinker/LoRA track; the remaining cells and independent audit are tracked separately.

Measured samplingtoken costupper: $2.084903 (nocachediscount). This endpoint ×1.5 for subsequent same-size generation: $3.127354; fullbatchadmission must stillaccountforotherjobs.

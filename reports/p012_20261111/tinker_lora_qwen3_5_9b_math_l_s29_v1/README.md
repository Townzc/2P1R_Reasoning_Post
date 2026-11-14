# Tinker LoRA Qwen/Qwen3.5-9B × MATH L, seed 29

MATH-5000: **69.74%** (3487/5000). MATH-500: **72.00%**. Cap rate 3.92%; loop count 112; normaltermination accuracy 72.59% (3487/4804).

| Baseline on MATH-500 | Before SFT | After SFT | Delta |
|---|---:|---:|---:|
| baseline4 | 91.80% | 72.00% | -19.80pp |
| baseline0 | 91.20% | 72.00% | -19.20pp |

All5,000 rawoutputs, labels, perresponseflags, trainingloss/order, savedstate/sampleridentities and the pre-score predictioncommit record are in `evidence.zip`. The frozenprediction remains8bbf06a7. This is the separate Tinker/LoRA track; the remaining cells and independent audit are tracked separately.

Measured samplingtoken costupper: $2.105350 (nocachediscount). This endpoint ×1.5 for subsequent same-size generation: $3.158024; fullbatchadmission must stillaccountforotherjobs.

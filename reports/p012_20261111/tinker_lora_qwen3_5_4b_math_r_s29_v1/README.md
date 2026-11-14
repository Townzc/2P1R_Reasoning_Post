# Tinker LoRA Qwen/Qwen3.5-4B × MATH R, seed 29

MATH-5000: **46.80%** (2340/5000). MATH-500: **45.60%**. Cap rate 3.04%; loop count 73; normaltermination accuracy 48.27% (2340/4848).

| Baseline on MATH-500 | Before SFT | After SFT | Delta |
|---|---:|---:|---:|
| baseline4 | 88.40% | 45.60% | -42.80pp |
| baseline0 | 81.80% | 45.60% | -36.20pp |

All5,000 rawoutputs, labels, perresponseflags, trainingloss/order, savedstate/sampleridentities and the pre-score predictioncommit record are in `evidence.zip`. The frozenprediction remains8bbf06a7. This is the separate Tinker/LoRA track; the remaining cells and independent audit are tracked separately.

Measured samplingtoken costupper: $2.679524 (nocachediscount). This endpoint ×1.5 for subsequent same-size generation: $4.019286; fullbatchadmission must stillaccountforotherjobs.

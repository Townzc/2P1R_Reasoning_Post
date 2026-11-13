# Tinker LoRA Qwen/Qwen3.5-9B × MATH L, seed 17

MATH-5000: **70.92%** (3546/5000). MATH-500: **71.20%**. Cap rate 3.72%; loop count 114; normaltermination accuracy 73.66% (3546/4814).

| Baseline on MATH-500 | Before SFT | After SFT | Delta |
|---|---:|---:|---:|
| baseline4 | 91.80% | 71.20% | -20.60pp |
| baseline0 | 91.20% | 71.20% | -20.00pp |

All5,000 rawoutputs, labels, perresponseflags, trainingloss/order, savedstate/sampleridentities and the pre-score predictioncommit record are in `evidence.zip`. The frozenprediction remains8bbf06a7. This is the separate Tinker/LoRA track; the setting’s othercells and secondseed are stillpending.

Measured samplingtoken costupper: $2.067337 (nocachediscount). This endpoint ×1.5 for subsequent same-size generation: $3.101005; fullbatchadmission must stillaccountforotherjobs.

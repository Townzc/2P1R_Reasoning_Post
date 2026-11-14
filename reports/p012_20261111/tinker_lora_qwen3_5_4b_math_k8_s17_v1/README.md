# Tinker LoRA Qwen/Qwen3.5-4B × MATH K8, seed 17

MATH-5000: **58.64%** (2932/5000). MATH-500: **61.00%**. Cap rate 6.82%; loop count 205; normaltermination accuracy 62.93% (2932/4659).

| Baseline on MATH-500 | Before SFT | After SFT | Delta |
|---|---:|---:|---:|
| baseline4 | 88.40% | 61.00% | -27.40pp |
| baseline0 | 81.80% | 61.00% | -20.80pp |

All5,000 rawoutputs, labels, perresponseflags, trainingloss/order, savedstate/sampleridentities and the pre-score predictioncommit record are in `evidence.zip`. The frozenprediction remains8bbf06a7. This is the separate Tinker/LoRA track; the setting’s othercells and secondseed are stillpending.

Measured samplingtoken costupper: $3.178276 (nocachediscount). This endpoint ×1.5 for subsequent same-size generation: $4.767415; fullbatchadmission must stillaccountforotherjobs.

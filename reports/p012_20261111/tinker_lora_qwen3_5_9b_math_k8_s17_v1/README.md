# Tinker LoRA Qwen/Qwen3.5-9B × MATH K8, seed 17

MATH-5000: **67.20%** (3360/5000). MATH-500: **69.60%**. Cap rate 3.94%; loop count 114; normaltermination accuracy 69.96% (3360/4803).

| Baseline on MATH-500 | Before SFT | After SFT | Delta |
|---|---:|---:|---:|
| baseline4 | 91.80% | 69.60% | -22.20pp |
| baseline0 | 91.20% | 69.60% | -21.60pp |

All5,000 rawoutputs, labels, perresponseflags, trainingloss/order, savedstate/sampleridentities and the pre-score predictioncommit record are in `evidence.zip`. The frozenprediction remains8bbf06a7. This is the separate Tinker/LoRA track; the setting’s othercells and secondseed are stillpending.

Measured samplingtoken costupper: $2.159243 (nocachediscount). This endpoint ×1.5 for subsequent same-size generation: $3.238865; fullbatchadmission must stillaccountforotherjobs.

# Tinker LoRA Qwen/Qwen3.5-4B × MATH L, seed 17

MATH-5000: **65.60%** (3280/5000). MATH-500: **63.40%**. Cap rate 5.26%; loop count 167; normaltermination accuracy 69.24% (3280/4737).

| Baseline on MATH-500 | Before SFT | After SFT | Delta |
|---|---:|---:|---:|
| baseline4 | 88.40% | 63.40% | -25.00pp |
| baseline0 | 81.80% | 63.40% | -18.40pp |

All5,000 rawoutputs, labels, perresponseflags, trainingloss/order, savedstate/sampleridentities and the pre-score predictioncommit record are in `evidence.zip`. The frozenprediction remains8bbf06a7. This is the separate Tinker/LoRA track; the setting’s othercells and secondseed are stillpending.

Measured samplingtoken costupper: $2.842995 (nocachediscount). This endpoint ×1.5 for subsequent same-size generation: $4.264493; fullbatchadmission must stillaccountforotherjobs.

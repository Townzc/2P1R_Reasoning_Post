# Tinker LoRA Qwen/Qwen3.5-9B × MATH R, seed 17

MATH-5000: **58.34%** (2917/5000). MATH-500: **60.40%**. Cap rate 1.58%; loop count 31; normaltermination accuracy 59.28% (2917/4921).

| Baseline on MATH-500 | Before SFT | After SFT | Delta |
|---|---:|---:|---:|
| baseline4 | 91.80% | 60.40% | -31.40pp |
| baseline0 | 91.20% | 60.40% | -30.80pp |

All5,000 rawoutputs, labels, perresponseflags, trainingloss/order, savedstate/sampleridentities and the pre-score predictioncommit record are in `evidence.zip`. The frozenprediction remains8bbf06a7. This is the separate Tinker/LoRA track; the setting’s othercells and secondseed are stillpending.

Measured samplingtoken costupper: $1.905727 (nocachediscount). This endpoint ×1.5 for subsequent same-size generation: $2.858590; fullbatchadmission must stillaccountforotherjobs.

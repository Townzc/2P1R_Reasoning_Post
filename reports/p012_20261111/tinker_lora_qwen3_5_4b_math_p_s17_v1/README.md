# Tinker LoRA Qwen/Qwen3.5-4B × MATH P, seed 17

MATH-5000: **60.06%** (3003/5000). MATH-500: **61.00%**. Cap rate 5.80%; loop count 190; normaltermination accuracy 63.76% (3003/4710).

| Baseline on MATH-500 | Before SFT | After SFT | Delta |
|---|---:|---:|---:|
| baseline4 | 88.40% | 61.00% | -27.40pp |
| baseline0 | 81.80% | 61.00% | -20.80pp |

All5,000 rawoutputs, labels, perresponseflags, trainingloss/order, savedstate/sampleridentities and the pre-score predictioncommit record are in `evidence.zip`. The frozenprediction remains8bbf06a7. This is the separate Tinker/LoRA track; the setting’s othercells and secondseed are stillpending.

Measured samplingtoken costupper: $2.945076 (nocachediscount). This endpoint ×1.5 for subsequent same-size generation: $4.417614; fullbatchadmission must stillaccountforotherjobs.

# Tinker LoRA Qwen/Qwen3.5-9B × MATH K4, seed 17

MATH-5000: **66.02%** (3301/5000). MATH-500: **68.80%**. Cap rate 4.40%; loop count 108; normaltermination accuracy 69.06% (3301/4780).

| Baseline on MATH-500 | Before SFT | After SFT | Delta |
|---|---:|---:|---:|
| baseline4 | 91.80% | 68.80% | -23.00pp |
| baseline0 | 91.20% | 68.80% | -22.40pp |

All5,000 rawoutputs, labels, perresponseflags, trainingloss/order, savedstate/sampleridentities and the pre-score predictioncommit record are in `evidence.zip`. The frozenprediction remains8bbf06a7. This is the separate Tinker/LoRA track; the setting’s othercells and secondseed are stillpending.

Measured samplingtoken costupper: $2.210179 (nocachediscount). This endpoint ×1.5 for subsequent same-size generation: $3.315268; fullbatchadmission must stillaccountforotherjobs.

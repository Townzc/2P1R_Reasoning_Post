# Tinker LoRA Qwen/Qwen3.5-9B × MATH P, seed 17

MATH-5000: **67.68%** (3384/5000). MATH-500: **68.60%**. Cap rate 3.64%; loop count 103; normaltermination accuracy 70.24% (3384/4818).

| Baseline on MATH-500 | Before SFT | After SFT | Delta |
|---|---:|---:|---:|
| baseline4 | 91.80% | 68.60% | -23.20pp |
| baseline0 | 91.20% | 68.60% | -22.60pp |

All5,000 rawoutputs, labels, perresponseflags, trainingloss/order, savedstate/sampleridentities and the pre-score predictioncommit record are in `evidence.zip`. The frozenprediction remains8bbf06a7. This is the separate Tinker/LoRA track; the setting’s othercells and secondseed are stillpending.

Measured samplingtoken costupper: $2.065785 (nocachediscount). This endpoint ×1.5 for subsequent same-size generation: $3.098677; fullbatchadmission must stillaccountforotherjobs.

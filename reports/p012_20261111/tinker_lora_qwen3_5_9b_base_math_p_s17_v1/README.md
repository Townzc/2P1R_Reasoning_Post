# Tinker LoRA Qwen/Qwen3.5-9B-Base × MATH P, seed 17

MATH-5000: **67.10%** (3355/5000). MATH-500: **69.40%**. Cap rate 3.60%; loop count 114; normaltermination accuracy 69.61% (3355/4820).

| Baseline on MATH-500 | Before SFT | After SFT | Delta |
|---|---:|---:|---:|
| baseline4 | 71.40% | 69.40% | -2.00pp |

All5,000 rawoutputs, labels, perresponseflags, trainingloss/order, savedstate/sampleridentities and the pre-score predictioncommit record are in `evidence.zip`. The frozenprediction remains8bbf06a7. This is the separate Tinker/LoRA track; the setting’s othercells and secondseed are stillpending.

Measured samplingtoken costupper: $2.065037 (nocachediscount). This endpoint ×1.5 for subsequent same-size generation: $3.097556; fullbatchadmission must stillaccountforotherjobs.

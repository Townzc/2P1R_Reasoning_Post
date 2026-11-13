# Tinker LoRA Qwen/Qwen3.5-9B-Base × MATH L, seed 17

MATH-5000: **70.40%** (3520/5000). MATH-500: **73.60%**. Cap rate 3.48%; loop count 105; normaltermination accuracy 72.94% (3520/4826).

| Baseline on MATH-500 | Before SFT | After SFT | Delta |
|---|---:|---:|---:|
| baseline4 | 71.40% | 73.60% | +2.20pp |

All5,000 rawoutputs, labels, perresponseflags, trainingloss/order, savedstate/sampleridentities and the pre-score predictioncommit record are in `evidence.zip`. The frozenprediction remains8bbf06a7. This is the separate Tinker/LoRA track; the setting’s othercells and secondseed are stillpending.

Measured samplingtoken costupper: $2.061894 (nocachediscount). This endpoint ×1.5 for subsequent same-size generation: $3.092841; fullbatchadmission must stillaccountforotherjobs.

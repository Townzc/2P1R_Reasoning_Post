# Tinker LoRA Qwen/Qwen3.5-9B-Base × MATH K4, seed 17

MATH-5000: **66.50%** (3325/5000). MATH-500: **68.80%**. Cap rate 4.36%; loop count 121; normaltermination accuracy 69.53% (3325/4782).

| Baseline on MATH-500 | Before SFT | After SFT | Delta |
|---|---:|---:|---:|
| baseline4 | 71.40% | 68.80% | -2.60pp |

All5,000 rawoutputs, labels, perresponseflags, trainingloss/order, savedstate/sampleridentities and the pre-score predictioncommit record are in `evidence.zip`. The frozenprediction remains8bbf06a7. This is the separate Tinker/LoRA track; the setting’s othercells and secondseed are stillpending.

Measured samplingtoken costupper: $2.218369 (nocachediscount). This endpoint ×1.5 for subsequent same-size generation: $3.327554; fullbatchadmission must stillaccountforotherjobs.

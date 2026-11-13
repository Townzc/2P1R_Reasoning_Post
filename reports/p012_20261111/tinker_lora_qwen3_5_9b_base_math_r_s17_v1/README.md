# Tinker LoRA Qwen/Qwen3.5-9B-Base × MATH R, seed 17

MATH-5000: **56.98%** (2849/5000). MATH-500: **56.80%**. Cap rate 3.04%; loop count 66; normaltermination accuracy 58.77% (2849/4848).

| Baseline on MATH-500 | Before SFT | After SFT | Delta |
|---|---:|---:|---:|
| baseline4 | 71.40% | 56.80% | -14.60pp |

All5,000 rawoutputs, labels, perresponseflags, trainingloss/order, savedstate/sampleridentities and the pre-score predictioncommit record are in `evidence.zip`. The frozenprediction remains8bbf06a7. This is the separate Tinker/LoRA track; the setting’s othercells and secondseed are stillpending.

Measured samplingtoken costupper: $2.114925 (nocachediscount). This endpoint ×1.5 for subsequent same-size generation: $3.172387; fullbatchadmission must stillaccountforotherjobs.

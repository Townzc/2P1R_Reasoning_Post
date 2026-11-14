# Tinker LoRA Qwen/Qwen3.5-9B-Base × MATH K8, seed 17

MATH-5000: **66.34%** (3317/5000). MATH-500: **66.40%**. Cap rate 4.00%; loop count 100; normaltermination accuracy 69.10% (3317/4800).

| Baseline on MATH-500 | Before SFT | After SFT | Delta |
|---|---:|---:|---:|
| baseline4 | 71.40% | 66.40% | -5.00pp |

All5,000 rawoutputs, labels, perresponseflags, trainingloss/order, savedstate/sampleridentities and the pre-score predictioncommit record are in `evidence.zip`. The frozenprediction remains8bbf06a7. This is the separate Tinker/LoRA track; the setting’s othercells and secondseed are stillpending.

Measured samplingtoken costupper: $2.184903 (nocachediscount). This endpoint ×1.5 for subsequent same-size generation: $3.277354; fullbatchadmission must stillaccountforotherjobs.

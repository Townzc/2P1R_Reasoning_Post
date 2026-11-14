# Tinker LoRA Qwen/Qwen3.5-4B × MATH K8, seed 29

MATH-5000: **59.18%** (2959/5000). MATH-500: **60.40%**. Cap rate 6.62%; loop count 219; normaltermination accuracy 63.38% (2959/4669).

| Baseline on MATH-500 | Before SFT | After SFT | Delta |
|---|---:|---:|---:|
| baseline4 | 88.40% | 60.40% | -28.00pp |
| baseline0 | 81.80% | 60.40% | -21.40pp |

All5,000 rawoutputs, labels, perresponseflags, trainingloss/order, savedstate/sampleridentities and the pre-score predictioncommit record are in `evidence.zip`. The frozenprediction remains8bbf06a7. This is the separate Tinker/LoRA track; the remaining cells and independent audit are tracked separately.

Measured samplingtoken costupper: $3.187818 (nocachediscount). This endpoint ×1.5 for subsequent same-size generation: $4.781727; fullbatchadmission must stillaccountforotherjobs.

Independent numeric review passed at8a8fac5c8ae75170e5c505f4215b5f1f9f0948d4; original Codex labels retained.

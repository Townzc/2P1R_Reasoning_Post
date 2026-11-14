# Tinker LoRA Qwen/Qwen3.5-4B × MATH P, seed 29

MATH-5000: **60.94%** (3047/5000). MATH-500: **60.60%**. Cap rate 5.80%; loop count 177; normaltermination accuracy 64.69% (3047/4710).

| Baseline on MATH-500 | Before SFT | After SFT | Delta |
|---|---:|---:|---:|
| baseline4 | 88.40% | 60.60% | -27.80pp |
| baseline0 | 81.80% | 60.60% | -21.20pp |

All5,000 rawoutputs, labels, perresponseflags, trainingloss/order, savedstate/sampleridentities and the pre-score predictioncommit record are in `evidence.zip`. The frozenprediction remains8bbf06a7. This is the separate Tinker/LoRA track; the remaining cells and independent audit are tracked separately.

Measured samplingtoken costupper: $2.964099 (nocachediscount). This endpoint ×1.5 for subsequent same-size generation: $4.446148; fullbatchadmission must stillaccountforotherjobs.

Independent numeric review passed at8a8fac5c8ae75170e5c505f4215b5f1f9f0948d4; original Codex labels retained.

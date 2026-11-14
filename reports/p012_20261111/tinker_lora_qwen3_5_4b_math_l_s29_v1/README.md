# Tinker LoRA Qwen/Qwen3.5-4B × MATH L, seed 29

MATH-5000: **66.42%** (3321/5000). MATH-500: **68.80%**. Cap rate 5.18%; loop count 140; normaltermination accuracy 70.05% (3321/4741).

| Baseline on MATH-500 | Before SFT | After SFT | Delta |
|---|---:|---:|---:|
| baseline4 | 88.40% | 68.80% | -19.60pp |
| baseline0 | 81.80% | 68.80% | -13.00pp |

All5,000 rawoutputs, labels, perresponseflags, trainingloss/order, savedstate/sampleridentities and the pre-score predictioncommit record are in `evidence.zip`. The frozenprediction remains8bbf06a7. This is the separate Tinker/LoRA track; the remaining cells and independent audit are tracked separately.

Measured samplingtoken costupper: $2.843729 (nocachediscount). This endpoint ×1.5 for subsequent same-size generation: $4.265593; fullbatchadmission must stillaccountforotherjobs.

Independent numerical review passed at [6af18b72](https://github.com/Townzc/2P1R_Reasoning_Post/blob/6af18b7263cdafa1c6c34efb89fdea763d74d21e/audit/claude/20261113j/AUDIT_f6785133_5_endpoints_and_4B_M512.md). Registered labels and original evidence archives are unchanged.

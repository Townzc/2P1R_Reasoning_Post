# Tinker LoRA Qwen/Qwen3.5-9B × MATH R, seed 29

MATH-5000: **57.02%** (2851/5000). MATH-500: **55.00%**. Cap rate 1.72%; loop count 38; normaltermination accuracy 58.02% (2851/4914).

| Baseline on MATH-500 | Before SFT | After SFT | Delta |
|---|---:|---:|---:|
| baseline4 | 91.80% | 55.00% | -36.80pp |
| baseline0 | 91.20% | 55.00% | -36.20pp |

All5,000 rawoutputs, labels, perresponseflags, trainingloss/order, savedstate/sampleridentities and the pre-score predictioncommit record are in `evidence.zip`. The frozenprediction remains8bbf06a7. This is the separate Tinker/LoRA track; the remaining cells and independent audit are tracked separately.

Measured samplingtoken costupper: $1.914074 (nocachediscount). This endpoint ×1.5 for subsequent same-size generation: $2.871110; fullbatchadmission must stillaccountforotherjobs.

Independent numerical audit **passed** at `72575b42a1d2ca80004d9114c0bcc2f6b66da26c`. Audit metadata was updated; original numerical results and evidence archives are unchanged. `RESULTS_before72575b42.json` preserves the reviewed result bytes.

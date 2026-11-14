# Tinker LoRA Qwen/Qwen3.5-9B-Base × MATH R, seed 29

MATH-5000: **58.32%** (2916/5000). MATH-500: **57.00%**. Cap rate 3.10%; loop count 64; normaltermination accuracy 60.19% (2916/4845).

| Baseline on MATH-500 | Before SFT | After SFT | Delta |
|---|---:|---:|---:|
| baseline4 | 71.40% | 57.00% | -14.40pp |

All5,000 rawoutputs, labels, perresponseflags, trainingloss/order, savedstate/sampleridentities and the pre-score predictioncommit record are in `evidence.zip`. The frozenprediction remains8bbf06a7. This is the separate Tinker/LoRA track; the remaining cells and independent audit are tracked separately.

Measured samplingtoken costupper: $2.179905 (nocachediscount). This endpoint ×1.5 for subsequent same-size generation: $3.269858; fullbatchadmission must stillaccountforotherjobs.

Independent numerical audit **passed** at `72575b42a1d2ca80004d9114c0bcc2f6b66da26c`. Audit metadata was updated; original numerical results and evidence archives are unchanged. `RESULTS_before72575b42.json` preserves the reviewed result bytes.

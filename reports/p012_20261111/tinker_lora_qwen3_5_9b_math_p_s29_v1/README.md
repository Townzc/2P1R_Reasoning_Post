# Tinker LoRA Qwen/Qwen3.5-9B × MATH P, seed 29

MATH-5000: **68.30%** (3415/5000). MATH-500: **68.00%**. Cap rate 4.12%; loop count 135; normaltermination accuracy 71.23% (3415/4794).

| Baseline on MATH-500 | Before SFT | After SFT | Delta |
|---|---:|---:|---:|
| baseline4 | 91.80% | 68.00% | -23.80pp |
| baseline0 | 91.20% | 68.00% | -23.20pp |

All5,000 rawoutputs, labels, perresponseflags, trainingloss/order, savedstate/sampleridentities and the pre-score predictioncommit record are in `evidence.zip`. The frozenprediction remains8bbf06a7. This is the separate Tinker/LoRA track; the remaining cells and independent audit are tracked separately.

Measured samplingtoken costupper: $2.146009 (nocachediscount). This endpoint ×1.5 for subsequent same-size generation: $3.219014; fullbatchadmission must stillaccountforotherjobs.

Independent numerical audit **passed** at `72575b42a1d2ca80004d9114c0bcc2f6b66da26c`. Audit metadata was updated; original numerical results and evidence archives are unchanged. `RESULTS_before72575b42.json` preserves the reviewed result bytes.

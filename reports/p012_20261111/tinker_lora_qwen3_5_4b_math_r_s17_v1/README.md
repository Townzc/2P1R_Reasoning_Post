# Tinker LoRA Qwen/Qwen3.5-4B × MATH R, seed 17

MATH-5000: **46.56%** (2328/5000). MATH-500: **48.20%**. Cap rate 1.44%; loop count 36; normaltermination accuracy 47.24% (2328/4928).

| Baseline on MATH-500 | Before SFT | After SFT | Delta |
|---|---:|---:|---:|
| baseline4 | 88.40% | 48.20% | -40.20pp |
| baseline0 | 81.80% | 48.20% | -33.60pp |

All5,000 rawoutputs, labels, perresponseflags, trainingloss/order, savedstate/sampleridentities and the pre-score predictioncommit record are in `evidence.zip`. The frozenprediction remains8bbf06a7. This is the separate Tinker/LoRA track; the setting’s othercells and secondseed are stillpending.

Measured samplingtoken costupper: $2.243861 (nocachediscount). This endpoint ×1.5 for subsequent same-size generation: $3.365791; fullbatchadmission must stillaccountforotherjobs.

Independent numerical audit **passed** at `72575b42a1d2ca80004d9114c0bcc2f6b66da26c`. Audit metadata was updated; original numerical results and evidence archives are unchanged. `RESULTS_before72575b42.json` preserves the reviewed result bytes.

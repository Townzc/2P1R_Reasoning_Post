# Tinker LoRA Qwen/Qwen3.5-4B × MATH K4, seed 17

MATH-5000: **60.30%** (3015/5000). MATH-500: **59.60%**. Cap rate 6.06%; loop count 213; normaltermination accuracy 64.19% (3015/4697).

| Baseline on MATH-500 | Before SFT | After SFT | Delta |
|---|---:|---:|---:|
| baseline4 | 88.40% | 59.60% | -28.80pp |
| baseline0 | 81.80% | 59.60% | -22.20pp |

All5,000 rawoutputs, labels, perresponseflags, trainingloss/order, savedstate/sampleridentities and the pre-score predictioncommit record are in `evidence.zip`. The frozenprediction remains8bbf06a7. This is the separate Tinker/LoRA track; the setting’s othercells and secondseed are stillpending.

Measured samplingtoken costupper: $3.032609 (nocachediscount). This endpoint ×1.5 for subsequent same-size generation: $4.548913; fullbatchadmission must stillaccountforotherjobs.

Independent numerical audit **passed** at `53a565dadcd648c50ac1ac2a3c08f5c69da123d0`. Numerical fields, registered labels and archives are unchanged; `RESULTS_before53a565da.json` preserves the reviewed result bytes.

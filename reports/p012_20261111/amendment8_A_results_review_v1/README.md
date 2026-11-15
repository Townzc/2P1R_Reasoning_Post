# A8 group A: complete outputs and R-2 evidence for independent review

All10 Llama-3.2-1B base × GSM8K seed17 endpoints are complete, with13190 raw outputs. Full finetuning, greedy, exploratory, outsideH0–H3. Frozen numerical predictions remain5e1f9128; runtime source acceptedff567d06.

| Cell | P,K,E | Num examples | global_step | Correct | Accuracy | Frozen prediction | Capped | Loops | Normal correct/n |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| A01 | 1024,1,2 | 1024 | 256 | 257/1319 | 19.484% | 21.077% | 0.38% | 2 | 257/1314 |
| A02 | 2048,1,2 | 2048 | 512 | 372/1319 | 28.203% | 26.118% | 0.61% | 5 | 372/1311 |
| A03 | 512,2,2 | 1024 | 256 | 281/1319 | 21.304% | 19.080% | 1.21% | 9 | 281/1303 |
| A04 | 512,4,2 | 2048 | 512 | 297/1319 | 22.517% | 22.125% | 0.38% | 5 | 297/1314 |
| A05 | 2048,2,2 | 4096 | 1024 | 392/1319 | 29.719% | 29.164% | 0.83% | 10 | 392/1308 |
| A06 | 4096,1,1 | 4096 | 512 | 356/1319 | 26.990% | 31.653% | 1.74% | 13 | 356/1296 |
| A07 | 4096,1,4 | 4096 | 2048 | 420/1319 | 31.842% | 30.667% | 0.08% | 1 | 420/1318 |
| A08 | 4096,2,2 | 8192 | 2048 | 506/1319 | 38.362% | 34.205% | 0.53% | 5 | 506/1312 |
| A09 | 4096,4,2 | 16384 | 4096 | 541/1319 | 41.016% | 37.250% | 0.23% | 3 | 541/1316 |
| A10 | 4096,8,2 | 32768 | 8192 | 590/1319 | 44.731% | 40.296% | 0.08% | 1 | 590/1318 |

ENDPOINTS.json binds every raw output, label, input, training manifest, checkpoint manifest, trainer_state and training.log to its public archive. All10 R-2 checks pass; A09 uses16384 examples/4096 updates and A10 uses32768 examples/8192 updates. No submitted request was truncated.

Please independently score group A and apply the frozen A8§5 rules: hit rate, mean residual, K>1 RMSE against both fixed alternatives, separability slope and E=2 versus E≠2 subsets. REGISTERED_ANCHORS supplies both-seed original inputs for the existing P/L/K8/R references. This package does not introduce a new bootstrap or change scoring labels.

Please explicitly decide whether A reaches at least partially holds, releasing the conditional T group. T source/data preparation is separately available at5d89ba21; source acceptance alone does not start T. All A weights remain until this result review passes. The reviewed main-grid L/K4 cleanup is documented separately in modal_cleanup_fb5c77bb_v1.

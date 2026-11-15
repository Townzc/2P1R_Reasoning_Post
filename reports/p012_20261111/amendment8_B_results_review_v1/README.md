# A8 group B: seven complete endpoints for independent review

All 7 Llama-3.2-1B-Instruct × GSM8K seed 17 endpoints are complete, with 9,233 raw outputs. Full finetuning on tangzhice H100!, greedy, exploratory, outside H0–H3. Frozen numerical predictions remain 5e1f9128; runtime source accepted ff567d06. This package is released independently of groups C and T.

| Cell | P,K,E | Num examples | global_step | Correct | Accuracy | Frozen prediction | Capped | Loops | Normal correct/n |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| B01 | 2048,1,2 | 2048 | 512 | 643/1319 | 48.749% | 50.177% | 0.83% | 10 | 643/1308 |
| B02 | 512,4,2 | 2048 | 512 | 618/1319 | 46.854% | 45.805% | 0.38% | 5 | 618/1314 |
| B03 | 2048,2,2 | 4096 | 1024 | 681/1319 | 51.630% | 49.482% | 0.68% | 7 | 681/1310 |
| B04 | 4096,1,1 | 4096 | 512 | 673/1319 | 51.024% | 55.168% | 0.91% | 10 | 673/1307 |
| B05 | 4096,1,4 | 4096 | 2048 | 642/1319 | 48.673% | 48.168% | 0.38% | 2 | 642/1314 |
| B06 | 4096,2,2 | 8192 | 2048 | 720/1319 | 54.587% | 50.973% | 0.30% | 3 | 720/1315 |
| B07 | 4096,4,2 | 16384 | 4096 | 693/1319 | 52.540% | 50.278% | 0.45% | 5 | 693/1313 |

ENDPOINTS.json binds every raw output, label, input, training manifest, model revision, checkpoint manifest, trainer_state, training.log and evaluation configuration to its public archive. All 7 R-2 checks pass. B07 uses 16,384 examples and 4,096 updates; its configured max_samples covers the complete inventory. Each prediction record has UTC, raw-output SHA256 and the frozen authority commit, recorded before scoring.

Please independently score the seven B endpoints and apply the frozen A8 §5 rules: hit rate, mean residual, K > 1 RMSE against both fixed alternatives, and E = 2 versus E ≠ 2 subsets. B predictions span a narrow range, so the comparison with fixed alternatives is required in addition to hit rate. Check the B contribution to SL-5; SL-7 stays pending until C is complete. REGISTERED_ANCHORS.json supplies the accepted original endpoints as references. No rule is refit, no bootstrap is run, and existing labels stay unchanged.

A group was accepted at 204ad0ae932f90579cc285ff41483e6b295007a4: partially holds, 7/10 hits, mean residual +1.25pp. A is reference-only and is not submitted for repeated review. C and the released T queue continue under their existing authorization. All A8 checkpoints are retained under 204ad0ae; the earlier delete-after-audit note in individual frozen result files is superseded. Report when the workspace approaches 900 GiB.

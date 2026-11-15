# A8 group C: five complete endpoints for independent review

All 5 Qwen2.5-1.5B-Instruct × GSM8K seed 17 endpoints are complete, with 6,595 raw outputs. Full finetuning on tangzhice H100!, greedy, exploratory, outside H0–H3. Frozen numerical predictions remain 5e1f9128; runtime source accepted ff567d06. T completion is not a release gate for this packet.

| Cell | P,K,E | Num examples | global_step | Correct | Accuracy | Frozen prediction | Capped | Loops | Normal correct/n |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| C01 | 512,4,2 | 2048 | 512 | 900/1319 | 68.234% | 66.869% | 0.99% | 10 | 900/1306 |
| C02 | 2048,2,2 | 4096 | 1024 | 938/1319 | 71.114% | 69.282% | 0.38% | 4 | 938/1314 |
| C03 | 4096,1,1 | 4096 | 512 | 905/1319 | 68.613% | 72.921% | 0.99% | 10 | 905/1306 |
| C04 | 4096,1,4 | 4096 | 2048 | 894/1319 | 67.779% | 68.019% | 0.38% | 5 | 894/1314 |
| C05 | 4096,2,2 | 8192 | 2048 | 938/1319 | 71.114% | 70.508% | 0.53% | 8 | 938/1312 |

ENDPOINTS.json binds all raw outputs, labels, inputs, training/model/checkpoint manifests, trainer_state, training.log and evaluation configurations. Every R-2 row count and update count passes. Timestamped prescore records bind each raw-output SHA256 to 5e1f9128. The actual training source stayed 61163c22 for every Modal cell; the reviewed T02 patch was applied only after C05 completion.

Please independently score the five C endpoints and apply frozen A8 §5: hit rate, mean residual, K > 1 RMSE against both alternatives, and E = 2 versus E ≠ 2 subsets. C predictions have a narrow range, so compare alternatives as specified. With all 22 Modal endpoints now complete, also conclude SL-5 and SL-7 using the accepted A/B references. REGISTERED_ANCHORS.json supplies original Qwen Instruct endpoints; ACCEPTED_AB_REFERENCES.json binds the previously accepted groups. No refit, new bootstrap or label change was introduced.

A was accepted at 204ad0ae (partially holds); B at 19af6f32 (holds). Their existing outputs are reference-only and need no repeated result audit. T01–T04 continue under b24f787a/204ad0ae. All A8 checkpoints remain retained under 204ad0ae and 19af6f32; report when the workspace approaches 900 GiB.

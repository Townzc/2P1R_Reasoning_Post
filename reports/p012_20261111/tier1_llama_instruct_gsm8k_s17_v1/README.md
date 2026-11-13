# Tier 1 Llama instruct x gsm8k, seed17

| Cell | Correct / total | Accuracy | Cap rate | Loops | Normal termination accuracy |
|---|---:|---:|---:|---:|---:|
| P | 682/1319 | 51.71% | 0.45% | 5 | 51.94% (682/1313) |
| K8 | 604/1319 | 45.79% | 0.76% | 8 | 46.14% (604/1309) |
| R | 474/1319 | 35.94% | 0.30% | 4 | 36.05% (474/1315) |
| K4 | 669/1319 | 50.72% | 1.59% | 20 | 51.54% (669/1298) |
| L | 621/1319 | 47.08% | 0.45% | 6 | 47.30% (621/1313) |

All original raw outputs, labels, per-response termination flags, training logs and checkpoint hashes are in the per-cell ZIPs. Same accepted full-finetuning and evaluation paths as the Qwen grid, using the frozen Llama-family template and C6 data. Normal-only accuracy has different denominators across cells. Built with Llama.

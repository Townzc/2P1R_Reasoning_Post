# Tier 1 Llama instruct x math, seed17

| Cell | Correct / total | Accuracy | Cap rate | Loops | Normal termination accuracy |
|---|---:|---:|---:|---:|---:|
| P | 1423/5000 | 28.46% | 10.34% | 422 | 31.72% (1422/4483) |
| K8 | 1302/5000 | 26.04% | 11.04% | 425 | 29.27% (1302/4448) |
| R | 956/5000 | 19.12% | 5.58% | 189 | 20.25% (956/4721) |
| K4 | 1332/5000 | 26.64% | 10.56% | 439 | 29.79% (1332/4472) |
| L | 1324/5000 | 26.48% | 13.26% | 511 | 30.53% (1324/4337) |

All original raw outputs, labels, per-response termination flags, training logs and checkpoint hashes are in the per-cell ZIPs. Same accepted full-finetuning and evaluation paths as the Qwen grid, using the frozen Llama-family template and C6 data. Normal-only accuracy has different denominators across cells. Built with Llama.

# Tier 2 qwen instruct x gsm8k, seed29

| Cell | Correct / total | Accuracy | Cap rate | Loops | Normal termination accuracy | First-box accuracy (diagnostic) |
|---|---:|---:|---:|---:|---:|---:|
| P | 939/1319 | 71.19% | 0.68% | 8 | 71.68% (939/1310) | not required |
| K8 | 883/1319 | 66.94% | 0.76% | 8 | 67.46% (883/1309) | not required |
| R | 798/1319 | 60.50% | 0.23% | 3 | 60.64% (798/1316) | not required |
| L | 897/1319 | 68.01% | 0.38% | 4 | 68.26% (897/1314) | not required |

All original raw outputs, labels, per-response termination flags, training logs and checkpoint hashes are in the per-cell ZIPs. Accepted full-finetuning and evaluation paths with the frozen family template and C6 data; one workspace and H100 GPU type per setting and seed. Normal-only accuracy has different denominators across cells.

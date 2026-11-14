# Tier 2 qwen base x gsm8k, seed29

| Cell | Correct / total | Accuracy | Cap rate | Loops | Normal termination accuracy | First-box accuracy (diagnostic) |
|---|---:|---:|---:|---:|---:|---:|
| P | 930/1319 | 70.51% | 0.91% | 12 | 71.16% (930/1307) | not required |
| K8 | 873/1319 | 66.19% | 0.91% | 10 | 66.79% (873/1307) | not required |
| R | 771/1319 | 58.45% | 0.76% | 7 | 58.90% (771/1309) | not required |
| L | 910/1319 | 68.99% | 0.23% | 2 | 69.15% (910/1316) | not required |

All original raw outputs, labels, per-response termination flags, training logs and checkpoint hashes are in the per-cell ZIPs. Accepted full-finetuning and evaluation paths with the frozen family template and C6 data; one workspace and H100 GPU type per setting and seed. Normal-only accuracy has different denominators across cells.

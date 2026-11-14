# Tier 2 qwen instruct x math, seed29

| Cell | Correct / total | Accuracy | Cap rate | Loops | Normal termination accuracy | First-box accuracy (diagnostic) |
|---|---:|---:|---:|---:|---:|---:|
| P | 2103/5000 | 42.06% | 9.74% | 347 | 46.60% (2103/4513) | not required |
| K8 | 2090/5000 | 41.80% | 11.72% | 473 | 47.35% (2090/4414) | not required |
| R | 1698/5000 | 33.96% | 2.00% | 109 | 34.65% (1698/4900) | not required |
| L | 2109/5000 | 42.18% | 8.44% | 336 | 46.07% (2109/4578) | not required |

All original raw outputs, labels, per-response termination flags, training logs and checkpoint hashes are in the per-cell ZIPs. Accepted full-finetuning and evaluation paths with the frozen family template and C6 data; one workspace and H100 GPU type per setting and seed. Normal-only accuracy has different denominators across cells.

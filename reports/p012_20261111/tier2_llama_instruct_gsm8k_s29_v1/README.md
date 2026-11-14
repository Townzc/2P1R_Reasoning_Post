# Tier 2 llama instruct x gsm8k, seed29

| Cell | Correct / total | Accuracy | Cap rate | Loops | Normal termination accuracy |
|---|---:|---:|---:|---:|---:|
| P | 681/1319 | 51.63% | 0.53% | 7 | 51.91% (681/1312) |
| K8 | 586/1319 | 44.43% | 0.61% | 8 | 44.70% (586/1311) |
| R | 494/1319 | 37.45% | 0.45% | 2 | 37.62% (494/1313) |
| L | 624/1319 | 47.31% | 0.68% | 7 | 47.63% (624/1310) |

All original raw outputs, labels, per-response termination flags, training logs and checkpoint hashes are in the per-cell ZIPs. Accepted full-finetuning and evaluation paths with the frozen family template and C6 data; one workspace and H100 GPU type per setting and seed. Normal-only accuracy has different denominators across cells. Built with Llama.

# Tier 2 qwen base x math, seed29

| Cell | Correct / total | Accuracy | Cap rate | Loops | Normal termination accuracy | First-box accuracy (diagnostic) |
|---|---:|---:|---:|---:|---:|---:|
| P | 2106/5000 | 42.12% | 9.80% | 351 | 46.70% (2106/4510) | not required |
| K8 | 2055/5000 | 41.10% | 11.32% | 437 | 46.35% (2055/4434) | not required |
| R | 1661/5000 | 33.22% | 2.48% | 132 | 34.06% (1661/4876) | not required |
| L | 2163/5000 | 43.26% | 14.14% | 608 | 48.19% (2069/4293) | not required |

All original raw outputs, labels, per-response termination flags, training logs and checkpoint hashes are in the per-cell ZIPs. Accepted full-finetuning and evaluation paths with the frozen family template and C6 data; one workspace and H100 GPU type per setting and seed. Normal-only accuracy has different denominators across cells.

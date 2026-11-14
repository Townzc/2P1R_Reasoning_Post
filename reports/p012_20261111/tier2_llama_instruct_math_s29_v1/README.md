# Tier 2 llama instruct x math, seed29

| Cell | Correct / total | Accuracy | Cap rate | Loops | Normal termination accuracy | First-box accuracy (diagnostic) |
|---|---:|---:|---:|---:|---:|---:|
| P | 1370/5000 | 27.40% | 11.26% | 445 | 30.88% (1370/4437) | not required |
| K8 | 1242/5000 | 24.84% | 12.24% | 507 | 28.30% (1242/4388) | not required |
| R | 928/5000 | 18.56% | 6.12% | 174 | 19.77% (928/4694) | not required |
| L | 1284/5000 | 25.68% | 13.70% | 566 | 29.76% (1284/4315) | not required |

All original raw outputs, labels, per-response termination flags, training logs and checkpoint hashes are in the per-cell ZIPs. Accepted full-finetuning and evaluation paths with the frozen family template and C6 data; one workspace and H100 GPU type per setting and seed. Normal-only accuracy has different denominators across cells. Built with Llama.

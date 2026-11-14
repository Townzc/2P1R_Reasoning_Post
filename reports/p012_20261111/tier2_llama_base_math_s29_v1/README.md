# Tier 2 llama base x math, seed29

| Cell | Correct / total | Accuracy | Cap rate | Loops | Normal termination accuracy | First-box accuracy (diagnostic) |
|---|---:|---:|---:|---:|---:|---:|
| P | 332/5000 | 6.64% | 22.78% | 970 | 8.60% (332/3861) | 6.64% |
| K8 | 306/5000 | 6.12% | 24.66% | 1012 | 8.12% (306/3767) | 6.10% |
| R | 196/5000 | 3.92% | 13.88% | 428 | 4.55% (196/4306) | not required |
| L | 204/5000 | 4.08% | 35.44% | 1549 | 6.26% (202/3228) | 4.12% |

All original raw outputs, labels, per-response termination flags, training logs and checkpoint hashes are in the per-cell ZIPs. Accepted full-finetuning and evaluation paths with the frozen family template and C6 data; one workspace and H100 GPU type per setting and seed. Normal-only accuracy has different denominators across cells. Built with Llama.

The corresponding C7 four-shot base baseline is degenerate under this conversation format: see `../c7_llama_baseline4_v1/`. Delta-SFT must be read with its termination failure visible. Main-cell comparisons retain the same initialization, template and evaluation conditions.

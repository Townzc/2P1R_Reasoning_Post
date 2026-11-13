# Tier 1 Llama base x math, seed17

| Cell | Correct / total | Accuracy | Cap rate | Loops | Normal termination accuracy |
|---|---:|---:|---:|---:|---:|
| P | 320/5000 | 6.40% | 25.20% | 1097 | 8.56% (320/3740) |
| K8 | 336/5000 | 6.72% | 23.28% | 993 | 8.76% (336/3836) |
| R | 190/5000 | 3.80% | 13.86% | 529 | 4.39% (189/4307) |
| K4 | 308/5000 | 6.16% | 23.20% | 994 | 8.02% (308/3840) |
| L | 223/5000 | 4.46% | 32.12% | 1419 | 6.57% (223/3394) |

All original raw outputs, labels, per-response termination flags, training logs and checkpoint hashes are in the per-cell ZIPs. Same accepted full-finetuning and evaluation paths as the Qwen grid, using the frozen Llama-family template and C6 data. Normal-only accuracy has different denominators across cells. Built with Llama.

The corresponding C7 four-shot base baseline is degenerate under this conversation format: see `../c7_llama_baseline4_v1/`. Delta-SFT must be read with its termination failure visible. Main-cell comparisons retain the same initialization, template and evaluation conditions.

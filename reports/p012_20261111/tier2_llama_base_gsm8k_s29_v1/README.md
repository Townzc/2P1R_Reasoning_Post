# Tier 2 llama base x gsm8k, seed29

| Cell | Correct / total | Accuracy | Cap rate | Loops | Normal termination accuracy |
|---|---:|---:|---:|---:|---:|
| P | 417/1319 | 31.61% | 0.68% | 9 | 31.83% (417/1310) |
| K8 | 323/1319 | 24.49% | 0.15% | 2 | 24.53% (323/1317) |
| R | 191/1319 | 14.48% | 0.38% | 4 | 14.54% (191/1314) |
| L | 209/1319 | 15.85% | 1.59% | 17 | 16.10% (209/1298) |

All original raw outputs, labels, per-response termination flags, training logs and checkpoint hashes are in the per-cell ZIPs. Accepted full-finetuning and evaluation paths with the frozen family template and C6 data; one workspace and H100 GPU type per setting and seed. Normal-only accuracy has different denominators across cells. Built with Llama.

The corresponding C7 four-shot base baseline is degenerate under this conversation format: see `../c7_llama_baseline4_v1/`. Delta-SFT must be read with its termination failure visible. Main-cell comparisons retain the same initialization, template and evaluation conditions.

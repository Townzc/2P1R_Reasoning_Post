# Tier 1 Llama base x gsm8k, seed17

| Cell | Correct / total | Accuracy | Cap rate | Loops | Normal termination accuracy |
|---|---:|---:|---:|---:|---:|
| P | 405/1319 | 30.71% | 0.15% | 1 | 30.75% (405/1317) |
| K8 | 341/1319 | 25.85% | 0.23% | 3 | 25.91% (341/1316) |
| R | 193/1319 | 14.63% | 0.61% | 6 | 14.72% (193/1311) |
| K4 | 359/1319 | 27.22% | 0.53% | 3 | 27.36% (359/1312) |
| L | 214/1319 | 16.22% | 0.83% | 9 | 16.36% (214/1308) |

All original raw outputs, labels, per-response termination flags, training logs and checkpoint hashes are in the per-cell ZIPs. Same accepted full-finetuning and evaluation paths as the Qwen grid, using the frozen Llama-family template and C6 data. Normal-only accuracy has different denominators across cells. Built with Llama.

The corresponding C7 four-shot base baseline is degenerate under this conversation format: see `../c7_llama_baseline4_v1/`. Delta-SFT must be read with its termination failure visible. Main-cell comparisons retain the same initialization, template and evaluation conditions.
